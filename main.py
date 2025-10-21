#!/usr/bin/env python3
"""
DuoFusion v1.0 - 雙相機錄製系統入口點
Entry Point for DuoFusion Dual Camera Recording System

用途 (Purpose):
    程式的主要入口點，負責啟動 DuoFusion 應用程式

使用方法 (Usage):
    python main.py

    或使用 uv:
    uv run python main.py

架構說明 (Architecture):
    此程式已重構為模組化架構:

    main.py (入口點)
      └─> core/duo_fusion.py (主應用程式類別)
            ├─> core/camera_manager.py (相機管理)
            ├─> core/recorder.py (錄製控制)
            ├─> core/file_manager.py (檔案管理)
            ├─> core/timestamp_buffer.py (時間戳記緩衝)
            ├─> utils/config.py (配置)
            ├─> utils/timing.py (時間工具)
            └─> utils/display.py (顯示和UI)

修改說明 (Modification Guide):
    - 修改配置參數: 編輯 utils/config.py
    - 修改相機邏輯: 編輯 core/camera_manager.py
    - 修改錄製邏輯: 編輯 core/recorder.py
    - 修改檔案操作: 編輯 core/file_manager.py
    - 修改顯示邏輯: 編輯 utils/display.py
    - 修改主流程: 編輯 core/duo_fusion.py

除錯技巧 (Debugging Tips):
    1. 檢查配置: 查看 utils/config.py
    2. 檢查相機初始化: 在 core/camera_manager.py 的 init_cameras() 添加 print()
    3. 檢查錄製迴圈: 在 core/recorder.py 的 _recording_loop() 添加 print()
    4. 檢查檔案儲存: 在 core/file_manager.py 的 save_* 函數添加 print()
    5. 查看錯誤日誌: 檢查 logs/error_*.txt

常見問題 (Common Issues):
    1. 相機初始化失敗:
       - 確認在 Raspberry Pi 上執行
       - 檢查相機連接
       - 檢查 GPIO 配置 (utils/config.py)

    2. 錄製跳幀過多:
       - 降低 FPS (utils/config.py 中的 DEFAULT_FPS)
       - 增加跳幀容忍度 (config.FRAME_TOLERANCE)
       - 檢查儲存速度（使用 RAM disk）

    3. 同步品質差:
       - 檢查 SPI 速度 (config.SPI_SPEED)
       - 減少系統負載
       - 檢查時序參數 (config.SLEEP_THRESHOLD)

    4. 檔案儲存失敗:
       - 檢查磁碟空間
       - 檢查儲存路徑權限
       - 降低 JPEG 品質 (config.JPEG_QUALITY)

歷史記錄 (Change Log):
    v1.0 (2024-10-21):
    - 重構為模組化架構
    - 分離關注點：相機、錄製、檔案、顯示
    - 添加詳細的中文註解
    - 提升程式碼可維護性

原始檔案 (Original File):
    原始的 main.py 已備份為 main_original.py
    如需參考原始實作，請查看該檔案
"""

import sys

# 檢查 Python 版本
# Check Python version
if sys.version_info < (3, 7):
    print("錯誤: 此程式需要 Python 3.7 或更高版本")
    print("Error: This program requires Python 3.7 or higher")
    sys.exit(1)

# 導入主應用程式類別
# Import main application class
try:
    from core.duo_fusion import DuoFusion
except ImportError as e:
    print(f"錯誤: 無法導入必要模組 - {e}")
    print(f"Error: Cannot import required module - {e}")
    print("\n請確認:")
    print("Please check:")
    print("1. 所有模組檔案都存在 (core/, utils/)")
    print("   All module files exist (core/, utils/)")
    print("2. 已安裝所有依賴套件")
    print("   All dependencies are installed")
    print("3. 在 Raspberry Pi 上執行（需要硬體相關套件）")
    print("   Running on Raspberry Pi (hardware packages required)")
    sys.exit(1)


def main():
    """
    主函數

    流程 (Flow):
        1. 建立 DuoFusion 實例
        2. 執行主程式
        3. 正常結束或錯誤處理

    修改說明 (Modification Guide):
        一般情況下不需要修改此函數
        如需修改程式流程，請編輯 core/duo_fusion.py 的 run() 方法
    """
    try:
        # 建立並執行 DuoFusion 應用程式
        # Create and run DuoFusion application
        app = DuoFusion()
        app.run()

    except KeyboardInterrupt:
        # 使用者中斷（Ctrl+C）
        # User interruption (Ctrl+C)
        print("\n\n程式已終止 (Program terminated)")
        sys.exit(0)

    except Exception as e:
        # 未預期的錯誤
        # Unexpected error
        print(f"\n\n✗ 嚴重錯誤 (Critical error): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    """
    程式入口點

    當直接執行此檔案時會執行 main()
    When this file is executed directly, main() will be called
    """
    main()
