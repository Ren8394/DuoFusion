#!/usr/bin/env python3
"""
相機管理模組 (Camera Manager Module)

用途 (Purpose):
    管理 RGB 相機和熱影像相機的初始化、配置和幀擷取
    封裝所有與硬體相關的操作，提供統一的介面

主要類別 (Main Class):
    CameraManager: 相機管理器，負責雙相機的控制

硬體需求 (Hardware Requirements):
    - Raspberry Pi Camera Module 3 (RGB)
    - Thermal-90 Camera HAT with MI48 processor (Thermal)
    - 必須在 Raspberry Pi 上執行

修改說明 (Modification Guide):
    - 如需調整相機參數，修改 utils/config.py
    - 如需變更 GPIO 配置，修改 config.py 中的 GPIO_* 常數
    - 如需調整熱影像濾波器，修改 _configure_thermal_filters()
"""

import time
import logging
import numpy as np
from typing import Optional, Tuple, Dict, Any

# 導入配置
from utils.config import (
    RGB_RESOLUTION, THERMAL_RESOLUTION, SPI_SPEED,
    I2C_BUS, I2C_ADDRESS, SPI_BUS, SPI_DEVICE, SPI_XFER_SIZE,
    GPIO_SPI_CS, GPIO_DATA_READY, GPIO_RESET,
    DEFAULT_EMISSIVITY, ENABLE_FILTER_F1, ENABLE_FILTER_F2, ENABLE_FILTER_F3,
    DEFAULT_OFFSET_CORR
)
from utils.timing import get_precise_timestamp

# 樹莓派硬體套件（只在 Raspberry Pi 上可用）
try:
    from picamera2 import Picamera2
    from senxor.mi48 import MI48
    from senxor.utils import data_to_frame
    from senxor.interfaces import SPI_Interface, I2C_Interface
    from smbus import SMBus
    from spidev import SpiDev
    from gpiozero import DigitalInputDevice, DigitalOutputDevice
except ImportError as e:
    print(f"錯誤: 無法導入硬體相關套件 - {e}")
    print("此程式需要在 Raspberry Pi 上執行")
    raise


