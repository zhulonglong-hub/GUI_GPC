"""
GPC Dataset Manager - 批量操作Tab

提供 name 字段批量替换的 dry-run 预览与确认执行。
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.batch_ops import NAME_EXACT, NAME_SUBSTR, find_batch_targets
from workers.batch_worker import BatchReplaceWorker
from ui.widgets.progress_dialog import ProgressDialog


class BatchTab(QWidget):
    """批量字段替换 Tab"""

    # 批量替换成功后通知主窗口刷新，参数为受影响的 task_id 列表
    batch_updated = pyqtSignal(list)

    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self._targets = []
        self._worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("批量字段替换")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)

        form_group = QGroupBox("1. 设置替换规则")
        form_layout = QVBoxLayout()

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("替换类型:"))
        self.replace_type_combo = QComboBox()
        self.replace_type_combo.addItem("name 精确替换", NAME_EXACT)
        self.replace_type_combo.addItem("name 子串替换", NAME_SUBSTR)
        type_layout.addWidget(self.replace_type_combo)
        form_layout.addLayout(type_layout)

        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("查找值:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("例如 agriculture")
        value_layout.addWidget(self.find_input)
        value_layout.addWidget(QLabel("替换为:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("例如 farmland")
        value_layout.addWidget(self.replace_input)
        form_layout.addLayout(value_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Split:"))
        self.split_combo = QComboBox()
        self.split_combo.addItems(["全部", "train", "val", "test"])
        filter_layout.addWidget(self.split_combo)
        filter_layout.addWidget(QLabel("仅限 name 等于:"))
        self.name_filter_input = QLineEdit()
        self.name_filter_input.setPlaceholderText("可选")
        filter_layout.addWidget(self.name_filter_input)
        form_layout.addLayout(filter_layout)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        action_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览 dry-run")
        self.preview_btn.clicked.connect(self.preview_targets)
        action_layout.addWidget(self.preview_btn)

        self.execute_btn = QPushButton("✅ 执行批量替换")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self.execute_replace)
        action_layout.addWidget(self.execute_btn)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        result_group = QGroupBox("2. 预览结果")
        result_layout = QVBoxLayout()
        self.result_label = QLabel("尚未预览")
        result_layout.addWidget(self.result_label)
        self.result_list = QListWidget()
        result_layout.addWidget(self.result_list)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

    def preview_targets(self):
        find_value = self.find_input.text().strip()
        replace_value = self.replace_input.text().strip()
        if not find_value or not replace_value:
            QMessageBox.warning(self, "警告", "请输入查找值和替换值")
            return

        split_filter = self.split_combo.currentText()
        split_filter = None if split_filter == "全部" else split_filter
        name_filter = self.name_filter_input.text().strip() or None
        replace_type = self.replace_type_combo.currentData()

        try:
            self._targets = find_batch_targets(
                self.dataset_index,
                replace_type,
                find_value,
                replace_value,
                split_filter=split_filter,
                name_filter=name_filter,
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        self.render_targets()

    def render_targets(self):
        self.result_list.clear()
        self.execute_btn.setEnabled(bool(self._targets))
        self.result_label.setText(f"找到 {len(self._targets)} 条将被修改的记录")

        for target in self._targets[:1000]:
            display = (
                f"{target['task_id']} | [{target['split']}] | "
                f"{target['old']} -> {target['new']} | image_id={target['image_id']}"
            )
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, target)
            self.result_list.addItem(item)

        if len(self._targets) > 1000:
            self.result_list.addItem(QListWidgetItem(f"... 仅显示前 1000 条，共 {len(self._targets)} 条"))

    def execute_replace(self):
        if not self._targets:
            QMessageBox.warning(self, "警告", "请先预览并确认存在可替换记录")
            return

        reply = QMessageBox.question(
            self,
            "确认批量替换",
            f"确定要批量替换 {len(self._targets)} 条记录吗？\n此操作会修改 refer 和 refer_input 文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.preview_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)

        self.progress_dialog = ProgressDialog("批量字段替换", self)
        self.progress_dialog.set_message("正在执行批量替换...")
        self.progress_dialog.enable_cancel(False)
        self.progress_dialog.show()

        self._worker = BatchReplaceWorker(self._targets, self)
        self._worker.progress_updated.connect(self.on_replace_progress)
        self._worker.finished.connect(self.on_replace_finished)
        self._worker.error_occurred.connect(self.on_replace_error)
        self._worker.start()

    def on_replace_progress(self, current: int, total: int, task_id: str):
        self.progress_dialog.set_message(f"正在更新: {task_id}")
        self.progress_dialog.set_progress(current, total)

    def on_replace_finished(self, result: dict):
        self.preview_btn.setEnabled(True)
        self.progress_dialog.close()

        updated_meta = result.get('updated_meta', {})
        failed = result.get('failed', [])
        if not failed:
            for task_id, meta in updated_meta.items():
                self.dataset_index.update_entry(task_id, meta)
            # 通知主窗口刷新浏览列表中受影响的行
            if updated_meta:
                self.batch_updated.emit(list(updated_meta.keys()))

        if failed:
            QMessageBox.warning(
                self,
                "批量替换完成(部分失败)",
                f"成功 {result.get('success_count', 0)} 条，失败 {len(failed)} 条\n" + '\n'.join(failed[:5])
            )
        else:
            QMessageBox.information(self, "成功", f"成功替换 {result.get('success_count', 0)} 条记录")

        self.preview_targets()

    def on_replace_error(self, error_msg: str):
        self.preview_btn.setEnabled(True)
        self.execute_btn.setEnabled(bool(self._targets))
        self.progress_dialog.close()
        QMessageBox.critical(self, "错误", error_msg)
