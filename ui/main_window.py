"""
GPC Dataset Manager - 主窗口

整合所有Tab和功能的主窗口
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QMessageBox,
                             QMenuBar, QMenu, QFileDialog, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui.tab_browse import BrowseTab
from ui.tab_add import AddTab
from ui.tab_delete import DeleteTab
from ui.tab_edit import EditTab
from ui.tab_stats import StatsTab
from ui.widgets.progress_dialog import ProgressDialog
from workers.index_builder import IndexBuilder
from config import validate_dataset_structure


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.dataset_index = None
        self.index_builder = None
        self.init_ui()
        self.load_index()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("GPC Dataset Manager v1.0")
        self.resize(1400, 900)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建Tab容器
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("正在加载索引...")
        self.status_bar.addWidget(self.status_label)
        
        self.stats_label = QLabel("")
        self.status_bar.addPermanentWidget(self.stats_label)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        refresh_action = QAction("🔄 刷新索引", self)
        refresh_action.triggered.connect(self.refresh_index)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 数据集菜单
        dataset_menu = menubar.addMenu("数据集(&D)")
        
        validate_action = QAction("验证数据集结构", self)
        validate_action.triggered.connect(self.validate_dataset)
        dataset_menu.addAction(validate_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def load_index(self):
        """加载数据集索引"""
        self.status_label.setText("⏳ 构建索引中...")
        
        # 创建进度对话框
        self.progress_dialog = ProgressDialog("加载数据集索引", self)
        self.progress_dialog.set_message("正在构建索引,请稍候...")
        
        # 创建索引构建线程
        self.index_builder = IndexBuilder()
        self.index_builder.progress_updated.connect(self.on_index_progress)
        self.index_builder.index_ready.connect(self.on_index_ready)
        self.index_builder.error_occurred.connect(self.on_index_error)
        
        # 启动线程
        self.index_builder.start()
        
        # 显示进度对话框
        QTimer.singleShot(500, self.progress_dialog.show)
    
    def on_index_progress(self, current, total):
        """索引构建进度更新"""
        self.progress_dialog.set_progress(current, total)
    
    def on_index_ready(self, index):
        """索引就绪"""
        self.dataset_index = index
        self.progress_dialog.close()
        
        # 创建所有Tab
        self.create_tabs()
        
        # 更新状态栏
        self.status_label.setText("✓ 索引就绪")
        self.update_stats_display()
    
    def on_index_error(self, error_msg):
        """索引构建失败"""
        self.progress_dialog.close()
        QMessageBox.critical(self, "错误", f"索引构建失败:\n{error_msg}")
        self.status_label.setText("✗ 索引加载失败")
    
    def create_tabs(self):
        """创建所有功能Tab"""
        # P1-5: 防护判断 - 索引未就绪时不创建Tab
        if not self.dataset_index:
            return

        # 浏览Tab
        self.browse_tab = BrowseTab(self.dataset_index)
        self.tabs.addTab(self.browse_tab, "📷 浏览")

        # 统计Tab
        self.stats_tab = StatsTab(self.dataset_index)
        self.tabs.addTab(self.stats_tab, "📊 统计")

        # 新增Tab
        self.add_tab = AddTab(self.dataset_index)
        self.tabs.addTab(self.add_tab, "➕ 新增")

        # 删除Tab
        self.delete_tab = DeleteTab(self.dataset_index)
        self.tabs.addTab(self.delete_tab, "🗑️ 删除")

        # 编辑Tab
        self.edit_tab = EditTab(self.dataset_index)
        self.tabs.addTab(self.edit_tab, "✏️ 编辑")
    
    def update_stats_display(self):
        """更新状态栏统计信息"""
        if not self.dataset_index:
            return
        
        stats = self.dataset_index.stats
        stats_text = f"train: {stats['train']:,} | val: {stats['val']:,} | test: {stats['test']:,} | 总计: {stats['total']:,}"
        self.stats_label.setText(stats_text)
    
    def refresh_index(self):
        """刷新索引"""
        reply = QMessageBox.question(
            self,
            "刷新索引",
            "确定要重新构建索引吗?这可能需要一些时间。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空当前Tabs
            self.tabs.clear()

            # P1-5: 重置索引状态
            self.dataset_index = None

            # 重新加载索引
            self.load_index()
    
    def validate_dataset(self):
        """验证数据集结构"""
        valid, errors = validate_dataset_structure()
        
        if valid:
            QMessageBox.information(self, "验证成功", "数据集结构完整,所有必要文件存在")
        else:
            error_text = '\n'.join(f"• {err}" for err in errors)
            QMessageBox.warning(self, "验证失败", f"数据集结构存在问题:\n\n{error_text}")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
<h2>GPC Dataset Manager</h2>
<p><b>版本:</b> v1.0</p>
<p><b>用途:</b> GeoPCDataset_V1.0 数据集管理工具</p>
<br>
<p><b>功能:</b></p>
<ul>
<li>浏览和预览数据集样本</li>
<li>新增样本和标注</li>
<li>删除样本(软删除到回收站)</li>
<li>编辑样本字段</li>
<li>数据集统计和分析</li>
</ul>
<br>
<p><b>技术栈:</b> PyQt6 + matplotlib + ijson</p>
        """
        
        QMessageBox.about(self, "关于 GPC Dataset Manager", about_text)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
