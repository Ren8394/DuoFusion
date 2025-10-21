#!/usr/bin/env python3
"""
顯示和使用者介面模組 (Display and UI Module)

用途 (Purpose):
    處理所有終端顯示和使用者輸入相關功能
    包括狀態顯示、資訊輸出、參數設定等

主要功能 (Main Functions):
    - 清屏和標題顯示
    - 系統資訊顯示
    - 錄製狀態顯示
    - 參數設定互動
    - 錄製摘要顯示

修改說明 (Modification Guide):
    - 如需調整顯示格式，修改各個顯示函數
    - 如需添加新的參數設定，修改 get_parameters()
"""

import os
import sys
import time
import termios
import tty
import select
from datetime import datetime
from typing import Optional, Callable

from utils.config import (
    VERSION, DEFAULT_FPS, RGB_RESOLUTION, THERMAL_RESOLUTION,
    SPI_SPEED, JPEG_QUALITY, DEFAULT_SAVE_PATH, TEMP_PATH, FRAME_TOLERANCE,
    SYNC_EXCELLENT, SYNC_GOOD, SYNC_FAIR
)


def clear_screen() -> None:
    """
    清除終端畫面

    用途 (Purpose):
        提供乾淨的顯示介面

    跨平台支援 (Cross-platform):
        - Linux/macOS: 使用 'clear'
        - Windows: 使用 'cls'
    """
    os.system('clear' if os.name == 'posix' else 'cls')


def display_header() -> None:
    """
    顯示程式標題

    輸出格式 (Output Format):
        ======================================================================
                            DuoFusion v1.0
                          雙相機錄製系統
        ======================================================================

    修改說明 (Modification Guide):
        如需更改標題樣式，調整此函數的輸出格式
    """
    clear_screen()
    print("=" * 70)
    print(" " * 20 + f"DuoFusion v{VERSION}")
    print(" " * 18 + "雙相機錄製系統")
    print("=" * 70)


