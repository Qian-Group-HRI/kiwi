# Stage 1 — Data Collection

> **Goal:** Record high-quality human demonstrations that the policy will learn from.

---

## Overview

Data collection is the foundation of the entire imitation learning pipeline. During this stage, a human operator physically moves the **leader arm** through a task while the **follower arm** mirrors every motion in real time. LeRobot records joint positions from both arms, camera frames, and timestamps into a structured dataset that can be used for training.

The quality of your demonstrations directly determines the quality of your trained policy. Noisy, inconsistent data produces noisy, inconsistent robot behavior. Clean, deliberate demonstrations produce smooth, reliable policies.

---

## Prerequisites

Before starting data collection, make sure you have completed:

- [x] Both arms assembled, calibrated, and tested ([Calibration Guide](calibrate.md))
- [x] Teleoperation working — leader moves, follower follows ([Teleoperation Guide](teleoperate.md))
- [x] Camera mounted and verified ([Camera Setup](cameras.md))
- [x] LeRobot environment configured ([Installation Guide](install.md))

---

## Hardware Setup

### Camera Placement

Camera placement has a **massive** impact on policy performance. The policy learns to map what it *sees* to what it should *do* — if the camera view changes between training and deployment, the policy will struggle.

**Recommended setup:**
- Mount the camera on a fixed tripod or clamp — it should not move between episodes
- Position it to capture the full workspace: the arm, the objects, and the target area
- Avoid backlighting (don't point the camera toward a window)
- Use consistent, diffuse lighting — avoid harsh shadows that shift throughout the day

### Workspace Preparation

- Clear the workspace of any objects not involved in the task
- Mark object starting positions with small tape pieces (helps with consistency)
- Make sure the arm can reach all task-relevant positions without hitting joint limits

---

## Recording Demonstrations

### Basic Recording Command

```bash
python lerobot/scripts/control_robot.py \
  --robot.type=so101 \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Pick up the block and place it in the bin" \
  --control.repo_id=YOUR_HF_USERNAME/so101_pick_place \
  --control.num_episodes=50 \
  --control.push_to_hub=1
```

### What Gets Recorded

Each episode captures:

| Data | Source | Format |
|------|--------|--------|
| **Joint positions (state)** | Follower arm servos | 6 values per frame (one per joint) |
| **Joint positions (action)** | Leader arm servos | 6 values per frame (the "command") |
| **Camera frames** | USB camera(s) | RGB images at configured resolution |
| **Timestamps** | System clock | Microsecond precision |
| **Episode metadata** | LeRobot | Task description, episode index, length |

### Recording Workflow

1. **Start the script** — it will initialize both arms and the camera
2. **Press Enter** to begin an episode
3. **Perform the task** with the leader arm — move slowly and deliberately
4. **Press Enter** again to end the episode
5. **Review** — LeRobot shows a summary of the recorded episode
6. **Repeat** until you reach your target number of episodes

### Episode Structure

```
dataset/
├── episode_000000/
│   ├── observation.images.camera/
│   │   ├── frame_000000.png
│   │   ├── frame_000001.png
│   │   └── ...
│   ├── observation.state.npy        # Follower joint positions
│   ├── action.npy                   # Leader joint positions (actions)
│   └── metadata.json
├── episode_000001/
│   └── ...
└── meta/
    └── info.json
```

---

## Best Practices

### How Many Episodes?

| Task Complexity | Episodes Needed | Examples |
|----------------|-----------------|----------|
| Simple (1 motion) | 20–30 | Push a button, wave |
| Medium (pick & place) | 50–80 | Pick up block, place in bin |
| Complex (multi-step) | 100–200 | Stack objects, sort by color |

Start with fewer episodes (20), train a quick policy, and see if it captures the general motion. If yes, collect more data for robustness. If no, fix your demonstration quality first.

### Demonstration Quality Checklist

- **Slow, deliberate motions.** If you're rushing, the policy will learn jerky behavior.
- **Consistent object placement.** Small variations are good (within a few centimeters). Random chaos is bad.
- **Consistent grip timing.** Close the gripper at roughly the same point in the task each time.
- **Full task completion.** Every episode should be a complete, successful demonstration.
- **No false starts.** If you mess up, discard the episode and redo it.

### Common Mistakes

| Mistake | Why It Hurts | Fix |
|---------|-------------|-----|
| Moving too fast | Policy learns noisy, imprecise actions | Slow down — aim for 3–5 seconds per motion |
| Object in different spots each time | Policy can't generalize from inconsistent data | Use tape markers for approximate placement |
| Camera bumped between episodes | Visual features shift, confusing the policy | Fix the camera mount rigidly |
| Recording failed attempts | Bad data pollutes the dataset | Only keep successful, clean episodes |
| Inconsistent lighting | Shadows change feature appearance | Use consistent overhead lighting |

---

## Reviewing Your Data

After collection, always review before training:

```bash
python lerobot/scripts/visualize_dataset.py \
  --repo-id YOUR_HF_USERNAME/so101_pick_place \
  --episode-index 0
```

This opens a visualization window where you can scrub through the episode frame-by-frame. Check for:
- Is the camera view consistent across episodes?
- Are the motions smooth and complete?
- Does the gripper timing look right?

---

## Pushing to HuggingFace Hub

If you set `--control.push_to_hub=1`, the dataset uploads automatically after collection. You can also push manually:

```bash
huggingface-cli upload YOUR_HF_USERNAME/so101_pick_place ./data/so101_pick_place
```

This makes your dataset available for training on any machine and enables collaboration with lab members.

---

## Next Step

Once you have a clean dataset, proceed to **[Stage 2 — Training](training.md)** to train a policy from your demonstrations.
