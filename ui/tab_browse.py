"""
GPC Dataset Manager - 浏览预览Tab

查询和预览数据集样本
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                             QLineEdit, QPushButton, QComboBox, QListWidget,
                             QLabel, QMessageBox)
from PyQt6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui.widgets.image_canvas import ImageCanvas
from ui.widgets.phrase_panel import PhrasePanel
from workers.image_loader import ImageLoader
from core.json_io import stream_records, build_offset_index, read_record_at_offset
from config import get_refer_json, CACHE_DIR


class BrowseTab(QWidget):
    """浏览和预览Tab"""
    
    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.current_image_loader = None
        self.offset_indices = {}  # split -> offset_index
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词...")
        self.search_input.returnPressed.connect(self.do_search)
        search_layout.addWidget(self.search_input)
        
        self.search_by_combo = QComboBox()
        self.search_by_combo.addItems(["task_id", "image_id", "name", "phrase"])
        search_layout.addWidget(self.search_by_combo)
        
        self.split_filter_combo = QComboBox()
        self.split_filter_combo.addItems(["全部", "train", "val", "test"])
        search_layout.addWidget(self.split_filter_combo)
        
        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self.do_search)
        search_layout.addWidget(search_btn)
        
        main_layout.addLayout(search_layout)
        
        # 分割器 (左侧结果列表 / 右侧预览)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧: 结果列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.result_label = QLabel("搜索结果: 0 条")
        left_layout.addWidget(self.result_label)
        
        self.result_list = QListWidget()
        self.result_list.itemClicked.connect(self.on_item_selected)
        left_layout.addWidget(self.result_list)
        
        splitter.addWidget(left_widget)
        
        # 右侧: 预览区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 图像画布
        self.canvas = ImageCanvas(self, width=6, height=4)
        right_layout.addWidget(self.canvas, stretch=2)
        
        # 字段面板
        self.phrase_panel = PhrasePanel(self)
        right_layout.addWidget(self.phrase_panel, stretch=1)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
    
    def do_search(self):
        """执行搜索"""
        query = self.search_input.text().strip()
        search_by = self.search_by_combo.currentText()
        split_filter = self.split_filter_combo.currentText()
        
        if split_filter == "全部":
            split_filter = None
        
        if not query:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return
        
        # 搜索
        results = self.dataset_index.search(query, by=search_by, split_filter=split_filter)
        
        # 更新结果列表
        self.result_list.clear()
        for task_id in results[:1000]:  # 限制显示前1000条
            meta = self.dataset_index.get_meta(task_id)
            if meta:
                display_text = f"{task_id} | {meta['phrase']} | [{meta['split']}]"
                self.result_list.addItem(display_text)
                self.result_list.item(self.result_list.count() - 1).setData(Qt.ItemDataRole.UserRole, task_id)
        
        self.result_label.setText(f"搜索结果: {len(results)} 条 (显示前 {min(len(results), 1000)} 条)")
    
    def on_item_selected(self, item):
        """列表项选中时触发"""
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if not task_id:
            return
        
        meta = self.dataset_index.get_meta(task_id)
        if not meta:
            return
        
        image_id = meta['image_id']
        split = meta['split']
        
        # 加载完整记录 (含Polygons)
        full_record = self.load_full_record(task_id, split)
        
        if full_record:
            # 显示字段
            full_record['split'] = split  # 添加split信息
            self.phrase_panel.display_record(full_record)
            
            # 异步加载图像
            self.load_and_render_image(image_id, [full_record])
        else:
            QMessageBox.warning(self, "错误", f"无法加载完整记录: {task_id}")
    
    def load_full_record(self, task_id: str, split: str) -> dict:
        """加载包含Polygons的完整记录"""
        # 构建偏移量索引 (如果还没有)
        if split not in self.offset_indices:
            cache_path = CACHE_DIR / f"offset_index_{split}.pkl"
            # 这里简化:直接流式查找
            for record in stream_records(get_refer_json(split)):
                if record.get('task_id') == task_id:
                    return record

        return None

    def load_and_render_image(self, image_id: str, mask_records: list):
        """异步加载图像并渲染"""
        # 取消之前的加载任务
        if self.current_image_loader and self.current_image_loader.isRunning():
            self.current_image_loader.terminate()

        # 创建新的加载任务
        self.current_image_loader = ImageLoader(image_id)
        self.current_image_loader.image_loaded.connect(
            lambda img: self.canvas.render(img, mask_records)
        )
        self.current_image_loader.error_occurred.connect(
            lambda msg: QMessageBox.warning(self, "错误", msg)
        )
        self.current_image_loader.start()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from core.dataset_index import DatasetIndex
    from config import ANNOTATIONS_DIR

    app = QApplication(sys.argv)

    # 构建索引
    index = DatasetIndex()
    index.build(ANNOTATIONS_DIR)

    # 创建窗口
    window = QMainWindow()
    tab = BrowseTab(index)
    window.setCentralWidget(tab)
    window.setWindowTitle("浏览Tab测试")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())
