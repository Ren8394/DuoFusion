#!/usr/bin/env python3
"""
錄製控制模組 (Recorder Module)

用途 (Purpose):
    管理錄製流程，包括:
    - 錄製迴圈的精確時序控制
    - 雙相機同步擷取
    - 同步品質計算
    - 統計資料收集

主要類別 (Main Class):
    Recorder: 錄製控制器

修改說明 (Modification Guide):
    - 如需調整同步邏輯，修改 _calculate_sync_quality()
    - 如需調整跳幀邏輯，修改 recording_loop() 中的跳幀判斷
    - 如需調整時序精度，修改 config.py 中的時序參數
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from typing import Optional, Callable
from datetime import datetime

from utils.config import (
    FRAME_TOLERANCE,
    TIMESTAMP_BATCH_SIZE,
    CAPTURE_WORKERS,
    SAVE_WORKERS,
)
from utils.timing import get_precise_timestamp, precise_sleep, calculate_fps_interval
from core.timestamp_buffer import TimestampBuffer


class Recorder:
    """
    錄製控制器

    用途 (Purpose):
        控制錄製流程，確保精確的時序和同步

    屬性 (Attributes):
        fps (int): 目標 FPS
        is_recording (bool): 錄製狀態
        frame_count (int): 已錄製幀數
        expected_frame_count (int): 期望幀數
        dropped_frames (int): 跳過幀數
        late_frames (int): 延遲幀數
        start_time (datetime): 錄製開始時間
        sync_history (deque): 同步誤差歷史
        timing_errors (deque): 時序誤差歷史

    使用範例 (Usage Example):
        >>> recorder = Recorder(fps=8)
        >>> recorder.start_recording(
        ...     capture_callback=capture_frames,
        ...     save_callback=save_frames,
        ...     session_path="/path/to/session"
        ... )
        >>> # ... 錄製中 ...
        >>> recorder.stop_recording()
    """

    def __init__(self, fps: int):
        """
        初始化錄製控制器

        參數 (Args):
            fps (int): 目標 FPS (1-25)
        """
        self.fps = fps
        self.frame_tolerance = FRAME_TOLERANCE

        # 錄製狀態
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None

        # 統計數據
        self.frame_count = 0
        self.expected_frame_count = 0
        self.dropped_frames = 0
        self.late_frames = 0
        self.start_time: Optional[datetime] = None

        # 歷史記錄（用於品質分析）
        self.sync_history = deque(maxlen=100)
        self.timing_errors = deque(maxlen=100)

        # 執行緒池
        self.capture_executor: Optional[ThreadPoolExecutor] = None
        self.save_executor: Optional[ThreadPoolExecutor] = None

        # AsyncIO 相關
        self.async_loop: Optional[asyncio.AbstractEventLoop] = None
        self.async_thread: Optional[threading.Thread] = None

    def init_thread_pools(self) -> None:
        """
        初始化執行緒池和非同步事件迴圈

        執行緒配置 (Thread Configuration):
            - capture_executor: 2 workers（RGB + Thermal 並行擷取）
            - save_executor: 2 workers（RGB + Thermal 並行儲存）
            - async_loop: 非同步事件迴圈用於I/O操作

        用途 (Purpose):
            平行處理以提升效能，使用asyncio優化I/O操作

        修改說明 (Modification Guide):
            如需調整執行緒數量，修改 config.CAPTURE_WORKERS 和 config.SAVE_WORKERS
        """
        self.capture_executor = ThreadPoolExecutor(
            max_workers=CAPTURE_WORKERS, thread_name_prefix="capture"
        )
        self.save_executor = ThreadPoolExecutor(
            max_workers=SAVE_WORKERS, thread_name_prefix="save"
        )

        # 初始化非同步事件迴圈
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(
            target=self._run_async_loop, daemon=True, name="async-io"
        )
        self.async_thread.start()

        print("✓ 執行緒池和非同步事件迴圈初始化完成")

    def _run_async_loop(self) -> None:
        """
        運行非同步事件迴圈（在獨立執行緒中）

        用途 (Purpose):
            處理非同步I/O操作，不阻塞主錄製執行緒
        """
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def cleanup_thread_pools(self) -> None:
        """
        清理執行緒池和非同步資源

        清理流程 (Cleanup Flow):
            1. capture_executor: 不等待，立即關閉
            2. save_executor: 不等待，立即關閉
            3. async_loop: 停止事件迴圈
            4. async_thread: 等待執行緒結束

        原因 (Reason):
            快速退出時不等待儲存任務，避免程式卡住

        修改說明 (Modification Guide):
            如需改變等待策略，調整 shutdown(wait=?) 參數
        """
        try:
            if self.capture_executor:
                self.capture_executor.shutdown(wait=False)
            if self.save_executor:
                self.save_executor.shutdown(wait=False)

            # 清理非同步資源
            if self.async_loop and not self.async_loop.is_closed():
                self.async_loop.stop()
            if self.async_thread and self.async_thread.is_alive():
                self.async_thread.join(timeout=1.0)

            print("✓ 執行緒池和非同步資源已關閉")
        except Exception as e:
            print(f"資源清理失敗: {e}")

    def start_recording(
        self,
        session_path: str,
        capture_callback: Callable,
        save_callback: Callable,
        timestamp_path: str,
    ) -> bool:
        """
        開始錄製

        參數 (Args):
            session_path (str): 錄製階段路徑
            capture_callback (callable): 擷取回呼函數
                簽名: () -> (rgb_array, rgb_timing, thermal_data, thermal_timing)
            save_callback (callable): 儲存回呼函數
                簽名: (rgb_array, thermal_data, session_path, frame_idx) -> None
            timestamp_path (str): 時間戳記檔案路徑

        返回 (Returns):
            bool: True 表示成功啟動錄製執行緒

        流程說明 (Flow):
            1. 重置所有統計數據
            2. 記錄開始時間
            3. 建立錄製執行緒
            4. 啟動執行緒

        修改說明 (Modification Guide):
            如需添加新的回呼，在參數中添加並傳遞給 recording_loop
        """
        try:
            # 重置統計數據
            self.frame_count = 0
            self.expected_frame_count = 0
            self.dropped_frames = 0
            self.late_frames = 0
            self.sync_history.clear()
            self.timing_errors.clear()

            # 記錄開始時間
            self.start_time = datetime.now()
            self.is_recording = True

            # 建立並啟動錄製執行緒
            self.recording_thread = threading.Thread(
                target=self._recording_loop,
                args=(session_path, capture_callback, save_callback, timestamp_path),
            )
            self.recording_thread.start()

            return True

        except Exception as e:
            print(f"啟動錄製失敗: {e}")
            self.is_recording = False
            return False

    def stop_recording(self) -> None:
        """
        停止錄製

        流程說明 (Flow):
            1. 設定停止旗標
            2. 等待錄製執行緒結束
            3. 等待儲存任務完成

        注意事項 (Notes):
            此函數會阻塞直到錄製執行緒結束

        修改說明 (Modification Guide):
            如需添加清理邏輯，在此函數中添加
        """
        self.is_recording = False

        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join()

        print("錄製已停止。")

    def _recording_loop(
        self,
        session_path: str,
        capture_callback: Callable,
        save_callback: Callable,
        timestamp_path: str,
    ) -> None:
        """
        錄製迴圈（在獨立執行緒中運行）

        參數 (Args):
            session_path (str): 錄製階段路徑
            capture_callback (callable): 擷取函數
            save_callback (callable): 儲存函數
            timestamp_path (str): 時間戳記路徑

        演算法說明 (Algorithm):
            精確時序控制的錄製迴圈:

            1. 計算幀間隔（frame_interval）
            2. 記錄錄製開始時間（recording_start_ns）
            3. 對每一幀:
               a. 計算目標時間 = 開始時間 + (幀索引 × 幀間隔)
               b. 計算當前需要等待的時間
               c. 如果延遲過大（超過容忍度），跳過此幀
               d. 精確等待到目標時間
               e. 並行擷取 RGB 和 Thermal
               f. 計算同步品質
               g. 並行儲存 RGB 和 Thermal
               h. 記錄時間戳記
               i. 批次寫入時間戳記

        跳幀邏輯 (Frame Skipping Logic):
            當 wait_time < -frame_interval × tolerance 時跳幀
            目的: 避免累積延遲，保持時序精度

        時序精度 (Timing Precision):
            使用絕對目標時間而非相對延遲
            避免誤差累積，確保長時間錄製的精度

        錯誤處理 (Error Handling):
            擷取失敗不會中斷迴圈，只會跳過該幀

        修改說明 (Modification Guide):
            - 調整跳幀容忍度: 修改 config.FRAME_TOLERANCE
            - 調整批次大小: 修改 config.TIMESTAMP_BATCH_SIZE
            - 添加除錯資訊: 在迴圈中添加 print()
        """
        # 計算幀間隔
        frame_interval_seconds, frame_interval_ns = calculate_fps_interval(self.fps)

        # 錄製開始時間（奈秒精度）
        recording_start_ns = get_precise_timestamp()

        # 時間戳記緩衝器
        timestamp_buffer = TimestampBuffer(batch_size=TIMESTAMP_BATCH_SIZE)

        tolerance_ms = frame_interval_seconds * 1000 * self.frame_tolerance
        print(f"\n開始錄製迴圈 (間隔: {frame_interval_seconds*1000:.1f}ms，可允許誤差: {tolerance_ms:.1f}ms)")

        try:
            while self.is_recording:
                # 計算此幀的目標時間
                target_time_ns = recording_start_ns + (
                    self.expected_frame_count * frame_interval_ns
                )
                current_time_ns = get_precise_timestamp()
                wait_time_ns = target_time_ns - current_time_ns

                # 跳幀邏輯: 如果延遲超過容忍度，跳過此幀
                if wait_time_ns < -frame_interval_ns * self.frame_tolerance:
                    self.dropped_frames += 1
                    self.expected_frame_count += 1
                    continue

                # 精確等待到目標時間
                if wait_time_ns > 0:
                    precise_sleep(wait_time_ns / 1e9)
                elif wait_time_ns < 0:
                    # 記錄延遲幀
                    self.late_frames += 1

                # 並行擷取雙相機
                try:
                    rgb_future = self.capture_executor.submit(capture_callback, "rgb")
                    thermal_future = self.capture_executor.submit(
                        capture_callback, "thermal"
                    )

                    rgb_result = rgb_future.result(timeout=5.0)
                    thermal_result = thermal_future.result(timeout=5.0)

                except Exception as e:
                    print(f"\n擷取失敗: {e}")
                    self.expected_frame_count += 1
                    continue

                # 檢查擷取結果
                if not rgb_result or not thermal_result:
                    self.expected_frame_count += 1
                    continue

                rgb_array, rgb_timing = rgb_result
                thermal_data, thermal_timing = thermal_result

                if rgb_array is None or thermal_data is None:
                    self.expected_frame_count += 1
                    continue

                # 計算同步品質
                sync_info = self._calculate_sync_quality(rgb_timing, thermal_timing)

                # 記錄時序誤差
                timing_error_ms = (current_time_ns - target_time_ns) / 1e6
                self.timing_errors.append(abs(timing_error_ms))

                # 當前幀索引
                frame_idx = self.frame_count
                self.frame_count += 1
                self.expected_frame_count += 1

                # 準備時間戳記資料
                timestamp_data = {
                    "frame_idx": frame_idx,
                    "expected_frame_idx": self.expected_frame_count - 1,
                    "target_time_ns": target_time_ns,
                    "timing_error_ms": timing_error_ms,
                    "sync_diff_ms": sync_info["sync_diff_ms"],
                }
                timestamp_buffer.add_timestamp(timestamp_data)

                # 非同步儲存
                asyncio.run_coroutine_threadsafe(
                    self._save_frame_async(
                        save_callback, rgb_array, thermal_data, session_path, frame_idx
                    ),
                    self.async_loop,
                )

                # 批次寫入時間戳記（在非同步任務中處理）
                if timestamp_buffer.should_flush():
                    asyncio.run_coroutine_threadsafe(
                        self._flush_timestamps_async(timestamp_buffer, timestamp_path),
                        self.async_loop,
                    )

        except Exception as e:
            print(f"\n錄製迴圈錯誤: {e}")

        finally:
            # 寫入剩餘的時間戳記
            try:
                timestamp_buffer.flush_to_file(timestamp_path)
            except Exception as e:
                print(f"最終時間戳記寫入失敗: {e}")

    def _calculate_sync_quality(self, rgb_timing: dict, thermal_timing: dict) -> dict:
        """
        計算雙相機同步品質

        參數 (Args):
            rgb_timing (dict): RGB 擷取時序資訊
                - start_ns: 開始時間（奈秒）
            thermal_timing (dict): Thermal 擷取時序資訊
                - start_ns: 開始時間（奈秒）

        返回 (Returns):
            dict: 同步資訊
                - sync_diff_ms: 同步差異（毫秒）
                - sync_quality: 品質評級 ('good' 或 'poor')

        演算法 (Algorithm):
            sync_diff = |rgb_start - thermal_start|
            品質判斷:
                - < 10 ms: good
                - >= 10 ms: poor

        用途 (Purpose):
            評估雙相機時間同步的精度

        修改說明 (Modification Guide):
            如需調整品質閾值（目前 10ms），修改此函數中的判斷邏輯
        """
        # 轉換為秒
        rgb_start = rgb_timing["start_ns"] / 1e9
        thermal_start = thermal_timing["start_ns"] / 1e9

        # 計算差異（毫秒）
        sync_diff_ms = abs(rgb_start - thermal_start) * 1000

        # 記錄到歷史
        self.sync_history.append(sync_diff_ms)

        # 品質評級
        sync_quality = "good" if sync_diff_ms < 10 else "poor"

        return {"sync_diff_ms": sync_diff_ms, "sync_quality": sync_quality}

    async def _save_frame_async(
        self, save_callback, rgb_array, thermal_data, session_path, frame_idx
    ):
        """
        非同步儲存幀資料

        參數 (Args):
            save_callback: 儲存回呼函數
            rgb_array: RGB影像陣列
            thermal_data: 熱影像資料
            session_path: 階段路徑
            frame_idx: 幀索引
        """
        # 並行儲存RGB和Thermal
        await self.async_loop.run_in_executor(
            self.save_executor,
            save_callback,
            rgb_array,
            thermal_data,
            session_path,
            frame_idx,
        )

    async def _flush_timestamps_async(self, timestamp_buffer, timestamp_path):
        """
        非同步批次寫入時間戳記

        參數 (Args):
            timestamp_buffer: 時間戳記緩衝器
            timestamp_path: 時間戳記檔案路徑
        """
        await self.async_loop.run_in_executor(
            self.save_executor, timestamp_buffer.flush_to_file, timestamp_path
        )

    def get_stats(self) -> dict:
        """
        取得錄製統計資訊

        返回 (Returns):
            dict: 統計資訊
                - frame_count: 已錄製幀數
                - expected_frame_count: 期望幀數
                - dropped_frames: 跳過幀數
                - late_frames: 延遲幀數
                - fps: 目標 FPS
                - sync_history: 同步誤差歷史（list）
                - timing_errors: 時序誤差歷史（list）

        用途 (Purpose):
            提供統計資料給檔案管理器和顯示模組

        修改說明 (Modification Guide):
            如需添加新的統計項目，在此函數中添加
        """
        return {
            "frame_count": self.frame_count,
            "expected_frame_count": self.expected_frame_count,
            "dropped_frames": self.dropped_frames,
            "late_frames": self.late_frames,
            "fps": self.fps,
            "sync_history": list(self.sync_history),
            "timing_errors": list(self.timing_errors),
        }

    def set_fps(self, fps: int) -> None:
        """
        設定目標 FPS

        參數 (Args):
            fps (int): 新的 FPS 值 (1-25)

        注意事項 (Notes):
            錄製期間修改 FPS 會影響時序計算
            建議在錄製前設定

        修改說明 (Modification Guide):
            如需添加 FPS 驗證，在此函數中添加
        """
        self.fps = fps
