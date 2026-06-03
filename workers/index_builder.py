"""
GPC Dataset Manager - 索引构建工作线程

后台构建数据集索引,避免阻塞UI
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.dataset_index import DatasetIndex
from config import ANNOTATIONS_DIR, CACHE_DIR


class IndexBuilder(QThread):
    """后台索引构建线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(int, int)  # 已处理, 总计
    index_ready = pyqtSignal(object)  # DatasetIndex对象
    error_occurred = pyqtSignal(str)  # 错误消息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False
        self.cache_path = CACHE_DIR / "dataset_index.pkl"
    
    def run(self):
        """线程主函数"""
        try:
            index = DatasetIndex()
            
            # 尝试从缓存加载
            if index.load_cache(self.cache_path):
                self.progress_updated.emit(100, 100)
                self.index_ready.emit(index)
                return
            
            # 全量构建
            self.progress_updated.emit(0, 100)
            
            if self._cancelled:
                return
            
            index.build(ANNOTATIONS_DIR)
            
            if self._cancelled:
                return
            
            self.progress_updated.emit(100, 100)
            
            # 保存缓存
            index.save_cache(self.cache_path)
            
            # 发送就绪信号
            self.index_ready.emit(index)
            
        except Exception as e:
            self.error_occurred.emit(f"索引构建失败: {str(e)}")
    
    def cancel(self):
        """取消构建"""
        self._cancelled = True


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    builder = IndexBuilder()
    
    def on_progress(current, total):
        print(f"进度: {current}/{total}")
    
    def on_ready(index):
        print(f"索引就绪! 统计: {index.stats}")
        app.quit()
    
    def on_error(msg):
        print(f"错误: {msg}")
        app.quit()
    
    builder.progress_updated.connect(on_progress)
    builder.index_ready.connect(on_ready)
    builder.error_occurred.connect(on_error)
    
    builder.start()
    
    sys.exit(app.exec())
