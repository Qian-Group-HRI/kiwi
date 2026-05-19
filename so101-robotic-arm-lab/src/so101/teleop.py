"""
Teleoperation — SO-101 Arm Lab
================================

Uses LeRobot's SO101Leader and SO101Follower classes directly.
This guarantees identical behavior to lerobot-teleoperate.

Usage:
    python src/so101/teleop.py --leader COM5 --follower COM6
    python src/so101/teleop.py --leader /dev/ttyACM0 --follower /dev/ttyACM1
    python so101_cli.py teleop --leader COM5 --follower COM6

Requires:
    pip install -e "path/to/Modern-Robot-Learning[feetech]"

Author: Gopi Trinadh
Project: SO-101 Robotic Arm Lab
"""
import time
import argparse

from lerobot.robots.so101_follower import SO101Follower
from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig
from lerobot.teleoperators.so101_leader import SO101Leader
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig


def teleop(leader_port, follower_port, fps=30,
           leader_id="leader_arm", follower_id="follower_arm"):

    leader = SO101Leader(SO101LeaderConfig(port=leader_port, id=leader_id))
    follower = SO101Follower(SO101FollowerConfig(port=follower_port, id=follower_id))

    leader.connect()
    follower.connect()

    print()
    print("=" * 50)
    print("  SO-101 TELEOPERATION")
    print(f"  Leader:   {leader_port}")
    print(f"  Follower: {follower_port}")
    print(f"  FPS:      {fps}")
    print("=" * 50)
    print()
    print("Teleop running! Move the leader arm. Ctrl+C to stop.")

    dropped = 0
    try:
        while True:
            try:
                action = leader.get_action()
                follower.send_action(action)
            except ConnectionError:
                dropped += 1
                print(f"WARNING: Dropped frame (total: {dropped})")
                continue
            time.sleep(1.0 / fps)
    except KeyboardInterrupt:
        print("\nStopped.")

    leader.disconnect()
    follower.disconnect()
    print("Disconnected.")


def main():
    parser = argparse.ArgumentParser(description="SO-101 Teleoperation")
    parser.add_argument("--leader", required=True, help="Leader port (COM5 or /dev/ttyACM0)")
    parser.add_argument("--follower", required=True, help="Follower port (COM6 or /dev/ttyACM1)")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--leader-id", default="leader_arm")
    parser.add_argument("--follower-id", default="follower_arm")
    args = parser.parse_args()
    teleop(args.leader, args.follower, args.fps, args.leader_id, args.follower_id)


if __name__ == "__main__":
    main()
