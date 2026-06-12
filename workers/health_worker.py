"""
GPC Dataset Manager - 数据集健康检查工作线程

后台执行健康检查，避免扫描大 JSON 或大量图片时阻塞主线程。
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.health_check import run_health_checks


class HealthCheckWorker(QThread):
    """后台健康检查线程"""

    progress_updated = pyqtSignal(str, int, int)
    check_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, dataset_index, selected_checks: dict | None = None, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.selected_checks = selected_checks or {}
        self._cancelled = False

    def run(self):
        try:
            result = run_health_checks(
                self.dataset_index,
                selected_checks=self.selected_checks,
                progress_cb=self._on_progress,
            )
            if not self._cancelled:
                self.check_finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f"健康检查失败: {str(e)}")

    def _on_progress(self, label: str, current: int, total: int):
        if self._cancelled:
            return
        self.progress_updated.emit(label, current, total)

    def cancel(self):
        self._cancelled = True
