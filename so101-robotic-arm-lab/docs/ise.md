<h1 align="center">Initial System Environment (ISE)</h1>

This page defines the **baseline software environment** we use for the SO101 robotic arm experiments, both on a **desktop Ubuntu x86 machine** and on the **Jetson Orin** platform.

> [!TIP]
> Set this up **before** touching calibration, teleoperation, or imitation learning.  
> If your environment is off, everything downstream becomes pain.

<br><br>

## 1. Summary 🧩

| Platform        | OS / SDK            | CUDA / Drivers | Python | Torch   |
|----------------|---------------------|----------------|--------|---------|
| **Ubuntu x86** | Ubuntu 22.04        | CUDA **12+**   | 3.10   | 2.6     |
| **Jetson Orin**| JetPack **6.2**     | (included in JP) | 3.10 | 2.6     |

All examples in this repo assume **Python 3.10** and **PyTorch 2.6** on both sides.

<br><br>


## 2. Ubuntu x86 Environment 💻

This is your **host PC** / development machine, used for:

- Code development
- Debugging
- Running LeRobot tooling
- Optional training if you have a decent GPU

### Required versions

- **OS:** Ubuntu **22.04**
- **CUDA:** **12+**
- **Python:** **3.10**
- **Torch:** **2.6**

### Quick checklist

- [ ] `Ubuntu 22.04` installed (or WSL2 with Ubuntu 22.04)
- [ ] NVIDIA driver + CUDA 12+ correctly installed
- [ ] `python3` points to Python 3.10
- [ ] `torch` imports and reports version 2.6

### How to verify

```bash
# OS version
lsb_release -a

# NVIDIA + CUDA
nvidia-smi

# Python
python3 --version

# Torch
python3 -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
