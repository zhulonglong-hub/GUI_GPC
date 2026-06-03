"""
GPC Dataset Manager - 新增样本Tab

导入新样本到数据集
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QComboBox, QTextEdit,
                             QFileDialog, QMessageBox, QLabel, QGroupBox)
from PyQt6.QtCore import Qt
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.writer import add_record
from core.validator import validate_import_data
from core.polygon_utils import bbox_to_polygon


class AddTab(QWidget):
    """新增样本Tab"""
    
    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.selected_image_path = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("新增样本")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # 图像选择
        image_group = QGroupBox("1. 选择图像文件")
        image_layout = QHBoxLayout()
        
        self.image_path_label = QLabel("未选择文件")
        self.image_path_label.setStyleSheet("color: gray;")
        image_layout.addWidget(self.image_path_label)
        
        select_btn = QPushButton("📁 选择图像")
        select_btn.clicked.connect(self.select_image)
        image_layout.addWidget(select_btn)
        
        image_group.setLayout(image_layout)
        main_layout.addWidget(image_group)
        
        # 标注信息
        annotation_group = QGroupBox("2. 输入标注信息")
        form_layout = QFormLayout()
        
        # 类别名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如: forest, agriculture, building")
        form_layout.addRow("类别名称 (name):", self.name_input)
        
        # 属性
        self.attributes_input = QLineEdit()
        self.attributes_input.setPlaceholderText("多个属性用逗号分隔,如: green, dense")
        form_layout.addRow("属性 (attributes):", self.attributes_input)
        
        # 关系描述
        self.relations_input = QLineEdit()
        self.relations_input.setPlaceholderText("可选,如: near road")
        form_layout.addRow("关系描述:", self.relations_input)
        
        # Split选择
        self.split_combo = QComboBox()
        self.split_combo.addItems(["train", "val", "test"])
        form_layout.addRow("数据集划分:", self.split_combo)
        
        # Polygons输入
        polygons_label = QLabel("多边形数据 (JSON格式):")
        form_layout.addRow(polygons_label)
        
        self.polygons_input = QTextEdit()
        self.polygons_input.setPlaceholderText('格式: [[[[x1,y1], [x2,y2], [x3,y3], ...]]]')
        self.polygons_input.setMaximumHeight(150)
        form_layout.addRow(self.polygons_input)
        
        # 快速矩形框按钮
        bbox_layout = QHBoxLayout()
        bbox_label = QLabel("或快速输入矩形框:")
        bbox_layout.addWidget(bbox_label)
        
        self.bbox_input = QLineEdit()
        self.bbox_input.setPlaceholderText("格式: x_min,y_min,x_max,y_max")
        bbox_layout.addWidget(self.bbox_input)
        
        convert_btn = QPushButton("转换为多边形")
        convert_btn.clicked.connect(self.convert_bbox_to_polygon)
        bbox_layout.addWidget(convert_btn)
        
        form_layout.addRow(bbox_layout)
        
        annotation_group.setLayout(form_layout)
        main_layout.addWidget(annotation_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self.preview_record)
        button_layout.addWidget(preview_btn)
        
        submit_btn = QPushButton("✅ 提交新增")
        submit_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        submit_btn.clicked.connect(self.submit_record)
        button_layout.addWidget(submit_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(clear_btn)
        
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
    
    def select_image(self):
        """选择图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像文件",
            "",
            "图像文件 (*.jpg *.jpeg *.png *.tif *.tiff)"
        )
        
        if file_path:
            self.selected_image_path = Path(file_path)
            self.image_path_label.setText(file_path)
            self.image_path_label.setStyleSheet("color: black;")
    
    def convert_bbox_to_polygon(self):
        """将矩形框转换为多边形"""
        bbox_str = self.bbox_input.text().strip()
        if not bbox_str:
            return
        
        try:
            parts = [float(x.strip()) for x in bbox_str.split(',')]
            if len(parts) != 4:
                raise ValueError("需要4个数值")
            
            polygon = bbox_to_polygon(parts)
            self.polygons_input.setText(json.dumps(polygon, ensure_ascii=False))
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"矩形框格式错误: {e}")

    def preview_record(self):
        """预览将要生成的记录"""
        try:
            record = self._build_record()
            preview_text = json.dumps(record, ensure_ascii=False, indent=2)

            msg = QMessageBox(self)
            msg.setWindowTitle("记录预览")
            msg.setText("即将生成的记录:")
            msg.setDetailedText(preview_text)
            msg.exec()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"预览失败: {e}")

    def submit_record(self):
        """提交新增记录"""
        # 验证输入
        if not self.selected_image_path:
            QMessageBox.warning(self, "警告", "请先选择图像文件")
            return

        if not self.name_input.text().strip():
            QMessageBox.warning(self, "警告", "请输入类别名称")
            return

        if not self.polygons_input.toPlainText().strip():
            QMessageBox.warning(self, "警告", "请输入多边形数据")
            return

        try:
            # 解析多边形
            polygons = json.loads(self.polygons_input.toPlainText())

            # 解析属性
            attributes = [attr.strip() for attr in self.attributes_input.text().split(',')
                         if attr.strip()]

            # 解析关系
            relations = [rel.strip() for rel in self.relations_input.text().split(',')
                        if rel.strip()]

            name = self.name_input.text().strip()
            split = self.split_combo.currentText()

            # 添加记录
            task_id = add_record(
                img_src_path=self.selected_image_path,
                polygons=polygons,
                name=name,
                attributes=attributes,
                relations=relations,
                split=split,
                dry_run=False
            )

            # 更新索引
            self.dataset_index.add_entry({
                'task_id': task_id,
                'image_id': self.selected_image_path.stem,
                'split': split,
                'name': name,
                'attributes': attributes,
                'phrase': ' '.join(attributes + [name] + relations)
            })

            QMessageBox.information(self, "成功", f"成功添加记录!\ntask_id: {task_id}")

            # 清空表单
            self.clear_form()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加记录失败:\n{str(e)}")

    def clear_form(self):
        """清空表单"""
        self.selected_image_path = None
        self.image_path_label.setText("未选择文件")
        self.image_path_label.setStyleSheet("color: gray;")
        self.name_input.clear()
        self.attributes_input.clear()
        self.relations_input.clear()
        self.polygons_input.clear()
        self.bbox_input.clear()

    def _build_record(self) -> dict:
        """构建记录用于预览"""
        polygons = json.loads(self.polygons_input.toPlainText())
        attributes = [attr.strip() for attr in self.attributes_input.text().split(',')
                     if attr.strip()]
        relations = [rel.strip() for rel in self.relations_input.text().split(',')
                    if rel.strip()]

        return {
            'image_id': self.selected_image_path.stem if self.selected_image_path else 'N/A',
            'name': self.name_input.text().strip(),
            'attributes': attributes,
            'relations': relations,
            'split': self.split_combo.currentText(),
            'polygons': polygons
        }