class CameraManager:
    """
    相機管理器

    用途 (Purpose):
        統一管理 RGB 和熱影像相機的初始化、配置和幀擷取
        提供高層次的 API，隱藏底層硬體細節

    屬性 (Attributes):
        picam2 (Picamera2): RGB 相機物件
        mi48 (MI48): 熱影像處理器物件
        mi48_spi_cs (DigitalOutputDevice): SPI 晶片選擇 GPIO
        rgb_resolution (tuple): RGB 解析度
        thermal_resolution (tuple): 熱影像解析度
        spi_speed (int): SPI 通訊速度

    使用範例 (Usage Example):
        >>> manager = CameraManager()
        >>> if manager.init_cameras(fps=8):
        ...     rgb, rgb_timing = manager.grab_rgb_frame()
        ...     thermal, thermal_timing = manager.read_thermal_frame_with_timing()
        ...     manager.cleanup()
    """

    def __init__(self):
        """
        初始化相機管理器

        說明 (Description):
            只初始化變數，不進行硬體初始化
            實際的硬體初始化在 init_cameras() 中進行
        """
        # 相機物件
        self.picam2: Optional[Picamera2] = None
        self.mi48: Optional[MI48] = None
        self.mi48_spi_cs: Optional[DigitalOutputDevice] = None

        # 從配置讀取參數
        self.rgb_resolution = RGB_RESOLUTION
        self.thermal_resolution = THERMAL_RESOLUTION
        self.spi_speed = SPI_SPEED

        # 日誌設定
        logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
        logging.getLogger('picamera2').setLevel(logging.ERROR)
        logging.getLogger('senxor').setLevel(logging.ERROR)

    def init_cameras(self, fps: int) -> bool:
        """
        初始化雙相機系統

        參數 (Args):
            fps (int): 目標 FPS (1-25)

        返回 (Returns):
            bool: True 表示初始化成功，False 表示失敗

        初始化流程 (Initialization Flow):
            1. 初始化 RGB 相機 (Camera Module 3)
            2. 初始化熱影像相機的 I2C 介面
            3. 初始化熱影像相機的 SPI 介面
            4. 配置 GPIO（晶片選擇、資料就緒、重置）
            5. 初始化 MI48 處理器
            6. 重置 MI48
            7. MI48 開機程序
            8. 設定 FPS 和發射率
            9. 啟用濾波器
            10. 測試熱影像讀取

        錯誤處理 (Error Handling):
            任何步驟失敗都會印出錯誤訊息並返回 False
            不會拋出例外，方便上層程式處理

        修改說明 (Modification Guide):
            - 修改 RGB 解析度: 調整 config.RGB_RESOLUTION
            - 修改 SPI 速度: 調整 config.SPI_SPEED
            - 修改 GPIO 引腳: 調整 config.GPIO_* 常數
            - 修改濾波器設定: 調整 _configure_thermal_filters()
        """
        print("\n正在初始化相機...")

        try:
            # ============================================================
            # 步驟 1: 初始化 RGB 相機
            # ============================================================
            print("- 初始化 RGB Camera Module 3...")
            self.picam2 = Picamera2()

            # 配置解析度
            camera_config = self.picam2.create_still_configuration(
                main={"size": self.rgb_resolution}
            )
            self.picam2.configure(camera_config)
            self.picam2.start()

            print(f"  ✓ RGB 相機就緒 (解析度: {self.rgb_resolution})")

            # ============================================================
            # 步驟 2-4: 初始化熱影像相機介面
            # ============================================================
            print("- 初始化 Thermal-90 Camera HAT...")

            # I2C 介面（用於控制暫存器）
            i2c = I2C_Interface(SMBus(I2C_BUS), I2C_ADDRESS)

            # SPI 介面（用於讀取影像資料）
            spi = SPI_Interface(SpiDev(SPI_BUS, SPI_DEVICE), xfer_size=SPI_XFER_SIZE)
            spi.device.mode = 0b00  # CPOL=0, CPHA=0
            spi.device.max_speed_hz = self.spi_speed
            spi.device.bits_per_word = 8
            spi.device.lsbfirst = False
            spi.cshigh = True
            spi.no_cs = True  # 手動控制 CS

            # GPIO 設定
            # CS (Chip Select): 手動控制 SPI 晶片選擇
            self.mi48_spi_cs = DigitalOutputDevice(
                GPIO_SPI_CS,
                active_high=False,
                initial_value=False
            )

            # Data Ready: 熱影像資料準備好的訊號
            mi48_data_ready = DigitalInputDevice(
                GPIO_DATA_READY,
                pull_up=False
            )

            # Reset: 重置 MI48 處理器
            mi48_reset = DigitalOutputDevice(
                GPIO_RESET,
                active_high=False,
                initial_value=True
            )

            # ============================================================
            # 步驟 5-7: 初始化和重置 MI48
            # ============================================================
            # 建立 MI48 物件
            self.mi48 = MI48(
                [i2c, spi],
                data_ready=mi48_data_ready,
                reset_handler=lambda: self._reset_mi48(mi48_reset)
            )

            # 執行硬體重置
            self._reset_mi48(mi48_reset)
            time.sleep(0.1)

            # 執行開機程序（bootup）
            self.mi48.bootup(verbose=True)

            # ============================================================
            # 步驟 8: 設定 FPS 和發射率
            # ============================================================
            self.mi48.set_fps(fps)
            self.mi48.set_emissivity(DEFAULT_EMISSIVITY)

            # ============================================================
            # 步驟 9: 配置濾波器
            # ============================================================
            self._configure_thermal_filters()

            # ============================================================
            # 步驟 10: 啟動串流並測試讀取
            # ============================================================
            self.mi48.start(stream=True, with_header=True)

            print(f"  ✓ 熱影像相機就緒 (解析度: {self.thermal_resolution}, SPI: {self.spi_speed//1000000}MHz)")

            # 測試讀取
            print("- 測試熱影像讀取...")
            test_data = self.read_thermal_frame()
            if test_data is not None:
                temp_avg = np.mean(test_data)
                print(f"  ✓ 測試成功 (平均溫度: {temp_avg:.1f}°C)")
            else:
                raise Exception("熱影像測試讀取失敗")

            print("\n✓ 所有相機初始化完成！")
            return True

        except Exception as e:
            print(f"\n✗ 相機初始化失敗: {str(e)}")
            return False

    def _reset_mi48(
        self,
        reset_pin: DigitalOutputDevice,
        assert_seconds: float = 0.000035,
        deassert_seconds: float = 0.050
    ) -> None:
        """
        重置 MI48 熱影像處理器

        參數 (Args):
            reset_pin (DigitalOutputDevice): 重置引腳
            assert_seconds (float): 重置訊號持續時間（秒）
                - 預設 35 微秒，符合 MI48 規格
            deassert_seconds (float): 重置後等待時間（秒）
                - 預設 50 毫秒，等待 MI48 重新啟動

        原理 (Principle):
            MI48 使用低電位觸發重置（active-low）
            1. 將 reset pin 拉高（觸發重置）
            2. 等待 assert_seconds
            3. 將 reset pin 拉低（結束重置）
            4. 等待 deassert_seconds 讓 MI48 完成開機

        修改說明 (Modification Guide):
            如果 MI48 重置不穩定，可以增加 deassert_seconds
            不建議修改 assert_seconds，除非有特殊需求
        """
        reset_pin.on()  # 觸發重置（active-low，所以 on = low）
        time.sleep(assert_seconds)
        reset_pin.off()  # 結束重置
        time.sleep(deassert_seconds)

    def _configure_thermal_filters(self) -> None:
        """
        配置熱影像濾波器

        濾波器說明 (Filter Description):
            - Filter F1: 時域濾波器（Temporal Filter）
                用途: 減少時間上的雜訊，平滑溫度變化
                適用: 靜態場景或緩慢移動的物體

            - Filter F2: 滾動平均濾波器（Rolling Average）
                用途: 計算多幀平均，減少隨機雜訊
                適用: 提升影像品質，但會增加延遲

            - Filter F3: 中值濾波器（Median Filter）
                用途: 去除突波雜訊（hot/dead pixels）
                適用: 感測器有壞點時使用

        韌體版本檢查 (Firmware Version Check):
            只有 MI48 韌體版本 >= 2.x 才支援濾波器設定
            版本 1.x 會跳過濾波器配置

        修改說明 (Modification Guide):
            修改 config.py 中的:
            - ENABLE_FILTER_F1
            - ENABLE_FILTER_F2
            - ENABLE_FILTER_F3

            如需調整濾波器強度，需要呼叫:
            - self.mi48.set_filter_1(setting)
            - self.mi48.set_filter_2(setting)
        """
        try:
            # 檢查韌體版本
            fw_version = self.mi48.fw_version
            major_version = int(fw_version[0])

            # 只有版本 2.x 以上支援濾波器
            if major_version >= 2:
                # 啟用濾波器
                self.mi48.enable_filter(
                    f1=ENABLE_FILTER_F1,
                    f2=ENABLE_FILTER_F2,
                    f3=ENABLE_FILTER_F3
                )

                # 設定溫度偏移校正
                self.mi48.set_offset_corr(DEFAULT_OFFSET_CORR)

                print(f"  ✓ 濾波器已配置 (F1:{ENABLE_FILTER_F1}, F2:{ENABLE_FILTER_F2}, F3:{ENABLE_FILTER_F3})")
            else:
                print(f"  ⚠ 韌體版本 {fw_version} 不支援濾波器設定")

        except Exception as e:
            # 濾波器設定失敗不影響基本功能
            print(f"  ⚠ 濾波器配置失敗: {e}")

    def grab_rgb_frame(self) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """
        擷取一幀 RGB 影像

        返回 (Returns):
            tuple: (rgb_array, timing_info)
                - rgb_array (np.ndarray): RGB 影像陣列，shape=(height, width, 3)
                - timing_info (dict): 時序資訊
                    - start_ns: 開始擷取時間（奈秒）
                    - end_ns: 結束擷取時間（奈秒）
                    - duration_ms: 擷取耗時（毫秒）

            失敗時返回 (None, None)

        使用範例 (Usage Example):
            >>> rgb, timing = manager.grab_rgb_frame()
            >>> if rgb is not None:
            ...     print(f"擷取耗時: {timing['duration_ms']:.2f} ms")
            ...     print(f"影像尺寸: {rgb.shape}")

        錯誤處理 (Error Handling):
            擷取失敗時印出錯誤訊息並返回 (None, None)
            不會拋出例外，避免中斷錄製流程

        修改說明 (Modification Guide):
            如需調整曝光、白平衡等參數，在 init_cameras() 的
            camera_config 中設定
        """
        try:
            # 記錄開始時間
            start_time_ns = get_precise_timestamp()

            # 擷取影像
            rgb_array = self.picam2.capture_array("main")

            # 記錄結束時間
            end_time_ns = get_precise_timestamp()

            # 計算耗時
            timing_info = {
                'start_ns': start_time_ns,
                'end_ns': end_time_ns,
                'duration_ms': (end_time_ns - start_time_ns) / 1e6
            }

            return rgb_array, timing_info

        except Exception as e:
            print(f"RGB 擷取失敗: {e}")
            return None, None

    def read_thermal_frame(self) -> Optional[np.ndarray]:
        """
        讀取一幀熱影像（不含時序資訊）

        返回 (Returns):
            np.ndarray: 溫度資料陣列（攝氏度），shape=(rows, cols)
            失敗時返回 None

        用途 (Purpose):
            簡化版的熱影像讀取，當不需要時序資訊時使用

        使用範例 (Usage Example):
            >>> thermal = manager.read_thermal_frame()
            >>> if thermal is not None:
            ...     print(f"最高溫度: {thermal.max():.1f}°C")
            ...     print(f"最低溫度: {thermal.min():.1f}°C")
        """
        try:
            thermal_data, _ = self.read_thermal_frame_with_timing()
            return thermal_data
        except Exception:
            return None

    def read_thermal_frame_with_timing(self) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """
        讀取一幀熱影像（含時序資訊）

        返回 (Returns):
            tuple: (thermal_data, timing_info)
                - thermal_data (np.ndarray): 溫度陣列（°C），shape=(rows, cols)
                - timing_info (dict): 時序資訊
                    - start_ns: 開始讀取時間（奈秒）
                    - end_ns: 結束讀取時間（奈秒）
                    - duration_ms: 讀取耗時（毫秒）

            失敗時返回 (None, None)

        讀取流程 (Read Flow):
            1. 記錄開始時間
            2. 等待 Data Ready 訊號
            3. 啟用 SPI Chip Select
            4. 透過 SPI 讀取資料
            5. 停用 SPI Chip Select
            6. 將原始資料轉換為溫度陣列
            7. 記錄結束時間
            8. 計算耗時

        資料格式 (Data Format):
            MI48 輸出的原始資料為 16-bit 整數
            轉換公式: temperature_celsius = (raw / 10.0) - 273.15

        使用範例 (Usage Example):
            >>> thermal, timing = manager.read_thermal_frame_with_timing()
            >>> if thermal is not None:
            ...     print(f"讀取耗時: {timing['duration_ms']:.2f} ms")
            ...     print(f"平均溫度: {thermal.mean():.1f}°C")

        錯誤處理 (Error Handling):
            任何步驟失敗都返回 (None, None)
            不會拋出例外，避免中斷錄製流程

        修改說明 (Modification Guide):
            如需調整 SPI 速度，修改 config.SPI_SPEED
            如需調整超時時間，修改 data_ready.wait_for_active() 的參數
        """
        try:
            # 記錄開始時間
            start_time_ns = get_precise_timestamp()

            # 等待資料準備好
            if hasattr(self.mi48, 'data_ready'):
                self.mi48.data_ready.wait_for_active()

            # SPI 通訊（手動控制 CS）
            self.mi48_spi_cs.on()  # 啟用 CS（active-low）
            data, _ = self.mi48.read()  # 讀取資料（忽略 header）
            self.mi48_spi_cs.off()  # 停用 CS

            # 檢查資料有效性
            if data is None:
                return None, None

            # 轉換為溫度陣列
            thermal_data = data_to_frame(data, self.mi48.fpa_shape)

            # 記錄結束時間
            end_time_ns = get_precise_timestamp()

            # 計算耗時
            timing_info = {
                'start_ns': start_time_ns,
                'end_ns': end_time_ns,
                'duration_ms': (end_time_ns - start_time_ns) / 1e6
            }

            return thermal_data, timing_info

        except Exception as e:
            print(f"熱影像讀取失敗: {e}")
            return None, None

    def cleanup(self) -> None:
        """
        清理相機資源

        清理流程 (Cleanup Flow):
            1. 停止 RGB 相機
            2. 停止熱影像相機
            3. 關閉 GPIO

        用途 (Purpose):
            程式結束時釋放硬體資源
            避免資源洩漏和硬體鎖定

        使用範例 (Usage Example):
            >>> manager = CameraManager()
            >>> manager.init_cameras(fps=8)
            >>> # ... 使用相機 ...
            >>> manager.cleanup()

        注意事項 (Notes):
            cleanup() 後無法再使用相機，需要重新 init_cameras()
        """
        # 停止 RGB 相機
        try:
            if self.picam2:
                self.picam2.stop()
                print("✓ RGB 相機已停止")
        except Exception as e:
            print(f"RGB 相機停止失敗: {e}")

        # 停止熱影像相機
        try:
            if self.mi48:
                self.mi48.stop()
                print("✓ 熱影像相機已停止")
        except OSError as e:
            # 忽略 "Bad file descriptor" 錯誤（相機已經關閉）
            if e.errno != 9:
                print(f"熱影像相機停止失敗: {e}")
        except Exception as e:
            print(f"熱影像相機停止失敗: {e}")

        # 關閉 GPIO
        try:
            if self.mi48_spi_cs:
                self.mi48_spi_cs.close()
                print("✓ GPIO 資源已清理")
        except Exception as e:
            print(f"GPIO 清理失敗: {e}")
