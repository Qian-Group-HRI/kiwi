<h1 align="center">Install LeRobot – Environment Setup Guide</h1>

This file is a **single, complete guide** to install LeRobot for SO100/SO101 on:

- Standard Linux (x86 Ubuntu 22.04, including VMs)
- Jetson (aarch64, JetPack)

It merges the official 🤗 Hugging Face instructions and the SeedStudio / SO101-specific notes (Orbbec, Feetech, Jetson quirks).

> **Important:** PyTorch and Torchvision **must** be installed according to your **CUDA / JetPack** version. LeRobot does **not** magically fix that for you.

---

## 1. Install Miniforge / Miniconda

You only need **one** of these paths depending on your hardware.

### 1.1 Generic Miniforge (any Linux)

This is the Hugging Face recommended Miniforge install:

```bash
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh
````

After installation, reload your shell:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

### 1.2 Jetson (Miniconda, aarch64)

If you are on **Jetson** and want to follow SeedStudio’s Miniconda route:

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
chmod +x Miniconda3-latest-Linux-aarch64.sh
./Miniconda3-latest-Linux-aarch64.sh
source ~/.bashrc
```

### 1.3 X86 Ubuntu 22.04 (Miniconda, x86_64)

If you are on **x86 Ubuntu 22.04** and prefer Miniconda:

```bash
mkdir -p ~/miniconda3
cd miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
conda init --all
```

---

## 2. Create the `lerobot` Conda Environment

Create a virtual environment with **Python 3.10**:

```bash
conda create -y -n lerobot python=3.10
```

Then **activate** your environment (you must do this every time you open a new shell):

```bash
conda activate lerobot
```

---

## 3. Install `ffmpeg` in the Environment

With the `lerobot` environment active, install ffmpeg:

```bash
conda install ffmpeg -c conda-forge
```

This usually installs **ffmpeg 7.X** for your platform compiled with the **libsvtav1** encoder.

If `libsvtav1` is not supported (check with `ffmpeg -encoders`), you can:

* **On any platform:** explicitly install a specific ffmpeg version:

  ```bash
  conda install ffmpeg=7.1.1 -c conda-forge
  ```

* **On Linux only:** install ffmpeg build dependencies and compile ffmpeg from source with `libsvtav1`, and make sure you use the corresponding ffmpeg binary (check with `which ffmpeg`).

---

## 4. System Dependencies (Linux)

If you encounter build errors or PyAV/ffmpeg-related issues, install these:

```bash
sudo apt-get install cmake build-essential python3-dev pkg-config \
  libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
  libswscale-dev libswresample-dev libavfilter-dev
```

For other systems, see the PyAV / ffmpeg compilation documentation.

---

## 5. Install PyTorch and Torchvision (GPU / CUDA)

> **Critical:** Environments such as **PyTorch** and **Torchvision** must be installed according to your **CUDA** (x86) or **JetPack** (Jetson). If you get this wrong, `torch.cuda.is_available()` will be `False` and GPU will be useless.

### 5.1 x86 Ubuntu (Conda + CUDA)

