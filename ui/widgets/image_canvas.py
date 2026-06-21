"""
GPC Dataset Manager - 图像渲染画布组件

基于 matplotlib 的图像+多边形叠加渲染
复用 DataPreview_ProMax.py 的渲染逻辑
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon as MplPolygon
from matplotlib import cm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import POLYGON_ALPHA, POLYGON_LINEWIDTH
from core.image_utils import load_mask_as_rgba


class ImageCanvas(FigureCanvasQTAgg):
    """图像渲染画布,支持多边形叠加"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.setParent(parent)
        
        # 色板 (tab20)
        self.colormap = cm.get_cmap('tab20')
        
        self.clear()
    
    def clear(self) -> None:
        """清空画布,显示占位提示"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, '请选择一个样本预览', 
                    ha='center', va='center', fontsize=14,
                    transform=self.ax.transAxes,
                    color='gray')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.draw()
    
    def render(self, image_np: np.ndarray, masks_records: list) -> None:
        """
        渲染图像和多边形掩膜
        
        Args:
            image_np: RGB图像数组 (H, W, 3)
            masks_records: 掩膜记录列表,每项包含:
                {
                    'phrase': str,
                    'Polygons': [[[[x,y], ...]]]
                }
        """
        self.ax.clear()
        
        # 显示图像
        self.ax.imshow(image_np)
        
        # 渲染多边形
        for i, record in enumerate(masks_records):
            color = self._get_color(i)
            phrase = record.get('phrase', f'mask_{i}')
            polygons = record.get('Polygons', [])
            
            # 渲染所有多边形
            for poly_group in polygons:
                for poly in poly_group:
                    if len(poly) < 3:
                        continue
                    
                    # 提取坐标
                    coords = np.array(poly)
                    
                    # 创建多边形patch
                    polygon_patch = MplPolygon(
                        coords,
                        closed=True,
                        facecolor=color,
                        edgecolor=color,
                        alpha=POLYGON_ALPHA,
                        linewidth=POLYGON_LINEWIDTH
                    )
                    self.ax.add_patch(polygon_patch)
            
            # 添加标签 (简化版,不做防遮挡)
            if polygons and polygons[0] and polygons[0][0]:
                first_point = polygons[0][0][0]
                x, y = first_point[0], first_point[1]
                
                self.ax.text(
                    x, y - 5,
                    phrase,
                    color='white',
                    fontsize=9,
                    bbox=dict(facecolor=color, alpha=0.7, edgecolor='none', pad=2),
                    verticalalignment='bottom'
                )
        
        self.ax.set_xlim(0, image_np.shape[1])
        self.ax.set_ylim(image_np.shape[0], 0)
        self.ax.set_aspect('equal')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        self.fig.tight_layout()
        self.draw()
    
    def _get_color(self, index: int) -> tuple:
        """获取颜色 (tab20色板)"""
        color_idx = index % 20
        rgba = self.colormap(color_idx)
        return rgba[:3]

    def render_with_mask_png(self, image_np: np.ndarray, mask_path: str, phrase: str = '') -> None:
        """
        渲染图像并叠加 PNG 掩膜（新版数据集适配）。

        Args:
            image_np: RGB 图像数组 (H, W, 3)
            mask_path: 相对数据集根目录的掩膜路径（来自 record['mask_path']）
            phrase: 用于图例标签的短语文本
        """
        self.ax.clear()
        self.ax.imshow(image_np)

        rgba = load_mask_as_rgba(mask_path)
        if rgba is not None:
            # 将掩膜缩放到与图像相同尺寸（若尺寸不一致）
            img_h, img_w = image_np.shape[:2]
            mask_h, mask_w = rgba.shape[:2]
            if (mask_h, mask_w) != (img_h, img_w):
                from PIL import Image as PilImage
                pil_rgba = PilImage.fromarray(rgba, 'RGBA')
                pil_rgba = pil_rgba.resize((img_w, img_h), PilImage.NEAREST)
                rgba = np.array(pil_rgba)

            self.ax.imshow(rgba)

            # 添加图例标签
            if phrase:
                self.ax.text(
                    5, 15, phrase,
                    color='white', fontsize=9,
                    bbox=dict(facecolor='#FF5000', alpha=0.7, edgecolor='none', pad=2),
                    verticalalignment='top'
                )
        else:
            # 掩膜文件不存在，仅显示原图并标注
            self.ax.text(
                0.5, 0.02, '⚠ 掩膜文件不存在',
                ha='center', va='bottom', fontsize=9,
                transform=self.ax.transAxes,
                color='orange',
                bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=2)
            )

        self.ax.set_xlim(0, image_np.shape[1])
        self.ax.set_ylim(image_np.shape[0], 0)
        self.ax.set_aspect('equal')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.fig.tight_layout()
        self.draw()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow
    import sys
    
    app = QApplication(sys.argv)
    
    # 测试窗口
    window = QMainWindow()
    canvas = ImageCanvas(window, width=8, height=6)
    window.setCentralWidget(canvas)
    window.setWindowTitle("ImageCanvas 测试")
    window.resize(800, 600)
    
    # 创建测试图像
    test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
    
    # 创建测试多边形
    test_masks = [
        {
            'phrase': 'Test Object 1',
            'Polygons': [[[[50, 50], [150, 50], [150, 150], [50, 150]]]]
        },
        {
            'phrase': 'Test Object 2',
            'Polygons': [[[[200, 200], [350, 200], [350, 300], [200, 300]]]]
        }
    ]
    
    canvas.render(test_image, test_masks)
    
    window.show()
    sys.exit(app.exec())
