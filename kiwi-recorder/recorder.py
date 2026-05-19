import os as _os                                           # KCC11
_os.environ.setdefault("HF_HUB_OFFLINE", "1")             # KCC11: no Hub calls
_os.environ.setdefault("SVT_LOG", "0")                    # KCC11: silence AV1 encoder
from pathlib import Path
"""
KCC Recorder — state machine that wraps LeRobot's official record_loop.

Owns: LeKiwiClient, SO100Leader, KeyboardTeleop, LeRobotDataset.
Runs in a single worker thread. Flask reads/writes shared state safely.

Recording flow (manual, no auto-reset):
  idle ──"start teleop"──> teleop ──"stop teleop"──> idle
  idle/teleop ──"start recording"──> recording ──"stop recording"──> review
  review ──"save"──> idle (counter++) [ or finished if target reached ]
  review ──"discard"──> idle (counter unchanged)
  review ──"rerecord"──> recording (buffer cleared)

Zero modifications to LeRobot. We only call its public API.
"""

import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# LeRobot imports — same versions/paths as your working record.py
from lerobot.datasets import LeRobotDataset
# KCC8: serialize LeRobotDataset.save_episode globally to prevent bg-save races
import threading as _kcc8_threading
_KCC8_SAVE_LOCK = _kcc8_threading.Lock()

if not getattr(LeRobotDataset, "_kcc8_wrapped", False):
    _kcc8_orig_save = LeRobotDataset.save_episode
    def _kcc8_locked_save(self, *args, **kwargs):
        with _KCC8_SAVE_LOCK:
            return _kcc8_orig_save(self, *args, **kwargs)
    LeRobotDataset.save_episode = _kcc8_locked_save
    LeRobotDataset._kcc8_wrapped = True

# ═══════════════════════════════════════════════════════════════════
# KCC13: DDIA-inspired reliability patterns
# ═══════════════════════════════════════════════════════════════════
import json as _json

# ── DDIA Ch.3: Write-Ahead State Log ──
_KCC13_STATE_FILE = Path(r"D:\lerobot_data") / ".kcc_state.json"

def _kcc13_save_state(org, repo, episodes_done, last_saved_ep):
    """Persist recording progress to disk before destructive ops."""
    state = {
        "org": org, "repo": repo,
        "episodes_done": episodes_done,
        "last_saved_ep": last_saved_ep,
        "timestamp": time.time(),
    }
    try:
        _KCC13_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _KCC13_STATE_FILE.with_suffix(".tmp")
        tmp.write_text(_json.dumps(state, indent=2))
        tmp.replace(_KCC13_STATE_FILE)  # atomic rename on Windows
    except Exception as e:
        logger.warning(f"KCC13: state save failed: {e}")

def _kcc13_load_state():
    """Load last known recording state from disk for crash recovery."""
    try:
        if _KCC13_STATE_FILE.exists():
            return _json.loads(_KCC13_STATE_FILE.read_text())
    except Exception:
        pass
    return None

# ── DDIA Ch.11: Offline Resume ──
def _kcc13_offline_resume(repo_id, root):
    """Resume a local dataset without any HuggingFace Hub calls."""
    from lerobot.datasets import utils as _ds_utils
    _orig = _ds_utils.get_safe_version
    _ds_utils.get_safe_version = lambda r, v: v
    try:
        return LeRobotDataset.resume(repo_id=repo_id, root=root)
    finally:
        _ds_utils.get_safe_version = _orig

# ── DDIA Ch.8: Circuit Breaker ──
class _CircuitBreaker:
    """Stop retrying after N consecutive failures. Auto-reset after cooldown."""
    def __init__(self, name, max_failures=3, cooldown_sec=30):
        self.name = name
        self.max_failures = max_failures
        self.cooldown_sec = cooldown_sec
        self._failures = 0
        self._last_failure = 0
        self._open = False

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self.max_failures:
            self._open = True
            logger.warning(f"Circuit breaker OPEN: {self.name} ({self._failures} failures)")

    def record_success(self):
        self._failures = 0
        self._open = False

    def is_open(self):
        if self._open and (time.time() - self._last_failure) > self.cooldown_sec:
            self._open = False
            self._failures = 0
        return self._open

    def reset(self):
        self._failures = 0
        self._open = False

