"""
GPC Dataset Manager - 健康检查修复工作线程

后台执行健康检查修复，避免 JSON 重写或图片移动阻塞主线程。
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.health_repair import (
    apply_missing_image_repair,
    apply_orphan_image_repair,
    apply_refer_mismatch_repair,
)


class HealthRepairWorker(QThread):
    """后台健康修复线程"""

    progress_updated = pyqtSignal(int, int, str)
    repair_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, repair_type: str, plan: dict, dataset_index=None, parent=None):
        super().__init__(parent)
        self.repair_type = repair_type
        self.plan = plan
        self.dataset_index = dataset_index
        self._cancelled = False

    def run(self):
        try:
            if self.repair_type == 'missing_image':
                result = apply_missing_image_repair(self.plan, progress_cb=self._on_progress)
            elif self.repair_type == 'orphan_image':
                result = apply_orphan_image_repair(
                    self.plan,
                    self.dataset_index,
                    progress_cb=self._on_progress,
                )
            elif self.repair_type == 'refer_mismatch':
                result = apply_refer_mismatch_repair(self.plan, progress_cb=self._on_progress)
            else:
                self.error_occurred.emit(f'不支持的修复类型: {self.repair_type}')
                return

            if not self._cancelled:
                result['repair_type'] = self.repair_type
                self.repair_finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f'健康修复失败: {str(e)}')

    def _on_progress(self, current: int, total: int, message: str):
        if self._cancelled:
            return
        self.progress_updated.emit(current, total, message)

    def cancel(self):
        self._cancelled = True
