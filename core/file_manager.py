#!/usr/bin/env python3
"""
檔案管理模組 (File Manager Module)

用途 (Purpose):
    處理所有檔案和目錄操作，包括:
    - 建立錄製目錄結構
    - 儲存 RGB 和熱影像資料
    - 管理暫存和永久儲存
    - 產生錄製摘要資訊

主要類別 (Main Class):
    FileManager: 檔案管理器

修改說明 (Modification Guide):
    - 如需改變儲存路徑，修改 config.py 中的 DEFAULT_SAVE_PATH
    - 如需改變檔案格式，修改 config.py 中的相關設定
    - 如需調整 JPEG 品質，修改 config.JPEG_QUALITY
"""

import os
import shutil
import traceback
from datetime import datetime
from typing import Optional
import numpy as np
from PIL import Image

from utils.config import (
    DEFAULT_SAVE_PATH, TEMP_PATH,
    JPEG_QUALITY, RGB_EXTENSION, THERMAL_EXTENSION, THERMAL_DTYPE,
    FOLDER_TIMESTAMP_FORMAT, FRAME_INDEX_FORMAT,
    RGB_RESOLUTION, THERMAL_RESOLUTION
)


class FileManager:
    """
    檔案管理器

    用途 (Purpose):
        集中管理所有檔案操作，確保資料正確儲存

    屬性 (Attributes):
        save_path (str): 最終儲存路徑
        temp_path (str): RAM disk 暫存路徑
        current_session_path (str): 當前錄製階段的路徑
        version (str): 系統版本號

    使用範例 (Usage Example):
        >>> fm = FileManager(version="1.0")
        >>> session_path = fm.create_session_directories()
        >>> fm.save_rgb_image(rgb_array, session_path, frame_idx=0)
        >>> fm.save_thermal_data(thermal_data, session_path, frame_idx=0)
        >>> fm.finalize_session(session_path, stats)
    """

    def __init__(self, version: str = "1.0", save_path: Optional[str] = None):
        """
        初始化檔案管理器

        參數 (Args):
            version (str): 系統版本號
            save_path (str, optional): 自訂儲存路徑，None 則使用預設值
        """
        self.version = version
        self.save_path = save_path if save_path else DEFAULT_SAVE_PATH
        self.temp_path = TEMP_PATH
        self.current_session_path = ""

    def set_save_path(self, path: str) -> bool:
        """
        設定儲存路徑

        參數 (Args):
            path (str): 新的儲存路徑

        返回 (Returns):
            bool: True 表示路徑有效且可用

        修改說明 (Modification Guide):
            可在程式執行時動態改變儲存位置
        """
        if os.path.isdir(path) or self._create_directory(path):
            self.save_path = path
            return True
        return False

    def _create_directory(self, path: str) -> bool:
        """
        建立目錄

        參數 (Args):
            path (str): 目錄路徑

        返回 (Returns):
            bool: True 表示建立成功或已存在

        錯誤處理 (Error Handling):
            建立失敗時返回 False，不拋出例外
        """
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            print(f"建立目錄失敗 ({path}): {e}")
            return False

    def create_session_directories(self) -> Optional[str]:
        """
        建立錄製階段的目錄結構

        目錄結構 (Directory Structure):
            /dev/shm/duofusion_recordings/  (RAM disk)
            └── YYYYMMDD_HHMMSS/
                ├── RGB/
                └── Thermal/

        返回 (Returns):
            str: 階段目錄路徑，失敗時返回 None

        流程說明 (Flow):
            1. 產生時間戳記命名
            2. 在 RAM disk 建立主目錄
            3. 建立 RGB 子目錄
            4. 建立 Thermal 子目錄
            5. 記錄並返回路徑

        修改說明 (Modification Guide):
            如需新增其他子目錄（如 Metadata/），在此函數添加
        """
        try:
            # 產生時間戳記
            timestamp = datetime.now().strftime(FOLDER_TIMESTAMP_FORMAT)
            session_path = os.path.join(self.temp_path, timestamp)

            # 建立目錄結構
            os.makedirs(self.temp_path, exist_ok=True)
            os.makedirs(os.path.join(session_path, "RGB"), exist_ok=True)
            os.makedirs(os.path.join(session_path, "Thermal"), exist_ok=True)

            # 記錄當前階段路徑
            self.current_session_path = session_path
            return session_path

        except Exception as e:
            print(f"建立錄製目錄失敗: {e}")
            return None

    def save_rgb_image(
        self,
        rgb_array: np.ndarray,
        session_path: str,
        frame_idx: int
    ) -> bool:
        """
        儲存 RGB 影像

        參數 (Args):
            rgb_array (np.ndarray): RGB 影像陣列
            session_path (str): 錄製階段路徑
            frame_idx (int): 幀索引

        返回 (Returns):
            bool: True 表示儲存成功

        檔案命名 (File Naming):
            RGB/000000.jpg, RGB/000001.jpg, ...

        壓縮設定 (Compression):
            使用 PIL 的 JPEG 壓縮
            - quality: 可在 config.JPEG_QUALITY 調整 (0-100)
            - optimize: False（關閉優化以加快速度）

        錯誤處理 (Error Handling):
            儲存失敗時印出訊息並返回 False
            不拋出例外，避免中斷錄製流程

        修改說明 (Modification Guide):
            如需改為 PNG 格式:
            1. 修改 config.RGB_EXTENSION = ".png"
            2. 修改此處的 save() 呼叫:
               rgb_image.save(rgb_path, 'PNG')
        """
        try:
            # 產生檔案路徑
            filename = FRAME_INDEX_FORMAT.format(frame_idx) + RGB_EXTENSION
            rgb_path = os.path.join(session_path, "RGB", filename)

            # 轉換為 PIL Image 並儲存
            rgb_image = Image.fromarray(rgb_array)
            rgb_image.save(
                rgb_path,
                'JPEG',
                quality=JPEG_QUALITY,
                optimize=False  # 關閉優化加快速度
            )
            return True

        except Exception as e:
            print(f"RGB 影像儲存失敗 (幀 {frame_idx}): {e}")
            return False

    def save_thermal_data(
        self,
        thermal_data: np.ndarray,
        session_path: str,
        frame_idx: int
    ) -> bool:
        """
        儲存熱影像資料

        參數 (Args):
            thermal_data (np.ndarray): 溫度陣列（攝氏度）
            session_path (str): 錄製階段路徑
            frame_idx (int): 幀索引

        返回 (Returns):
            bool: True 表示儲存成功

        檔案格式 (File Format):
            NPY (NumPy binary) 格式
            - 快速: 儲存速度比 CSV 快 2-4倍
            - 精確: 保持完整浮點數精度
            - 小巧: 檔案大小比 CSV 小 40%
            - 使用 float32: 精度足夠且節省空間

        檔案命名 (File Naming):
            Thermal/000000.npy, Thermal/000001.npy, ...

        讀取方式 (How to Read):
            >>> import numpy as np
            >>> data = np.load('000000.npy')
            >>> print(f"溫度範圍: {data.min():.1f}°C - {data.max():.1f}°C")

        錯誤處理 (Error Handling):
            儲存失敗時印出訊息並返回 False

        修改說明 (Modification Guide):
            如需改回 CSV 格式:
            1. 修改 config.THERMAL_FORMAT = "CSV"
            2. 修改 config.THERMAL_EXTENSION = ".txt"
            3. 使用 np.savetxt() 取代 np.save()

            如需改變精度:
            - float16: 更小但精度 ±0.1°C (修改 config.THERMAL_DTYPE)
            - float64: 更大但精度更高
        """
        try:
            # 產生檔案路徑
            filename = FRAME_INDEX_FORMAT.format(frame_idx) + THERMAL_EXTENSION
            thermal_path = os.path.join(session_path, "Thermal", filename)

            # 轉換為指定精度並儲存為 NPY 二進位格式
            # float32 提供足夠精度（約 6-7 位有效數字）且節省空間
            thermal_data_typed = thermal_data.astype(THERMAL_DTYPE)
            np.save(thermal_path, thermal_data_typed)

            return True

        except Exception as e:
            print(f"熱影像資料儲存失敗 (幀 {frame_idx}): {e}")
            return False

    def move_to_permanent_storage(self, session_path: str) -> bool:
        """
        將錄製資料從 RAM disk 移動到永久儲存

        參數 (Args):
            session_path (str): 暫存路徑（在 RAM disk）

        返回 (Returns):
            bool: True 表示移動成功

        流程說明 (Flow):
            1. 檢查來源路徑是否存在
            2. 產生目標路徑（使用相同的時間戳記目錄名）
            3. 確保目標目錄的父目錄存在
            4. 使用 shutil.move() 移動整個目錄
            5. 更新 current_session_path

        為何要移動 (Why Move):
            - RAM disk (/dev/shm/) 重開機後資料會消失
            - 移動到永久儲存（如 SD 卡）確保資料安全
            - 錄製時用 RAM disk 可獲得最快寫入速度

        錯誤處理 (Error Handling):
            移動失敗時印出詳細錯誤並返回 False

        修改說明 (Modification Guide):
            如果儲存空間不足，考慮:
            1. 即時壓縮資料
            2. 只保留關鍵幀
            3. 降低影像品質
        """
        try:
            # 檢查來源路徑
            if not session_path or not os.path.exists(session_path):
                print(f"來源路徑不存在: {session_path}")
                return False

            # 產生目標路徑（保持相同的目錄名稱）
            session_name = os.path.basename(session_path)
            final_path = os.path.join(self.save_path, session_name)

            print(f"正在移動數據到: {final_path}")

            # 確保目標目錄的父目錄存在
            os.makedirs(os.path.dirname(final_path), exist_ok=True)

            # 移動數據
            shutil.move(session_path, final_path)

            # 更新當前階段路徑
            self.current_session_path = final_path

            print(f"✓ 數據已移動到永久儲存")
            return True

        except Exception as e:
            print(f"✗ 移動數據失敗: {e}")
            return False

    def save_session_info(
        self,
        session_path: str,
        start_time: datetime,
        stats: dict
    ) -> bool:
        """
        儲存錄製階段資訊檔案

        參數 (Args):
            session_path (str): 階段路徑
            start_time (datetime): 錄製開始時間
            stats (dict): 統計資訊，包含:
                - frame_count: 實際錄製幀數
                - expected_frame_count: 期望幀數
                - dropped_frames: 跳過幀數
                - late_frames: 延遲幀數
                - fps: 目標 FPS
                - sync_history: 同步誤差歷史
                - timing_errors: 時序誤差歷史

        返回 (Returns):
            bool: True 表示儲存成功

        檔案內容 (File Content):
            session_info.txt 包含:
            - 基本資訊（時間、解析度）
            - 錄製統計（幀數、FPS、成功率）
            - 同步品質（平均同步差異、時間偏差）
            - 系統設定（SPI 速度、JPEG 品質等）

        用途 (Purpose):
            方便後續分析錄製品質和問題除錯

        修改說明 (Modification Guide):
            如需添加新資訊，在寫入區塊中加入新的 f.write() 行
        """
        try:
            info_path = os.path.join(session_path, "session_info.txt")

            end_time = datetime.now()
            total_seconds = (end_time - start_time).total_seconds()

            frame_count = stats.get('frame_count', 0)
            expected_frame_count = stats.get('expected_frame_count', 0)
            dropped_frames = stats.get('dropped_frames', 0)
            late_frames = stats.get('late_frames', 0)
            fps = stats.get('fps', 0)

            # 計算統計
            actual_fps = frame_count / total_seconds if total_seconds > 0 else 0
            success_rate = (frame_count / expected_frame_count * 100) if expected_frame_count > 0 else 0

            # 同步和時序統計
            sync_history = stats.get('sync_history', [])
            timing_errors = stats.get('timing_errors', [])

            avg_sync = sum(sync_history) / len(sync_history) if sync_history else 0
            avg_timing_error = sum(timing_errors) / len(timing_errors) if timing_errors else 0

            # 寫入檔案
            with open(info_path, "w", encoding='utf-8') as f:
                f.write(f"DuoFusion v{self.version} 錄製資訊\n")
                f.write("=" * 40 + "\n\n")

                f.write("基本資訊\n")
                f.write("-" * 20 + "\n")
                f.write(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"結束時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"錄製時長: {total_seconds:.1f} 秒\n")
                f.write(f"RGB 解析度: {RGB_RESOLUTION}\n")
                f.write(f"熱影像解析度: {THERMAL_RESOLUTION}\n\n")

                f.write("錄製統計\n")
                f.write("-" * 20 + "\n")
                f.write(f"期望幀數: {expected_frame_count}\n")
                f.write(f"實際幀數: {frame_count}\n")
                f.write(f"成功率: {success_rate:.1f}%\n")
                f.write(f"目標 FPS: {fps}\n")
                f.write(f"實際 FPS: {actual_fps:.1f}\n")
                f.write(f"跳過幀數: {dropped_frames}\n")
                f.write(f"延遲幀數: {late_frames}\n\n")

                f.write("同步品質\n")
                f.write("-" * 20 + "\n")
                f.write(f"平均同步差異: {avg_sync:.3f} ms\n")
                f.write(f"平均時間偏差: {avg_timing_error:.3f} ms\n\n")

                f.write("系統設定\n")
                f.write("-" * 20 + "\n")
                f.write(f"SPI 速度: {stats.get('spi_speed', 0)//1000000} MHz\n")
                f.write(f"JPEG 品質: {JPEG_QUALITY}\n")
                f.write(f"跳幀容忍: {stats.get('frame_tolerance', 0)} 個間隔\n")

            return True

        except Exception as e:
            print(f"儲存資訊檔案失敗: {e}")
            return False

    def log_error(self, error_msg: str, stats: dict) -> None:
        """
        記錄錯誤到日誌檔案

        參數 (Args):
            error_msg (str): 錯誤訊息
            stats (dict): 系統狀態資訊

        檔案位置 (File Location):
            logs/error_YYYYMMDD_HHMMSS.txt

        用途 (Purpose):
            除錯和問題追蹤

        修改說明 (Modification Guide):
            如需更詳細的日誌，添加更多 stats 資訊
        """
        try:
            # 確保 logs 目錄存在
            logs_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "logs"
            )
            os.makedirs(logs_dir, exist_ok=True)

            # 產生日誌檔案路徑
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(logs_dir, f"error_{timestamp}.txt")

            # 寫入錯誤資訊
            with open(log_path, "w", encoding='utf-8') as f:
                f.write(f"DuoFusion v{self.version} 錯誤記錄\n")
                f.write("=" * 40 + "\n")
                f.write(f"錯誤時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"錯誤訊息: {error_msg}\n\n")

                f.write("系統狀態:\n")
                f.write(f"- 錄製中: {stats.get('is_recording', False)}\n")
                f.write(f"- 幀數: {stats.get('frame_count', 0)}/{stats.get('expected_frame_count', 0)}\n")
                f.write(f"- 當前路徑: {stats.get('current_session_path', 'N/A')}\n\n")

                f.write("錯誤堆疊:\n")
                f.write(traceback.format_exc())

            print(f"錯誤已記錄到: {log_path}")

        except Exception as e:
            print(f"記錄錯誤失敗: {e}")

    def cleanup_temp_directory(self) -> None:
        """
        清理暫存目錄

        用途 (Purpose):
            移除 RAM disk 上的空目錄

        注意事項 (Notes):
            只會移除空目錄，有資料的目錄不會刪除
        """
        try:
            if os.path.exists(self.temp_path) and not os.listdir(self.temp_path):
                os.rmdir(self.temp_path)
                print("✓ 臨時目錄已清理")
        except Exception as e:
            print(f"清理臨時目錄失敗: {e}")
