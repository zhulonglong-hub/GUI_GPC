"""
GPC Dataset Manager - 删除样本Tab

删除数据集中的样本
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QListWidget, QMessageBox, QLabel,
                             QCheckBox, QGroupBox, QListWidgetItem)
from PyQt6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.writer import delete_record


class DeleteTab(QWidget):
    """删除样本Tab"""
    
    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.pending_deletions = []  # 待删除的 (task_id, split) 列表
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("删除样本")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # 搜索区域
        search_group = QGroupBox("1. 搜索要删除的样本")
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入 task_id 或 image_id...")
        self.search_input.returnPressed.connect(self.search_samples)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self.search_samples)
        search_layout.addWidget(search_btn)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # 结果列表
        result_group = QGroupBox("2. 选择要删除的条目")
        result_layout = QVBoxLayout()
        
        self.result_list = QListWidget()
        self.result_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        result_layout.addWidget(self.result_list)
        
        # 全选/反选按钮
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        select_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all)
        select_layout.addWidget(deselect_all_btn)
        
        select_layout.addStretch()
        result_layout.addLayout(select_layout)
        
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)
        
        # 选项
        options_group = QGroupBox("3. 删除选项")
        options_layout = QVBoxLayout()
        
        self.delete_image_checkbox = QCheckBox("同时删除图像文件 (仅当该图所有标注均被删除时)")
        options_layout.addWidget(self.delete_image_checkbox)
        
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        delete_btn = QPushButton("🗑️ 删除选中条目")
        delete_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(delete_btn)
        
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
    
    def search_samples(self):
        """搜索样本"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return
        
        self.result_list.clear()
        self.pending_deletions.clear()
        
        # 尝试作为 task_id 搜索
        results = self.dataset_index.search(query, by='task_id')
        
        # 如果没找到,尝试作为 image_id 搜索
        if not results:
            results = self.dataset_index.search(query, by='image_id')
        
        if not results:
            QMessageBox.information(self, "提示", "未找到匹配的样本")
            return
        
        # 显示结果
        for task_id in results:
            meta = self.dataset_index.get_meta(task_id)
            if meta:
                display_text = f"{task_id} | {meta['phrase']} | [{meta['split']}] | {meta['image_id']}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, (task_id, meta['split']))
                self.result_list.addItem(item)
        
        # 如果是通过 image_id 找到多个,提示用户
        if len(results) > 1:
            image_id = self.dataset_index.get_meta(results[0])['image_id']
            QMessageBox.information(
                self,
                "提示",
                f"找到 {len(results)} 条标注属于同一图像: {image_id}\n请选择要删除的条目"
            )
    
    def select_all(self):
        """全选"""
        for i in range(self.result_list.count()):
            self.result_list.item(i).setSelected(True)
    
    def deselect_all(self):
        """取消全选"""
        for i in range(self.result_list.count()):
            self.result_list.item(i).setSelected(False)
    
    def delete_selected(self):
        """删除选中的条目"""
        selected_items = self.result_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要删除的条目")
            return
        
        # 二次确认
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除 {len(selected_items)} 条记录吗?\n此操作会将记录备份到回收站。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        delete_image = self.delete_image_checkbox.isChecked()
        
        # 执行删除
        success_count = 0
        failed_items = []
        
        for item in selected_items:
            task_id, split = item.data(Qt.ItemDataRole.UserRole)
            
            try:
                result = delete_record(task_id, split, delete_image_file=delete_image)
                
                if result['success']:
                    # 从索引中移除
                    self.dataset_index.remove_entry(task_id)
                    success_count += 1
                else:
                    failed_items.append(f"{task_id}: {result['message']}")
                    
            except Exception as e:
                failed_items.append(f"{task_id}: {str(e)}")
        
        # 显示结果
        if failed_items:
            QMessageBox.warning(
                self,
                "删除完成(部分失败)",
                f"成功删除 {success_count} 条\n失败 {len(failed_items)} 条:\n" + '\n'.join(failed_items[:5])
            )
        else:
            QMessageBox.information(self, "成功", f"成功删除 {success_count} 条记录")
        
        # 清空列表
        self.result_list.clear()
        self.search_input.clear()
