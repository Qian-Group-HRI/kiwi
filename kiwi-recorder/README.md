# KCC Recorder

A production-grade web dashboard for recording robot demonstration episodes with [LeRobot](https://github.com/huggingface/lerobot).

Built for the [LeKiwi](https://github.com/huggingface/lerobot/tree/main/examples/robots/lekiwi) mobile manipulator with SO-101 arm. Compatible with any LeRobot-supported robot.

![Dashboard](docs/screenshots/dashboard.png)

## Features

- **Live camera feeds** — dual camera view with `observation.images.front` / `.wrist` labels
- **Recording state machine** — record → review → save/discard/rerecord workflow
- **3D arm visualization** — live Three.js arm pose in the dashboard
- **Action trace chart** — Chart.js plot of last episode's 6 joint positions
- **Data inspector** — auto-verify after every save: frame count, arm range, wheel check, entanglement E
- **Gamepad support** — plug-and-play joystick with configurable button mapping
- **Full keyboard shortcuts** — Space, Enter, Esc, R, T, V, I — never touch the mouse
- **DDIA reliability** — write-ahead state log, circuit breaker, backpressure, data validation
- **Production hardening** — persistent audit log, state transition validation, disk space guard, health checks
- **Offline-first** — no HuggingFace Hub dependency during recording

## Quick Start

### Prerequisites

- Python 3.10+
- [LeRobot](https://github.com/huggingface/lerobot) installed
- LeKiwi robot with Pi 5 host running
- Leader SO-101 arm connected via USB

### Installation

```bash
git clone https://github.com/Qian-Group-HRI/kcc-recorder.git
cd kcc-recorder
pip install -r requirements.txt
```

### Configuration

Edit `config.json`:

```json
{
  "remote_ip": "100.68.160.45",   // Pi 5 Tailscale IP
  "leader_port": "COM4",           // Windows: COM4, Linux: /dev/ttyACM0
  "data_dir": "D:\\lerobot_data",  // Where datasets are saved
  "hf_org": "YourOrg",
  "hf_repo_name": "your_dataset",
  "task_description": "Pick up the object",
  "target_episodes": 50,
  "fps": 30
}
```

### Start the Pi 5 host first

```bash
ssh pi@100.68.160.45
cd ~/lerobot && source .venv/bin/activate
python -m lerobot.robots.lekiwi.lekiwi_host \
    --robot.id=my_kiwi --robot.port=/dev/ttyACM0 \
    --robot.cameras='{"front":{"type":"opencv","index_or_path":"/dev/video0","fps":30,"width":640,"height":480,"fourcc":"MJPG"},"wrist":{"type":"opencv","index_or_path":"/dev/video2","fps":30,"width":640,"height":480,"fourcc":"MJPG"}}' \
    --host.connection_time_s=7200
```

### Launch the recorder

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

## Usage

### Recording workflow

1. Click **init dataset** (or press `I`)
2. Press **Space** to start recording
3. Teleoperate the robot with leader arm + joystick
4. Press **Space** to stop
5. Review the episode — press **Enter** to save, **Esc** to discard, **R** to redo
6. Repeat until target reached

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Space` / `F2` | Toggle recording |
| `Enter` / `F3` | Save episode |
| `Esc` / `F4` | Discard episode |
| `R` / `F6` | Rerecord |
| `T` / `F7` | Toggle teleop |
| `V` | Verify dataset |
| `I` | Init dataset |
| `F8` / `F9` | Episode count ±1 |

### Gamepad

Plug in any USB gamepad. Click the 🎮 badge in the header to configure button mapping. Default mapping (Thrustmaster T16000M):

| Button | Action |
|--------|--------|
| Trigger (0) | Toggle recording |
| Button 1 | Save |
| Button 2 | Discard |
| Button 3 | Rerecord |
| Button 4 | Teleop toggle |

Mappings are saved per-gamepad and persist across sessions.

### Data Inspector

After every save, the inspector auto-checks:
- Episode count and frame count
- Arm joint range (min/max degrees)
- Wheel activity (should be 0 for grasp-only tasks)
- Entanglement E value
- Parquet and video file integrity

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Current state, cameras, episode count |
| `/health` | GET | System health (disk, connections, uptime) |
| `/audit` | GET | Last 100 audit log entries |
| `/dataset_stats` | GET | Dataset metrics + last episode analysis |
| `/telemetry` | GET | Live joint angles for 3D visualization |
| `/camera/<name>.mjpg` | GET | MJPEG camera stream |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Browser (UI)                    │
│  cameras │ chart │ 3D arm │ controls │ inspector │
├─────────────────────────────────────────────────┤
│              Flask + Waitress (app.py)           │
│  /status │ /health │ /dataset_stats │ MJPEG     │
├─────────────────────────────────────────────────┤
│           State Machine (recorder.py)            │
│  IDLE → TELEOP → RECORDING → REVIEW → IDLE      │
├─────────────────────────────────────────────────┤
│              LeRobot (record_loop)               │
│  LeKiwiClient │ SO100Leader │ LeRobotDataset     │
├──────────┬──────────────────────────────────────┤
│  Pi 5    │  ROG Laptop                           │
│  cameras │  leader arm (COM4)                    │
│  motors  │  joystick                             │
│  ZMQ     │  wrapper UI                           │
└──────────┴──────────────────────────────────────┘
```

## Reliability (DDIA-Inspired)

| Pattern | Implementation |
|---------|----------------|
| Write-Ahead Log | `.kcc_state.json` before every save |
| Circuit Breaker | COM4 stops retrying after 5 failures |
| Backpressure | Recording blocked during active save |
| Data Validation | Parquet + video verified after every save |
| State Validation | Invalid transitions rejected and logged |
| Audit Log | Every operation persisted to `.kcc_audit.log` |
| Disk Guard | Recording blocked if <1GB free |
| Health Checks | `/health` endpoint for monitoring |

## Dataset Format

Episodes are saved in [LeRobot v3.0](https://huggingface.co/docs/lerobot) format:

```
data_dir/org/repo/
├── meta/
│   └── info.json
├── data/
│   └── chunk-000/
│       └── file-000.parquet
└── videos/
    ├── observation.images.front/
    │   └── chunk-000/file-000.mp4
    └── observation.images.wrist/
        └── chunk-000/file-000.mp4
```

## License

MIT License. See [LICENSE](LICENSE).

## Citation

If you use KCC Recorder in your research, please cite:

```bibtex
@software{kcc_recorder,
  title={KCC Recorder: A Production-Grade Dashboard for Robot Demonstration Recording},
  author={Gopi Trinadh and Qian Group HRI Lab},
  year={2026},
  url={https://github.com/Qian-Group-HRI/kcc-recorder}
}
```

## Acknowledgments

Built on [LeRobot](https://github.com/huggingface/lerobot) by HuggingFace. Part of the [Qian Group HRI Lab](https://github.com/Qian-Group-HRI) at the University of Houston.
