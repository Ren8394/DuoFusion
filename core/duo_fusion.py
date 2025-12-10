#!/usr/bin/env python3
"""
DuoFusion 主類別模組 (DuoFusion Main Class Module)

用途 (Purpose):
    整合所有子模組，提供統一的應用程式介面
    協調相機、錄製、檔案、顯示等功能

主要類別 (Main Class):
    DuoFusion: 主應用程式類別

修改說明 (Modification Guide):
    - 此類別主要負責協調，修改具體功能請到對應的子模組
    - 如需添加新功能，先在對應子模組實作，再在此整合
    - 如需修改流程邏輯，修改 run() 方法
"""

import sys
import signal
import os

# 導入配置
from utils.config import VERSION, DEFAULT_FPS, SPI_SPEED, FRAME_TOLERANCE

# 導入子模組
from core.camera_manager import CameraManager
from core.recorder import Recorder
from core.file_manager import FileManager
from utils.display import (
    display_welcome_message, display_header, display_system_info,
    display_control_hint, display_recording_summary,
    get_parameters, TerminalManager
)


class DuoFusion:
    """
    DuoFusion 主應用程式類別

    用途 (Purpose):
        整合並協調所有功能模組:
        - CameraManager: 管理相機
        - Recorder: 管理錄製
        - FileManager: 管理檔案
        - TerminalManager: 管理終端

    使用範例 (Usage Example):
        >>> app = DuoFusion()
        >>> app.run()

    修改說明 (Modification Guide):
        - 添加新模組: 在 __init__() 中初始化
        - 修改流程: 調整 run() 方法
        - 修改錄製邏輯: 到 recorder.py
        - 修改顯示邏輯: 到 utils/display.py
    """

    def __init__(self):
        """
        初始化 DuoFusion 應用程式

        初始化內容 (Initialization):
            - 基本設定（版本、FPS）
            - 子模組（相機、錄製器、檔案管理器）
            - 終端管理器
            - 信號處理器

        修改說明 (Modification Guide):
            如需添加新的子模組，在此初始化
        """
        # 基本設定
        self.version = VERSION
        self.fps = DEFAULT_FPS

        # 子模組
        self.camera_manager = CameraManager()
        self.recorder = Recorder(fps=self.fps)
        self.file_manager = FileManager(version=self.version)

        # 終端管理
        self.terminal = TerminalManager()

        # 當前錄製階段路徑
        self.current_session_path = ""

        # 設定信號處理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, _signum, _frame):
        """
        處理中斷信號 (SIGINT, SIGTERM)

        流程 (Flow):
            1. 印出中斷訊息
            2. 停止錄製（如果正在錄製）
            3. 清理資源
            4. 退出程式

        修改說明 (Modification Guide):
            如需添加清理邏輯，在 cleanup() 中添加
        """
        print("\n接收到中斷信號，正在停止...")
        if self.recorder.is_recording:
            self.stop_recording()
        self.cleanup()
        sys.exit(0)

    def init_cameras(self) -> bool:
        """
        初始化相機

        返回 (Returns):
            bool: True 表示初始化成功

        流程 (Flow):
            1. 呼叫 CameraManager.init_cameras()
            2. 如果成功，初始化錄製器的執行緒池
            3. 返回初始化結果

        修改說明 (Modification Guide):
            相機初始化邏輯在 core/camera_manager.py
        """
        if self.camera_manager.init_cameras(self.fps):
            self.recorder.init_thread_pools()
            return True
        return False

    def get_parameters(self) -> bool:
        """
        取得使用者參數設定

        返回 (Returns):
            bool: True 表示使用者確認設定

        流程 (Flow):
            1. 呼叫 display.get_parameters()
            2. 更新 FPS 和儲存路徑
            3. 返回確認結果

        修改說明 (Modification Guide):
            參數設定邏輯在 utils/display.py
        """
        confirmed, new_fps, new_save_path = get_parameters(
            current_fps=self.fps,
            current_save_path=self.file_manager.save_path,
            set_fps_callback=lambda fps: self.camera_manager.mi48.set_fps(fps)
        )

        if confirmed:
            self.fps = new_fps
            self.recorder.set_fps(new_fps)
            self.file_manager.set_save_path(new_save_path)

        return confirmed

    def start_recording(self) -> bool:
        """
        開始錄製

        返回 (Returns):
            bool: True 表示成功啟動錄製

        流程 (Flow):
            1. 建立錄製目錄
            2. 啟動錄製器
            3. 顯示錄製資訊

        修改說明 (Modification Guide):
            - 目錄建立: core/file_manager.py
            - 錄製邏輯: core/recorder.py
        """
        # 建立錄製目錄
        session_path = self.file_manager.create_session_directories()
        if not session_path:
            print("建立錄製目錄失敗")
            return False

        self.current_session_path = session_path

        # 時間戳記檔案路徑
        timestamp_path = os.path.join(session_path, "timestamps.txt")

        # 啟動錄製
        success = self.recorder.start_recording(
            session_path=session_path,
            capture_callback=self._capture_frame,
            save_callback=self._save_frame,
            timestamp_path=timestamp_path
        )

        if success:
            self.terminal.restore()
            print(f"\n✓ 開始錄製！")
            print(f"  解析度: RGB {self.camera_manager.rgb_resolution}, 熱影像 {self.camera_manager.thermal_resolution}")
            print(f"  Frame Rate: {self.fps} FPS")
            print(f"  暫存於: {session_path}")
            print(f"  按 Enter 停止錄製...")
        else:
            print("啟動錄製失敗")

        return success

    def stop_recording(self) -> None:
        """
        停止錄製

        流程 (Flow):
            1. 停止錄製器
            2. 移動資料到永久儲存
            3. 儲存階段資訊
            4. 顯示錄製摘要
            5. 清理暫存目錄

        修改說明 (Modification Guide):
            - 停止邏輯: core/recorder.py
            - 檔案移動: core/file_manager.py
            - 摘要顯示: utils/display.py
        """
        # 停止錄製
        self.recorder.stop_recording()

        # 移動到永久儲存
        if self.file_manager.move_to_permanent_storage(self.current_session_path):
            # 取得統計資料
            stats = self.recorder.get_stats()
            stats['spi_speed'] = SPI_SPEED
            stats['frame_tolerance'] = FRAME_TOLERANCE

            # 儲存階段資訊
            self.file_manager.save_session_info(
                self.file_manager.current_session_path,
                self.recorder.start_time,
                stats
            )

            # 顯示摘要
            display_recording_summary(
                self.file_manager.current_session_path,
                stats['frame_count'],
                stats['expected_frame_count'],
                self.recorder.start_time,
                stats['dropped_frames'],
                stats['late_frames'],
                stats['sync_history']
            )
        else:
            print("⚠️ 錄製數據處理失敗")

        # 恢復終端
        self.terminal.restore()
        display_control_hint()

    def _capture_frame(self, camera_type: str):
        """
        擷取幀（供錄製器回呼使用）

        參數 (Args):
            camera_type (str): 'rgb' 或 'thermal'

        返回 (Returns):
            tuple: (data, timing) 或 None

        修改說明 (Modification Guide):
            擷取邏輯在 core/camera_manager.py
        """
        if camera_type == 'rgb':
            return self.camera_manager.grab_rgb_frame()
        elif camera_type == 'thermal':
            return self.camera_manager.read_thermal_frame_with_timing()
        return None

    def _save_frame(self, rgb_array, thermal_data, session_path, frame_idx):
        """
        儲存幀（供錄製器回呼使用）

        參數 (Args):
            rgb_array: RGB 影像陣列
            thermal_data: 熱影像資料陣列
            session_path: 錄製階段路徑
            frame_idx: 幀索引

        修改說明 (Modification Guide):
            儲存邏輯在 core/file_manager.py
        """
        self.file_manager.save_rgb_image(rgb_array, session_path, frame_idx)
        self.file_manager.save_thermal_data(thermal_data, session_path, frame_idx)

    def wait_for_command(self) -> bool:
        """
        等待使用者指令

        返回 (Returns):
            bool: True 繼續運行，False 退出程式

        支援的指令 (Supported Commands):
            - Enter: 開始/停止錄製
            - s: 顯示狀態
            - q / ESC: 退出程式

        修改說明 (Modification Guide):
            如需添加新指令，在此函數中添加處理邏輯
        """
        import select

        self.terminal.set_raw_mode()
        should_continue = True

        try:
            while should_continue:
                # 非阻塞檢查輸入
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    chars = []
                    while select.select([sys.stdin], [], [], 0)[0]:
                        chars.append(sys.stdin.read(1))

                    for char_code_str in chars:
                        char_code = ord(char_code_str)

                        # Ctrl+C
                        if char_code == 3:
                            raise KeyboardInterrupt

                        # Enter: 開始/停止錄製
                        elif char_code in [13, 10]:
                            self.terminal.restore()
                            if self.recorder.is_recording:
                                print("\n⏹️  停止錄製...")
                                self.stop_recording()
                            else:
                                print("\n▶️  開始錄製...")
                                self.start_recording()
                            self.terminal.set_raw_mode()
                            break

                        # ESC 或 q: 退出
                        elif char_code == 27 or char_code_str.lower() == 'q':
                            self.terminal.restore()
                            print("\n正在退出程式...")
                            if self.recorder.is_recording:
                                self.recorder.is_recording = False  # 立即停止錄製
                                if self.recorder.recording_thread and self.recorder.recording_thread.is_alive():
                                    self.recorder.recording_thread.join(timeout=2.0)  # 最多等待2秒
                            self.cleanup()
                            should_continue = False
                            break

                        # s: 顯示狀態
                        elif char_code_str.lower() == 's':
                            self.terminal.restore()
                            display_header()
                            display_system_info(
                                self.fps,
                                SPI_SPEED,
                                self.recorder.is_recording,
                                self.recorder.start_time,
                                self.recorder.frame_count,
                                self.recorder.expected_frame_count,
                                self.recorder.dropped_frames,
                                self.recorder.late_frames
                            )
                            display_control_hint()
                            self.terminal.set_raw_mode()

                # 顯示錄製狀態（如果正在錄製）
                if self.recorder.is_recording and self.recorder.start_time:
                    from utils.display import display_recording_status
                    display_recording_status(
                        self.recorder.frame_count,
                        self.recorder.expected_frame_count,
                        self.recorder.start_time,
                        self.fps,
                        self.recorder.dropped_frames,
                        self.recorder.sync_history
                    )

        except KeyboardInterrupt:
            self.terminal.restore()
            raise

        return should_continue

    def cleanup(self) -> None:
        """
        清理所有資源

        清理內容 (Cleanup):
            1. 執行緒池
            2. 相機
            3. 暫存目錄
            4. 終端設定

        修改說明 (Modification Guide):
            如需添加新的清理邏輯，在此函數中添加
        """
        print("\n正在清理資源...")

        # 清理執行緒池
        self.recorder.cleanup_thread_pools()

        # 清理相機
        self.camera_manager.cleanup()

        # 清理暫存目錄
        self.file_manager.cleanup_temp_directory()

        # 恢復終端
        self.terminal.restore()

        print("✅ 資源清理完成")

    def run(self) -> None:
        """
        主執行方法

        流程 (Flow):
            1. 顯示歡迎訊息
            2. 初始化相機
            3. 取得參數設定
            4. 進入主迴圈（等待使用者指令）
            5. 錯誤處理和清理

        修改說明 (Modification Guide):
            如需改變程式流程，修改此方法
        """
        try:
            # 顯示歡迎訊息
            display_welcome_message()

            # 初始化相機
            if not self.init_cameras():
                self.cleanup()
                return

            # 取得參數
            if not self.get_parameters():
                self.cleanup()
                return

            # 主迴圈
            display_header()
            display_system_info(
                self.fps,
                SPI_SPEED,
                self.recorder.is_recording
            )
            display_control_hint()

            while self.wait_for_command():
                display_header()
                display_system_info(
                    self.fps,
                    SPI_SPEED,
                    self.recorder.is_recording
                )

        except KeyboardInterrupt:
            print("\n程式由使用者中斷")

        except Exception as e:
            error_msg = f"程式執行錯誤: {str(e)}"
            print(f"\n✗ {error_msg}")

            # 記錄錯誤
            stats = self.recorder.get_stats()
            stats['is_recording'] = self.recorder.is_recording
            stats['current_session_path'] = self.current_session_path
            self.file_manager.log_error(error_msg, stats)

        finally:
            if self.recorder.is_recording:
                self.stop_recording()
            self.cleanup()
            print("程式已結束。")
