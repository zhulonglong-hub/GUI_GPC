"""
GPC Dataset Manager - 健康检查Tab

提供数据集健康扫描入口、结果展示与受控修复操作。
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QCheckBox, QListWidget, QListWidgetItem, QTextEdit, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.health_repair import (
    build_missing_image_repair_plan,
    build_orphan_image_repair_plan,
    build_refer_mismatch_repair_plan,
)
from workers.health_repair_worker import HealthRepairWorker
from workers.health_worker import HealthCheckWorker
from ui.widgets.progress_dialog import ProgressDialog


CHECK_TITLES = {
    'missing_images': '图片缺失',
    'orphan_images': '孤儿图片',
    'refer_consistency': 'refer 一致性',
    'empty_fields': '关键字段空值',
    'missing_image': '图片缺失',
    'orphan_image': '孤儿图片',
    'refer_mismatch': 'refer 一致性',
    'empty_field': '关键字段空值',
    'missing_masks': '掩膜文件缺失',
    'missing_mask': '掩膜文件缺失',
}


class HealthTab(QWidget):
    """数据集健康检查 Tab"""

    health_repaired = pyqtSignal(dict)

    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self._worker = None
        self._repair_worker = None
        self._latest_result = None
        self._repair_plans = {}
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

        self.missing_masks_checkbox = QCheckBox("掩膜文件缺失检查（新版数据集）")
        self.missing_masks_checkbox.setChecked(True)
        options_layout.addWidget(self.missing_masks_checkbox)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        action_layout = QHBoxLayout()
        self.run_btn = QPushButton("🔍 开始扫描")
        self.run_btn.clicked.connect(self.run_checks)
        action_layout.addWidget(self.run_btn)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        repair_group = QGroupBox("修复操作（先预览，后执行）")
        repair_layout = QVBoxLayout()

        missing_layout = QHBoxLayout()
        self.preview_missing_btn = QPushButton("预览 missing_image 修复")
        self.preview_missing_btn.clicked.connect(lambda: self.preview_repair('missing_image'))
        missing_layout.addWidget(self.preview_missing_btn)
        self.execute_missing_btn = QPushButton("删除缺失图片对应 JSON task")
        self.execute_missing_btn.clicked.connect(lambda: self.execute_repair('missing_image'))
        missing_layout.addWidget(self.execute_missing_btn)
        repair_layout.addLayout(missing_layout)

        orphan_layout = QHBoxLayout()
        self.preview_orphan_btn = QPushButton("预览 orphan_image 修复")
        self.preview_orphan_btn.clicked.connect(lambda: self.preview_repair('orphan_image'))
        orphan_layout.addWidget(self.preview_orphan_btn)
        self.execute_orphan_btn = QPushButton("移动孤儿图片到回收目录")
        self.execute_orphan_btn.clicked.connect(lambda: self.execute_repair('orphan_image'))
        orphan_layout.addWidget(self.execute_orphan_btn)
        repair_layout.addLayout(orphan_layout)

        mismatch_layout = QHBoxLayout()
        self.preview_mismatch_btn = QPushButton("预览 refer_mismatch 修复")
        self.preview_mismatch_btn.clicked.connect(lambda: self.preview_repair('refer_mismatch'))
        mismatch_layout.addWidget(self.preview_mismatch_btn)
        self.execute_mismatch_btn = QPushButton("修复 refer_mismatch")
        self.execute_mismatch_btn.clicked.connect(lambda: self.execute_repair('refer_mismatch'))
        mismatch_layout.addWidget(self.execute_mismatch_btn)
        repair_layout.addLayout(mismatch_layout)

        repair_group.setLayout(repair_layout)
        main_layout.addWidget(repair_group)
        self.set_repair_buttons_enabled(False)

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

    def set_repair_buttons_enabled(self, enabled: bool):
        for button in (
            self.preview_missing_btn, self.preview_orphan_btn, self.preview_mismatch_btn,
            self.execute_missing_btn, self.execute_orphan_btn, self.execute_mismatch_btn,
        ):
            button.setEnabled(enabled)

    def build_selected_checks(self) -> dict[str, bool]:
        return {
            'missing_images': self.missing_images_checkbox.isChecked(),
            'orphan_images': self.orphan_images_checkbox.isChecked(),
            'refer_consistency': self.refer_consistency_checkbox.isChecked(),
            'empty_fields': self.empty_fields_checkbox.isChecked(),
            'missing_masks': self.missing_masks_checkbox.isChecked(),
        }

    def run_checks(self):
        selected_checks = self.build_selected_checks()
        if not any(selected_checks.values()):
            QMessageBox.warning(self, '警告', '请至少选择一个检查项')
            return

        self.run_btn.setEnabled(False)
        self.set_repair_buttons_enabled(False)
        self.summary_text.clear()
        self.issue_list.clear()
        self.detail_text.clear()
        self._repair_plans.clear()

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
        self.set_repair_buttons_enabled(bool(result.get('issues')))

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
        self.issue_list.clear()

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

    def _issues(self) -> list[dict]:
        if not self._latest_result:
            return []
        return self._latest_result.get('issues', [])

    def build_repair_plan(self, repair_type: str) -> dict:
        issues = self._issues()
        if repair_type == 'missing_image':
            return build_missing_image_repair_plan(issues, self.dataset_index)
        if repair_type == 'orphan_image':
            return build_orphan_image_repair_plan(issues)
        if repair_type == 'refer_mismatch':
            return build_refer_mismatch_repair_plan(issues)
        raise ValueError(f'不支持的修复类型: {repair_type}')

    def preview_repair(self, repair_type: str):
        if not self._latest_result:
            QMessageBox.warning(self, '警告', '请先运行健康检查')
            return

        plan = self.build_repair_plan(repair_type)
        self._repair_plans[repair_type] = plan
        self.detail_text.setText(self.format_repair_plan(plan))

    def format_repair_plan(self, plan: dict) -> str:
        action = plan.get('action', '')
        lines = [plan.get('summary', '')]

        if action == 'missing_image':
            lines.append(f"删除 task 数: {len(plan.get('task_ids', []))}")
            lines.append(f"清理 image_data_split 条目数: {len(plan.get('image_data_remove', []))}")
            for item in plan.get('items', [])[:50]:
                lines.append(f"- {item['task_id']} | [{item['split']}] | image_id={item['image_id']}")
        elif action == 'orphan_image':
            for item in plan.get('items', [])[:50]:
                lines.append(f"- {item['filename']} | image_id={item['image_id']}")
        elif action == 'refer_mismatch':
            lines.append(f"仅 refer，可重建 refer_input: {len(plan.get('refer_only', []))}")
            lines.append(f"仅 refer_input，可删除孤立输入记录: {len(plan.get('input_only', []))}")
            for item in (plan.get('refer_only', []) + plan.get('input_only', []))[:50]:
                lines.append(f"- {item['task_id']} | [{item['split']}] | {item['message']}")

        lines.append('')
        lines.append('注意：以上只是预览，尚未修改任何文件。')
        return '\n'.join(lines)

    def execute_repair(self, repair_type: str):
        plan = self._repair_plans.get(repair_type) or self.build_repair_plan(repair_type)
        self._repair_plans[repair_type] = plan

        if not self.plan_has_work(plan):
            QMessageBox.information(self, '提示', '当前没有可执行的修复项')
            return

        reply = QMessageBox.question(
            self,
            '确认执行健康修复',
            self.build_confirm_message(plan),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.run_btn.setEnabled(False)
        self.set_repair_buttons_enabled(False)
        self.progress_dialog = ProgressDialog('健康检查结果修复', self)
        self.progress_dialog.set_message('正在执行修复...')
        self.progress_dialog.enable_cancel(False)
        self.progress_dialog.show()

        self._repair_worker = HealthRepairWorker(repair_type, plan, self.dataset_index, self)
        self._repair_worker.progress_updated.connect(self.on_repair_progress)
        self._repair_worker.repair_finished.connect(self.on_repair_finished)
        self._repair_worker.error_occurred.connect(self.on_repair_error)
        self._repair_worker.start()

    def plan_has_work(self, plan: dict) -> bool:
        action = plan.get('action')
        if action == 'missing_image':
            return bool(plan.get('task_ids'))
        if action == 'orphan_image':
            return bool(plan.get('items'))
        if action == 'refer_mismatch':
            return bool(plan.get('refer_only') or plan.get('input_only'))
        return False

    def build_confirm_message(self, plan: dict) -> str:
        action = plan.get('action')
        if action == 'missing_image':
            return (
                f"确定要删除 {len(plan.get('task_ids', []))} 条缺失图片对应的 JSON task 记录吗？\n"
                "此操作会修改 refer、refer_input，必要时修改 image_data_split。"
            )
        if action == 'orphan_image':
            return (
                f"确定要移动 {len(plan.get('items', []))} 张孤儿图片到回收目录吗？\n"
                "图片不会直接永久删除，但会从 images 目录移出。"
            )
        if action == 'refer_mismatch':
            return (
                f"确定要修复 refer_mismatch 吗？\n"
                f"将重建 refer_input {len(plan.get('refer_only', []))} 条，"
                f"删除孤立 refer_input {len(plan.get('input_only', []))} 条。"
            )
        return '确定执行修复吗？'

    def on_repair_progress(self, current: int, total: int, message: str):
        self.progress_dialog.set_message(message)
        self.progress_dialog.set_progress(current, total)

    def on_repair_finished(self, result: dict):
        self.run_btn.setEnabled(True)
        self.set_repair_buttons_enabled(True)
        self.progress_dialog.close()
        self.apply_result_to_index(result)
        self.health_repaired.emit(result)
        self._repair_plans.clear()

        failed = result.get('failed', [])
        if failed:
            QMessageBox.warning(self, '修复完成(部分失败)', '\n'.join(failed[:8]))
        else:
            QMessageBox.information(self, '成功', '健康检查结果修复完成，建议重新扫描确认。')

    def apply_result_to_index(self, result: dict):
        repair_type = result.get('repair_type')
        if repair_type == 'missing_image':
            for task_id in result.get('deleted_task_ids', []):
                self.dataset_index.remove_entry(task_id)
        elif repair_type == 'refer_mismatch':
            for task_id in result.get('deleted_task_ids', []):
                self.dataset_index.remove_entry(task_id)
            for task_id, meta in result.get('rebuilt_meta', {}).items():
                if self.dataset_index.get_meta(task_id):
                    self.dataset_index.update_entry(task_id, meta)
                else:
                    self.dataset_index.add_entry(meta)

    def on_repair_error(self, error_msg: str):
        self.run_btn.setEnabled(True)
        self.set_repair_buttons_enabled(bool(self._latest_result and self._latest_result.get('issues')))
        self.progress_dialog.close()
        QMessageBox.critical(self, '错误', error_msg)
