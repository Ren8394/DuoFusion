# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DuoFusion is a dual-camera recording system for Raspberry Pi that synchronizes capture from:
- **RGB Camera**: Raspberry Pi Camera Module 3 (800x600 resolution)
- **Thermal Camera**: Thermal-90 Camera HAT with MI48 thermal imaging processor (80x62 resolution)

The system achieves precise frame-level synchronization using high-speed SPI communication (31.2 MHz), nanosecond-precision timing, and RAM disk buffering for optimal I/O performance.

**Platform Requirement**: This application MUST run on a Raspberry Pi with the specific hardware attached. It will not run on standard development machines.

## Running the Application

### Main Commands

```bash
# Run the dual-camera recording system (requires Raspberry Pi hardware)
python main.py

# The application is interactive - commands within the application:
# - Press Enter: Start/stop recording
# - Press 's': Show status
# - Press 'q' or ESC: Quit program
```

### Dependencies Management

This project uses `uv` for dependency management:

```bash
# Install dependencies (from pyproject.toml)
uv sync

# Run with uv
uv run python main.py
```

### PySenXor Library

The thermal camera interface is provided by the included `pysenxor-master/` library:
- Located in: `pysenxor-master/senxor/`
- Main module: `mi48.py` - MI48 thermal imaging processor interface
- Interfaces: `interfaces.py` - SPI and I2C communication wrappers
- Utilities: `utils.py` - Data conversion and filtering utilities
- Examples: `pysenxor-master/example/` - Reference implementations

## Architecture

### High-Level Structure

**Main Application (`main.py`)**:
- `DuoFusion` class: Central orchestrator for dual-camera recording
- `TimestampBuffer` class: Batched I/O for timestamp logging

**Hardware Abstraction**:
- RGB Camera: Via `picamera2` library (Raspberry Pi Camera Module 3)
- Thermal Camera: Via custom `senxor.mi48` library (MI48 processor with SPI/I2C)
- GPIO Control: Via `gpiozero` for chip select and data-ready signals

**Recording Pipeline**:
1. **Initialization**: Camera configuration and hardware interface setup
2. **Synchronization Loop**: Nanosecond-precision frame scheduling at target FPS
3. **Parallel Capture**: ThreadPoolExecutor for concurrent RGB/thermal frame acquisition
4. **Buffered I/O**: Temporary storage in `/dev/shm/` (RAM disk), batched timestamp writes
5. **Post-Processing**: Move completed recordings to final storage with session metadata

### Key Technical Details

**Timing System**:
- Uses `time.time_ns()` for nanosecond-precision timestamps
- Custom `precise_sleep()` function for sub-millisecond accuracy
- Frame scheduling based on absolute target times (not relative delays)
- Frame drop tolerance: 1.2× frame interval (configurable via `frame_tolerance`)

**SPI Communication**:
- Speed: 31.2 MHz (`spi_speed = 31200000`)
- Mode: 0b00 (CPOL=0, CPHA=0)
- Manual chip select via GPIO (BCM7) for precise control
- Data-ready signal via GPIO (BCM24) for frame availability detection

**Synchronization Quality Metrics**:
- Tracks inter-camera timing differences (`sync_history`)
- Monitors frame timing errors (`timing_errors`)
- Real-time quality indicators: <5ms (excellent), 5-10ms (good), 10-20ms (fair), >20ms (poor)

**Thread Architecture**:
- `capture_executor`: 2 worker threads for parallel camera frame acquisition
- `save_executor`: 2 worker threads for asynchronous file I/O
- `recording_thread`: Main recording loop with precise timing control

**File Output Structure**:
```
records/
└── YYYYMMDD_HHMMSS/
    ├── RGB/
    │   ├── 000000.jpg
    │   ├── 000001.jpg
    │   └── ...
    ├── Thermal/
    │   ├── 000000.npy (NumPy binary format with temperature values)
    │   ├── 000001.npy
    │   └── ...
    ├── timestamps.txt (CSV with sync metadata)
    └── session_info.txt (recording summary)
```

**Thermal Data Format**:
- **Format**: NPY (NumPy binary) - Fast, compact, preserves precision
- **Size**: ~20 KB per frame (40% smaller than CSV)
- **Speed**: 2-4× faster write, 5-10× faster read than CSV
- **Precision**: float32 (sufficient for thermal imaging)
- **Reading**: `data = np.load('000000.npy')`
- **Tools**: See `utils/thermal_reader.py` for analysis utilities

### MI48 Thermal Camera Details

**Register Configuration** (from `pysenxor-master/senxor/mi48.py`):
- `FRAME_MODE`: Controls capture and streaming (0xB1)
- `FRAME_RATE`: FPS divisor register (0xB4)
- `EMISSIVITY`: Temperature conversion parameter (0xCA)
- `FILTER_CTRL`: Enable/disable temporal and spatial filters (0xD0)
- `STATUS`: Data ready, capture errors, bootup state (0xB6)

**Initialization Sequence** (see `DuoFusion.init_cameras()` in main.py:145-222):
1. I2C interface setup (SMBus on bus 1, address 0x40)
2. SPI interface setup (bus 0, device 0, custom chip select)
3. GPIO configuration (CS on BCM7, data-ready on BCM24, reset on BCM23)
4. MI48 reset and bootup sequence
5. FPS and emissivity configuration
6. Filter enable (F1 and F2 enabled for firmware v2+)

**Frame Data Format**:
- Raw data: 16-bit integers (temperature × 10 in Kelvin)
- Converted: `np.float16` in Celsius via `data / 10.0 + KELVIN_0` (-273.15°C)
- Optional header: Frame counter, timestamp, VDD, sensor temp, min/max, CRC-16

