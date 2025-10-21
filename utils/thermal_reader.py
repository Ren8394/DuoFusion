#!/usr/bin/env python3
"""
熱影像資料讀取工具 (Thermal Data Reader Utilities)

用途 (Purpose):
    提供讀取和分析 NPY 格式熱影像資料的工具函數
    方便後續資料處理、分析和視覺化

主要功能 (Main Functions):
    - load_thermal_frame(): 讀取單幀熱影像
    - load_thermal_sequence(): 批次讀取多幀
    - get_temperature_stats(): 計算溫度統計
    - visualize_thermal(): 視覺化熱影像（可選）

使用範例 (Usage Example):
    >>> from utils.thermal_reader import load_thermal_frame, get_temperature_stats
    >>>
    >>> # 讀取單幀
    >>> data = load_thermal_frame('records/20241021_080000/Thermal/000000.npy')
    >>> print(f"溫度範圍: {data.min():.1f} - {data.max():.1f}°C")
    >>>
    >>> # 取得統計資訊
    >>> stats = get_temperature_stats(data)
    >>> print(f"平均: {stats['mean']:.1f}°C, 標準差: {stats['std']:.2f}°C")

修改說明 (Modification Guide):
    - 如需添加新的分析功能，在此檔案中添加新函數
    - 如需改變視覺化方式，修改 visualize_thermal()
"""

import os
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path


def load_thermal_frame(file_path: str) -> Optional[np.ndarray]:
    """
    讀取單幀熱影像資料

    參數 (Args):
        file_path (str): NPY 檔案路徑

    返回 (Returns):
        np.ndarray: 溫度陣列（攝氏度），shape=(rows, cols)
        None: 讀取失敗

    使用範例 (Usage Example):
        >>> data = load_thermal_frame('Thermal/000000.npy')
        >>> if data is not None:
        ...     print(f"解析度: {data.shape}")
        ...     print(f"溫度範圍: {data.min():.1f} - {data.max():.1f}°C")

    錯誤處理 (Error Handling):
        讀取失敗時印出錯誤訊息並返回 None
    """
    try:
        data = np.load(file_path)
        return data
    except Exception as e:
        print(f"讀取熱影像失敗 ({file_path}): {e}")
        return None


def load_thermal_sequence(
    thermal_dir: str,
    start_idx: int = 0,
    end_idx: Optional[int] = None,
    step: int = 1
) -> List[np.ndarray]:
    """
    批次讀取熱影像序列

    參數 (Args):
        thermal_dir (str): Thermal 目錄路徑
        start_idx (int): 起始幀索引（預設 0）
        end_idx (int, optional): 結束幀索引（None = 全部）
        step (int): 步進（預設 1，設為 2 表示每隔一幀讀取）

    返回 (Returns):
        List[np.ndarray]: 熱影像陣列列表

    使用範例 (Usage Example):
        >>> # 讀取前 10 幀
        >>> frames = load_thermal_sequence('records/20241021/Thermal', end_idx=10)
        >>> print(f"讀取了 {len(frames)} 幀")
        >>>
        >>> # 每隔 5 幀讀取一次（降低記憶體使用）
        >>> frames = load_thermal_sequence('records/20241021/Thermal', step=5)

    修改說明 (Modification Guide):
        如需只讀取特定範圍的幀，設定 start_idx 和 end_idx
    """
    frames = []
    thermal_path = Path(thermal_dir)

    # 取得所有 NPY 檔案並排序
    npy_files = sorted(thermal_path.glob("*.npy"))

    # 確定範圍
    if end_idx is None:
        end_idx = len(npy_files)

    # 讀取指定範圍的幀
    for i in range(start_idx, min(end_idx, len(npy_files)), step):
        data = load_thermal_frame(str(npy_files[i]))
        if data is not None:
            frames.append(data)

    return frames


def get_temperature_stats(thermal_data: np.ndarray) -> Dict[str, float]:
    """
    計算溫度統計資訊

    參數 (Args):
        thermal_data (np.ndarray): 溫度陣列

    返回 (Returns):
        dict: 統計資訊
            - min: 最低溫度（°C）
            - max: 最高溫度（°C）
            - mean: 平均溫度（°C）
            - median: 中位數溫度（°C）
            - std: 標準差（°C）
            - range: 溫度範圍（°C）

    使用範例 (Usage Example):
        >>> data = load_thermal_frame('000000.npy')
        >>> stats = get_temperature_stats(data)
        >>> print(f"溫度統計:")
        >>> print(f"  平均: {stats['mean']:.1f}°C")
        >>> print(f"  範圍: {stats['min']:.1f} - {stats['max']:.1f}°C")
        >>> print(f"  標準差: {stats['std']:.2f}°C")

    修改說明 (Modification Guide):
        如需添加其他統計量（如百分位數），在此函數中添加計算
    """
    return {
        'min': float(np.min(thermal_data)),
        'max': float(np.max(thermal_data)),
        'mean': float(np.mean(thermal_data)),
        'median': float(np.median(thermal_data)),
        'std': float(np.std(thermal_data)),
        'range': float(np.max(thermal_data) - np.min(thermal_data))
    }