Go to [https://pytorch.org](https://pytorch.org) and use their install selector:

* OS: **Linux**
* Package: **Conda**
* Compute Platform: **your CUDA version** (e.g. CUDA 12.1)

They will give you a command similar to:

```bash
# EXAMPLE ONLY – use what pytorch.org gives you
conda install pytorch torchvision pytorch-cuda=12.1 -c pytorch -c nvidia
```

Run this **inside** the `lerobot` environment.

### 5.2 Jetson (JetPack)

If you are using a Jetson device, install PyTorch and Torchvision according to the official Jetson tutorial for your JetPack version.

---

## 6. Clone and Install LeRobot (From Source)

You have **two** relevant repos:

* Official 🤗 [**Hugging Face LeRobot**](https://huggingface.co/docs/lerobot/installation)
* SO101 / Orbbec fork from [**SeedStudio** (`ZhuYaoHui1998/lerobot`)](https://wiki.seeedstudio.com/lerobot_so100m/#install-lerobot)

### 6.1 Official Hugging Face LeRobot (Recommended Base)

Clone and install in editable mode:

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot

# Inside the lerobot conda environment
conda activate lerobot
pip install -e .
```

This allows you to contribute or modify the code and see changes immediately.

### 6.2 SeedStudio / SO101 Fork (Orbbec Gemini2)

If you are following SeedStudio’s SO101 setup:

```bash
git clone https://github.com/ZhuYaoHui1998/lerobot.git ~/lerobot
cd ~/lerobot
```

If you use the **Orbbec Gemini2 depth camera**:

```bash
cd ~/lerobot
git checkout orbbec
```

If you are **only using RGB cameras**, **do not** switch to the `orbbec` branch, otherwise dependency-related errors may occur. To revert back to the original version:

```bash
cd ~/lerobot
git checkout main
```

Now install LeRobot with Feetech motor support:

```bash
cd ~/lerobot
conda activate lerobot
pip install -e ".[feetech]"
```

---

## 7. Install LeRobot from PyPI (Alternative)

If you don’t care about editing the source and just want the package:

### 7.1 Core Library

```bash
pip install lerobot
```

This installs only the default dependencies.

### 7.2 Extra Features

To install additional functionality:

```bash
pip install "lerobot[all]"          # All available features
pip install "lerobot[aloha,pusht]"  # Specific features (Aloha & Pusht)
pip install "lerobot[feetech]"      # Feetech motor support
```

For LeRobot **0.4.0**, if you want to install **pi**:

```bash
pip install "lerobot[pi]@git+https://github.com/huggingface/lerobot.git"
```

For a full list of optional dependencies, see: [https://pypi.org/project/lerobot/](https://pypi.org/project/lerobot/)

---

## 8. Jetson-Specific Fixes (OpenCV / numpy / ffmpeg)

For **Jetson JetPack** devices (after you have installed PyTorch-GPU and Torchvision as in Section 5):

```bash
conda activate lerobot

# Install OpenCV and other dependencies via conda (JetPack 6.0+)
conda install -y -c conda-forge "opencv>=4.10.0.84"

# Remove conda OpenCV
conda remove opencv

# Install OpenCV via pip
pip3 install opencv-python==4.10.0.84

# Ensure ffmpeg via conda
conda install -y -c conda-forge ffmpeg

# Fix numpy version to match torchvision
conda uninstall numpy
pip3 install numpy==1.26.0
```

---

## 9. Check PyTorch and Torchvision After LeRobot Install

Installing LeRobot (especially via `pip`) can sometimes uninstall your original GPU-enabled PyTorch and Torchvision and replace them with CPU builds.

Always verify inside Python:

```python
import torch
print(torch.cuda.is_available())
```

If the printed result is `False`:

* Reinstall PyTorch and Torchvision according to the **official website** for your platform / CUDA.
* On Jetson, follow the Jetson-specific tutorial again.

---

## 10. Optional Dependencies and Extras

LeRobot provides optional extras for specific functionalities. Multiple extras can be combined (e.g. `.[aloha,feetech]`). For all available extras, refer to `pyproject.toml` in the repo.

### 10.1 Simulations

Install environment packages:

* `aloha` (gym-aloha)
* `pusht` (gym-pusht)

Example:

```bash
pip install -e ".[aloha]"   # or ".[pusht]" for example
```

### 10.2 Motor Control

For **Koch v1.1**, install the **Dynamixel** SDK.
For **SO100 / SO101 / Moss**, install the **Feetech** SDK.

```bash
pip install -e ".[feetech]"    # for Feetech motors (SO100/SO101/Moss)
pip install -e ".[dynamixel]"  # for Dynamixel motors (Koch v1.1)
```

### 10.3 Experiment Tracking (Weights & Biases)

If you want experiment tracking with Weights & Biases:

```bash
pip install wandb
wandb login
```

---

## 11. Final Sanity Check

With the `lerobot` environment active and your chosen LeRobot repo installed:

```bash
conda activate lerobot
python -c "import lerobot, torch; print('LeRobot OK, CUDA:', torch.cuda.is_available())"
```

You want:

* No errors or stack traces.
* Output like:

```text
LeRobot OK, CUDA: True
```

(if your machine has a GPU; `False` is expected only on pure CPU machines).

At this point, your **LeRobot installation is complete**. You can now:

* Assemble or connect your robot (SO100/SO101).
* Configure cameras (RGB or Orbbec Gemini2).
* Follow the hardware calibration, teleoperation, and imitation learning guides for your specific setup.


