"""
GPC Dataset Manager - 记录加载工作线程

P2-4: 异步加载完整记录（含Polygons），避免主线程阻塞
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.json_io import stream_records
from config import get_refer_json


class RecordLoader(QThread):
    """后台加载完整记录线程"""
    
    # 信号定义
    record_loaded = pyqtSignal(dict)  # 加载成功，返回完整记录
    error_occurred = pyqtSignal(str)  # 加载失败，返回错误消息
    
    def __init__(self, task_id: str, split: str, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.split = split
        self._cancelled = False
    
    def run(self):
        """线程主函数"""
        try:
            # P2-4: 流式查找目标记录
            for record in stream_records(get_refer_json(self.split)):
                if self._cancelled:
                    return
                
                if record.get('task_id') == self.task_id:
                    self.record_loaded.emit(record)
                    return
            
            # 未找到记录
            self.error_occurred.emit(f"未找到记录: {self.task_id}")
            
        except Exception as e:
            self.error_occurred.emit(f"加载失败: {str(e)}")
    
    def cancel(self):
        """取消加载"""
        self._cancelled = True


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 测试加载
    loader = RecordLoader("test_task_id", "train")
    
    def on_loaded(record):
        print(f"记录加载成功: {record.get('task_id')}")
        app.quit()
    
    def on_error(msg):
        print(f"加载失败: {msg}")
        app.quit()
    
    loader.record_loaded.connect(on_loaded)
    loader.error_occurred.connect(on_error)
    
    loader.start()
    
    sys.exit(app.exec())
