import os
"""
KCC Recorder — Flask app.

Routes:
  GET  /                       → main page
  GET  /status                 → JSON snapshot for UI polling
  POST /init_dataset           → create LeRobotDataset (one-time per session)
  POST /settings               → update org / repo name / task / times / target
  POST /start_teleop           → idle → teleop
  POST /stop_teleop            → teleop → idle
  POST /start_recording        → idle/teleop → recording
  POST /end_episode            → exit_early during recording
  POST /save                   → review → save_episode
  POST /discard                → review → clear_episode_buffer
  POST /rerecord               → review → re-record this episode
  POST /skip_reset             → reset → recording
  POST /set_episode_count      → manually override episodes_done
  GET  /camera/<name>.mjpg     → MJPEG stream of one camera
  POST /shutdown               → clean exit

Runs on ROG. The Jetson host must be running first.
"""

import threading
import atexit
import io
import logging
import signal
import sys
import time
from dataclasses import asdict
from threading import Lock

import cv2
from flask import Flask, Response, jsonify, render_template, request

from recorder import Recorder, RecorderConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# --- Default config — edit these or override via UI ---
# Load config from config.json (fall back to defaults)
import json as _json
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_cfg = {}
if os.path.exists(_CONFIG_FILE):
    try:
        with open(_CONFIG_FILE, "r") as _f:
            _cfg = _json.loads(_f.read())
        logging.info(f"KCC: loaded config from {_CONFIG_FILE}")
    except Exception as _e:
        logging.warning(f"KCC: config.json error: {_e}, using defaults")

DEFAULT_CONFIG = RecorderConfig(
    remote_ip=_cfg.get("remote_ip", "100.68.160.45"),
    leader_port=_cfg.get("leader_port", "COM4"),
    robot_id=_cfg.get("robot_id", "my_kiwi"),
    leader_id=_cfg.get("leader_id", "my_leader"),
    fps=_cfg.get("fps", 30),
    episode_time_sec=_cfg.get("episode_time_sec", 3600),
    reset_time_sec=_cfg.get("reset_time_sec", 0),
    target_episodes=_cfg.get("target_episodes", 50),
    hf_org=_cfg.get("hf_org", "QianGroup"),
    hf_repo_name=_cfg.get("hf_repo_name", "lekiwi_test"),
    task_description=_cfg.get("task_description", "Default task"),
    data_dir=_cfg.get("data_dir", r"D:\lerobot_data"),
)

app = Flask(__name__)
recorder = Recorder(DEFAULT_CONFIG)

# Built-in joystick mapper (replaces AntiMicro)
recorder.start()

# Lock to serialize JPEG re-encoding so we don't spawn unbounded encoder load
_encode_lock = Lock()


# ---------------------------------------------------------------------
# Clean shutdown — prevents Windows COM-port lockouts after Ctrl+C
# ---------------------------------------------------------------------
_shutdown_done = False

def _graceful_shutdown(*_args):
    global _shutdown_done
    if _shutdown_done:
        return
    _shutdown_done = True
    logging.info("KCC: shutdown signal received — disconnecting hardware...")
    try:
        recorder.stop()  # joins the worker, runs _cleanup_hardware
        logging.info("KCC: hardware released cleanly")
    except Exception as e:
        logging.error(f"KCC: error during shutdown: {e}")
    sys.exit(0)


# Catches Ctrl+C in the terminal AND Windows close-window
signal.signal(signal.SIGINT, _graceful_shutdown)
try:
    signal.signal(signal.SIGTERM, _graceful_shutdown)
except (AttributeError, ValueError):
    pass  # Windows doesn't always support SIGTERM in the same way
atexit.register(_graceful_shutdown)


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ----------------------------------------------------------------------
# Status
# ----------------------------------------------------------------------
@app.route("/status")
def status():
    return jsonify(asdict(recorder.get_status()))