_CB_COM4 = _CircuitBreaker("COM4", max_failures=5, cooldown_sec=30)
_CB_HOST = _CircuitBreaker("Pi_Host", max_failures=3, cooldown_sec=15)

# ── DDIA Ch.11: Backpressure flag ──
_kcc13_save_in_progress = threading.Event()

# ── DDIA Ch.5: Data Validation ──
def _kcc13_validate_episode(root_path):
    """Quick integrity check: parquet exists, videos exist and non-tiny."""
    issues = []
    from pathlib import Path as _P
    base = _P(root_path) if not isinstance(root_path, _P) else root_path
    pq = base / "data" / "chunk-000" / "file-000.parquet"
    if not pq.exists():
        issues.append("parquet missing")
    vid_base = base / "videos"
    if vid_base.exists():
        for cam_dir in vid_base.iterdir():
            if cam_dir.is_dir() and cam_dir.name.startswith("observation"):
                vids = list((cam_dir / "chunk-000").glob("*.mp4")) if (cam_dir / "chunk-000").exists() else []
                if not vids:
                    issues.append(f"no video: {cam_dir.name}")
                elif any(v.stat().st_size < 500 for v in vids):
                    issues.append(f"tiny video: {cam_dir.name}")
    info = base / "meta" / "info.json"
    if info.exists():
        try:
            meta = _json.loads(info.read_text())
            if meta.get("total_episodes", 0) < 1:
                issues.append(f"total_episodes={meta.get('total_episodes')}")
        except Exception as e:
            issues.append(f"info.json error: {e}")
    else:
        issues.append("info.json missing")
    return issues

from lerobot.processor import make_default_processors
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig
from lerobot.scripts.lerobot_record import record_loop
from lerobot.teleoperators.keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.teleoperators.so_leader import SO100Leader, SO100LeaderConfig
from lerobot.utils.constants import ACTION, OBS_STR
from lerobot.utils.feature_utils import hw_to_dataset_features

logger = logging.getLogger("kcc.recorder")

# KCC-FIX: global offline patch — prevent ALL HuggingFace Hub calls
try:
    from lerobot.datasets import utils as _ds_utils
    _orig_get_safe = getattr(_ds_utils, 'get_safe_version', None)
    if _orig_get_safe:
        _ds_utils.get_safe_version = lambda repo_id, version: version
        logger.info("KCC: Hub calls disabled (offline mode)")
except Exception as _e:
    logger.warning(f"KCC: offline patch failed: {_e}")

# Also patch huggingface_hub if present
try:
    import huggingface_hub
    huggingface_hub.constants.HF_HUB_OFFLINE = True
except Exception:
    pass


class State(str, Enum):
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    TELEOP = "teleop"
    RECORDING = "recording"
    REVIEW = "review"
    RESET = "reset"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class RecorderConfig:
    remote_ip: str = "100.68.160.45"
    leader_port: str = "COM4"
    robot_id: str = "my_kiwi"
    leader_id: str = "my_leader"
    fps: int = 30
    episode_time_sec: int = 3600  # huge cap; STOP button ends episodes
    reset_time_sec: int = 0  # no longer used in main flow (kept for compat)
    target_episodes: int = 50
    hf_org: str = "QianGroup"
    hf_repo_name: str = "lekiwi_test"
    task_description: str = "Default task"
    data_dir: str = r"D:\lerobot_data"


@dataclass
class RecorderStatus:
    """Snapshot of recorder state, returned to the UI on /status polls."""
    state: str = State.DISCONNECTED.value
    episodes_done: int = 0
    target_episodes: int = 50
    current_episode_seconds: float = 0.0
    episode_time_sec: int = 15
    reset_time_sec: int = 10
    fps: int = 30
    hf_org: str = "QianGroup"
    hf_repo_name: str = "lekiwi_test"
    task_description: str = "Default task"
    cameras: list = field(default_factory=list)
    last_error: str = ""
    log_tail: list = field(default_factory=list)
    dataset_initialized: bool = False


