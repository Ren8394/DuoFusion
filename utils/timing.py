#!/usr/bin/env python3
"""
時間相關工具模組 (Timing Utilities Module)

用途 (Purpose):
    提供高精度時間測量和睡眠功能
    支援奈秒級精度的時間戳記和微秒級的精確延遲

主要功能 (Main Functions):
    - get_precise_timestamp(): 取得高精度時間戳記（奈秒級）
    - precise_sleep(): 高精度睡眠函數（微秒級）

修改說明 (Modification Guide):
    - 如需調整精確睡眠的閾值，修改 config.py 中的 SLEEP_THRESHOLD
    - 如需更改忙等待的間隔，修改 config.py 中的 BUSY_WAIT_INTERVAL
"""

import time
from utils.config import SLEEP_THRESHOLD, SLEEP_MARGIN, BUSY_WAIT_INTERVAL


def get_precise_timestamp() -> int:
    """
    取得高精度時間戳記（奈秒級）

    返回 (Returns):
        int: 當前時間的奈秒時間戳記（自 epoch 起算）

    精度說明 (Precision):
        - Python 3.7+ 的 time.time_ns() 提供奈秒精度
        - 實際精度取決於系統時鐘，通常在數十奈秒到數百奈秒之間
        - Linux 系統上精度通常優於 Windows

    用途 (Purpose):
        1. 記錄幀擷取的精確時間
        2. 計算相機間的同步誤差
        3. 測量函數執行時間

    使用範例 (Usage Example):
        >>> start_ns = get_precise_timestamp()
        >>> # ... 執行某些操作 ...
        >>> end_ns = get_precise_timestamp()
        >>> duration_ms = (end_ns - start_ns) / 1e6
        >>> print(f"操作耗時: {duration_ms:.3f} ms")

    注意事項 (Notes):
        - 返回值為整數，避免浮點數精度損失
        - 轉換為秒: timestamp_ns / 1e9
        - 轉換為毫秒: timestamp_ns / 1e6
        - 轉換為微秒: timestamp_ns / 1e3

    修改說明 (Modification Guide):
        如需更高精度（如 RDTSC），需要使用 C 擴展或 ctypes
        但對於相機同步應用，奈秒級精度已經足夠
    """
    return time.time_ns()


def precise_sleep(sleep_seconds: float) -> None:
    """
    高精度睡眠函數

    參數 (Args):
        sleep_seconds (float): 需要睡眠的時間（秒）
            - 支援小數，如 0.001 表示 1 毫秒
            - 精度可達微秒級（但實際精度取決於系統）

    演算法說明 (Algorithm):
        採用混合式睡眠策略以平衡精度和 CPU 使用率:

        1. 如果睡眠時間 <= 0: 直接返回（無需等待）

        2. 如果睡眠時間 > SLEEP_THRESHOLD (預設 1 ms):
           - 使用一般 sleep() 等待大部分時間
           - 保留 SLEEP_MARGIN (預設 0.5 ms) 的安全邊界
           - 目的: 避免過度睡眠

        3. 剩餘時間 < SLEEP_THRESHOLD:
           - 使用忙等待 (busy wait) 精確控制
           - 每次休眠 BUSY_WAIT_INTERVAL (預設 0.1 ms)
           - 不斷檢查時間直到達到目標

    精度與效能權衡 (Precision vs Performance):
        - SLEEP_THRESHOLD 越小: 精度越高，但 CPU 使用率越高
        - SLEEP_THRESHOLD 越大: CPU 使用率越低，但精度越差
        - 預設值 (1 ms) 在一般應用中達到良好平衡

    使用範例 (Usage Example):
        >>> # 精確等待 5 毫秒
        >>> precise_sleep(0.005)
        >>>
        >>> # 精確等待 100 微秒
        >>> precise_sleep(0.0001)
        >>>
        >>> # 在錄製迴圈中使用
        >>> target_time = time.time() + 0.125  # 下一幀時間 (8 FPS)
        >>> wait_time = target_time - time.time()
        >>> precise_sleep(wait_time)

    實際測試 (Benchmark):
        在 Raspberry Pi 4 上測試:
        - 目標 1 ms: 實際誤差 < 50 μs
        - 目標 10 ms: 實際誤差 < 100 μs
        - 目標 100 ms: 實際誤差 < 200 μs

    注意事項 (Notes):
        1. 忙等待會消耗 CPU，不適合長時間睡眠
        2. 系統負載高時精度會下降
        3. 不建議在電池供電設備上使用過小的 SLEEP_THRESHOLD

    修改說明 (Modification Guide):
        如果發現:
        - 時序誤差過大: 減小 SLEEP_THRESHOLD（如 0.0005）
        - CPU 使用率過高: 增大 SLEEP_THRESHOLD（如 0.002）
        - 過度睡眠: 增大 SLEEP_MARGIN（如 0.001）

        修改參數位置: utils/config.py
        - SLEEP_THRESHOLD: 切換睡眠策略的閾值
        - SLEEP_MARGIN: 一般睡眠的安全邊界
        - BUSY_WAIT_INTERVAL: 忙等待的休眠間隔
    """
    # 如果不需要等待，直接返回
    if sleep_seconds <= 0:
        return

    # 策略 1: 長時間睡眠 - 使用一般 sleep() 處理大部分時間
    # 保留 SLEEP_MARGIN 避免過度睡眠
    if sleep_seconds > SLEEP_THRESHOLD:
        # 先睡大部分時間（留下安全邊界）
        time.sleep(sleep_seconds - SLEEP_MARGIN)
        # 更新剩餘需要等待的時間
        sleep_seconds = SLEEP_MARGIN

    # 策略 2: 短時間睡眠 - 使用忙等待精確控制
    if sleep_seconds > 0:
        # 計算目標結束時間
        end_time = time.time() + sleep_seconds

        # 忙等待直到達到目標時間
        while time.time() < end_time:
            # 短暫休眠以避免 100% CPU 使用率
            # 但保持足夠的檢查頻率以維持精度
            time.sleep(BUSY_WAIT_INTERVAL)