# ----------------------------------------------------------------------
# Settings & dataset lifecycle
# ----------------------------------------------------------------------
def _apply_settings(data: dict) -> dict:
    """Filter, cast and apply UI settings to the recorder config. Returns what was applied."""
    allowed = {
        "hf_org", "hf_repo_name", "task_description",
        "target_episodes", "episode_time_sec", "reset_time_sec", "fps",
    }
    payload = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        if k in ("target_episodes", "episode_time_sec", "reset_time_sec", "fps"):
            try:
                payload[k] = int(v)
            except (TypeError, ValueError):
                continue
        else:
            payload[k] = str(v)
    recorder.update_settings(**payload)
    return payload


@app.route("/settings", methods=["POST"])
def settings():
    data = request.get_json(force=True) or {}
    return jsonify({"ok": True, "applied": _apply_settings(data)})


@app.route("/init_dataset", methods=["POST"])
def init_dataset():
    data = request.get_json(force=True) or {}
    if data:
        _apply_settings(data)
    ok = recorder.init_dataset()
    return jsonify({"ok": ok, "error": recorder.last_error if not ok else ""})


# ----------------------------------------------------------------------
# Control commands
# ----------------------------------------------------------------------
def _simple(fn):
    fn()
    return jsonify({"ok": True})


@app.route("/start_teleop", methods=["POST"])
def start_teleop():
    return _simple(recorder.cmd_start_teleop)


@app.route("/stop_teleop", methods=["POST"])
def stop_teleop():
    return _simple(recorder.cmd_stop_teleop)


@app.route("/start_recording", methods=["POST"])
def start_recording():
    ok = recorder.cmd_start_recording()
    return jsonify({"ok": ok, "error": recorder.last_error if not ok else ""})


@app.route("/end_episode", methods=["POST"])
def end_episode():
    return _simple(recorder.cmd_end_episode_early)


@app.route("/stop_recording", methods=["POST"])
def stop_recording():
    return _simple(recorder.cmd_stop_recording)


@app.route("/save", methods=["POST"])
def save():
    return _simple(recorder.cmd_save)


@app.route("/discard", methods=["POST"])
def discard():
    return _simple(recorder.cmd_discard)


@app.route("/rerecord", methods=["POST"])
def rerecord():
    return _simple(recorder.cmd_rerecord)


@app.route("/skip_reset", methods=["POST"])
def skip_reset():
    return _simple(recorder.cmd_skip_reset)


@app.route("/set_episode_count", methods=["POST"])
def set_episode_count():
    data = request.get_json(force=True) or {}
    try:
        n = int(data.get("count", -1))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad count"}), 400
    recorder.cmd_set_episode_count(n)
    return jsonify({"ok": True})


@app.route("/set_next_episode", methods=["POST"])
def set_next_episode():
    data = request.get_json(force=True) or {}
    try:
        n = int(data.get("next", -1))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad next"}), 400
    recorder.cmd_set_next_episode(n)
    return jsonify({"ok": True})


@app.route("/reconnect", methods=["POST"])
def reconnect():
    recorder.cmd_reconnect()
    return jsonify({"ok": True, "state": recorder.state.value})


@app.route("/shutdown", methods=["POST"])
def shutdown():
    recorder.stop()
    return jsonify({"ok": True})





# KCC-PROD: Health check endpoint (Ch.8 — Detecting Faults)
@app.route("/health")
def health():
    """Production health check. Returns system status for monitoring."""
    import shutil as _sh
    try:
        disk = _sh.disk_usage(r"D:\lerobot_data")
        disk_free_gb = round(disk.free / (1024**3), 2)
        disk_pct = round(disk.used / disk.total * 100, 1)
    except Exception:
        disk_free_gb = -1
        disk_pct = -1

    state = recorder.state.value
    robot_ok = recorder.robot is not None
    leader_ok = recorder.leader_arm is not None
    dataset_ok = recorder.dataset_initialized
    uptime = round(time.time() - getattr(recorder, '_session_start', time.time()), 1)

    healthy = state not in ("error", "disconnected") and robot_ok and leader_ok
    return jsonify({
        "healthy": healthy,
        "state": state,
        "robot_connected": robot_ok,
        "leader_connected": leader_ok,
        "dataset_initialized": dataset_ok,
        "episodes_done": recorder.episodes_done,
        "disk_free_gb": disk_free_gb,
        "disk_used_pct": disk_pct,
        "uptime_sec": uptime,
        "last_error": recorder.last_error,
    })