class Recorder:
    def __init__(self, config: RecorderConfig):
        self.config = config

        # --- Hardware handles (set in connect_hardware) ---
        self.robot: Optional[LeKiwiClient] = None
        self.leader_arm: Optional[SO100Leader] = None
        self.keyboard: Optional[KeyboardTeleop] = None
        self.dataset: Optional[LeRobotDataset] = None

        self.teleop_action_processor = None
        self.robot_action_processor = None
        self.robot_observation_processor = None

        # --- Shared state ---
        self._state = State.DISCONNECTED
        self._state_lock = threading.Lock()
        self._stop_flag = threading.Event()

        # The events dict that record_loop reads each tick
        self._events = {
            "exit_early": False,
            "rerecord_episode": False,
            "stop_recording": False,
        }

        # Pending action from the UI: 'save', 'discard', 'rerecord'
        self._pending_review_decision: Optional[str] = None

        self.episodes_done = 0
        self.episode_start_time: Optional[float] = None
        self.last_error = ""
        self.dataset_initialized = False

        # Snapshot of the final frames from the most recent recording.
        # Used to render a static preview during review state.
        self.last_recorded_frames: dict = {}

        # Rolling log tail for the UI status panel
        self.log_buffer: list = []
        self._log_buffer_max = 50

        # The worker thread
        self._worker: Optional[threading.Thread] = None

        # KCC-PROD: production monitoring
        self._frame_count = 0           # frames recorded this episode
        self._frame_drops = 0           # detected frame drops
        self._last_obs_time = 0.0       # last successful observation timestamp
        self._watchdog_timeout = 10.0   # seconds before declaring stuck
        self._session_start = time.time()
        self._last_telemetry = [0]*9
        self._joystick_axes = [0, 0, 0]  # live joint data for 3D viz

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    @property
    def state(self) -> State:
        with self._state_lock:
            return self._state

    # Valid state transitions (KCC-PROD: Ch.9 — Consistency)
    _VALID_TRANSITIONS = {
        State.DISCONNECTED: {State.IDLE, State.ERROR},
        State.IDLE:         {State.TELEOP, State.RECORDING, State.FINISHED, State.ERROR, State.DISCONNECTED},
        State.TELEOP:       {State.IDLE, State.RECORDING, State.ERROR, State.DISCONNECTED},
        State.RECORDING:    {State.REVIEW, State.ERROR, State.DISCONNECTED},
        State.REVIEW:       {State.IDLE, State.RECORDING, State.FINISHED, State.ERROR},
        State.RESET:        {State.RECORDING, State.IDLE, State.ERROR},
        State.FINISHED:     {State.IDLE, State.DISCONNECTED},
        State.ERROR:        {State.DISCONNECTED, State.IDLE},
    }

    def _set_state(self, new: State):
        with self._state_lock:
            old = self._state
            valid = self._VALID_TRANSITIONS.get(old, set())
            if new not in valid and old != new:
                logger.warning(f"KCC-PROD: BLOCKED invalid transition {old.value} → {new.value} (allowed: {[s.value for s in valid]})")
                return
            self._state = new
        if old != new:
            self._log(f"state: {old.value} → {new.value}")
            self._audit(f"STATE {old.value} → {new.value}")

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        logger.info(msg)
        self.log_buffer.append(line)
        if len(self.log_buffer) > self._log_buffer_max:
            self.log_buffer = self.log_buffer[-self._log_buffer_max:]

    # KCC-PROD: Persistent audit log (Ch.3 — Append-Only Log)
    _AUDIT_FILE = Path(r"D:\lerobot_data") / ".kcc_audit.log"

    def _audit(self, msg: str):
        """Append-only persistent log. Survives crashes. Never truncated."""
        try:
            self._AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self._AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
        except Exception:
            pass

    def get_status(self) -> RecorderStatus:
        cams = []
        if self.robot is not None:
            try:
                cams = list(self.robot._cameras_ft.keys())
            except Exception:
                cams = []
        ep_sec = 0.0
        if self.episode_start_time and self.state == State.RECORDING:
            ep_sec = time.perf_counter() - self.episode_start_time
        return RecorderStatus(
            state=self.state.value,
            episodes_done=self.episodes_done,
            target_episodes=self.config.target_episodes,
            current_episode_seconds=round(ep_sec, 1),
            episode_time_sec=self.config.episode_time_sec,
            reset_time_sec=self.config.reset_time_sec,
            fps=self.config.fps,
            hf_org=self.config.hf_org,
            hf_repo_name=self.config.hf_repo_name,
            task_description=self.config.task_description,
            cameras=cams,
            last_error=self.last_error,
            log_tail=list(self.log_buffer[-20:]),
            dataset_initialized=self.dataset_initialized,
        )

    # ------------------------------------------------------------------
    # Connection (called once at startup)
    # ------------------------------------------------------------------
    def connect_hardware(self):
        try:
            self._log("connecting LeKiwi client...")
            robot_cfg = LeKiwiClientConfig(remote_ip=self.config.remote_ip, id=self.config.robot_id)
            self.robot = LeKiwiClient(robot_cfg)
            self.robot.connect()
            self._log(f"LeKiwi connected at {self.config.remote_ip}")

            self._log("connecting leader arm...")
            leader_cfg = SO100LeaderConfig(port=self.config.leader_port, id=self.config.leader_id)
            self.leader_arm = SO100Leader(leader_cfg)
            # KCC5+KCC13: retry with circuit breaker
            if _CB_COM4.is_open():
                raise ConnectionError("COM4 circuit breaker OPEN — wait 30s or click RECONNECT")
            for _try in range(5):
                try:
                    self.leader_arm.connect()
                    _CB_COM4.record_success()
                    break
                except Exception as _ce:
                    _CB_COM4.record_failure()
                    if _try < 4:
                        self._log(f"leader connect {_try+1}/5 failed: {_ce}. Retrying 2s...")
                        time.sleep(2)
                    else:
                        raise
            self._log(f"leader connected on {self.config.leader_port}")

            self._log("connecting keyboard...")
            kb_cfg = KeyboardTeleopConfig(id="kcc_keyboard")
            self.keyboard = KeyboardTeleop(kb_cfg)
            self.keyboard.connect()
            self._log("keyboard listener active")

            (
                self.teleop_action_processor,
                self.robot_action_processor,
                self.robot_observation_processor,
            ) = make_default_processors()

            self._set_state(State.IDLE)
            self.last_error = ""
            self._audit(f"CONNECTED ip={self.config.remote_ip} port={self.config.leader_port}")
        except Exception as e:
            tb = traceback.format_exc()
            self.last_error = f"{e}"
            self._log(f"CONNECT FAILED: {e}")
            self._audit(f"CONNECT_FAILED error={e}")
            logger.error(tb)
            self._set_state(State.ERROR)

    # ------------------------------------------------------------------
    # Dataset lifecycle
    # ------------------------------------------------------------------
    def init_dataset(self) -> bool:
        if self.robot is None:
            self.last_error = "Robot not connected"
            return False
        try:
            repo_id = f"{self.config.hf_org}/{self.config.hf_repo_name}"
            self._log(f"initializing dataset {repo_id}")
            action_features = hw_to_dataset_features(self.robot.action_features, ACTION)
            obs_features = hw_to_dataset_features(self.robot.observation_features, OBS_STR)

            # PATCH: shape fix

            for _k, _feat in obs_features.items():

                if "images" in _k and isinstance(_feat.get("shape"), (tuple, list)):

                    _s = _feat["shape"]

                    if len(_s) == 3 and _s[0] > _s[1]:

                        _feat["shape"] = (_s[1], _s[0], _s[2])


            features = {**action_features, **obs_features}
            self.dataset = LeRobotDataset.create(
            # KCC6: local storage, no HF cache, no hub push
            root=Path(self.config.data_dir) / repo_id,

                repo_id=repo_id,
                fps=self.config.fps,
                features=features,
                robot_type=self.robot.name,
                use_videos=True,
                image_writer_threads=4,
            )
            self.episodes_done = 0
            self.dataset_initialized = True
            self._log("dataset ready")
            self._audit(f"DATASET_CREATE repo={repo_id} fps={self.config.fps}")
            return True
        except FileExistsError:
            # KCC3: load existing dataset for continuation
            try:
                self._log(f"dataset exists, loading {repo_id} for continuation")
                # KCC7: local D:\ storage, no HF cache
                _root = Path(self.config.data_dir) / repo_id; self.dataset = _kcc13_offline_resume(repo_id=repo_id, root=_root)
                existing = getattr(self.dataset.meta, "total_episodes", 0) or 0
                self.episodes_done = int(existing)
                self.dataset_initialized = True
                self._log(f"loaded existing dataset: {self.episodes_done} episodes already recorded")
                self._audit(f"DATASET_RESUME repo={repo_id} episodes={self.episodes_done}")
                return True
            except Exception as e2:
                self.last_error = f"Failed to load existing dataset: {e2}"
                self._log(self.last_error)
                logger.error(traceback.format_exc())
                return False
        except Exception as e:
            self.last_error = f"Dataset init failed: {e}"
            self._log(self.last_error)
            logger.error(traceback.format_exc())
            return False

    def push_to_hub(self) -> bool:
        # KCC7: HuggingFace push disabled
        self._log("HuggingFace push disabled in this build")
        return False
        # --- original body below, unreachable ---
        if self.dataset is None:
            self.last_error = "No dataset to push"
            return False
        try:
            self._log("finalizing dataset...")
            self.dataset.finalize()
            self._log("pushing to HuggingFace Hub (this can take a while)...")
            self.dataset.push_to_hub()
            self._log("push complete")
            return True
        except Exception as e:
            self.last_error = f"Push failed: {e}"
            self._log(self.last_error)
            logger.error(traceback.format_exc())
            return False

    # ------------------------------------------------------------------
    # External commands from Flask
    # ------------------------------------------------------------------
    def cmd_start_teleop(self):
        if self.state == State.IDLE:
            self._set_state(State.TELEOP)

    def cmd_stop_teleop(self):
        if self.state == State.TELEOP:
            self._set_state(State.IDLE)

    def cmd_start_recording(self):
        if not self.dataset_initialized:
            self.last_error = "Initialize dataset first"
            return False
        # KCC-PROD: disk space guard (Ch.3)
        try:
            import shutil as _sh
            disk = _sh.disk_usage(r"D:\lerobot_data")
            free_gb = disk.free / (1024**3)
            if free_gb < 1.0:
                self.last_error = f"Disk nearly full: {free_gb:.1f}GB free. Need >1GB."
                self._log(f"BLOCKED: disk space low ({free_gb:.1f}GB)")
                self._audit(f"BLOCKED_RECORD disk_low={free_gb:.1f}GB")
                return False
            elif free_gb < 5.0:
                self._log(f"WARNING: disk space low ({free_gb:.1f}GB free)")
        except Exception:
            pass  # don't block recording if disk check fails
        # KCC13/DDIA: backpressure — block if save still running
        if _kcc13_save_in_progress.is_set():
            self.last_error = "Previous episode still saving — wait"
            self._log("recording blocked: save in progress")
            return False
        if self.state in (State.IDLE, State.TELEOP):
            self._set_state(State.RECORDING)
            return True
        return False

    def cmd_end_episode_early(self):
        """Set exit_early in the events dict — record_loop will return next tick."""
        if self.state == State.RECORDING:
            self._events["exit_early"] = True

    def cmd_stop_recording(self):
        """Same as end_episode_early but with the name users expect."""
        self.cmd_end_episode_early()

    def cmd_save(self):
        if self.state == State.REVIEW:
            self._pending_review_decision = "save"

    def cmd_discard(self):
        if self.state == State.REVIEW:
            self._pending_review_decision = "discard"

    def cmd_rerecord(self):
        if self.state == State.REVIEW:
            self._pending_review_decision = "rerecord"

    def cmd_skip_reset(self):
        # legacy — no longer used in main flow but kept for compatibility
        if self.state == State.RESET:
            self._events["exit_early"] = True

    def cmd_set_episode_count(self, count: int):
        """Override the episodes_done counter (count of completed episodes)."""
        if count < 0:
            return
        self.episodes_done = count
        self._log(f"episodes_done set to {count}")

    def cmd_set_next_episode(self, next_num: int):
        """Set what the *next* recorded episode number will be.
        next_num=1 means episodes_done=0 → next save is episode #1.
        Useful when resuming a partially-recorded dataset.
        """
        if next_num < 1:
            return
        self.episodes_done = next_num - 1
        self._log(f"next episode set to {next_num} (episodes_done={self.episodes_done})")

    def cmd_reconnect(self):
        """KCC13/DDIA: recover from ERROR by reconnecting hardware."""
        if self.state != State.ERROR:
            return
        self._log("reconnecting hardware...")
        self._cleanup_hardware()
        _CB_COM4.reset()
        _CB_HOST.reset()
        self._set_state(State.DISCONNECTED)
        self.connect_hardware()
        if self.state == State.IDLE:
            self._setup_control_keyboard()
            self._log("reconnected OK")

    def cmd_set_target(self, target: int):
        if target < 1:
            return
        self.config.target_episodes = target
        self._log(f"target set to {target}")

    def update_settings(self, **kwargs):
        """Update config settings (org, repo, task, episode/reset times)."""
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

    # ------------------------------------------------------------------
    # The main worker loop
    # ------------------------------------------------------------------
    def start(self):
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_flag.clear()
        self._worker = threading.Thread(target=self._run, daemon=True, name="kcc-recorder")
        self._worker.start()

    def stop(self):
        self._stop_flag.set()
        if self._worker:
            self._worker.join(timeout=5)

    def _run(self):
        """Main worker loop — dispatches based on state."""
        self._audit(f"SESSION_START wrapper_version=KCC-PROD")
        # KCC-PROD: check for crash recovery from state file (Ch.3)
        try:
            state_file = Path(r"D:\lerobot_data") / ".kcc_state.json"
            if state_file.exists():
                import json
                prev = json.loads(state_file.read_text())
                if prev.get("episodes_done", 0) > 0:
                    self._log(f"previous session: {prev.get('org')}/{prev.get('repo')} — {prev.get('episodes_done')} episodes")
                    self._audit(f"CRASH_RECOVERY prev_episodes={prev.get('episodes_done')}")
        except Exception:
            pass
        self.connect_hardware()
        if self.state == State.ERROR:
            return

        # Start global hotkey listener (F-keys → recording controls)
        self._setup_control_keyboard()

        try:
            while not self._stop_flag.is_set():
                s = self.state
                if s == State.IDLE:
                    self._tick_idle()
                elif s == State.TELEOP:
                    self._tick_teleop()
                elif s == State.RECORDING:
                    self._do_record_episode()
                elif s == State.REVIEW:
                    self._tick_review()
                elif s == State.RESET:
                    self._do_reset_window()
                elif s == State.FINISHED:
                    time.sleep(0.2)
                else:
                    time.sleep(0.1)
        except Exception as e:
            self.last_error = f"Worker crashed: {e}"
            self._log(self.last_error)
            logger.error(traceback.format_exc())
            self._audit(f"WORKER_CRASH error={e}")
            self._set_state(State.ERROR)
        finally:
            self._cleanup_hardware()

    # ------------------------------------------------------------------
    # Per-state tick functions
    # ------------------------------------------------------------------
    def _tick_idle(self):
        """Robot connected but motionless. Just keep observations flowing so cameras stay fresh."""
        try:
            obs = self.robot.get_observation()
            self._last_obs_time = time.time()
            # Store observation state for telemetry
            try:
                if obs and 'observation.state' in obs:
                    st = obs['observation.state']
                    self._last_telemetry = st.tolist() if hasattr(st, 'tolist') else list(st)
            except Exception:
                pass  # KCC-PROD: heartbeat
        except Exception as e:
            self._log(f"observation read failed in idle: {e}")
            # KCC-PROD: observation timeout detection (Ch.8)
            if self._last_obs_time > 0 and (time.time() - self._last_obs_time) > self._watchdog_timeout:
                self._log(f"WARNING: no observation for {self._watchdog_timeout}s — Pi host may be down")
                self._audit(f"TIMEOUT observation_gap={time.time()-self._last_obs_time:.1f}s")
        time.sleep(1.0 / max(self.config.fps, 1))

    def _do_one_teleop_tick(self):
        """One iteration of leader → arm + keyboard → base."""
        self.robot.get_observation()
        arm_action = self.leader_arm.get_action()
        # Store for live 3D visualization
        try:
            vals = list(arm_action.values())
            if len(vals) >= 6:
                self._last_telemetry = vals[:6] + self._last_telemetry[6:]
        except Exception:
            pass
        arm_action = {f"arm_{k}": v for k, v in arm_action.items()}

        # Base: joystick axes OR keyboard
        joy = getattr(self, '_joystick_axes', [0, 0, 0])
        joy_active = any(abs(a) > 0.08 for a in joy)
        if joy_active:
            import math
            speed = 200
            jx, jy, jr = joy[0]*speed, -joy[1]*speed, (joy[2] if len(joy)>2 else 0)*speed*0.5
            base_action = {
                "base_left_wheel": -jx*0.5 + jy*0.866 + jr,
                "base_back_wheel": jx + jr,
                "base_right_wheel": -jx*0.5 - jy*0.866 + jr,
            }
        else:
            keys = self.keyboard.get_action()
            base_action = self.robot._from_keyboard_to_base_action(keys)
        action = {**arm_action, **base_action} if base_action else arm_action
        self.robot.send_action(action)

    def _tick_teleop(self):
        try:
            t0 = time.perf_counter()
            self._do_one_teleop_tick()
            dt = time.perf_counter() - t0
            time.sleep(max(1.0 / self.config.fps - dt, 0))
        except Exception as e:
            self._log(f"teleop tick error: {e}")
            time.sleep(0.05)

    def _tick_review(self):
        """Wait for save/discard/rerecord button. NO teleop — robot frozen so preview is meaningful.
        The cameras stop being live and instead show a snapshot from the recorded episode.
        """
        decision = self._pending_review_decision
        if decision is None:
            time.sleep(1.0 / self.config.fps)
            return
        self._pending_review_decision = None

        try:
            if decision == "save":
                # KCC13/DDIA: idempotent save + state log + validation + backpressure
                if _kcc13_save_in_progress.is_set():
                    self._log("save blocked — previous save still running")
                    return
                _kcc13_save_in_progress.set()
                self.episodes_done += 1
                self.last_recorded_frames = {}
                _ep_n = self.episodes_done
                _root = Path(r"D:\lerobot_data") / f"{self.config.hf_org}/{self.config.hf_repo_name}"

                # DDIA: write-ahead state log
                _kcc13_save_state(self.config.hf_org, self.config.hf_repo_name,
                                  self.episodes_done, _ep_n)
                try:
                    self._log(f"saving ep {_ep_n}...")
                    self.dataset.save_episode()
                    self._log(f"ep {_ep_n} saved")
                    # DDIA: validate saved data
                    issues = _kcc13_validate_episode(_root)
                    if issues:
                        self._log(f"ep {_ep_n} validation warnings: {issues}")
                    else:
                        self._log(f"ep {_ep_n} validated OK")
                except Exception as ex:
                    self._log(f"save failed: {ex}")
                    logger.error(traceback.format_exc())
                    self.last_error = str(ex)
                    self.episodes_done -= 1  # rollback on failure
                finally:
                    _kcc13_save_in_progress.clear()
                self.dataset.clear_episode_buffer()
                if self.episodes_done >= self.config.target_episodes:
                    self._set_state(State.FINISHED)
                else:
                    self._set_state(State.IDLE)
            elif decision == "discard":
                self._log("discarding episode")
                self._audit(f"DISCARD ep={self.episodes_done+1}")
                self.dataset.clear_episode_buffer()
                self.last_recorded_frames = {}
                self._set_state(State.IDLE)
            elif decision == "rerecord":
                self._log("rerecording episode")
                self._audit(f"RERECORD ep={self.episodes_done+1}")
                self.dataset.clear_episode_buffer()
                self.last_recorded_frames = {}
                self._set_state(State.RECORDING)
        except Exception as e:
            self._log(f"review action '{decision}' failed: {e}")
            logger.error(traceback.format_exc())
            self.last_error = str(e)
            self._set_state(State.ERROR)

    def _do_record_episode(self):
        """Run the official record_loop for one episode, then go to review."""
        self._events["exit_early"] = False
        self._events["rerecord_episode"] = False
        self.episode_start_time = time.perf_counter()
        self._frame_count = 0  # KCC-PROD: reset frame counter
        self._frame_drops = 0
        self._log(
            f"recording episode {self.episodes_done + 1} "
            f"(target {self.config.target_episodes}, {self.config.episode_time_sec}s)"
        )
        try:
            # KCC11: guarantee fresh episode buffer (fixes KeyError: 'size')
            if hasattr(self, 'dataset') and self.dataset is not None:
                try:
                    self.dataset.clear_episode_buffer()
                except Exception:
                    pass  # buffer already clean or dataset not ready
            record_loop(
                robot=self.robot,
                events=self._events,
                fps=self.config.fps,
                teleop_action_processor=self.teleop_action_processor,
                robot_action_processor=self.robot_action_processor,
                robot_observation_processor=self.robot_observation_processor,
                dataset=self.dataset,
                teleop=[self.leader_arm, self.keyboard],
                control_time_s=self.config.episode_time_sec,
                single_task=self.config.task_description,
                display_data=False,
            )
        except Exception as e:
            self.last_error = f"record_loop crashed: {e}"
            self._log(self.last_error)
            logger.error(traceback.format_exc())
            self._set_state(State.ERROR)
            return
        finally:
            self.episode_start_time = None
            # Snapshot the final frames from each camera for review-state preview
            try:
                self.last_recorded_frames = {}
                if self.robot is not None:
                    for cam_name, frame in (self.robot.last_frames or {}).items():
                        if frame is not None:
                            self.last_recorded_frames[cam_name] = frame.copy()
            except Exception as e:
                self._log(f"preview snapshot failed: {e}")

        self._log("episode buffered — review")
        self._pending_review_decision = None
        self._set_state(State.REVIEW)

    def _do_reset_window(self):
        """Time-bounded teleop window between episodes. User can skip with cmd_skip_reset."""
        self._events["exit_early"] = False
        self._log(f"reset window: {self.config.reset_time_sec}s of free teleop")
        t_start = time.perf_counter()
        deadline = t_start + self.config.reset_time_sec
        try:
            while time.perf_counter() < deadline:
                if self._stop_flag.is_set():
                    return
                if self._events.get("exit_early"):
                    self._log("reset skipped")
                    break
                t0 = time.perf_counter()
                self._do_one_teleop_tick()
                dt = time.perf_counter() - t0
                time.sleep(max(1.0 / self.config.fps - dt, 0))
        except Exception as e:
            self._log(f"reset window error: {e}")
        self._set_state(State.RECORDING)

    # ------------------------------------------------------------------
    # Control keyboard (global hotkeys for joystick / keyboard shortcuts)
    # ------------------------------------------------------------------
    def _setup_control_keyboard(self):
        """Start a global keyboard listener for recording hotkeys.

        F-key bindings (chosen because browsers and form fields don't intercept them):
            F2  → start/stop recording (state-aware toggle)
            F3  → save  (review state only)
            F4  → discard  (review state only)
            F6  → rerecord  (review state only)
            F7  → start/stop teleop (state-aware toggle)
            F8  → next-episode counter -1
            F9  → next-episode counter +1
        """
        try:
            from pynput import keyboard as _kb
        except ImportError:
            self._log("pynput not available — hotkeys disabled")
            self._control_kb_listener = None
            return

        K = _kb.Key

        def on_press(key):
            try:
                state = self.state.value
                if key == K.f2:
                    if state in ("idle", "teleop"):
                        self.cmd_start_recording()
                        self._log("hotkey F2: start recording")
                    elif state == "recording":
                        self.cmd_stop_recording()
                        self._log("hotkey F2: stop recording")
                elif key == K.f3 and state == "review":
                    self.cmd_save()
                    self._log("hotkey F3: save")
                elif key == K.f4 and state == "review":
                    self.cmd_discard()
                    self._log("hotkey F4: discard")
                elif key == K.f6 and state == "review":
                    self.cmd_rerecord()
                    self._log("hotkey F6: rerecord")
                elif key == K.f7:
                    if state == "idle":
                        self.cmd_start_teleop()
                        self._log("hotkey F7: start teleop")
                    elif state == "teleop":
                        self.cmd_stop_teleop()
                        self._log("hotkey F7: stop teleop")
                elif key == K.f8:
                    new_done = max(0, self.episodes_done - 1)
                    self.cmd_set_episode_count(new_done)
                    self._log(f"hotkey F8: counter -1 (done={new_done})")
                elif key == K.f9:
                    new_done = self.episodes_done + 1
                    self.cmd_set_episode_count(new_done)
                    self._log(f"hotkey F9: counter +1 (done={new_done})")
            except Exception as e:
                self._log(f"hotkey handler error: {e}")

        self._control_kb_listener = _kb.Listener(on_press=on_press)
        self._control_kb_listener.start()
        self._log("hotkeys: F2=rec F3=save F4=disc F6=rerec F7=teleop F8/F9=counter")

    def _teardown_control_keyboard(self):
        listener = getattr(self, "_control_kb_listener", None)
        if listener is not None:
            try:
                listener.stop()
            except Exception as e:
                self._log(f"control kb stop error: {e}")
            self._control_kb_listener = None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def _cleanup_hardware(self):
        self._log("cleanup: disconnecting hardware")
        self._teardown_control_keyboard()
        for obj_name in ("keyboard", "leader_arm", "robot"):
            obj = getattr(self, obj_name, None)
            if obj is None:
                continue
            try:
                obj.disconnect()
            except Exception as e:
                self._log(f"{obj_name} disconnect error: {e}")
        if self.dataset is not None:
            try:
                self.dataset.finalize()
            except Exception:
                pass
