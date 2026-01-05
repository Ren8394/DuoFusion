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

### 1. Install Dependencies
```bash
# Install system packages
sudo apt update
sudo apt install python3-picamera2 python3-gpiozero python3-spidev

# Install Python packages
pip install numpy pillow matplotlib
```

### 2. Connect Hardware
1. Install Camera Module 3 to CSI interface
2. Connect Thermal HAT to GPIO
3. Enable SPI and I2C: `sudo raspi-config`

### 3. Run Program
```bash
python main.py
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