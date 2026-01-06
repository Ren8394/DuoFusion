#!/usr/bin/env python3
"""
配置檔案 - 存放所有系統常數和預設值
Configuration file - Contains all system constants and default values

用途 (Purpose):
    集中管理所有可調整的參數，方便修改和維護
    Centrally manage all adjustable parameters for easy modification and maintenance

修改說明 (Modification Guide):
    - 如需調整 FPS，修改 DEFAULT_FPS (範圍: 1-25)
    - 如需調整解析度，修改 RGB_RESOLUTION 或 THERMAL_RESOLUTION
    - 如需調整儲存品質，修改 JPEG_QUALITY (範圍: 0-100)
    - 如需調整 SPI 速度，修改 SPI_SPEED (小心：過高可能導致通訊錯誤)
"""

import os

# ============================================================================
# 版本資訊 (Version Information)
# ============================================================================
VERSION = "1.0"

# ============================================================================
# 相機參數 (Camera Parameters)
# ============================================================================
# RGB 相機解析度 (RGB camera resolution)
# 修改說明: Camera Module 3 支援多種解析度，這是優化過的設定
RGB_RESOLUTION = (640, 640)

# 熱影像相機解析度 (Thermal camera resolution)
# 修改說明: MI0801/MI0802 感測器固定解析度，不建議修改
THERMAL_RESOLUTION = (80, 62)

# 預設 FPS (Default frame rate)
# 修改說明:
#   - 範圍: 1-25 FPS
#   - 實際上限受熱影像相機限制 (~25.5 FPS)
#   - 較高 FPS 需要更快的儲存速度
DEFAULT_FPS = 12

# ============================================================================
# 硬體通訊參數 (Hardware Communication Parameters)
# ============================================================================
# SPI 通訊速度 (SPI communication speed in Hz)
# 修改說明:
#   - 當前設定: 31.2 MHz (經測試穩定)
#   - 可嘗試範圍: 20-40 MHz
#   - 過高可能導致 CRC 錯誤或資料遺失
#   - 過低會增加每幀讀取時間
SPI_SPEED = 31200000  # 31.2 MHz

# I2C 設定 (I2C configuration)
# 修改說明: 樹莓派 I2C bus 編號和熱影像感測器地址
I2C_BUS = 1          # Raspberry Pi I2C bus number
I2C_ADDRESS = 0x40   # MI48 thermal sensor I2C address

# SPI 設定 (SPI configuration)
# 修改說明: 樹莓派 SPI bus 和 device 編號
SPI_BUS = 0          # Raspberry Pi SPI bus number
SPI_DEVICE = 0       # Raspberry Pi SPI device number
SPI_XFER_SIZE = 160  # SPI transfer size in bytes

# GPIO 引腳配置 (GPIO pin configuration)
# 修改說明: BCM 編號，根據實際接線修改
GPIO_SPI_CS = "BCM7"       # SPI Chip Select pin
GPIO_DATA_READY = "BCM24"  # Data Ready signal pin
GPIO_RESET = "BCM23"       # Reset signal pin

# ============================================================================
# 檔案儲存參數 (File Storage Parameters)
# ============================================================================
# JPEG 壓縮品質 (JPEG compression quality)
# 修改說明:
#   - 範圍: 0-100
#   - 60: 平衡品質與檔案大小 (建議值)
#   - 85+: 高品質，但檔案較大，寫入較慢
#   - 40-: 低品質，檔案小但影像品質差
JPEG_QUALITY = 60

# 預設儲存路徑 (Default save path)
# 修改說明: 最終錄製檔案的儲存位置
DEFAULT_SAVE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "records"
)

# RAM Disk 暫存路徑 (RAM disk temporary path)
# 修改說明:
#   - /dev/shm/ 是 Linux RAM disk，寫入速度極快
#   - 重開機後資料會消失，所以只用於暫存
#   - 確保 RAM 足夠（每分鐘約 100-200 MB）
TEMP_PATH = "/dev/shm/duofusion_recordings"

# ============================================================================
# 效能調校參數 (Performance Tuning Parameters)
# ============================================================================
# 跳幀容忍度 (Frame drop tolerance)
# 修改說明:
#   - 當延遲超過 (容忍度 × 幀間隔) 時跳過該幀
#   - 1.2: 延遲超過 1.2 個幀間隔時跳幀
#   - 較大值: 較不容易跳幀，但可能累積延遲
#   - 較小值: 較容易跳幀，但時間精度較好
FRAME_TOLERANCE = 1.2

# 時間戳記批次大小 (Timestamp batch size)
# 修改說明:
#   - 每累積 N 個時間戳記才寫入檔案
#   - 較大值: 減少磁碟 I/O 次數，但遺失風險較高
#   - 較小值: 更即時，但 I/O 負擔較重
TIMESTAMP_BATCH_SIZE = 50

# 執行緒池大小 (Thread pool size)
# 修改說明:
#   - CAPTURE_WORKERS: 相機擷取執行緒數（2 = RGB + Thermal 並行）
#   - SAVE_WORKERS: 檔案儲存執行緒數（2 = RGB + Thermal 並行儲存）
CAPTURE_WORKERS = 2
SAVE_WORKERS = 2

