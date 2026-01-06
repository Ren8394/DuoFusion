#!/usr/bin/env python3
"""
影像對齊工具 (Image Alignment Tool)

用途 (Purpose):
    提供 GUI 介面來對齊 RGB 和熱影像資料
    方便後續資料處理和分析

主要功能 (Main Functions):
    - 選擇錄製資料夾
    - 顯示 RGB、Thermal、疊圖
    - 調整 Thermal 影像位置和縮放
    - 儲存對齊參數

使用範例 (Usage Example):
    >>> python utils/align.py

修改說明 (Modification Guide):
    - 如需調整預設縮放倍數，修改 DEFAULT_ZOOM
    - 如需改變色彩映射，修改 thermal_to_image()
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
try:
    from PIL import ImageTk
except ImportError:
    # For some systems, ImageTk is in tkinter
    from tkinter import ImageTk
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

# 預設參數
DEFAULT_ZOOM = 1.0
DEFAULT_OFFSET_X = 0
DEFAULT_OFFSET_Y = 0
ZOOM_STEP = 0.1
MOVE_STEP = 10

class AlignGUI:
    """
    影像對齊 GUI 應用程式

    屬性 (Attributes):
        root: Tkinter 根視窗
        current_folder: 當前選擇的資料夾
        rgb_images: RGB 影像列表
        thermal_data: Thermal 資料列表
        current_idx: 當前顯示的影像索引
        thermal_zoom: Thermal 縮放倍數
        thermal_offset_x: Thermal X 偏移
        thermal_offset_y: Thermal Y 偏移
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DuoFusion 影像對齊工具")
        self.root.geometry("1200x800")

        # 資料
        self.current_folder = ""
        self.rgb_images = []
        self.thermal_data = []
        self.current_idx = 0

        # 對齊參數
        self.thermal_zoom = DEFAULT_ZOOM
        self.thermal_offset_x = DEFAULT_OFFSET_X
        self.thermal_offset_y = DEFAULT_OFFSET_Y

        # GUI 元素
        self.rgb_label = None
        self.thermal_label = None
        self.mix_label = None
        self.status_label = None

        # 摺疊狀態
        self.rgb_visible = True
        self.thermal_visible = True
        self.rgb_frame = None
        self.thermal_frame = None
        self.mix_frame = None

        self.setup_gui()

    def setup_gui(self):
        """設定 GUI 介面"""
        # 工具列
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # 選擇資料夾按鈕
        select_btn = tk.Button(toolbar, text="選擇資料夾", command=self.select_folder)
        select_btn.pack(side=tk.LEFT, padx=5)

        # 導航按鈕
        prev_btn = tk.Button(toolbar, text="上一張", command=self.prev_image)
        prev_btn.pack(side=tk.LEFT, padx=5)

        next_btn = tk.Button(toolbar, text="下一張", command=self.next_image)
        next_btn.pack(side=tk.LEFT, padx=5)

        # Thermal 控制
        tk.Label(toolbar, text="Thermal:").pack(side=tk.LEFT, padx=5)

        zoom_in_btn = tk.Button(toolbar, text="放大", command=self.zoom_in)
        zoom_in_btn.pack(side=tk.LEFT, padx=2)

        zoom_out_btn = tk.Button(toolbar, text="縮小", command=self.zoom_out)
        zoom_out_btn.pack(side=tk.LEFT, padx=2)

        move_up_btn = tk.Button(toolbar, text="↑", command=self.move_up)
        move_up_btn.pack(side=tk.LEFT, padx=2)

        move_down_btn = tk.Button(toolbar, text="↓", command=self.move_down)
        move_down_btn.pack(side=tk.LEFT, padx=2)

        move_left_btn = tk.Button(toolbar, text="←", command=self.move_left)
        move_left_btn.pack(side=tk.LEFT, padx=2)

        move_right_btn = tk.Button(toolbar, text="→", command=self.move_right)
        move_right_btn.pack(side=tk.LEFT, padx=2)

        # 儲存按鈕
        save_btn = tk.Button(toolbar, text="儲存對齊參數", command=self.save_alignment)
        save_btn.pack(side=tk.RIGHT, padx=5)

        # 離開按鈕
        exit_btn = tk.Button(toolbar, text="離開", command=self.exit_app)
        exit_btn.pack(side=tk.RIGHT, padx=5)

        # 顯示區域
        display_frame = tk.Frame(self.root)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 摺疊控制按鈕
        control_frame = tk.Frame(display_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=2)

        self.rgb_toggle_btn = tk.Button(control_frame, text="隱藏 RGB", command=self.toggle_rgb)
        self.rgb_toggle_btn.pack(side=tk.LEFT, padx=2)

        self.thermal_toggle_btn = tk.Button(control_frame, text="隱藏 Thermal", command=self.toggle_thermal)
        self.thermal_toggle_btn.pack(side=tk.LEFT, padx=2)

        show_all_btn = tk.Button(control_frame, text="顯示全部", command=self.show_all)
        show_all_btn.pack(side=tk.LEFT, padx=2)

        # RGB 顯示
        self.rgb_frame = tk.LabelFrame(display_frame, text="RGB")
        self.rgb_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.rgb_label = tk.Label(self.rgb_frame)
        self.rgb_label.pack(fill=tk.BOTH, expand=True)

        # Thermal 顯示
        self.thermal_frame = tk.LabelFrame(display_frame, text="Thermal")
        self.thermal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.thermal_label = tk.Label(self.thermal_frame)
        self.thermal_label.pack(fill=tk.BOTH, expand=True)

        # 疊圖顯示
        self.mix_frame = tk.LabelFrame(display_frame, text="疊圖 (RGB + Thermal)")
        self.mix_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.mix_label = tk.Label(self.mix_frame)
        self.mix_label.pack(fill=tk.BOTH, expand=True)

        # 狀態列
        self.status_label = tk.Label(self.root, text="請選擇資料夾", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def select_folder(self):
        """選擇資料夾"""
        folder = filedialog.askdirectory(title="選擇錄製資料夾")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder_path: str):
        """載入資料夾中的影像"""
        try:
            rgb_dir = os.path.join(folder_path, "RGB")
            thermal_dir = os.path.join(folder_path, "Thermal")

            if not os.path.exists(rgb_dir) or not os.path.exists(thermal_dir):
                messagebox.showerror("錯誤", "資料夾結構不正確，缺少 RGB/ 或 Thermal/ 子目錄")
                return

            # 載入 RGB 影像
            self.rgb_images = []
            rgb_files = sorted(Path(rgb_dir).glob("*.jpg"))
            for rgb_file in rgb_files:
                img = Image.open(str(rgb_file))
                self.rgb_images.append(img)

            # 載入 Thermal 資料
            self.thermal_data = []
            thermal_files = sorted(Path(thermal_dir).glob("*.npy"))
            for thermal_file in thermal_files:
                data = np.load(str(thermal_file))
                self.thermal_data.append(data)

            if len(self.rgb_images) != len(self.thermal_data):
                messagebox.showwarning("警告", f"RGB 影像數 ({len(self.rgb_images)}) 與 Thermal 資料數 ({len(self.thermal_data)}) 不匹配")

            self.current_folder = folder_path
            self.current_idx = 0
            self.reset_alignment()
            self.update_display()

            self.update_status(f"載入完成: {len(self.rgb_images)} 張影像")

        except Exception as e:
            messagebox.showerror("錯誤", f"載入資料夾失敗: {e}")

    def reset_alignment(self):
        """重置對齊參數"""
        self.thermal_zoom = DEFAULT_ZOOM
        self.thermal_offset_x = DEFAULT_OFFSET_X
        self.thermal_offset_y = DEFAULT_OFFSET_Y

    def update_display(self):
        """更新顯示"""
        if not self.rgb_images or not self.thermal_data:
            return

        # 顯示 RGB
        rgb_img = self.rgb_images[self.current_idx]
        rgb_photo = ImageTk.PhotoImage(rgb_img)
        self.rgb_label.config(image=rgb_photo)
        self.rgb_label.image = rgb_photo

        # 顯示 Thermal
        thermal_data = self.thermal_data[self.current_idx]
        thermal_img = self.thermal_to_image(thermal_data)
        thermal_photo = ImageTk.PhotoImage(thermal_img)
        self.thermal_label.config(image=thermal_photo)
        self.thermal_label.image = thermal_photo

        # 顯示疊圖
        mix_img = self.create_overlay(rgb_img, thermal_data)
        mix_photo = ImageTk.PhotoImage(mix_img)
        self.mix_label.config(image=mix_photo)
        self.mix_label.image = mix_photo

        # 更新狀態
        self.update_status(f"第 {self.current_idx + 1}/{len(self.rgb_images)} 張 | 縮放: {self.thermal_zoom:.1f} | 偏移: ({self.thermal_offset_x}, {self.thermal_offset_y})")

    def thermal_to_image(self, thermal_data: np.ndarray) -> Image.Image:
        """將 Thermal 資料轉換為 PIL 影像"""
        # 正規化到 0-255
        min_temp = np.min(thermal_data)
        max_temp = np.max(thermal_data)
        if max_temp > min_temp:
            normalized = (thermal_data - min_temp) / (max_temp - min_temp) * 255
        else:
            normalized = np.zeros_like(thermal_data)

        # 轉換為 uint8
        thermal_uint8 = normalized.astype(np.uint8)

        # 建立灰階影像
        img = Image.fromarray(thermal_uint8, mode='L')

        # 套用色彩映射 (熱色調)
        img = ImageOps.colorize(img, black="black", white="red", mid="yellow")

        return img

    def create_overlay(self, rgb_img: Image.Image, thermal_data: np.ndarray) -> Image.Image:
        """建立 RGB 和 Thermal 的疊圖"""
        # 取得 Thermal 影像
        thermal_img = self.thermal_to_image(thermal_data)

        # 調整 Thermal 大小和位置
        rgb_width, rgb_height = rgb_img.size
        thermal_width, thermal_height = thermal_img.size

        # 計算縮放後的大小
        new_width = int(thermal_width * self.thermal_zoom)
        new_height = int(thermal_height * self.thermal_zoom)
        thermal_resized = thermal_img.resize((new_width, new_height), Image.LANCZOS)

        # 計算位置
        x = self.thermal_offset_x + (rgb_width - new_width) // 2
        y = self.thermal_offset_y + (rgb_height - new_height) // 2

        # 將 Thermal 轉為 RGBA 並設定透明度 (較不透明，讓熱影像更清楚)
        thermal_rgba = thermal_resized.convert('RGBA')
        # 設定 alpha 通道為較不透明 (200/255 ≈ 78% 不透明)
        alpha = Image.new('L', thermal_rgba.size, 200)  # 讓熱影像更清楚
        thermal_rgba.putalpha(alpha)

        # 將 RGB 轉為 RGBA 並稍微透明化
        rgb_rgba = rgb_img.convert('RGBA')
        # 讓 RGB 稍微透明 (230/255 ≈ 90% 不透明)
        rgb_alpha = Image.new('L', rgb_rgba.size, 230)
        rgb_rgba.putalpha(rgb_alpha)

        # 建立基礎影像
        result = Image.new('RGBA', rgb_img.size)

        # 先貼上 RGB
        result.paste(rgb_rgba, (0, 0))

        # 再疊加 Thermal (只在有效區域)
        if x < rgb_width and y < rgb_height and x + new_width > 0 and y + new_height > 0:
            # 計算有效的貼上區域
            paste_x = max(0, x)
            paste_y = max(0, y)
            crop_x = max(0, -x)
            crop_y = max(0, -y)
            crop_width = min(new_width - crop_x, rgb_width - paste_x)
            crop_height = min(new_height - crop_y, rgb_height - paste_y)

            if crop_width > 0 and crop_height > 0:
                thermal_cropped = thermal_rgba.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
                result.paste(thermal_cropped, (paste_x, paste_y), thermal_cropped)

        return result

    def prev_image(self):
        """上一張影像"""
        if self.rgb_images:
            self.current_idx = (self.current_idx - 1) % len(self.rgb_images)
            self.update_display()

    def next_image(self):
        """下一張影像"""
        if self.rgb_images:
            self.current_idx = (self.current_idx + 1) % len(self.rgb_images)
            self.update_display()

    def zoom_in(self):
        """放大 Thermal"""
        self.thermal_zoom += ZOOM_STEP
        self.update_display()

    def zoom_out(self):
        """縮小 Thermal"""
        self.thermal_zoom = max(0.1, self.thermal_zoom - ZOOM_STEP)
        self.update_display()

    def move_up(self):
        """向上移動 Thermal"""
        self.thermal_offset_y -= MOVE_STEP
        self.update_display()

    def move_down(self):
        """向下移動 Thermal"""
        self.thermal_offset_y += MOVE_STEP
        self.update_display()

    def move_left(self):
        """向左移動 Thermal"""
        self.thermal_offset_x -= MOVE_STEP
        self.update_display()

    def move_right(self):
        """向右移動 Thermal"""
        self.thermal_offset_x += MOVE_STEP
        self.update_display()

    def save_alignment(self):
        """儲存對齊參數"""
        if not self.current_folder:
            messagebox.showwarning("警告", "請先選擇資料夾")
            return

        try:
            align_file = os.path.join(self.current_folder, "alignment.txt")
            with open(align_file, 'w', encoding='utf-8') as f:
                f.write("# DuoFusion 影像對齊參數\n")
                f.write(f"thermal_zoom: {self.thermal_zoom}\n")
                f.write(f"thermal_offset_x: {self.thermal_offset_x}\n")
                f.write(f"thermal_offset_y: {self.thermal_offset_y}\n")
                f.write("# RGB 裁切/擴展範圍 (尚未實作)\n")
                f.write("rgb_crop_left: 0\n")
                f.write("rgb_crop_right: 0\n")
                f.write("rgb_crop_top: 0\n")
                f.write("rgb_crop_bottom: 0\n")

            messagebox.showinfo("成功", f"對齊參數已儲存到 {align_file}")
            self.update_status("對齊參數已儲存")

        except Exception as e:
            messagebox.showerror("錯誤", f"儲存失敗: {e}")

    def update_status(self, text: str):
        """更新狀態列"""
        self.status_label.config(text=text)

    def toggle_rgb(self):
        """切換 RGB 顯示"""
        if self.rgb_visible:
            self.rgb_frame.pack_forget()
            self.rgb_toggle_btn.config(text="顯示 RGB")
            self.rgb_visible = False
        else:
            self.rgb_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5, before=self.thermal_frame)
            self.rgb_toggle_btn.config(text="隱藏 RGB")
            self.rgb_visible = True
        self.update_layout()

    def toggle_thermal(self):
        """切換 Thermal 顯示"""
        if self.thermal_visible:
            self.thermal_frame.pack_forget()
            self.thermal_toggle_btn.config(text="顯示 Thermal")
            self.thermal_visible = False
        else:
            if self.rgb_visible:
                self.thermal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5, before=self.mix_frame)
            else:
                self.thermal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5, after=self.rgb_frame)
            self.thermal_toggle_btn.config(text="隱藏 Thermal")
            self.thermal_visible = True
        self.update_layout()

    def show_all(self):
        """顯示全部面板"""
        if not self.rgb_visible:
            self.toggle_rgb()
        if not self.thermal_visible:
            self.toggle_thermal()

    def update_layout(self):
        """更新佈局"""
        # 重新打包以確保正確的順序和擴展
        self.root.update_idletasks()

    def exit_app(self):
        """離開應用程式"""
        self.root.quit()

    def run(self):
        """運行應用程式"""
        self.root.mainloop()


def main():
    """主函數"""
    app = AlignGUI()
    app.run()


if __name__ == "__main__":
    main()