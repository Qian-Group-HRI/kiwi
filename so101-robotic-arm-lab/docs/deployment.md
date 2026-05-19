# Stage 3 — Evaluation & Deployment

> **Goal:** Load a trained policy, run it on the real arm, evaluate performance, and iterate.

---

## Overview

Deployment closes the imitation learning loop. You load a trained checkpoint, feed live camera frames and joint positions through the policy network, and send the predicted actions to the follower arm's servos in real time. This is where you find out what the policy actually learned — and where the iteration cycle begins.

---

## Prerequisites

- [x] Trained policy checkpoint available ([Stage 2](training.md))
- [x] Follower arm connected and calibrated
- [x] Camera mounted in the **same position** as during data collection
- [x] Objects placed in similar positions as during data collection

---

## Deployment Command

### Basic Deployment

```bash
python lerobot/scripts/control_robot.py \
  --robot.type=so101 \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Pick up the block and place it in the bin" \
  --control.policy.path=outputs/act_pick_place/checkpoints/last/pretrained_model \
  --control.num_episodes=10
```

### What Happens During Deployment

Each inference cycle (at 30 FPS):

1. **Read** current joint positions from all 6 follower servos
2. **Capture** a camera frame
3. **Feed** the observation (joints + image) into the policy network
4. **Get** predicted action (target joint positions)
5. **Send** the action to the follower arm's servos
6. **Repeat** at the configured FPS

The entire cycle needs to complete within ~33ms (for 30 FPS). ACT is fast enough for this on both desktop GPUs and Jetson Orin Nano.

---

## Evaluation Protocol

A single successful run doesn't prove the policy works. You need systematic evaluation.

### Recommended Protocol

1. **Run 10–20 evaluation episodes** without any intervention
2. **Record success/failure** for each episode (binary: did the task succeed?)
3. **Calculate success rate** — aim for >70% on your first policy, >90% after iteration
4. **Log failure modes** — what specific behaviors failed and when

### Evaluation Metrics

| Metric | What It Tells You | Target |
|--------|------------------|--------|
| **Success rate** | % of episodes where the task completed | >80% for demo-ready |
| **Completion time** | How long the policy takes vs. human demos | Within 2x of human time |
| **Smoothness** | Visual assessment of motion quality | No jerky pauses or oscillations |
| **Generalization** | Performance when objects shift slightly | Should tolerate ±2cm shifts |

---

## Troubleshooting Deployment

### Common Issues and Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| **Arm reaches but misses the object** | Camera position shifted since training | Re-mount camera in the exact training position, or collect a few new demos with current setup |
| **Gripper closes too early or too late** | Inconsistent gripper timing in demos | Re-record 10–20 episodes focusing on deliberate gripper actions |
| **Jerky, stuttering motion** | FPS too low or inference too slow | Check actual inference FPS in logs; reduce image resolution; use a lighter model |
| **Arm freezes mid-task** | Policy outputting constant values (degenerate) | Check loss curves — model may have collapsed; retrain with different LR |
| **Random, nonsensical actions** | Wrong checkpoint or config mismatch | Verify the config YAML matches training setup exactly |
| **Works sometimes, fails randomly** | Policy learned the average case but not edge cases | Collect more data, especially in failure regions |
| **Arm oscillates near the target** | Action chunking misaligned with actual dynamics | Reduce chunk size in ACT config; try temporal ensembling |

### Debugging Checklist

If deployment isn't working, check these in order:

1. **Camera** — Is it in the same position? Same resolution? Same frame rate?
2. **Calibration** — Has the arm been recalibrated since training? Joint offsets matter.
3. **Config** — Does the deployment config match the training config exactly?
4. **Checkpoint** — Try an earlier checkpoint (sometimes they outperform the final one).
5. **Environment** — Are objects, lighting, and background similar to training?

---

## Deploying on Jetson Orin Nano Super

For fully on-board inference without a laptop:

### Setup

1. Copy the trained checkpoint to the Jetson
2. Connect the follower arm via USB (`/dev/ttyACM0` or `/dev/ttyACM1`)
3. Connect the camera via USB
4. Run the same deployment command

### Performance Expectations

| Model | Inference Speed | Memory Usage | Real-Time? |
|-------|----------------|-------------|------------|
| ACT (default) | ~25–35 FPS | ~2–3 GB | ✓ Yes |
| Diffusion Policy | ~8–15 FPS | ~3–4 GB | ✓ Usable (reduce FPS to 15) |
| ACT (large) | ~15–20 FPS | ~4–5 GB | ✓ At reduced FPS |

The Jetson Orin Nano Super's 8 GB shared GPU memory handles ACT and Diffusion Policy comfortably for single-camera setups at 30 FPS.

### Optimization Tips for Jetson

- **Use TensorRT** if available — can give 2–3x speedup on inference
- **Reduce image resolution** to 160×120 or 224×224 if latency is tight
- **Pre-warm the model** by running a few dummy inferences before starting the task
- **Monitor temperature** — sustained inference can heat up the Jetson; ensure adequate cooling

---

## The Iteration Cycle

Deployment is not a one-shot process. Expect to iterate:

```
Collect data → Train → Deploy → Evaluate → Identify failures → Collect more data → ...
```

### When to Collect More Data

- Success rate is below 70%
- The policy consistently fails in one specific region of the workspace
- Objects in new positions cause failures

### When to Retrain

- You've added 20+ new episodes to the dataset
- You want to try a different architecture or hyperparameters
- You've fixed a camera or calibration issue

### When to Ship

- Success rate is above 85% across 20+ evaluation episodes
- The policy generalizes to small object position variations
- Motion is smooth and confidence-inspiring

---

## Recording Evaluation Videos

To record deployment episodes as video (useful for demos and documentation):

```bash
python lerobot/scripts/control_robot.py \
  --robot.type=so101 \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Pick up the block and place it in the bin" \
  --control.policy.path=outputs/act_pick_place/checkpoints/last/pretrained_model \
  --control.num_episodes=5 \
  --control.repo_id=YOUR_HF_USERNAME/so101_pick_place_eval \
  --control.push_to_hub=1
```

This records both the policy's actions and the camera feed, creating a shareable evaluation dataset.

---

## Next Steps

Once you have a reliable policy, you can:

- **Share it** — push the checkpoint to HuggingFace Hub for others to use
- **Extend it** — collect data for new tasks and train additional policies
- **Deploy on Jetson** — run fully on-board without a laptop
- **Integrate with KIWI** — add the policy to the KIWI Control Center for dashboard-triggered execution

← Back to [README](../README.md)