# ============================================================================
# 時序參數 (Timing Parameters)
# ============================================================================
# 精確睡眠閾值 (Precise sleep threshold in seconds)
# 修改說明:
#   - 當需要等待時間 > SLEEP_THRESHOLD 時使用一般 sleep
#   - 當需要等待時間 < SLEEP_THRESHOLD 時使用忙等待
#   - 較大值: CPU 使用率較低，但精度較差
#   - 較小值: CPU 使用率較高，但精度較好
SLEEP_THRESHOLD = 0.001         # 1 ms
SLEEP_MARGIN = 0.0005           # 0.5 ms safety margin
BUSY_WAIT_INTERVAL = 0.0001     # 0.1 ms busy wait interval

# 同步品質閾值 (Synchronization quality thresholds in milliseconds)
# 修改說明: 定義同步品質的判斷標準
SYNC_EXCELLENT = 5.0   # < 5 ms: 優秀
SYNC_GOOD = 10.0       # 5-10 ms: 良好
SYNC_FAIR = 20.0       # 10-20 ms: 普通
# > 20 ms: 需改善

# ============================================================================
# MI48 熱影像感測器參數 (MI48 Thermal Sensor Parameters)
# ============================================================================
# 發射率 (Emissivity)
# 修改說明:
#   - 範圍: 0.01-1.0
#   - 1.0: 黑體輻射（大部分物體）
#   - 0.95: 人體皮膚
#   - 0.3-0.5: 金屬表面
DEFAULT_EMISSIVITY = 0.98

# 濾波器設定 (Filter settings)
# 修改說明:
#   - ENABLE_FILTER_F1: 時域濾波器（減少時間雜訊）
#   - ENABLE_FILTER_F2: 滾動平均濾波器（平滑影像）
#   - ENABLE_FILTER_F3: 中值濾波器（去除突波）
ENABLE_FILTER_F1 = True
ENABLE_FILTER_F2 = True
ENABLE_FILTER_F3 = False

# 溫度偏移校正 (Temperature offset correction in Kelvin)
# 修改說明:
#   - 範圍: -6.4 到 +6.35 K
#   - 用於校正感測器系統性偏差
DEFAULT_OFFSET_CORR = 0.0

# ============================================================================
# 狀態監控參數 (Status Monitoring Parameters)
# ============================================================================
# 歷史記錄長度 (History buffer length)
# 修改說明: 保留最近 N 個數據用於計算平均值和趨勢
SYNC_HISTORY_LENGTH = 100
TIMING_ERROR_HISTORY_LENGTH = 100

# 顯示更新間隔 (Display update interval in seconds)
# 修改說明: 錄製時狀態顯示的更新頻率
DISPLAY_UPDATE_INTERVAL = 0.05  # 50 ms

# ============================================================================
# 日誌設定 (Logging Configuration)
# ============================================================================
# 日誌目錄 (Log directory)
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs"
)

# 日誌等級 (Log level)
# 修改說明:
#   - ERROR: 只記錄錯誤
#   - WARNING: 記錄警告和錯誤
#   - INFO: 記錄一般資訊、警告和錯誤
#   - DEBUG: 記錄所有詳細資訊（除錯用）
import logging
LOG_LEVEL = logging.ERROR

# ============================================================================
# 檔案輸出格式 (File Output Format)
# ============================================================================
# RGB 影像格式 (RGB image format)
RGB_FORMAT = "JPEG"
RGB_EXTENSION = ".jpg"

# 熱影像資料格式 (Thermal data format)
# 修改說明:
#   - NPY: NumPy 二進位格式（推薦）
#     優點: 儲存快 2-4倍，檔案小 40%，讀取快 5-10倍
#     缺點: 無法用文字編輯器查看
#   - CSV: 純文字格式
#     優點: 可用 Excel/文字編輯器查看
#     缺點: 儲存慢，檔案大，讀取慢
THERMAL_FORMAT = "NPY"
THERMAL_EXTENSION = ".npy"
THERMAL_DTYPE = "float32"  # float32 足夠精度且省空間

# 時間戳記格式 (Timestamp format)
TIMESTAMP_EXTENSION = ".txt"
SESSION_INFO_EXTENSION = ".txt"

# 檔案命名格式 (File naming format)
# 修改說明: 使用 6 位數補零的索引 (000000, 000001, ...)
FRAME_INDEX_FORMAT = "{:06d}"

# 錄製資料夾時間戳記格式 (Recording folder timestamp format)
# 修改說明: 格式 YYYYMMDD_HHMMSS
FOLDER_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# ============================================================================
# 使用範例 (Usage Example)
# ============================================================================
"""
在其他模組中使用配置:

    from utils.config import DEFAULT_FPS, RGB_RESOLUTION

    fps = DEFAULT_FPS
    resolution = RGB_RESOLUTION

如果需要在執行時修改配置:

    import utils.config as config
    config.DEFAULT_FPS = 10
    config.JPEG_QUALITY = 80
"""
