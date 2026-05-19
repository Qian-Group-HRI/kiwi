# Stage 2 — Training

> **Goal:** Train a visuomotor policy that maps camera observations + joint states to motor actions.

---

## Overview

Training takes your recorded demonstrations and distills them into a neural network (the "policy") that can reproduce — and generalize from — the demonstrated behavior. LeRobot handles the data pipeline, model architecture, optimization, and logging. Your job is to pick the right architecture, configure the run, and monitor convergence.

---

## Prerequisites

- [x] Completed data collection with 20+ clean episodes ([Stage 1](data_collection.md))
- [x] Dataset uploaded to HuggingFace Hub or available locally
- [x] GPU available (recommended) or Jetson Orin Nano for smaller runs
- [x] LeRobot environment configured with PyTorch

---

## Choosing an Architecture

LeRobot ships with several imitation learning architectures. For SO-101 tasks, we recommend starting with one of these two:

### ACT (Action Chunking with Transformers)

**Best for:** Most tasks. Start here.

ACT predicts *chunks* of future actions at once (typically 50–100 timesteps) using a Transformer encoder-decoder. This reduces compounding error — instead of predicting one action at a time (where each small error accumulates), ACT looks ahead and produces a smooth trajectory.

**Strengths:**
- Fast training (~2–4 hours on 50 episodes with an RTX 3090)
- Smooth, fluid motions
- Works well with 50–100 demonstrations
- Lightweight enough for Jetson inference

### Diffusion Policy

**Best for:** Tasks with multiple valid strategies.

Diffusion Policy treats action prediction as a denoising diffusion process. Starting from random noise, it iteratively refines a sequence of actions through learned denoising steps. This naturally handles multi-modal distributions — if there are multiple "correct" ways to do a task (approach from left vs. right), Diffusion Policy captures all of them.

**Strengths:**
- Robust to ambiguous or multi-modal demonstrations
- Produces diverse, natural-looking behaviors
- State-of-the-art performance on complex manipulation benchmarks

**Tradeoffs:**
- Slower inference (multiple denoising steps per prediction)
- Longer training time
- Higher memory usage

---

## Training Configuration

LeRobot uses Hydra-based YAML configs. Key parameters to know:

| Parameter | What It Controls | Recommended |
|-----------|-----------------|-------------|
| `policy.type` | Architecture (act, diffusion, etc.) | `act` to start |
| `dataset.repo_id` | HuggingFace dataset path | Your dataset |
| `dataset.episodes` | Which episodes to use | All, or a subset for quick tests |
| `training.num_epochs` | Total training epochs | 2000 for ACT, 3000+ for Diffusion |
| `training.batch_size` | Samples per batch | 8 (reduce to 4 if OOM) |
| `training.lr` | Learning rate | 1e-4 (ACT default) |
| `eval.use_async_eval` | Run eval in background | `true` |
| `wandb.enable` | Log to Weights & Biases | `true` (recommended) |

---

## Launching Training

### ACT Policy

```bash
python lerobot/scripts/train.py \
  --policy.type=act \
  --dataset.repo_id=YOUR_HF_USERNAME/so101_pick_place \
  --dataset.episodes=[0:50] \
  --training.num_epochs=2000 \
  --training.batch_size=8 \
  --eval.use_async_eval=true \
  --output_dir=outputs/act_pick_place \
  --wandb.enable=true
```

### Diffusion Policy

```bash
python lerobot/scripts/train.py \
  --policy.type=diffusion \
  --dataset.repo_id=YOUR_HF_USERNAME/so101_pick_place \
  --dataset.episodes=[0:50] \
  --training.num_epochs=3000 \
  --training.batch_size=4 \
  --output_dir=outputs/diffusion_pick_place \
  --wandb.enable=true
```

---

## Monitoring Training

### What to Watch

- **Action prediction loss** — should decrease steadily. For ACT, expect a sharp drop in the first 500 steps, then gradual improvement.
- **Validation loss** — should track training loss. If it diverges, you're overfitting.
- **Learning rate schedule** — most configs use cosine annealing or step decay.

### Using WandB

If you enabled WandB logging, visit [wandb.ai](https://wandb.ai) to see live charts of loss curves, learning rate, gradient norms, and evaluation metrics.

### Checkpoints

LeRobot saves checkpoints at regular intervals to `output_dir/checkpoints/`. The directory structure:

```
outputs/act_pick_place/
├── checkpoints/
│   ├── 000500/
│   │   └── pretrained_model/
│   ├── 001000/
│   │   └── pretrained_model/
│   └── last/
│       └── pretrained_model/
├── config.yaml
└── logs/
```

---

## Hardware Recommendations

| Platform | Batch Size | ACT Training Time (50 eps) | Notes |
|----------|-----------|---------------------------|-------|
| RTX 3090 / 4090 | 8–16 | ~2–4 hours | Recommended for full runs |
| RTX 3060 / 3070 | 4–8 | ~4–6 hours | Works well, smaller batch |
| A100 (cloud) | 16–32 | ~1–2 hours | Fastest option |
| Jetson Orin Nano Super | 2–4 | ~8–16 hours | Viable for small experiments |
| CPU only | 1–2 | Days | Not recommended |

### Training on Jetson Orin Nano Super

The Jetson Orin Nano Super (8 GB shared GPU memory) can handle training for sub-200M parameter models like ACT and Diffusion Policy. Tips:

- Use batch size 2 to stay within memory
- Reduce image resolution if needed (160×120 works for many tasks)
- Enable mixed precision (`fp16`) if supported
- Be patient — it's slower but absolutely viable

---

## Tips for Better Policies

1. **Start small.** Train on 20 episodes first. If the policy captures the rough motion, scale up. If not, fix your data.

2. **Use image augmentation.** Random crops, color jitter, and brightness shifts dramatically improve generalization. LeRobot supports these in the config:
   ```yaml
   augmentation:
     random_crop: true
     color_jitter: true
   ```

3. **Save checkpoints frequently.** An earlier checkpoint sometimes outperforms the final one, especially on small datasets.

4. **Don't over-train.** If validation loss starts climbing while training loss keeps dropping, stop. You're overfitting.

5. **Compare architectures.** If ACT produces jerky behavior on a task where there are multiple valid strategies, try Diffusion Policy.

---

## Common Training Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Loss doesn't decrease | Learning rate too low or data quality issue | Check data quality first, then try higher LR |
| Loss explodes (NaN) | Learning rate too high | Reduce LR by 2–5x |
| Out of memory (OOM) | Batch size or image resolution too high | Reduce batch size or image resolution |
| Policy works on training data but fails on new objects | Overfitting / no augmentation | Enable augmentation, collect more diverse data |
| Training takes forever | CPU-only or large batch on small GPU | Use GPU, reduce batch size |

---

## Next Step

Once training converges and you have a promising checkpoint, proceed to **[Stage 3 — Evaluation & Deployment](deployment.md)** to test the policy on the real arm.
