"""
Teleoperation Script — SO-101 Arm Lab
Thin wrapper around src/so101/teleop.py

Usage:
    python scripts/teleop.py --leader /dev/ttyACM0 --follower /dev/ttyACM1
    python scripts/teleop.py --leader COM5 --follower COM6
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from so101.teleop import main

if __name__ == "__main__":
    main()
