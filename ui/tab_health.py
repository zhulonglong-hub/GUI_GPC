"""
GPC Dataset Manager - 健康检查Tab

提供数据集健康扫描入口与结果展示。
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QCheckBox, QListWidget, QListWidgetItem, QTextEdit, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).parent.parent))
from workers.health_worker import HealthCheckWorker
from ui.widgets.progress_dialog import ProgressDialog


CHECK_TITLES = {
    'missing_images': '图片缺失',
    'orphan_images': '孤儿图片',
    'refer_consistency': 'refer 一致性',
    'empty_fields': '关键字段空值',
}


class HealthTab(QWidget):
    """数据集健康检查 Tab"""

    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self._worker = None
        self._latest_result = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("数据集健康检查")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)

        options_group = QGroupBox("检查项")
        options_layout = QVBoxLayout()
        self.missing_images_checkbox = QCheckBox("图片缺失检查")
        self.missing_images_checkbox.setChecked(True)
        options_layout.addWidget(self.missing_images_checkbox)

        self.orphan_images_checkbox = QCheckBox("孤儿图片检查")
        self.orphan_images_checkbox.setChecked(True)
        options_layout.addWidget(self.orphan_images_checkbox)

        self.refer_consistency_checkbox = QCheckBox("refer / refer_input 一致性检查")
        self.refer_consistency_checkbox.setChecked(True)
        options_layout.addWidget(self.refer_consistency_checkbox)

        self.empty_fields_checkbox = QCheckBox("关键字段空值检查")
        self.empty_fields_checkbox.setChecked(True)
        options_layout.addWidget(self.empty_fields_checkbox)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        action_layout = QHBoxLayout()
        self.run_btn = QPushButton("🔍 开始扫描")
        self.run_btn.clicked.connect(self.run_checks)
        action_layout.addWidget(self.run_btn)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("扫描完成后，这里会显示结果摘要")
        left_layout.addWidget(self.summary_text)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.issue_list = QListWidget()
        self.issue_list.itemClicked.connect(self.on_issue_selected)
        right_layout.addWidget(self.issue_list)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("点击某条问题后，这里显示详细信息")
        right_layout.addWidget(self.detail_text)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)

    def build_selected_checks(self) -> dict[str, bool]:
        return {
            'missing_images': self.missing_images_checkbox.isChecked(),
            'orphan_images': self.orphan_images_checkbox.isChecked(),
            'refer_consistency': self.refer_consistency_checkbox.isChecked(),
            'empty_fields': self.empty_fields_checkbox.isChecked(),
        }

    def run_checks(self):
        selected_checks = self.build_selected_checks()
        if not any(selected_checks.values()):
            QMessageBox.warning(self, '警告', '请至少选择一个检查项')
            return

        self.run_btn.setEnabled(False)
        self.summary_text.clear()
        self.issue_list.clear()
        self.detail_text.clear()

        self.progress_dialog = ProgressDialog('数据集健康检查', self)
        self.progress_dialog.set_message('正在扫描数据集问题...')
        self.progress_dialog.enable_cancel(False)
        self.progress_dialog.show()

        self._worker = HealthCheckWorker(self.dataset_index, selected_checks, self)
        self._worker.progress_updated.connect(self.on_progress_updated)
        self._worker.check_finished.connect(self.on_checks_finished)
        self._worker.error_occurred.connect(self.on_checks_error)
        self._worker.start()

    def on_progress_updated(self, label: str, current: int, total: int):
        self.progress_dialog.set_message(label)
        self.progress_dialog.set_progress(current, total)

    def on_checks_finished(self, result: dict):
        self.run_btn.setEnabled(True)
        self.progress_dialog.close()
        self._latest_result = result
        self.render_result(result)

    def on_checks_error(self, error_msg: str):
        self.run_btn.setEnabled(True)
        self.progress_dialog.close()
        QMessageBox.critical(self, '错误', error_msg)

    def render_result(self, result: dict):
        issues = result.get('issues', [])
        summary = result.get('summary', {})
        lines = []

        if not issues:
            lines.append('✅ 未发现健康问题')
        else:
            lines.append(f'共发现 {len(issues)} 条问题')
            for issue_type, count in summary.items():
                title = CHECK_TITLES.get(issue_type, issue_type)
                lines.append(f'- {title}: {count} 条')

        self.summary_text.setText('\n'.join(lines))

        for issue in issues:
            task_id = issue.get('task_id') or '(无 task_id)'
            image_id = issue.get('image_id') or '-'
            message = issue.get('message', '')
            title = CHECK_TITLES.get(issue.get('issue_type', ''), issue.get('issue_type', '问题'))
            item = QListWidgetItem(f'{title} | {task_id} | {image_id}')
            item.setData(Qt.ItemDataRole.UserRole, issue)
            item.setToolTip(message)
            self.issue_list.addItem(item)

        if issues:
            self.issue_list.setCurrentRow(0)
            self.on_issue_selected(self.issue_list.item(0))

    def on_issue_selected(self, item):
        issue = item.data(Qt.ItemDataRole.UserRole)
        if not issue:
            return

        title = CHECK_TITLES.get(issue.get('issue_type', ''), issue.get('issue_type', '问题'))
        detail = (
            f"类型: {title}\n"
            f"task_id: {issue.get('task_id', '')}\n"
            f"split: {issue.get('split', '')}\n"
            f"image_id: {issue.get('image_id', '')}\n"
            f"说明: {issue.get('message', '')}"
        )
        self.detail_text.setText(detail)