def find_hot_spots(
    thermal_data: np.ndarray,
    threshold: Optional[float] = None,
    top_n: int = 5
) -> List[Tuple[int, int, float]]:
    """
    找出熱點位置

    參數 (Args):
        thermal_data (np.ndarray): 溫度陣列
        threshold (float, optional): 溫度閾值（None = 自動計算）
        top_n (int): 返回前 N 個最熱的點

    返回 (Returns):
        List[Tuple[int, int, float]]: 熱點列表 [(row, col, temperature), ...]

    使用範例 (Usage Example):
        >>> data = load_thermal_frame('000000.npy')
        >>> hot_spots = find_hot_spots(data, top_n=3)
        >>> for row, col, temp in hot_spots:
        ...     print(f"位置 ({row}, {col}): {temp:.1f}°C")

    修改說明 (Modification Guide):
        如需改變熱點判定標準，調整 threshold 計算方式
    """
    # 自動計算閾值（平均溫度 + 標準差）
    if threshold is None:
        threshold = np.mean(thermal_data) + np.std(thermal_data)

    # 找出超過閾值的點
    hot_mask = thermal_data > threshold
    hot_indices = np.argwhere(hot_mask)

    # 取得溫度值並排序
    hot_temps = thermal_data[hot_mask]
    sorted_indices = np.argsort(hot_temps)[::-1]  # 降序排列

    # 返回前 N 個最熱的點
    result = []
    for i in sorted_indices[:top_n]:
        row, col = hot_indices[i]
        temp = thermal_data[row, col]
        result.append((int(row), int(col), float(temp)))

    return result


def calculate_temporal_average(frames: List[np.ndarray]) -> np.ndarray:
    """
    計算時間平均（多幀平均）

    參數 (Args):
        frames (List[np.ndarray]): 多幀熱影像列表

    返回 (Returns):
        np.ndarray: 平均後的熱影像

    用途 (Purpose):
        減少雜訊，取得更穩定的溫度分布

    使用範例 (Usage Example):
        >>> frames = load_thermal_sequence('Thermal/', end_idx=10)
        >>> avg_frame = calculate_temporal_average(frames)
        >>> print(f"平均溫度: {np.mean(avg_frame):.1f}°C")

    修改說明 (Modification Guide):
        如需使用中位數而非平均值，將 np.mean 改為 np.median
    """
    if not frames:
        raise ValueError("幀列表為空")

    # 堆疊所有幀並計算平均值
    stacked = np.stack(frames, axis=0)
    return np.mean(stacked, axis=0)


def export_to_csv(
    thermal_data: np.ndarray,
    output_path: str,
    delimiter: str = ','
) -> bool:
    """
    將 NPY 格式轉換為 CSV 格式

    參數 (Args):
        thermal_data (np.ndarray): 溫度陣列
        output_path (str): 輸出 CSV 檔案路徑
        delimiter (str): 分隔符號（預設逗號）

    返回 (Returns):
        bool: True 表示轉換成功

    用途 (Purpose):
        方便用 Excel 或其他工具查看數據

    使用範例 (Usage Example):
        >>> data = load_thermal_frame('000000.npy')
        >>> export_to_csv(data, '000000.csv')
        >>> # 現在可以用 Excel 開啟 000000.csv

    修改說明 (Modification Guide):
        如需改變浮點數格式，添加 fmt 參數到 np.savetxt()
    """
    try:
        np.savetxt(output_path, thermal_data, delimiter=delimiter, fmt='%.2f')
        return True
    except Exception as e:
        print(f"轉換為 CSV 失敗: {e}")
        return False


