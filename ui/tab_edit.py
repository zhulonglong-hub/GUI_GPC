"""
GPC Dataset Manager - 编辑样本Tab

编辑数据集中样本的字段
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QMessageBox, QLabel, QGroupBox,
                             QFormLayout, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from workers.write_worker import WriteWorker  # P2-6: 新增异步写操作


class EditTab(QWidget):
    """编辑样本Tab"""

    record_updated = pyqtSignal(str)

    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.current_task_id = None
        self.current_split = None
        self._write_worker = None       # P2-6: 写操作线程
        self._pending_updates = None    # P2-6: 暂存待写入字段
        self._baseline_values = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("编辑样本字段")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # 搜索区域
        search_group = QGroupBox("1. 查找要编辑的样本")
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入 task_id...")
        self.search_input.returnPressed.connect(self.load_record)
        search_layout.addWidget(self.search_input)
        
        load_btn = QPushButton("📥 加载")
        load_btn.clicked.connect(self.load_record)
        search_layout.addWidget(load_btn)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # 当前记录信息
        self.current_info_label = QLabel("尚未加载记录")
        self.current_info_label.setStyleSheet("color: gray; padding: 10px;")
        main_layout.addWidget(self.current_info_label)
        
        # 编辑表单
        edit_group = QGroupBox("2. 编辑字段")
        form_layout = QFormLayout()
        
        self.phrase_input = QLineEdit()
        form_layout.addRow("短语 (phrase):", self.phrase_input)
        
        self.name_input = QLineEdit()
        form_layout.addRow("类别名 (name):", self.name_input)
        
        self.attributes_input = QLineEdit()
        self.attributes_input.setPlaceholderText("多个属性用逗号分隔")
        form_layout.addRow("属性 (attributes):", self.attributes_input)
        
        edit_group.setLayout(form_layout)
        main_layout.addWidget(edit_group)
        
        # 说明
        hint_label = QLabel("提示: 加载后会显示当前值，只会保存实际发生变化的字段")
        hint_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        main_layout.addWidget(hint_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(clear_btn)

        # P2-6: 保存为实例属性，以便 on_write_finished 恢复状态
        self.update_btn = QPushButton("✅ 保存修改")
        self.update_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        self.update_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(self.update_btn)
        
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
    
    def load_record(self):
        """加载记录"""
        task_id = self.search_input.text().strip()
        if not task_id:
            QMessageBox.warning(self, "警告", "请输入 task_id")
            return
        
        # 搜索记录
        meta = self.dataset_index.get_meta(task_id)
        if not meta:
            QMessageBox.warning(self, "错误", f"未找到记录: {task_id}")
            return
        
        # 保存当前信息
        self.current_task_id = task_id
        self.current_split = meta['split']
        
        # 显示当前信息
        info_text = f"""
当前记录: {task_id}
图像ID: {meta['image_id']}
数据集: [{meta['split']}]
短语: {meta['phrase']}
类别: {meta['name']}
属性: {', '.join(meta['attributes'])}
        """.strip()
        
        self.current_info_label.setText(info_text)
        self.current_info_label.setStyleSheet("color: black; padding: 10px; background-color: #f0f0f0;")
        
        # 填充表单
        self.phrase_input.setText(meta['phrase'])
        self.name_input.setText(meta['name'])
        self.attributes_input.setText(', '.join(meta['attributes']))
        self._baseline_values = {
            'phrase': meta['phrase'],
            'name': meta['name'],
            'attributes': list(meta['attributes'])
        }
    
    def save_changes(self):
        """
        保存修改

        P2-6: 改为异步执行，避免 filter_rewrite 在主线程导致 UI 卡死
        """
        if not self.current_task_id:
            QMessageBox.warning(self, "警告", "请先加载一条记录")
            return

        # 收集修改的字段
        field_updates = {}
        baseline = self._baseline_values or {}

        phrase = self.phrase_input.text().strip()
        if phrase != baseline.get('phrase', ''):
            field_updates['phrase'] = phrase

        name = self.name_input.text().strip()
        if name != baseline.get('name', ''):
            field_updates['name'] = name

        attributes = [attr.strip() for attr in self.attributes_input.text().split(',')
                     if attr.strip()]
        if attributes != baseline.get('attributes', []):
            field_updates['attributes'] = attributes

        if not field_updates:
            QMessageBox.warning(self, "警告", "没有任何修改")
            return

        # 确认修改
        reply = QMessageBox.question(
            self,
            "确认修改",
            f"确定要修改以下字段吗?\n{', '.join(field_updates.keys())}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # P2-6: 禁用按钮，防止重复提交
        self.update_btn.setEnabled(False)
        self.current_info_label.setText(f"⏳ 正在保存修改...")
        self.current_info_label.setStyleSheet("color: #2196F3; padding: 10px;")

        # P2-6: 暂存待更新字段（完成后需要同步到索引）
        self._pending_updates = field_updates
        self._updated_task_id = self.current_task_id

        # P2-6: 创建后台写操作线程
        self._write_worker = WriteWorker('update', {
            'task_id': self.current_task_id,
            'split': self.current_split,
            'field_updates': field_updates,
            'dry_run': False
        })
        self._write_worker.progress_updated.connect(self.on_write_progress)
        self._write_worker.finished.connect(self.on_write_finished)
        self._write_worker.error_occurred.connect(self.on_write_error)
        self._write_worker.start()

    def on_write_progress(self, message: str):
        """P2-6: 写操作进度更新"""
        self.current_info_label.setText(f"⏳ {message}")

    def on_write_finished(self, result: dict):
        """P2-6: 写操作完成回调"""
        self.update_btn.setEnabled(True)

        if result['success']:
            updated_meta = result.get('updated_meta')
            updated_task_id = self.current_task_id
            if updated_meta and updated_task_id:
                self.dataset_index.update_entry(updated_task_id, updated_meta)
                self.current_split = updated_meta['split']
                self.record_updated.emit(updated_task_id)
                self.search_input.setText(updated_task_id)
                self.load_record()

            QMessageBox.information(self, "成功", f"✅ {result['message']}")
        else:
            self.current_info_label.setText(f"尚未加载记录")
            self.current_info_label.setStyleSheet("color: gray; padding: 10px;")
            QMessageBox.warning(self, "失败", result['message'])

    def on_write_error(self, error_msg: str):
        """P2-6: 写操作失败回调"""
        self.update_btn.setEnabled(True)
        self.current_info_label.setText(f"尚未加载记录")
        self.current_info_label.setStyleSheet("color: gray; padding: 10px;")
        QMessageBox.critical(self, "错误", f"更新失败:\n{error_msg}")
    
    def clear_form(self):
        """清空表单"""
        self._baseline_values = None
        self.search_input.clear()
        self.phrase_input.clear()
        self.name_input.clear()
        self.attributes_input.clear()
        self.current_task_id = None
        self.current_split = None
        self.current_info_label.setText("尚未加载记录")
        self.current_info_label.setStyleSheet("color: gray; padding: 10px;")
