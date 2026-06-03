"""
GPC Dataset Manager - 短语字段展示面板

以树形结构展示完整的记录字段
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel)
from PyQt6.QtCore import Qt
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