# KCC-PROD: Audit log viewer
@app.route("/audit")
def audit():
    """View the persistent audit log."""
    from pathlib import Path
    audit_file = Path(r"D:\lerobot_data") / ".kcc_audit.log"
    if audit_file.exists():
        lines = audit_file.read_text().strip().split("\n")[-100:]  # last 100 entries
        return jsonify({"ok": True, "entries": lines})
    return jsonify({"ok": True, "entries": []})

# ── KCC14-v7: Telemetry endpoint for live arm visualization ──



@app.route("/joystick", methods=["POST"])
def joystick():
    """Simulate keyboard presses from joystick axes."""
    global _joy_pressed
    _joy_init()
    if _joy_kb is None:
        return jsonify({"ok": False, "error": "pynput not available"})

    data = request.get_json(force=True) or {}
    axes = data.get("axes", [0, 0, 0, 0, 0, 0])
    mapping = data.get("axis_map", {})
    deadzone = data.get("deadzone", 0.15)

    # Determine which keys should be pressed
    should_press = set()
    for axis_idx_str, keys in mapping.items():
        axis_idx = int(axis_idx_str)
        if axis_idx >= len(axes):
            continue
        val = axes[axis_idx]
        neg_key = keys.get("neg", "")
        pos_key = keys.get("pos", "")
        if val < -deadzone and neg_key:
            should_press.add(neg_key)
        elif val > deadzone and pos_key:
            should_press.add(pos_key)

    # Release keys that should no longer be pressed
    for key in _joy_pressed - should_press:
        try:
            _joy_kb.release(key)
        except Exception:
            pass

    # Press keys that should be pressed
    for key in should_press - _joy_pressed:
        try:
            _joy_kb.press(key)
        except Exception:
            pass

    _joy_pressed = should_press
    return jsonify({"ok": True})


@app.route("/joystick/config", methods=["GET", "POST"])
def joystick_config():
    if request.method == "GET":
        return jsonify({"ok": True, "config": joy_mapper.get_config()})
    data = request.get_json(force=True) or {}
    if "axes" in data:
        joy_mapper.mapping["axes"] = data["axes"]
    if "deadzone" in data:
        joy_mapper.mapping["deadzone"] = data["deadzone"]
    if "buttons" in data:
        joy_mapper.mapping["buttons"] = data["buttons"]
    joy_mapper.save_config()
    return jsonify({"ok": True})


# Base speed control
_base_speed = 1.0

@app.route("/speed", methods=["GET", "POST"])
def speed():
    global _base_speed
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        if "delta" in data:
            _base_speed = max(0.3, min(2.0, _base_speed + data["delta"]))
        elif "value" in data:
            _base_speed = max(0.3, min(2.0, data["value"]))
        return jsonify({"ok": True, "speed": _base_speed})
    return jsonify({"ok": True, "speed": _base_speed})

@app.route("/telemetry")
def telemetry():
    """Return current joint state for live 3D arm visualization."""
    try:
        data = getattr(recorder, '_last_telemetry', None)
        if data and any(v != 0 for v in data):
            return jsonify({"ok": True, "state": data})
        return jsonify({"ok": False})
    except Exception:
        return jsonify({"ok": False})

# ── Dataset stats endpoint ──

def _dataset_root():
    """Local path of the active dataset."""
    from pathlib import Path
    return Path(recorder.config.data_dir) / recorder.config.hf_org / recorder.config.hf_repo_name


