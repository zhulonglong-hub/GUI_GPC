"""
GPC Dataset Manager - 批量替换工作线程

后台执行批量 name 替换，避免大 JSON 重写阻塞 UI。
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.batch_ops import apply_batch_replace


class BatchReplaceWorker(QThread):
    """批量替换后台线程"""

    progress_updated = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, targets: list[dict], parent=None):
        super().__init__(parent)
        self.targets = targets
        self._cancelled = False

    def run(self):
        try:
            result = apply_batch_replace(self.targets, progress_cb=self._on_progress)
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f"批量替换失败: {str(e)}")

    def _on_progress(self, current: int, total: int, task_id: str):
        if not self._cancelled:
            self.progress_updated.emit(current, total, task_id)

    def cancel(self):
        self._cancelled = True