## Development Notes

### Error Handling

The application includes comprehensive error handling:
- Signal handlers for graceful shutdown (SIGINT, SIGTERM)
- Terminal state restoration on exit
- Automatic cleanup of temporary files on errors
- Error logging to `logs/error_YYYYMMDD_HHMMSS.txt` with stack traces

### Performance Considerations

- **RAM Disk**: Uses `/dev/shm/` for temporary storage to minimize I/O latency
- **Batched Writes**: Timestamp data buffered (50 frames) before disk writes
- **JPEG Quality**: Set to 60 for balance between quality and write speed
- **Frame Tolerance**: Drops frames if >1.2× frame interval late (prevents cascade delays)

### Hardware Dependencies

Required Raspberry Pi packages:
- `picamera2`: Raspberry Pi camera interface
- `gpiozero`: GPIO control for chip select and data-ready signals
- `smbus`: I2C communication
- `spidev`: SPI communication (not in pyproject.toml but required)

Standard packages (in `pyproject.toml`):
- `numpy`: Array operations and thermal data processing
- `opencv-python`: Image processing
- `matplotlib`: Plotting utilities
- `cmapy`: Colormap support for thermal visualization
- `crcmod`: CRC-16 validation for thermal data frames
- `pyserial`: Serial communication utilities

### Configuration Parameters

Key parameters in `utils/config.py`:
- `DEFAULT_FPS`: 8 FPS (adjustable 1-25 FPS, limited by thermal camera max ~25.5 FPS)
- `RGB_RESOLUTION`: (800, 600) - Fixed for Camera Module 3
- `THERMAL_RESOLUTION`: (80, 62) - Fixed for MI0801/MI0802 sensor
- `JPEG_QUALITY`: 60 (range 0-100)
- `SPI_SPEED`: 31200000 Hz (31.2 MHz)
- `FRAME_TOLERANCE`: 1.2 (multiplier for frame drop threshold)
- `THERMAL_FORMAT`: "NPY" (NumPy binary format)
- `THERMAL_DTYPE`: "float32" (data type for thermal storage)

## Modular Architecture (Refactored v1.0)

The codebase has been refactored into a modular structure for better maintainability:

### Core Modules (`core/`)

**`duo_fusion.py`** - Main Application Class
- Orchestrates all subsystems
- Handles program flow and user interaction
- Coordinates camera, recorder, and file manager

**`camera_manager.py`** - Camera Management
- RGB camera initialization and capture (Picamera2)
- Thermal camera initialization and capture (MI48)
- GPIO and SPI/I2C communication handling

**`recorder.py`** - Recording Control
- Precise timing control with nanosecond accuracy
- Parallel frame capture using ThreadPoolExecutor
- Synchronization quality monitoring
- Frame drop logic

**`file_manager.py`** - File I/O Operations
- Directory structure creation
- RGB (JPEG) and Thermal (NPY) data saving
- RAM disk to permanent storage migration
- Session info and error logging

**`timestamp_buffer.py`** - Timestamp Buffering
- Batched timestamp writes to reduce I/O
- Records timing and sync metadata

### Utility Modules (`utils/`)

**`config.py`** - Configuration Hub
- All adjustable parameters in one place
- Extensive Chinese comments explaining each setting
- Easy modification without touching code

**`timing.py`** - Timing Utilities
- Nanosecond-precision timestamps (`get_precise_timestamp()`)
- Microsecond-precision sleep (`precise_sleep()`)
- Timing statistics calculation

**`display.py`** - Display and UI
- Terminal interface and formatting
- User input handling
- Status display and progress monitoring

**`thermal_reader.py`** - Thermal Data Analysis
- Load NPY thermal frames
- Temperature statistics
- Hot spot detection
- Batch conversion to images
- Export to CSV for Excel compatibility

### How to Modify

**To change camera settings:**
- Edit `utils/config.py` for parameters
- Edit `core/camera_manager.py` for camera logic

**To change recording behavior:**
- Edit `utils/config.py` for timing parameters
- Edit `core/recorder.py` for recording loop logic

**To change file operations:**
- Edit `utils/config.py` for file formats
- Edit `core/file_manager.py` for save/load logic

**To change display:**
- Edit `utils/display.py` for UI functions

## Reading Thermal Data

### Basic Reading

```python
import numpy as np

# Load a single frame
data = np.load('records/20241021_120000/Thermal/000000.npy')
print(f"Temperature range: {data.min():.1f} - {data.max():.1f}°C")
```

### Using Thermal Reader Utilities

```python
from utils.thermal_reader import load_thermal_frame, get_temperature_stats

# Load and analyze
data = load_thermal_frame('Thermal/000000.npy')
stats = get_temperature_stats(data)
print(f"Mean: {stats['mean']:.1f}°C, Std: {stats['std']:.2f}°C")

# Find hot spots
from utils.thermal_reader import find_hot_spots
hot_spots = find_hot_spots(data, top_n=5)
for row, col, temp in hot_spots:
    print(f"Hot spot at ({row}, {col}): {temp:.1f}°C")

# Batch load sequence
from utils.thermal_reader import load_thermal_sequence
frames = load_thermal_sequence('records/20241021/Thermal', end_idx=100)
print(f"Loaded {len(frames)} frames")
```

### Converting to CSV (for Excel)

```python
from utils.thermal_reader import export_to_csv

data = np.load('000000.npy')
export_to_csv(data, '000000.csv')
# Now open with Excel or any text editor
```
