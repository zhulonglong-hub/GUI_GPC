"""
GPC Dataset Manager - 图像加载工作线程

异步加载图像,避免UI阻塞
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.image_utils import load_image_by_id
from config import MAX_RENDER_SIZE


class ImageLoader(QThread):
    """异步图像加载线程"""
    
    # 信号定义
    image_loaded = pyqtSignal(np.ndarray)  # 图像数组
    error_occurred = pyqtSignal(str)  # 错误消息
    
    def __init__(self, image_id: str, parent=None):
        super().__init__(parent)
        self.image_id = image_id
    
    def run(self):
        """线程主函数"""
        try:
            # 加载图像 (带缩略图处理)
            image_np = load_image_by_id(
                self.image_id,
                max_size=MAX_RENDER_SIZE,
                as_array=True
            )
            
            if image_np is not None:
                self.image_loaded.emit(image_np)
            else:
                self.error_occurred.emit(f"无法加载图像: {self.image_id}")
                
        except Exception as e:
            self.error_occurred.emit(f"加载图像失败: {str(e)}")


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    test_image_id = "test_image"
    loader = ImageLoader(test_image_id)
    
    def on_loaded(image_np):
        print(f"图像加载成功! Shape: {image_np.shape}")
        app.quit()
    
    def on_error(msg):
        print(f"错误: {msg}")
        app.quit()
    
    loader.image_loaded.connect(on_loaded)
    loader.error_occurred.connect(on_error)
    
    loader.start()
    
    sys.exit(app.exec())
