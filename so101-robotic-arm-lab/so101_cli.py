"""
SO-101 CLI — One command for everything
========================================

Usage:
    python so101_cli.py teleop --leader /dev/ttyACM0 --follower /dev/ttyACM1
    python so101_cli.py status --port /dev/ttyACM0
    python so101_cli.py reset --port /dev/ttyACM1
    python so101_cli.py find-ports
    python so101_cli.py temps --port /dev/ttyACM0

Author: Gopi Trinadh
Project: SO-101 Robotic Arm Lab
"""
import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from so101.servo import ServoController
from so101.arm import ArmController, find_port, find_all_ports
from so101.teleop import Teleop


def print_help():
    print("""
  ╔══════════════════════════════════════════════════════╗
  ║           SO-101 Robotic Arm CLI                     ║
  ╚══════════════════════════════════════════════════════╝

  COMMANDS:

    teleop                       Leader-follower teleoperation
    status   --port PORT         Full arm status
    temps    --port PORT         Temperature report
    benchmark --port PORT        Read speed benchmark
    reset    --port PORT         Factory reset servo EEPROM
    verify   --port PORT         Check if servo EEPROM is clean
    find-ports                   Detect ports (unplug method)
    calibrate --port PORT        Interactive calibration
    quick-cal --port PORT        Quick calibration
    home     --port PORT         Move to home position

  TELEOP OPTIONS:

    --leader PORT               Leader arm port (required for teleop)
    --follower PORT             Follower arm port (required for teleop)
    --fps N                     Frames per second (default: 30)

  GENERAL OPTIONS:

    --port PORT                 Serial port
    --id NAME                   Arm name (default: follower)

  EXAMPLES:

    python so101_cli.py teleop --leader /dev/ttyACM0 --follower /dev/ttyACM1
    python so101_cli.py teleop --leader COM5 --follower COM6
    python so101_cli.py status --port /dev/ttyACM0
    python so101_cli.py reset --port /dev/ttyACM1
    python so101_cli.py verify --port /dev/ttyACM1
    python so101_cli.py temps --port /dev/ttyACM0
    python so101_cli.py find-ports
    python so101_cli.py benchmark --port /dev/ttyACM0
""")


def parse_args():
    args = sys.argv[1:]
    if not args or args[0] in ["-h", "--help", "help"]:
        print_help()
        sys.exit(0)

    command = args[0]
    port = None
    arm_id = "follower"
    leader = None
    follower = None
    fps = 30

    i = 1
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = args[i + 1]
            i += 2
        elif args[i] == "--id" and i + 1 < len(args):
            arm_id = args[i + 1]
            i += 2
        elif args[i] == "--leader" and i + 1 < len(args):
            leader = args[i + 1]
            i += 2
        elif args[i] == "--follower" and i + 1 < len(args):
            follower = args[i + 1]
            i += 2
        elif args[i] == "--fps" and i + 1 < len(args):
            fps = int(args[i + 1])
            i += 2
        else:
            i += 1

    return command, port, arm_id, leader, follower, fps


def main():
    command, port, arm_id, leader, follower, fps = parse_args()

    # ── teleop ───────────────────────────────────────────────────
    if command == "teleop":
        if not leader or not follower:
            print("Error: teleop requires --leader and --follower")
            print("Example: python so101_cli.py teleop --leader /dev/ttyACM0 --follower /dev/ttyACM1")
            sys.exit(1)
        teleop = Teleop(leader, follower, fps)
        teleop.run()
        return

    # ── find-ports ───────────────────────────────────────────────
    if command == "find-ports":
        response = input("Detect [1] single arm or [2] both arms? (1/2): ")
        if response.strip() == "2":
            find_all_ports()
        else:
            find_port(f"{arm_id.upper()} arm")
        return

    # ── All other commands need --port ───────────────────────────
    if not port:
        print("Error: --port required")
        print("Example: python so101_cli.py status --port /dev/ttyACM0")
        sys.exit(1)

    # ── reset (Layer 1) ──────────────────────────────────────────
    if command == "reset":
        with ServoController(port) as arm:
            arm.factory_reset()
        return

    # ── verify (Layer 1) ─────────────────────────────────────────
    if command == "verify":
        with ServoController(port) as arm:
            arm.verify_servos()
        return

    # ── benchmark (Layer 1) ──────────────────────────────────────
    if command == "benchmark":
        with ServoController(port) as arm:
            arm.benchmark_read()
        return

    # ── Commands using ArmController (Layer 2) ───────────────────
    arm = ArmController.from_port(port, arm_id)

    try:
        if command == "status":
            arm.print_status()

        elif command == "temps":
            arm.print_temperatures()

        elif command == "calibrate":
            arm.calibrate()

        elif command == "quick-cal":
            arm.quick_calibrate()

        elif command == "home":
            arm.home()
            import time
            time.sleep(2)

        else:
            print(f"Unknown command: {command}")
            print_help()

    finally:
        arm.disconnect()


if __name__ == "__main__":
    main()
