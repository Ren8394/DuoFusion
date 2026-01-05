# DuoFusion

**Dual Camera Recording System** - High-precision synchronised recording solution for Raspberry Pi

## Features

- 🎥 **Dual Camera Synchronisation**: RGB Camera Module 3 + Thermal-90 Camera HAT
- ⚡ **High Performance**: RAM disk optimisation, precise timing control
- 📊 **Complete Data**: Timestamp tracking, statistical analysis
- 🛠️ **Easy to Use**: Simple command-line interface

## Hardware Requirements

- Raspberry Pi 4 or 5
- Raspberry Pi Camera Module 3
- Thermal-90 Camera HAT with MI48
- MicroSD card (32GB+)

## Quick Start

### 1. Environment Setup
```bash
# Use uv Python 3.13
uv python pin 3.13

# Download pysenxor-master
# Download from: https://files.waveshare.com/wiki/common/Thermal_Camera_Hat.zip
```

### 2. Install Dependencies
```bash
# Install system packages
sudo apt update
sudo apt install python3-picamera2 python3-gpiozero python3-spidev

# Install Python packages with uv
uv add cmapy crcmod gpiod pyserial smbus matplotlib numpy opencv-python

# Install pysenxor (use 'from senxor import ...')
uv pip install -e ./pysenxor-master
```

**Note for Raspberry Pi:** To use system-installed packages like picamera2 in uv's venv, set `include-system-site-packages = true` in `.venv/pyvenv.cfg`, or create venv with: `uv venv --system-site-packages`

### 3. Connect Hardware
1. Install Camera Module 3 to CSI interface
2. Connect Thermal HAT to GPIO
3. Enable SPI and I2C: `sudo raspi-config`

### 4. Run Program
```bash
uv run python main.py
```

## Usage Instructions

1. After starting the program, set FPS and save path
2. Press `Enter` to start recording
3. Press `Enter` again to stop recording
4. Press `q` to exit program

## Recording Results

Data will be saved in the `records/` folder:
```
records/
└── 20241021_143022/
    ├── RGB/          # JPEG images
    ├── Thermal/      # NPY data
    ├── timestamps.txt
    └── session_info.txt
```

## Configuration Options

Edit `utils/config.py` to modify settings:

```python
DEFAULT_FPS = 12          # Frame rate (1-25)
JPEG_QUALITY = 60         # Image quality (0-100)
SPI_SPEED = 31200000      # SPI speed
```

## Common Issues

### Camera Initialisation Failed
- Check Camera Module connection
- Confirm Thermal HAT GPIO connection
- Verify SPI/I2C are enabled

### Stuttering During Recording
- Reduce FPS
- Use SSD storage
- Check system resource usage

### Insufficient Storage Space
- Reduce JPEG_QUALITY
- Use external hard drive
- Clean up old recording data

## Licence

MIT Licence