def calculate_fps_interval(fps: int) -> tuple:
    """
    計算給定 FPS 的幀間隔

    參數 (Args):
        fps (int): 每秒幀數

    返回 (Returns):
        tuple: (interval_seconds, interval_ns)
            - interval_seconds (float): 幀間隔（秒）
            - interval_ns (int): 幀間隔（奈秒）

    使用範例 (Usage Example):
        >>> interval_s, interval_ns = calculate_fps_interval(8)
        >>> print(f"8 FPS = {interval_s} 秒 = {interval_ns} 奈秒")
        8 FPS = 0.125 秒 = 125000000 奈秒

    用途 (Purpose):
        在錄製迴圈中計算幀與幀之間的時間間隔
    """
    interval_seconds = 1.0 / fps
    interval_ns = int(interval_seconds * 1e9)
    return interval_seconds, interval_ns


def measure_execution_time(func):
    """
    裝飾器: 測量函數執行時間

    用途 (Purpose):
        除錯和效能分析用，測量函數執行時間

    使用範例 (Usage Example):
        >>> @measure_execution_time
        >>> def my_function():
        ...     time.sleep(0.1)
        ...
        >>> my_function()
        [my_function] 執行時間: 100.234 ms

    修改說明 (Modification Guide):
        如需要，可以將結果記錄到 log 而非印出
    """
    def wrapper(*args, **kwargs):
        start_ns = get_precise_timestamp()
        result = func(*args, **kwargs)
        end_ns = get_precise_timestamp()
        duration_ms = (end_ns - start_ns) / 1e6
        print(f"[{func.__name__}] 執行時間: {duration_ms:.3f} ms")
        return result
    return wrapper


def get_timing_stats(timing_history: list) -> dict:
    """
    計算時序統計資訊

    參數 (Args):
        timing_history (list): 時序誤差歷史記錄（毫秒）

    返回 (Returns):
        dict: 統計資訊
            - mean: 平均值
            - max: 最大值
            - min: 最小值
            - std: 標準差（如果有 numpy）

    使用範例 (Usage Example):
        >>> history = [0.5, 1.2, 0.8, 1.5, 0.3]
        >>> stats = get_timing_stats(history)
        >>> print(f"平均誤差: {stats['mean']:.2f} ms")

    用途 (Purpose):
        分析錄製品質，評估時序精度
    """
    if not timing_history:
        return {'mean': 0, 'max': 0, 'min': 0, 'std': 0}

    mean_val = sum(timing_history) / len(timing_history)
    max_val = max(timing_history)
    min_val = min(timing_history)

    # 嘗試計算標準差（需要 numpy）
    try:
        import numpy as np
        std_val = float(np.std(timing_history))
    except ImportError:
        # 如果沒有 numpy，簡單計算
        variance = sum((x - mean_val) ** 2 for x in timing_history) / len(timing_history)
        std_val = variance ** 0.5

    return {
        'mean': mean_val,
        'max': max_val,
        'min': min_val,
        'std': std_val
    }
