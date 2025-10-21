#!/usr/bin/env python3
"""
時間戳記緩衝器模組 (Timestamp Buffer Module)

用途 (Purpose):
    批次化時間戳記的寫入，減少磁碟 I/O 次數，提升效能
    Batch timestamp writes to reduce disk I/O and improve performance

主要類別 (Main Class):
    TimestampBuffer: 批次時間戳記緩衝器

修改說明 (Modification Guide):
    - 如需調整批次大小，修改初始化時的 batch_size 參數
    - 如需改變輸出格式，修改 flush_to_file() 中的寫入邏輯
    - 如需添加新的時間戳記欄位，在 flush_to_file() 的 header 和資料寫入處修改
"""

import os
from typing import Dict, Any


class TimestampBuffer:
    """
    批次時間戳記緩衝器

    用途 (Purpose):
        將時間戳記資料暫存在記憶體中，累積到一定數量後才批次寫入檔案
        避免每一幀都進行磁碟寫入，大幅提升錄製效能

    屬性 (Attributes):
        buffer (list): 暫存時間戳記資料的列表
        batch_size (int): 批次大小，達到此數量時觸發寫入

    使用範例 (Usage Example):
        >>> buffer = TimestampBuffer(batch_size=50)
        >>>
        >>> # 添加時間戳記
        >>> timestamp_data = {
        ...     'frame_idx': 0,
        ...     'expected_frame_idx': 0,
        ...     'target_time_ns': 1234567890,
        ...     'timing_error_ms': 0.5,
        ...     'sync_diff_ms': 2.3
        ... }
        >>> buffer.add_timestamp(timestamp_data)
        >>>
        >>> # 檢查是否需要寫入
        >>> if buffer.should_flush():
        ...     buffer.flush_to_file('/path/to/timestamps.txt')

    注意事項 (Notes):
        - 錄製結束時記得呼叫 flush_to_file() 寫入剩餘資料
        - batch_size 越大，I/O 次數越少，但意外中斷時遺失資料越多
        - batch_size 越小，資料越安全，但 I/O 負擔越重
    """

    def __init__(self, batch_size: int = 50):
        """
        初始化時間戳記緩衝器

        參數 (Args):
            batch_size (int): 批次大小
                - 預設 50: 平衡效能與資料安全
                - 建議範圍: 20-100
                - 每批次約 2-5 KB 資料量

        修改建議 (Modification Tips):
            如果錄製過程中經常當機，可以減小 batch_size 以減少資料遺失
            如果 I/O 成為瓶頸，可以增大 batch_size 以減少寫入次數
        """
        self.buffer = []          # 時間戳記資料列表
        self.batch_size = batch_size  # 批次大小閾值

    def add_timestamp(self, timestamp_data: Dict[str, Any]) -> None:
        """
        添加一筆時間戳記到緩衝區

        參數 (Args):
            timestamp_data (dict): 時間戳記資料字典，必須包含:
                - frame_idx (int): 實際幀索引（成功錄製的幀編號）
                - expected_frame_idx (int): 期望幀索引（應該錄製的幀編號）
                - target_time_ns (int): 目標時間（奈秒）
                - timing_error_ms (float): 時序誤差（毫秒）
                - sync_diff_ms (float): 雙相機同步差異（毫秒）

        使用說明 (Usage):
            在每次成功擷取一幀後呼叫此方法

        修改說明 (Modification Guide):
            如需記錄其他資訊（如溫度、曝光時間等），在 timestamp_data 中添加即可
            記得同步修改 flush_to_file() 中的 header 和寫入邏輯
        """
        self.buffer.append(timestamp_data)

    def should_flush(self) -> bool:
        """
        檢查是否應該執行批次寫入

        返回 (Returns):
            bool: True 表示緩衝區已滿，應該寫入；False 表示尚未達到閾值

        使用說明 (Usage):
            在 add_timestamp() 後呼叫，決定是否觸發寫入

        修改說明 (Modification Guide):
            如需更複雜的觸發條件（如時間間隔），可以在此添加邏輯
        """
        return len(self.buffer) >= self.batch_size

    def flush_to_file(self, timestamp_path: str) -> None:
        """
        將緩衝區的時間戳記批次寫入檔案

        參數 (Args):
            timestamp_path (str): 時間戳記檔案的完整路徑

        檔案格式 (File Format):
            CSV 格式，包含以下欄位:
            - frame_idx: 實際錄製的幀編號
            - expected_frame_idx: 期望錄製的幀編號（若相同表示無跳幀）
            - target_time_ns: 預定擷取時間（奈秒精度）
            - timing_error_ms: 實際時間與目標時間的誤差（毫秒）
            - sync_diff_ms: RGB 和熱影像相機的同步差異（毫秒）

        寫入邏輯 (Write Logic):
            1. 如果緩衝區為空，直接返回
            2. 檢查檔案是否存在，決定是否寫入 CSV header
            3. 以 append 模式打開檔案
            4. 如需要，先寫入 header
            5. 逐行寫入緩衝區的所有資料
            6. 清空緩衝區
            7. 如果寫入失敗，印出錯誤訊息（不中斷錄製）

        錯誤處理 (Error Handling):
            寫入失敗不會拋出例外，只會印出錯誤訊息
            這樣設計是為了避免時間戳記寫入問題影響主要的錄製流程

        修改說明 (Modification Guide):
            添加新欄位的步驟:
            1. 在 header 字串中添加欄位名稱
            2. 在 f.write() 行添加對應的資料欄位
            3. 確保 add_timestamp() 提供的 dict 包含新欄位

        範例 (Example):
            假設要添加 'rgb_exposure_ms' 欄位:
            1. Header: "...,sync_diff_ms,rgb_exposure_ms\n"
            2. Data: f"...{data['sync_diff_ms']:.3f},{data['rgb_exposure_ms']:.3f}\n"
            3. add_timestamp() 時: data['rgb_exposure_ms'] = exposure_time
        """
        # 檢查緩衝區是否有資料
        if not self.buffer:
            return

        # 判斷是否需要寫入 header（檔案不存在時）
        write_header = not os.path.exists(timestamp_path)

        try:
            # 以 append 模式打開檔案（不會覆蓋既有內容）
            with open(timestamp_path, "a") as f:
                # 如果是新檔案，先寫入 CSV header
                if write_header:
                    f.write("frame_idx,expected_frame_idx,target_time_ns,timing_error_ms,sync_diff_ms\n")

                # 批次寫入所有緩衝的時間戳記
                for data in self.buffer:
                    # 每一行包含：實際幀號、期望幀號、目標時間、時序誤差、同步差異
                    f.write(f"{data['frame_idx']},{data['expected_frame_idx']},")
                    f.write(f"{data['target_time_ns']},{data['timing_error_ms']:.3f},")
                    f.write(f"{data['sync_diff_ms']:.3f}\n")

            # 寫入成功後清空緩衝區
            self.buffer.clear()

        except Exception as e:
            # 時間戳記寫入失敗不應該中斷錄製，只印出警告
            # 修改說明: 如需更詳細的錯誤處理，可以在此使用 logging
            print(f"時間戳記寫入失敗: {e}")

    def get_buffer_size(self) -> int:
        """
        取得當前緩衝區的資料筆數

        返回 (Returns):
            int: 緩衝區中的時間戳記筆數

        用途 (Purpose):
            可用於監控或除錯
        """
        return len(self.buffer)

    def clear(self) -> None:
        """
        清空緩衝區（不寫入檔案）

        警告 (Warning):
            此操作會直接丟棄緩衝區的所有資料
            一般情況下應該使用 flush_to_file() 而非 clear()

        用途 (Purpose):
            用於錯誤恢復或重置狀態
        """
        self.buffer.clear()
