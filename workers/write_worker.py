"""
GPC Dataset Manager - 统一写操作工作线程

P2-5: 封装所有写操作（增/删/改），避免主线程阻塞UI
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.writer import update_fields, delete_record, add_record


class WriteWorker(QThread):
    """
    统一写操作后台线程
    
    封装增/删/改操作，解决 filter_rewrite 在主线程导致的 UI 卡死问题
    """
    
    # 信号定义
    progress_updated = pyqtSignal(str)  # 当前步骤描述
    finished = pyqtSignal(dict)         # 操作结果 {'success': bool, 'message': str, ...}
    error_occurred = pyqtSignal(str)    # 错误信息
    
    def __init__(self, operation: str, params: dict, parent=None):
        """
        Args:
            operation: 'update' | 'delete' | 'add'
            params: 对应操作所需的参数字典
        """
        super().__init__(parent)
        self.operation = operation
        self.params = params
        self._cancelled = False
    
    def run(self):
        """线程主函数"""
        try:
            if self._cancelled:
                return

            # 根据操作类型调用对应的写函数
            if self.operation == 'update':
                self.progress_updated.emit("正在更新字段...")
                result = update_fields(**self.params)

            elif self.operation == 'delete':
                self.progress_updated.emit("正在删除记录...")
                result = delete_record(**self.params)

            elif self.operation == 'add':
                self.progress_updated.emit("正在新增记录...")
                result = add_record(**self.params)

            else:
                self.error_occurred.emit(f"未知操作类型: {self.operation}")
                return

            if self._cancelled:
                return

            # 发送结果
            self.finished.emit(result)

        except Exception as e:
            self.error_occurred.emit(f"操作失败: {str(e)}")
    
    def cancel(self):
        """取消操作"""
        self._cancelled = True


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 测试写操作
    worker = WriteWorker('update', {
        'task_id': 'test_id',
        'split': 'train',
        'field_updates': {'phrase': 'test'},
        'dry_run': True
    })
    
    def on_progress(msg):
        print(f"进度: {msg}")
    
    def on_finished(result):
        print(f"完成: {result}")
        app.quit()
    
    def on_error(msg):
        print(f"错误: {msg}")
        app.quit()
    
    worker.progress_updated.connect(on_progress)
    worker.finished.connect(on_finished)
    worker.error_occurred.connect(on_error)
    
    worker.start()
    
    sys.exit(app.exec())