def visualize_thermal(
    thermal_data: np.ndarray,
    title: str = "Thermal Image",
    colormap: str = "hot",
    show_colorbar: bool = True,
    save_path: Optional[str] = None
) -> None:
    """
    視覺化熱影像

    參數 (Args):
        thermal_data (np.ndarray): 溫度陣列
        title (str): 圖表標題
        colormap (str): 色彩映射（'hot', 'jet', 'viridis' 等）
        show_colorbar (bool): 是否顯示色條
        save_path (str, optional): 儲存路徑（None = 不儲存）

    使用範例 (Usage Example):
        >>> data = load_thermal_frame('000000.npy')
        >>> visualize_thermal(data, title="第一幀", save_path="frame_0.png")

    注意事項 (Notes):
        需要安裝 matplotlib: pip install matplotlib

    修改說明 (Modification Guide):
        如需改變色彩映射，修改 colormap 參數:
        - 'hot': 黑-紅-黃-白（適合熱影像）
        - 'jet': 藍-綠-黃-紅
        - 'viridis': 感知均勻色彩
        - 'gray': 灰階
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("視覺化需要 matplotlib，請安裝: pip install matplotlib")
        return

    plt.figure(figsize=(10, 8))
    im = plt.imshow(thermal_data, cmap=colormap, interpolation='nearest')

    if show_colorbar:
        cbar = plt.colorbar(im)
        cbar.set_label('Temperature (°C)', rotation=270, labelpad=20)

    plt.title(title)
    plt.xlabel('Column')
    plt.ylabel('Row')

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"圖片已儲存: {save_path}")

    plt.show()


def batch_convert_to_images(
    thermal_dir: str,
    output_dir: str,
    colormap: str = "hot",
    start_idx: int = 0,
    end_idx: Optional[int] = None
) -> int:
    """
    批次將熱影像轉換為圖片

    參數 (Args):
        thermal_dir (str): Thermal 目錄路徑
        output_dir (str): 輸出目錄路徑
        colormap (str): 色彩映射
        start_idx (int): 起始幀索引
        end_idx (int, optional): 結束幀索引

    返回 (Returns):
        int: 成功轉換的幀數

    使用範例 (Usage Example):
        >>> count = batch_convert_to_images(
        ...     'records/20241021/Thermal',
        ...     'thermal_images',
        ...     colormap='jet'
        ... )
        >>> print(f"轉換了 {count} 幀")

    修改說明 (Modification Guide):
        如需改變輸出格式或 DPI，修改 visualize_thermal() 的 savefig 參數
    """
    os.makedirs(output_dir, exist_ok=True)
    frames = load_thermal_sequence(thermal_dir, start_idx, end_idx)

    count = 0
    for i, frame in enumerate(frames):
        output_path = os.path.join(output_dir, f"thermal_{i:06d}.png")
        visualize_thermal(
            frame,
            title=f"Frame {i}",
            colormap=colormap,
            save_path=output_path
        )
        count += 1

    return count


# ============================================================================
# 使用範例腳本 (Example Usage Script)
# ============================================================================
if __name__ == "__main__":
    """
    示範如何使用熱影像讀取工具

    執行方式 (How to run):
        python utils/thermal_reader.py
    """
    import sys

    print("=" * 60)
    print("熱影像資料讀取工具示範")
    print("=" * 60)

    # 範例 1: 讀取單幀
    print("\n範例 1: 讀取單幀")
    print("-" * 60)
    example_file = "records/example/Thermal/000000.npy"

    if os.path.exists(example_file):
        data = load_thermal_frame(example_file)
        if data is not None:
            print(f"✓ 成功讀取: {example_file}")
            print(f"  解析度: {data.shape}")
            stats = get_temperature_stats(data)
            print(f"  溫度範圍: {stats['min']:.1f} - {stats['max']:.1f}°C")
            print(f"  平均溫度: {stats['mean']:.1f}°C")
            print(f"  標準差: {stats['std']:.2f}°C")
    else:
        print(f"⚠ 範例檔案不存在: {example_file}")
        print("  請先錄製一些資料")

    # 範例 2: 批次讀取
    print("\n範例 2: 批次讀取序列")
    print("-" * 60)
    example_dir = "records/example/Thermal"

    if os.path.exists(example_dir):
        frames = load_thermal_sequence(example_dir, end_idx=5)
        print(f"✓ 讀取了 {len(frames)} 幀")

        if frames:
            avg_frame = calculate_temporal_average(frames)
            avg_stats = get_temperature_stats(avg_frame)
            print(f"  平均後溫度: {avg_stats['mean']:.1f}°C")
    else:
        print(f"⚠ 範例目錄不存在: {example_dir}")

    # 範例 3: 找熱點
    print("\n範例 3: 找出熱點")
    print("-" * 60)

    if os.path.exists(example_file):
        data = load_thermal_frame(example_file)
        if data is not None:
            hot_spots = find_hot_spots(data, top_n=3)
            print(f"✓ 找到 {len(hot_spots)} 個熱點:")
            for i, (row, col, temp) in enumerate(hot_spots, 1):
                print(f"  {i}. 位置 ({row}, {col}): {temp:.1f}°C")

    print("\n" + "=" * 60)
    print("如需更多功能，請參考函數文檔字串")
    print("=" * 60)
