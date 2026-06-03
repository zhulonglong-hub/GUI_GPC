"""
GPC Dataset Manager - 编辑样本Tab

编辑数据集中样本的字段
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QMessageBox, QLabel, QGroupBox,
                             QFormLayout, QComboBox)
from PyQt6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.writer import update_fields


class EditTab(QWidget):
    """编辑样本Tab"""
    
    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.current_task_id = None
        self.current_split = None
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
        hint_label = QLabel("提示: 只修改需要变更的字段,其他字段留空则保持不变")
        hint_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        main_layout.addWidget(hint_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(clear_btn)
        
        update_btn = QPushButton("✅ 保存修改")
        update_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        update_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(update_btn)
        
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
        
        # 填充表单 (作为参考)
        self.phrase_input.setPlaceholderText(meta['phrase'])
        self.name_input.setPlaceholderText(meta['name'])
        self.attributes_input.setPlaceholderText(', '.join(meta['attributes']))
    
    def save_changes(self):
        """保存修改"""
        if not self.current_task_id:
            QMessageBox.warning(self, "警告", "请先加载一条记录")
            return
        
        # 收集修改的字段
        field_updates = {}
        
        if self.phrase_input.text().strip():
            field_updates['phrase'] = self.phrase_input.text().strip()
        
        if self.name_input.text().strip():
            field_updates['name'] = self.name_input.text().strip()
        
        if self.attributes_input.text().strip():
            attributes = [attr.strip() for attr in self.attributes_input.text().split(',')
                         if attr.strip()]
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
        
        try:
            # 执行更新
            result = update_fields(
                self.current_task_id,
                self.current_split,
                field_updates,
                dry_run=False
            )
            
            if result['success']:
                # 更新索引
                meta = self.dataset_index.get_meta(self.current_task_id)
                if meta:
                    for field, value in field_updates.items():
                        if field == 'phrase':
                            meta['phrase'] = value
                        elif field == 'name':
                            meta['name'] = value
                        elif field == 'attributes':
                            meta['attributes'] = value
                    
                    self.dataset_index.update_entry(self.current_task_id, meta)
                
                QMessageBox.information(self, "成功", f"成功更新字段: {', '.join(field_updates.keys())}")
                
                # 清空表单
                self.clear_form()
            else:
                QMessageBox.warning(self, "失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新失败:\n{str(e)}")
    
    def clear_form(self):
        """清空表单"""
        self.search_input.clear()
        self.phrase_input.clear()
        self.name_input.clear()
        self.attributes_input.clear()
        self.current_task_id = None
        self.current_split = None
        self.current_info_label.setText("尚未加载记录")
        self.current_info_label.setStyleSheet("color: gray; padding: 10px;")
