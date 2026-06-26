"""
GPC Dataset Manager - 批量操作Tab

统一筛选目标记录，并对当前结果执行批量替换或批量删除。
"""

import sys
from pathlib import Path
from collections import Counter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.batch_ops import (
    NAME_EXACT, NAME_SUBSTR,
    NAME_MATCH_NONE, NAME_MATCH_EXACT, NAME_MATCH_SUBSTR,
    PHRASE_MATCH_NONE, PHRASE_MATCH_SUBSTR,
    filter_batch_targets, build_replace_targets, build_delete_targets,
)
from workers.batch_worker import BatchReplaceWorker
from workers.write_worker import WriteWorker
from ui.widgets.progress_dialog import ProgressDialog


class BatchTab(QWidget):
    """统一筛选 + 操作分流的批量操作 Tab"""

    batch_updated = pyqtSignal(list)
    batch_deleted = pyqtSignal(list)

    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self._filtered_targets = []
        self._replace_targets = []
        self._delete_targets = []
        self._worker = None
        self._delete_worker = None
        self._delete_queue = []
        self._delete_results = {'success': 0, 'failed': []}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("批量操作工作台")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)

        filter_group = QGroupBox("1. 筛选目标记录")
        filter_layout = QVBoxLayout()

        split_layout = QHBoxLayout()
        split_layout.addWidget(QLabel("Split:"))
        self.split_combo = QComboBox()
        self.split_combo.addItems(["全部", "train", "val", "test"])
        split_layout.addWidget(self.split_combo)
        split_layout.addStretch()
        filter_layout.addLayout(split_layout)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("name:"))
        self.name_match_combo = QComboBox()
        self.name_match_combo.addItem("不使用", NAME_MATCH_NONE)
        self.name_match_combo.addItem("精确匹配", NAME_MATCH_EXACT)
        self.name_match_combo.addItem("子串匹配", NAME_MATCH_SUBSTR)
        name_layout.addWidget(self.name_match_combo)
        self.name_filter_input = QLineEdit()
        self.name_filter_input.setPlaceholderText("可选，例如 agriculture")
        name_layout.addWidget(self.name_filter_input)
        filter_layout.addLayout(name_layout)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("data_source:"))
        self.data_source_input = QLineEdit()
        self.data_source_input.setPlaceholderText("可选，例如 LoveDA（精确匹配）")
        source_layout.addWidget(self.data_source_input)
        filter_layout.addLayout(source_layout)

        phrase_layout = QHBoxLayout()
        phrase_layout.addWidget(QLabel("phrase:"))
        self.phrase_match_combo = QComboBox()
        self.phrase_match_combo.addItem("不使用", PHRASE_MATCH_NONE)
        self.phrase_match_combo.addItem("子串匹配", PHRASE_MATCH_SUBSTR)
        phrase_layout.addWidget(self.phrase_match_combo)
        self.phrase_filter_input = QLineEdit()
        self.phrase_filter_input.setPlaceholderText("可选，例如 road")
        phrase_layout.addWidget(self.phrase_filter_input)
        filter_layout.addLayout(phrase_layout)

        filter_action_layout = QHBoxLayout()
        self.preview_filter_btn = QPushButton("预览筛选结果")
        self.preview_filter_btn.clicked.connect(self.preview_filtered_targets)
        filter_action_layout.addWidget(self.preview_filter_btn)
        filter_action_layout.addStretch()
        filter_layout.addLayout(filter_action_layout)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        result_group = QGroupBox("2. 目标预览")
        result_layout = QVBoxLayout()
        self.filter_summary_label = QLabel("尚未预览筛选结果")
        result_layout.addWidget(self.filter_summary_label)
        self.result_label = QLabel("")
        result_layout.addWidget(self.result_label)
        self.result_list = QListWidget()
        result_layout.addWidget(self.result_list)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

        replace_group = QGroupBox("3A. 对当前结果执行批量修改")
        replace_layout = QVBoxLayout()

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("替换类型:"))
        self.replace_type_combo = QComboBox()
        self.replace_type_combo.addItem("name 精确替换", NAME_EXACT)
        self.replace_type_combo.addItem("name 子串替换", NAME_SUBSTR)
        type_layout.addWidget(self.replace_type_combo)
        replace_layout.addLayout(type_layout)

        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("查找值:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("例如 agriculture")
        value_layout.addWidget(self.find_input)
        value_layout.addWidget(QLabel("替换为:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("例如 farmland")
        value_layout.addWidget(self.replace_input)
        replace_layout.addLayout(value_layout)

        replace_action_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览修改效果")
        self.preview_btn.clicked.connect(self.preview_targets)
        self.preview_btn.setEnabled(False)
        replace_action_layout.addWidget(self.preview_btn)
        self.execute_btn = QPushButton("✅ 执行批量替换")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self.execute_replace)
        replace_action_layout.addWidget(self.execute_btn)
        replace_action_layout.addStretch()
        replace_layout.addLayout(replace_action_layout)

        replace_group.setLayout(replace_layout)
        main_layout.addWidget(replace_group)

        delete_group = QGroupBox("3B. 对当前结果执行批量删除")
        delete_layout = QVBoxLayout()
        self.delete_result_label = QLabel("删除范围将直接复用当前筛选结果")
        delete_layout.addWidget(self.delete_result_label)

        delete_action_layout = QHBoxLayout()
        self.preview_delete_btn = QPushButton("预览删除范围")
        self.preview_delete_btn.clicked.connect(self.preview_delete_targets)
        self.preview_delete_btn.setEnabled(False)
        delete_action_layout.addWidget(self.preview_delete_btn)
        self.execute_delete_btn = QPushButton("🗑️ 执行批量删除")
        self.execute_delete_btn.setEnabled(False)
        self.execute_delete_btn.clicked.connect(self.execute_batch_delete)
        delete_action_layout.addWidget(self.execute_delete_btn)
        delete_action_layout.addStretch()
        delete_layout.addLayout(delete_action_layout)

        delete_group.setLayout(delete_layout)
        main_layout.addWidget(delete_group)

    def _collect_filter_values(self) -> dict:
        split_filter = self.split_combo.currentText()
        return {
            'split': None if split_filter == '全部' else split_filter,
            'name_match_mode': self.name_match_combo.currentData(),
            'name_value': self.name_filter_input.text().strip(),
            'data_source': self.data_source_input.text().strip(),
            'phrase_match_mode': self.phrase_match_combo.currentData(),
            'phrase_value': self.phrase_filter_input.text().strip(),
        }

    def preview_filtered_targets(self):
        try:
            self._filtered_targets = filter_batch_targets(
                self.dataset_index,
                self._collect_filter_values(),
            )
        except Exception as e:
            QMessageBox.critical(self, '错误', str(e))
            return

        self._replace_targets = []
        self._delete_targets = []
        self.render_filtered_targets()

    def render_filtered_targets(self):
        self.result_list.clear()
        count = len(self._filtered_targets)
        self.preview_btn.setEnabled(bool(count))
        self.preview_delete_btn.setEnabled(bool(count))
        self.execute_btn.setEnabled(False)
        self.execute_delete_btn.setEnabled(False)

        if not count:
            self.filter_summary_label.setText('未命中任何目标记录')
            self.result_label.setText('请调整筛选条件后重新预览')
            self.delete_result_label.setText('当前没有可删除的筛选结果')
            return

        splits = sorted({item['split'] for item in self._filtered_targets if item.get('split')})
        sources = sorted({item['data_source'] for item in self._filtered_targets if item.get('data_source')})
        image_count = len({item['image_id'] for item in self._filtered_targets})
        top_names = Counter(item['name'] for item in self._filtered_targets if item.get('name')).most_common(3)
        top_name_text = '，'.join(f'{name}({qty})' for name, qty in top_names) if top_names else '无'
        source_text = '，'.join(sources[:5]) if sources else '（未标注）'
        split_text = '，'.join(splits) if splits else '无'

        self.filter_summary_label.setText(
            f'命中 {count} 条 task，涉及 {image_count} 个 image_id；split: {split_text}；data_source: {source_text}'
        )
        self.result_label.setText(f'Top name 分布：{top_name_text}')
        self.delete_result_label.setText(f'当前筛选结果可直接删除，共 {count} 条记录')

        for target in self._filtered_targets[:1000]:
            display = (
                f"{target['task_id']} | [{target['split']}] | {target['name']} | "
                f"{target['data_source'] or '（未标注）'} | {target['phrase']} | image_id={target['image_id']}"
            )
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, target)
            self.result_list.addItem(item)

        if count > 1000:
            self.result_list.addItem(QListWidgetItem(f'... 仅显示前 1000 条，共 {count} 条'))

    def preview_targets(self):
        if not self._filtered_targets:
            QMessageBox.warning(self, '警告', '请先完成目标筛选预览')
            return

        find_value = self.find_input.text().strip()
        replace_value = self.replace_input.text().strip()
        if not find_value or not replace_value:
            QMessageBox.warning(self, '警告', '请输入查找值和替换值')
            return

        replace_type = self.replace_type_combo.currentData()

        try:
            self._replace_targets = build_replace_targets(
                self._filtered_targets,
                replace_type,
                find_value,
                replace_value,
            )
        except Exception as e:
            QMessageBox.critical(self, '错误', str(e))
            return

        self.render_replace_targets()

    def render_replace_targets(self):
        self.result_list.clear()
        self.execute_btn.setEnabled(bool(self._replace_targets))
        self.preview_delete_btn.setEnabled(bool(self._filtered_targets))
        self.execute_delete_btn.setEnabled(False)
        self.result_label.setText(f'找到 {len(self._replace_targets)} 条将被修改的记录')

        for target in self._replace_targets[:1000]:
            display = (
                f"{target['task_id']} | [{target['split']}] | "
                f"{target['old']} -> {target['new']} | image_id={target['image_id']}"
            )
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, target)
            self.result_list.addItem(item)

        if len(self._replace_targets) > 1000:
            self.result_list.addItem(QListWidgetItem(f"... 仅显示前 1000 条，共 {len(self._replace_targets)} 条"))

    def execute_replace(self):
        if not self._replace_targets:
            QMessageBox.warning(self, '警告', '请先预览并确认存在可替换记录')
            return

        reply = QMessageBox.question(
            self,
            '确认批量替换',
            f"确定要批量替换 {len(self._replace_targets)} 条记录吗？\n此操作会修改 refer 和 refer_input 文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.preview_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)

        self.progress_dialog = ProgressDialog('批量字段替换', self)
        self.progress_dialog.set_message('正在执行批量替换...')
        self.progress_dialog.enable_cancel(False)
        self.progress_dialog.show()

        self._worker = BatchReplaceWorker(self._replace_targets, self)
        self._worker.progress_updated.connect(self.on_replace_progress)
        self._worker.finished.connect(self.on_replace_finished)
        self._worker.error_occurred.connect(self.on_replace_error)
        self._worker.start()

    def on_replace_progress(self, current: int, total: int, task_id: str):
        self.progress_dialog.set_message(f'正在更新: {task_id}')
        self.progress_dialog.set_progress(current, total)

    def on_replace_finished(self, result: dict):
        self.preview_btn.setEnabled(True)
        self.progress_dialog.close()

        updated_meta = result.get('updated_meta', {})
        failed = result.get('failed', [])
        for task_id, meta in updated_meta.items():
            self.dataset_index.update_entry(task_id, meta)
        if updated_meta:
            self.batch_updated.emit(list(updated_meta.keys()))

        if failed:
            QMessageBox.warning(
                self,
                '批量替换完成(部分失败)',
                f"成功 {result.get('success_count', 0)} 条，失败 {len(failed)} 条\n" + '\n'.join(failed[:5])
            )
        else:
            QMessageBox.information(self, '成功', f"成功替换 {result.get('success_count', 0)} 条记录")

        self.preview_filtered_targets()

    def on_replace_error(self, error_msg: str):
        self.preview_btn.setEnabled(True)
        self.execute_btn.setEnabled(bool(self._replace_targets))
        self.progress_dialog.close()
        QMessageBox.critical(self, '错误', error_msg)

    def preview_delete_targets(self):
        if not self._filtered_targets:
            QMessageBox.warning(self, '警告', '请先完成目标筛选预览')
            return

        self._delete_targets = build_delete_targets(self._filtered_targets)
        self.result_list.clear()
        self.execute_delete_btn.setEnabled(bool(self._delete_targets))
        self.execute_btn.setEnabled(False)
        self.delete_result_label.setText(f'找到 {len(self._delete_targets)} 条将被删除的记录')
        self.result_label.setText('当前列表展示的是将被删除的目标记录')

        for target in self._delete_targets[:1000]:
            display = (
                f"{target['task_id']} | [{target['split']}] | {target['name']} | "
                f"{target['data_source'] or '（未标注）'} | image_id={target['image_id']}"
            )
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, target)
            self.result_list.addItem(item)

        if len(self._delete_targets) > 1000:
            self.result_list.addItem(QListWidgetItem(
                f"... 仅显示前 1000 条，共 {len(self._delete_targets)} 条"
            ))

    def execute_batch_delete(self):
        if not self._delete_targets:
            QMessageBox.warning(self, '警告', '请先预览并确认存在可删除记录')
            return

        reply = QMessageBox.question(
            self,
            '确认批量删除',
            f"确定要批量删除 {len(self._delete_targets)} 条记录吗？\n此操作会修改 refer 和 refer_input 文件，并将记录备份到回收站。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.preview_delete_btn.setEnabled(False)
        self.execute_delete_btn.setEnabled(False)

        self.progress_dialog = ProgressDialog('批量删除', self)
        self.progress_dialog.set_message('正在执行批量删除...')
        self.progress_dialog.enable_cancel(False)
        self.progress_dialog.show()

        self._delete_queue = [
            {
                'task_id': target['task_id'],
                'split': target['split'],
                'delete_image_file': False,
            }
            for target in self._delete_targets
        ]
        self._delete_results = {'success': 0, 'failed': []}
        self._process_next_delete()

    def _process_next_delete(self):
        if not self._delete_queue:
            self._show_batch_delete_results()
            return

        params = self._delete_queue.pop(0)
        self._delete_worker = WriteWorker('delete', params)
        self._delete_worker.progress_updated.connect(
            lambda msg, tid=params['task_id']: self.on_delete_progress(tid, msg)
        )
        self._delete_worker.finished.connect(
            lambda result, tid=params['task_id']: self.on_delete_finished(tid, result)
        )
        self._delete_worker.error_occurred.connect(
            lambda err, tid=params['task_id']: self.on_delete_error(tid, err)
        )
        self._delete_worker.start()

    def on_delete_progress(self, task_id: str, message: str):
        done = self._delete_results['success'] + len(self._delete_results['failed'])
        total = done + len(self._delete_queue) + 1
        self.progress_dialog.set_message(f'{message} {task_id}')
        self.progress_dialog.set_progress(done + 1, total)

    def on_delete_finished(self, task_id: str, result: dict):
        if result.get('success'):
            self.dataset_index.remove_entry(task_id)
            self._delete_results['success'] += 1
        else:
            self._delete_results['failed'].append(f"{task_id}: {result.get('message', '删除失败')}")
        self._process_next_delete()

    def on_delete_error(self, task_id: str, error_msg: str):
        self._delete_results['failed'].append(f'{task_id}: {error_msg}')
        self._process_next_delete()

    def _show_batch_delete_results(self):
        self.preview_delete_btn.setEnabled(True)
        self.progress_dialog.close()

        deleted_ids = [target['task_id'] for target in self._delete_targets]
        if deleted_ids:
            self.batch_deleted.emit(deleted_ids)

        failed_items = self._delete_results['failed']
        if failed_items:
            QMessageBox.warning(
                self,
                '批量删除完成(部分失败)',
                f"成功删除 {self._delete_results['success']} 条，失败 {len(failed_items)} 条\n" + '\n'.join(failed_items[:5])
            )
        else:
            QMessageBox.information(self, '成功', f"成功删除 {self._delete_results['success']} 条记录")

        self.preview_filtered_targets()

