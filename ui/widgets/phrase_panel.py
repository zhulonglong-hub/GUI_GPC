"""
GPC Dataset Manager - 短语字段展示面板

以树形结构展示完整的记录字段
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QLabel, QMenu, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class PhrasePanel(QWidget):
    """短语和字段展示面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("记录详情")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # 树形控件
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["字段", "值"])
        self.tree.setColumnWidth(0, 200)

        # P1-4: 启用右键菜单
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # P1-4: 双击复制值
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        layout.addWidget(self.tree)
    
    def display_record(self, record: dict) -> None:
        """
        显示记录详情
        
        Args:
            record: 完整的记录字典
        """
        self.tree.clear()
        
        if not record:
            return
        
        # 基本字段
        self._add_item(None, "task_id", str(record.get('task_id', '')))
        self._add_item(None, "image_id", str(record.get('image_id', '')))
        self._add_item(None, "split", str(record.get('split', 'N/A')))
        self._add_item(None, "phrase", str(record.get('phrase', '')))
        
        # phrase_structure
        phrase_struct = record.get('phrase_structure', {})
        if phrase_struct:
            ps_item = QTreeWidgetItem(self.tree, ["phrase_structure", ""])
            self._add_item(ps_item, "name", str(phrase_struct.get('name', '')))
            self._add_item(ps_item, "attributes", str(phrase_struct.get('attributes', [])))
            self._add_item(ps_item, "type", str(phrase_struct.get('type', '')))
            relations = phrase_struct.get('relation_descriptions', [])
            self._add_item(ps_item, "relation_descriptions", str(relations))
        
        # instance_boxes
        boxes = record.get('instance_boxes', [])
        if boxes:
            self._add_item(None, "instance_boxes", str(boxes))
        
        # Polygons (显示顶点总数)
        polygons = record.get('Polygons', [])
        if polygons:
            vertex_count = sum(
                len(poly) 
                for poly_group in polygons 
                for poly in poly_group
            )
            self._add_item(None, "Polygons", f"{len(polygons)} 组, 共 {vertex_count} 个顶点")
        
        self.tree.expandAll()
    
    def _add_item(self, parent, field: str, value: str) -> QTreeWidgetItem:
        """添加树节点"""
        if parent is None:
            item = QTreeWidgetItem(self.tree, [field, value])
        else:
            item = QTreeWidgetItem(parent, [field, value])
        return item
    
    def clear(self) -> None:
        """清空面板"""
        self.tree.clear()

    def show_context_menu(self, position):
        """
        P1-4: 显示右键菜单
        """
        item = self.tree.itemAt(position)
        if not item:
            return

        # 获取值列的文本
        value = item.text(1)
        if not value:
            return

        menu = QMenu(self)
        copy_action = QAction("📋 复制值", self)
        copy_action.triggered.connect(lambda: self.copy_to_clipboard(value))
        menu.addAction(copy_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def on_item_double_clicked(self, item, column):
        """
        P1-4: 双击复制值到剪贴板
        """
        value = item.text(1)
        if value:
            self.copy_to_clipboard(value)
            # 在父窗口状态栏显示提示（如果有的话）
            parent_window = self.window()
            if hasattr(parent_window, 'statusBar'):
                parent_window.statusBar().showMessage(f"已复制: {value[:50]}...", 2000)

    def copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    panel = PhrasePanel()
    
    test_record = {
        "task_id": "test_001",
        "image_id": "test_image",
        "split": "train",
        "phrase": "green forest",
        "phrase_structure": {
            "name": "forest",
            "attributes": ["green"],
            "type": "attribute",
            "relation_descriptions": []
        },
        "instance_boxes": [[10, 10, 100, 100]],
        "Polygons": [[[[10, 10], [100, 10], [100, 100], [10, 100]]]]
    }
    
    panel.display_record(test_record)
    panel.resize(400, 500)
    panel.show()
    
    sys.exit(app.exec())