def display_system_info(
    fps: int,
    spi_speed: int,
    is_recording: bool,
    start_time: Optional[datetime] = None,
    frame_count: int = 0,
    expected_frame_count: int = 0,
    dropped_frames: int = 0,
    late_frames: int = 0
) -> None:
    """
    顯示系統資訊和錄製狀態

    參數 (Args):
        fps (int): 目標 FPS
        spi_speed (int): SPI 速度（Hz）
        is_recording (bool): 是否正在錄製
        start_time (datetime, optional): 錄製開始時間
        frame_count (int): 已錄製幀數
        expected_frame_count (int): 期望幀數
        dropped_frames (int): 跳過幀數
        late_frames (int): 延遲幀數

    輸出格式 (Output Format):
        【設備資訊】
        ├─ 當前時間: 2024-10-21 08:00:00
        ├─ RGB 解析度: (800, 600)
        ├─ 熱影像解析度: (80, 62)
        ├─ Frame Rate: 8 FPS
        ├─ SPI 速度: 31MHz
        ├─ JPEG 品質: 60
        └─ 狀態: 待機中

        【錄製資訊】(僅在錄製時顯示)
        ├─ 已錄製幀數: 100
        ├─ 期望幀數: 105
        ├─ 錄製時長: 12.5 秒
        ├─ 實際 FPS: 8.0
        ├─ 跳過幀數: 5
        └─ 延遲幀數: 10

    修改說明 (Modification Guide):
        如需添加新資訊，在函數中加入新的 print() 行
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n【設備資訊】")
    print(f"├─ 當前時間: {current_time}")
    print(f"├─ RGB 解析度: {RGB_RESOLUTION}")
    print(f"├─ 熱影像解析度: {THERMAL_RESOLUTION}")
    print(f"├─ Frame Rate: {fps} FPS")
    print(f"├─ SPI 速度: {spi_speed//1000000}MHz")
    print(f"├─ JPEG 品質: {JPEG_QUALITY}")
    print(f"└─ 狀態: {'錄製中...' if is_recording else '待機中'}")

    if is_recording and start_time:
        elapsed = (datetime.now() - start_time).total_seconds()
        actual_fps = frame_count / elapsed if elapsed > 0 else 0

        print(f"\n【錄製資訊】")
        print(f"├─ 已錄製幀數: {frame_count}")
        print(f"├─ 期望幀數: {expected_frame_count}")
        print(f"├─ 錄製時長: {elapsed:.1f} 秒")
        print(f"├─ 實際 FPS: {actual_fps:.1f}")
        print(f"├─ 跳過幀數: {dropped_frames}")
        print(f"└─ 延遲幀數: {late_frames}")


def display_recording_status(
    frame_count: int,
    expected_frame_count: int,
    start_time: datetime,
    fps: int,
    dropped_frames: int,
    sync_history: list
) -> None:
    """
    顯示即時錄製狀態（單行更新）

    參數 (Args):
        frame_count (int): 已錄製幀數
        expected_frame_count (int): 期望幀數
        start_time (datetime): 錄製開始時間
        fps (int): 目標 FPS
        dropped_frames (int): 跳過幀數
        sync_history (list): 同步誤差歷史

    輸出格式 (Output Format):
        🔴 錄製: 100/105 | 12s | FPS:8.0/8 | 🟢2.3ms | 跳幀:5

    同步品質指示器 (Sync Quality Indicator):
        🟢 (綠) < 5 ms: 優秀
        🟡 (黃) 5-15 ms: 良好
        🔴 (紅) > 15 ms: 需改善
        ⚪ (白) 無資料

    修改說明 (Modification Guide):
        如需更改顯示格式或閾值，調整此函數
    """
    elapsed = (datetime.now() - start_time).total_seconds()
    actual_fps = frame_count / elapsed if elapsed > 0 else 0

    # 計算同步品質
    if sync_history:
        recent_sync = list(sync_history)[-10:]  # 最近 10 個
        avg_sync = sum(recent_sync) / len(recent_sync)

        if avg_sync < SYNC_EXCELLENT:
            sync_indicator = "🟢"
        elif avg_sync < SYNC_GOOD:
            sync_indicator = "🟡"
        else:
            sync_indicator = "🔴"
    else:
        avg_sync = 0
        sync_indicator = "⚪"

    # 單行狀態顯示（會覆蓋前一行）
    status_line = (
        f"🔴 錄製: {frame_count}/{expected_frame_count} | "
        f"{elapsed:.0f}s | FPS:{actual_fps:.1f}/{fps} | "
        f"{sync_indicator}{avg_sync:.1f}ms | 跳幀:{dropped_frames}"
    )

    # \r 回到行首，覆蓋前一行
    print(f"\r{' ' * 80}\r{status_line}", end="", flush=True)


def get_parameters(
    current_fps: int,
    current_save_path: str,
    set_fps_callback: Optional[Callable[[int], None]] = None
) -> tuple:
    """
    互動式參數設定

    參數 (Args):
        current_fps (int): 當前 FPS 設定
        current_save_path (str): 當前儲存路徑
        set_fps_callback (callable, optional): 設定 FPS 的回呼函數

    返回 (Returns):
        tuple: (confirmed, new_fps, new_save_path)
            - confirmed (bool): 使用者是否確認設定
            - new_fps (int): 新的 FPS 設定
            - new_save_path (str): 新的儲存路徑

    互動流程 (Interaction Flow):
        1. 輸入 FPS（Enter 保持預設）
        2. 輸入儲存路徑（Enter 保持預設）
        3. 顯示確認資訊
        4. 確認設定（Y/n）

    輸入驗證 (Input Validation):
        - FPS: 必須在 1-25 範圍內
        - 路徑: 必須有效或可建立

    修改說明 (Modification Guide):
        如需添加新參數:
        1. 添加輸入提示
        2. 添加驗證邏輯
        3. 添加到返回值
        4. 更新確認顯示
    """
    print("\n【參數設定】")

    new_fps = current_fps
    new_save_path = current_save_path

    # FPS 設定
    while True:
        try:
            fps_input = input(
                f"請輸入 Frame Rate (1-25 FPS) [預設: {current_fps}]: "
            ).strip()

            if fps_input == "":
                break

            fps = int(fps_input)
            if 1 <= fps <= 25:
                new_fps = fps
                # 如果有回呼函數，立即設定 FPS
                if set_fps_callback:
                    set_fps_callback(fps)
                break
            else:
                print("  ✗ 請輸入 1-25 之間的數字")

        except ValueError:
            print("  ✗ 請輸入有效的數字")

    # 儲存路徑設定
    path_input = input(
        f"請輸入儲存路徑 [預設: {current_save_path}]: "
    ).strip()

    if path_input:
        # 檢查路徑是否有效
        if os.path.isdir(path_input):
            new_save_path = path_input
        else:
            # 嘗試建立目錄
            try:
                os.makedirs(path_input, exist_ok=True)
                new_save_path = path_input
            except Exception:
                print(f"  ✗ 路徑無效，使用預設路徑: {current_save_path}")

    # 確認設定
    print("\n【確認設定】")
    print(f"├─ Frame Rate: {new_fps} FPS")
    print(f"├─ RGB 解析度: {RGB_RESOLUTION}")
    print(f"├─ 熱影像解析度: {THERMAL_RESOLUTION}")
    print(f"├─ 儲存路徑: {new_save_path}")
    print(f"├─ 臨時儲存: {TEMP_PATH}")
    print(f"├─ SPI 速度: {SPI_SPEED//1000000}MHz")
    print(f"├─ JPEG 品質: {JPEG_QUALITY}")
    print(f"└─ 跳幀容忍: {FRAME_TOLERANCE}個間隔")

    confirm = input("\n確認以上設定嗎? (Y/n): ").strip().lower()
    confirmed = (confirm != 'n')

    return confirmed, new_fps, new_save_path


def display_recording_summary(
    session_path: str,
    frame_count: int,
    expected_frame_count: int,
    start_time: datetime,
    dropped_frames: int,
    late_frames: int,
    sync_history: list
) -> None:
    """
    顯示錄製完成摘要

    參數 (Args):
        session_path (str): 錄製資料儲存路徑
        frame_count (int): 實際錄製幀數
        expected_frame_count (int): 期望幀數
        start_time (datetime): 開始時間
        dropped_frames (int): 跳過幀數
        late_frames (int): 延遲幀數
        sync_history (list): 同步誤差歷史

    輸出格式 (Output Format):
        ✅ 錄製完成！
           儲存位置: /path/to/session
           實際/期望幀數: 100/105
           成功率: 95.2%
           錄製時長: 12.5 秒
           實際 FPS: 8.0
           跳幀/延遲: 5/10
           同步品質: 優秀 (2.34ms)

    同步品質評級 (Sync Quality Rating):
        - 優秀: < 5 ms
        - 良好: 5-10 ms
        - 普通: 10-20 ms
        - 需改善: > 20 ms

    修改說明 (Modification Guide):
        如需更改品質評級閾值，修改 config.py 中的 SYNC_* 常數
    """
    end_time = datetime.now()
    total_seconds = (end_time - start_time).total_seconds()
    actual_fps = frame_count / total_seconds if total_seconds > 0 else 0
    success_rate = (frame_count / expected_frame_count * 100) if expected_frame_count > 0 else 0

    # 計算平均同步品質
    avg_sync = sum(sync_history) / len(sync_history) if sync_history else 0

    if avg_sync < SYNC_EXCELLENT:
        sync_quality = "優秀"
    elif avg_sync < SYNC_GOOD:
        sync_quality = "良好"
    elif avg_sync < SYNC_FAIR:
        sync_quality = "普通"
    else:
        sync_quality = "需改善"

    print(f"\n✅ 錄製完成！")
    print(f"   儲存位置: {session_path}")
    print(f"   實際/期望幀數: {frame_count}/{expected_frame_count}")
    print(f"   成功率: {success_rate:.1f}%")
    print(f"   錄製時長: {total_seconds:.1f} 秒")
    print(f"   實際 FPS: {actual_fps:.1f}")
    print(f"   跳幀/延遲: {dropped_frames}/{late_frames}")
    print(f"   同步品質: {sync_quality} ({avg_sync:.2f}ms)")


def display_welcome_message() -> None:
    """
    顯示歡迎訊息和系統特性

    用途 (Purpose):
        程式啟動時的歡迎畫面

    輸出內容 (Output):
        - 版本資訊
        - 硬體需求
        - 系統特性

    修改說明 (Modification Guide):
        如需更改歡迎訊息，調整此函數的輸出
    """
    print("=" * 60)
    print(" " * 15 + f"DuoFusion v{VERSION}")
    print(" " * 12 + "雙相機錄製系統")
    print("=" * 60)
    print("\n系統特性:")
    print("  • RGB Camera Module 3 + Thermal-90 Camera HAT")
    print(f"  • 固定解析度: RGB {RGB_RESOLUTION}, 熱影像 {THERMAL_RESOLUTION}")
    print(f"  • 高速 SPI 通訊: {SPI_SPEED//1000000}MHz")
    print("  • 精確時間同步與 FPS 控制")
    print("  • 批次化 I/O 優化")
    print("  • RAM disk 暫存機制")
    print("-" * 60)


def display_control_hint() -> None:
    """
    顯示控制提示

    輸出內容 (Output):
        按鍵功能說明

    修改說明 (Modification Guide):
        如需添加新的控制按鍵，在此更新說明
    """
    print("\n" + "=" * 70)
    print("按 Enter 開始/結束錄製 | 按 ESC 或 q 退出程式 | 按 s 顯示狀態")
    print("=" * 70)


def wait_for_keypress(timeout: float = 0.5) -> Optional[str]:
    """
    等待按鍵輸入（非阻塞）

    參數 (Args):
        timeout (float): 等待超時時間（秒）

    返回 (Returns):
        str: 按下的鍵，None 表示超時

    用途 (Purpose):
        在錄製時檢測使用者輸入而不阻塞主迴圈

    修改說明 (Modification Guide):
        如需更改超時時間，調整 timeout 參數
    """
    if select.select([sys.stdin], [], [], timeout)[0]:
        return sys.stdin.read(1)
    return None


class TerminalManager:
    """
    終端管理器

    用途 (Purpose):
        管理終端設定，確保程式結束時正確恢復

    使用範例 (Usage Example):
        >>> tm = TerminalManager()
        >>> tm.set_raw_mode()
        >>> # ... 使用原始模式 ...
        >>> tm.restore()
    """

    def __init__(self):
        """初始化並儲存當前終端設定"""
        self.old_settings = termios.tcgetattr(sys.stdin)

    def set_raw_mode(self) -> None:
        """設定為原始模式（raw mode）"""
        tty.setraw(sys.stdin.fileno())

    def restore(self) -> None:
        """恢復原始終端設定"""
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        except Exception as e:
            print(f"恢復終端設定失敗: {e}")

    def __del__(self):
        """解構時自動恢復終端設定"""
        self.restore()