def _action_to_matrix(series):
    """Convert a pandas Series of action values to a 2D numpy array (N, D).

    LeRobot v3 stores 'action' as one column containing per-frame array values.
    This handles numpy arrays, lists, and tuples uniformly.
    """
    import numpy as np
    return np.asarray([np.asarray(a, dtype=float) for a in series.values])


def _compute_episode_stats(actions):
    """Compute arm range, wheel activity, and entanglement E from an actions matrix.

    actions: ndarray of shape (N, D) where D >= 9.
             cols 0..5 = arm joints, cols 6..8 = wheel velocities.
    Returns a dict with the three metrics. Returns Nones if shape is wrong.
    """
    import numpy as np
    if actions.ndim != 2 or actions.shape[1] < 9 or len(actions) < 2:
        return {"arm_range": None, "wheel_range": None,
                "wheels_still": None, "entanglement": None}

    arm = actions[:, :6]
    wheels = actions[:, 6:9]

    arm_range = f"{arm.min():.1f} to {arm.max():.1f}"
    wmax = float(np.abs(wheels).max())
    wheel_range = f"max={wmax:.4f}"
    wheels_still = wmax < 0.01

    # Entanglement E = fraction of frames where arm AND wheels are both active.
    # arm "moving" = any joint changed by >0.5 units between consecutive frames.
    # wheel "moving" = any wheel velocity magnitude >0.01.
    arm_moving = np.any(np.abs(np.diff(arm, axis=0)) > 0.5, axis=1)
    wheel_moving = np.any(np.abs(wheels[1:]) > 0.01, axis=1)
    E = float(np.mean(arm_moving & wheel_moving))

    return {
        "arm_range": arm_range,
        "wheel_range": wheel_range,
        "wheels_still": bool(wheels_still),
        "entanglement": round(E, 4),
    }


@app.route("/dataset_stats")
def dataset_stats():
    """Return dataset statistics — works fully offline from local files."""
    try:
        if not recorder.dataset_initialized:
            return jsonify({"ok": False, "error": "no dataset"})
        
        import numpy as np
        from pathlib import Path
        
        data_dir = Path(recorder.config.data_dir)
        repo_id = f"{recorder.config.hf_org}/{recorder.config.hf_repo_name}"
        root = data_dir / repo_id
        
        result = {"ok": True}
        
        # Episode count
        result["total_episodes"] = recorder.episodes_done
        
        # Read parquet files
        parquet_dir = root / "data"
        parquet_files = sorted(parquet_dir.glob("**/*.parquet")) if parquet_dir.exists() else []
        result["parquet_ok"] = len(parquet_files) > 0
        
        # Video files
        video_dir = root / "videos"
        video_files = sorted(video_dir.glob("**/*.mp4")) if video_dir.exists() else []
        result["videos_ok"] = len(video_files) > 0
        
        total_frames = 0
        all_actions = []
        last_ep_frames = 0
        
        if parquet_files:
            try:
                import pandas as pd
                for pf in parquet_files:
                    try:
                        df = pd.read_parquet(pf)
                        total_frames += len(df)
                        last_ep_frames = len(df)
                        
                        # Collect actions — LeRobot v3 stores as array column
                        if 'action' in df.columns:
                            raw = df['action'].values
                            actions = np.stack([np.array(a) for a in raw])
                            all_actions.append(actions)
                        if 'observation.state' in df.columns:
                            raw_s = df['observation.state'].values
                            all_states = np.stack([np.array(a) for a in raw_s])
                    except Exception as pe:
                        logging.warning(f"Error reading {pf}: {pe}")
            except ImportError:
                pass
        
        result["total_frames"] = total_frames
        result["last_ep_duration"] = round(last_ep_frames / max(recorder.config.fps, 1), 1) if last_ep_frames > 0 else None
        
        # Arm range + wheel activity + entanglement from actions
        if all_actions:
            try:
                actions = np.concatenate(all_actions, axis=0)
                if actions.shape[1] >= 9:
                    arm = actions[:, :6]
                    wheels = actions[:, 6:]
                    
                    # Arm range
                    arm_min = arm.min(axis=0)
                    arm_max = arm.max(axis=0)
                    result["arm_range"] = f"{arm_min.min():.1f} to {arm_max.max():.1f}"
                    
                    # Wheels
                    wheel_activity = np.abs(wheels).max()
                    result["wheel_range"] = f"max={wheel_activity:.2f}"
                    result["wheels_still"] = float(wheel_activity) < 0.5
                    
                    # Entanglement E
                    arm_vel = np.abs(np.diff(arm, axis=0))
                    base_vel = np.abs(wheels[1:])
                    arm_on = arm_vel.max(axis=1) > 0.5
                    base_on = base_vel.max(axis=1) > 0.1
                    entangled = (arm_on & base_on).sum()
                    total = len(arm_on)
                    E = round(float(entangled / total), 4) if total > 0 else 0.0
                    result["entanglement"] = E
                elif actions.shape[1] >= 6:
                    arm = actions[:, :6]
                    arm_min = arm.min(axis=0)
                    arm_max = arm.max(axis=0)
                    result["arm_range"] = f"{arm_min.min():.1f} to {arm_max.max():.1f}"
                    result["entanglement"] = 0.0
                    result["wheels_still"] = True
                    result["wheel_range"] = "N/A"
            except Exception as ae:
                logging.warning(f"Action analysis error: {ae}")
        
        # Last episode actions for chart
        if all_actions and len(all_actions[-1]) > 0:
            last = all_actions[-1]
            result["last_ep_actions"] = last.tolist()
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"dataset_stats error: {e}")
        return jsonify({"ok": False, "error": str(e)})


def dataset_stats():
    """Return live metrics about the current dataset on disk.

    Reads:
      - meta/info.json for canonical episode/frame counts and fps
      - all parquet shards under data/**/ for actions (globbed, not hardcoded)
      - all camera dirs under videos/ for presence and size

    Last-episode metrics (arm range, wheel activity, entanglement E) are computed
    from the parquet shard that contains max(episode_index), which may be any
    file in v3 layout — not necessarily file-000.parquet.
    """
    import json
    import numpy as np
    from pathlib import Path

    result = {"ok": False}

    try:
        root = _dataset_root()
        info_path = root / "meta" / "info.json"
        if not info_path.exists():
            result["error"] = "dataset not initialized (no meta/info.json)"
            return jsonify(result)

        meta = json.loads(info_path.read_text())
        result["total_episodes"] = int(meta.get("total_episodes", 0) or 0)
        result["total_frames"] = int(meta.get("total_frames", 0) or 0)
        result["fps"] = int(meta.get("fps", 30) or 30)

        # Parquet inventory — all shards, not just chunk-000/file-000
        data_dir = root / "data"
        parquet_files = sorted(data_dir.rglob("*.parquet")) if data_dir.exists() else []
        result["parquet_ok"] = len(parquet_files) > 0
        result["parquet_files"] = len(parquet_files)

        # Video inventory — same multi-shard treatment
        vid_base = root / "videos"
        vid_ok = True
        vid_sizes = []
        if vid_base.exists():
            for cam_dir in sorted(vid_base.iterdir()):
                if not (cam_dir.is_dir() and cam_dir.name.startswith("observation")):
                    continue
                vids = list(cam_dir.rglob("*.mp4"))
                if not vids:
                    vid_ok = False
                    continue
                last_vid = max(vids, key=lambda p: p.stat().st_mtime)
                sz_mb = last_vid.stat().st_size / (1024 * 1024)
                cam_label = cam_dir.name.split(".")[-1]
                vid_sizes.append(f"{cam_label}:{sz_mb:.1f}MB")
        else:
            vid_ok = False
        result["videos_ok"] = vid_ok
        result["video_sizes"] = " ".join(vid_sizes)

        # Per-episode metrics from the parquet shard containing the latest episode.
        result["last_ep_frames"] = None
        result["last_ep_duration"] = None
        result["arm_range"] = None
        result["wheel_range"] = None
        result["wheels_still"] = None
        result["entanglement"] = None
        result["last_ep_actions"] = []

        if parquet_files:
            import pandas as pd

            # Find which shard holds the latest episode. Scan shards in reverse
            # mtime order so we usually hit it on the first try.
            #
            # Robustness: LeRobot may be actively writing to a parquet file when
            # we read (e.g. during save_episode, or via streaming encoding).
            # Mid-write reads raise pyarrow.lib.ArrowInvalid ("Parquet magic
            # bytes not found in footer"). We skip such files quietly — the
            # next monitor tick will catch them once the write completes.
            target_df = None
            target_ep = -1
            for pf in sorted(parquet_files, key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    df = pd.read_parquet(pf, columns=["episode_index"])
                except Exception:
                    continue  # file being written, corrupted, or has different schema
                if "episode_index" not in df.columns or len(df) == 0:
                    continue
                shard_max = int(df["episode_index"].max())
                if shard_max > target_ep:
                    target_ep = shard_max
                    # Re-read the full shard. Same try/except — if it fails
                    # mid-read, leave target_df None and the caller renders
                    # the "no last episode" path.
                    try:
                        target_df = pd.read_parquet(pf)
                    except Exception:
                        target_df = None
                    break  # mtime-latest is almost always the winner

            if target_df is not None and "action" in target_df.columns:
                ep_df = target_df[target_df["episode_index"] == target_ep]
                if len(ep_df) > 0:
                    try:
                        actions = _action_to_matrix(ep_df["action"])
                        result["last_ep_frames"] = len(ep_df)
                        result["last_ep_duration"] = round(len(ep_df) / max(result["fps"], 1), 2)
                        result.update(_compute_episode_stats(actions))
                        # Down-sample actions for the UI chart (~150 points max)
                        step = max(1, len(actions) // 150)
                        result["last_ep_actions"] = actions[::step].tolist()
                    except Exception as ex:
                        # Action column schema can vary between LeRobot versions.
                        # Don't fail the whole endpoint over one bad shard.
                        logging.warning(f"last-episode stats failed: {ex}")

        result["ok"] = True
    except Exception as ex:
        result["error"] = str(ex)
        import traceback as _tb
        logging.error(_tb.format_exc())

    return jsonify(result)


# ----------------------------------------------------------------------
# MJPEG camera streaming
# ----------------------------------------------------------------------
def _placeholder_frame(text: str) -> bytes:
    """Generate a tiny placeholder JPEG when no frame is available yet."""
    import numpy as np
    img = np.full((240, 320, 3), 229, dtype=np.uint8)  # cream bg
    cv2.putText(img, text, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 60, 60), 2)
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buf.tobytes() if ok else b""


# KCC1: shared JPEG cache - ONE encoder thread serves all streams
_latest_jpeg = {}
_jpeg_encoder_running = False

# KCC2: recording buffer + looping review playback
_recording_buffer = {}
_buffer_idx = {}
_last_state = None
_MAX_BUFFER_FRAMES = 600

def _jpeg_encoder_loop():
    global _last_state
    while _jpeg_encoder_running:
        try:
            state = recorder.state.value
            if state == "recording" and _last_state != "recording":
                _recording_buffer.clear()
                _buffer_idx.clear()
            elif state == "review" and _last_state != "review":
                _buffer_idx.clear()
            _last_state = state

            if state == "review":
                if _recording_buffer:
                    for cam_name, jpegs in list(_recording_buffer.items()):
                        if not jpegs:
                            continue
                        idx = _buffer_idx.get(cam_name, 0)
                        _latest_jpeg[cam_name] = jpegs[idx % len(jpegs)]
                        _buffer_idx[cam_name] = idx + 1
                else:
                    src_frames = recorder.last_recorded_frames or {}
                    for cam_name, fr in src_frames.items():
                        if fr is None:
                            continue
                        fr2 = fr.copy()
                        h, w = fr2.shape[:2]
                        bh = max(28, h // 14)
                        cv2.rectangle(fr2, (0, 0), (w, bh), (58, 85, 196), -1)
                        fs = max(0.55, min(1.0, w / 900.0))
                        txt = "PREVIEW (static) - save / discard"
                        (tw, _th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)
                        cv2.putText(fr2, txt, (max(8, (w-tw)//2), int(bh*0.7)),
                                    cv2.FONT_HERSHEY_SIMPLEX, fs, (255,255,255), 2, cv2.LINE_AA)
                        ok, buf = cv2.imencode(".jpg", fr2, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                        if ok:
                            _latest_jpeg[cam_name] = buf.tobytes()
            else:
                if recorder.robot is not None:
                    frames = recorder.robot.last_frames or {}
                    for cam_name, fr in frames.items():
                        if fr is None:
                            continue
                        ok, buf = cv2.imencode(".jpg", fr, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                        if ok:
                            jpeg_bytes = buf.tobytes()
                            _latest_jpeg[cam_name] = jpeg_bytes
                            if state == "recording":
                                bl = _recording_buffer.setdefault(cam_name, [])
                                bl.append(jpeg_bytes)
                                if len(bl) > _MAX_BUFFER_FRAMES:
                                    bl.pop(0)
        except Exception:
            pass
        time.sleep(1.0 / 25.0)

def _ensure_encoder():
    global _jpeg_encoder_running
    if not _jpeg_encoder_running:
        _jpeg_encoder_running = True
        threading.Thread(target=_jpeg_encoder_loop, daemon=True).start()


def _frame_generator(camera_name: str, target_fps: int = 15):
    """KCC1: yields cached JPEGs from background encoder."""
    _ensure_encoder()
    boundary = b"--frame"
    interval = 1.0 / max(target_fps, 1)
    while True:
        t0 = time.perf_counter()
        jpeg = _latest_jpeg.get(camera_name)
        if not jpeg:
            in_review = recorder.state.value == "review"
            label = f"{camera_name}: preview" if in_review else f"{camera_name}: waiting..."
            jpeg = _placeholder_frame(label)
        yield (
            boundary + b"\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
            + jpeg + b"\r\n"
        )
        elapsed = time.perf_counter() - t0
        if elapsed < interval:
            time.sleep(interval - elapsed)



@app.route("/camera/<name>.mjpg")
def camera_stream(name):
    return Response(
        _frame_generator(name),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/preview/<name>.jpg")
def preview(name):
    """Static JPEG of the final frame of the most recently recorded episode.
    Used during review state to show what was captured.
    """
    frame = recorder.last_recorded_frames.get(name)
    if frame is None:
        # Fall through to placeholder if no preview is available
        return Response(_placeholder_frame(f"{name}: no preview"), mimetype="image/jpeg")
    with _encode_lock:
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return Response(_placeholder_frame(f"{name}: encode err"), mimetype="image/jpeg")
    return Response(buf.tobytes(), mimetype="image/jpeg")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # threaded=True is essential — MJPEG streams hold long-lived connections,
    # and we need /status + /control to remain responsive during a stream.
    import argparse
    parser = argparse.ArgumentParser(description="KCC Recorder — LeRobot recording dashboard")
    parser.add_argument("--host", default=_cfg.get("host", "0.0.0.0"), help="Bind address")
    parser.add_argument("--port", type=int, default=_cfg.get("port", 5000), help="Port number")
    parser.add_argument("--threads", type=int, default=_cfg.get("threads", 16), help="Server threads")
    args = parser.parse_args()
    print(f"\n  KCC Recorder running at http://{args.host}:{args.port}")
    print(f"  Config: {_CONFIG_FILE}")
    print(f"  Robot: {DEFAULT_CONFIG.remote_ip} | Leader: {DEFAULT_CONFIG.leader_port}")
    print(f"  Data: {_cfg.get('data_dir', 'D:\\lerobot_data')}\n")
    from waitress import serve; serve(app, host=args.host, port=args.port, threads=args.threads)
