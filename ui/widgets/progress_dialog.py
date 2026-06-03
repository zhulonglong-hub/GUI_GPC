"""
GPC Dataset Manager - 进度对话框

显示后台任务进度,支持取消
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, 
                             QProgressBar, QPushButton)
from PyQt6.QtCore import Qt


class ProgressDialog(QDialog):
    """进度对话框"""
    
    def __init__(self, title: str = "处理中", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 任务描述
        self.label = QLabel("正在处理...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # 详细信息
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.detail_label)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
    
    def set_message(self, message: str) -> None:
        """设置主消息"""
        self.label.setText(message)
    
    def set_progress(self, current: int, total: int) -> None:
        """
        更新进度
        
        Args:
            current: 当前进度
            total: 总数
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress.setValue(percentage)
            self.detail_label.setText(f"{current} / {total}")
        else:
            self.progress.setMaximum(0)  # 不确定进度
    
    def set_detail(self, detail: str) -> None:
        """设置详细信息"""
        self.detail_label.setText(detail)
    
    def enable_cancel(self, enabled: bool) -> None:
        """启用/禁用取消按钮"""
        self.cancel_btn.setEnabled(enabled)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
    import sys
    
    app = QApplication(sys.argv)
    
    def show_progress():
        dialog = ProgressDialog("测试进度", window)
        dialog.set_message("正在加载数据...")
        dialog.set_progress(50, 100)
        dialog.exec()
    
    window = QWidget()
    layout = QVBoxLayout(window)
    btn = QPushButton("显示进度对话框")
    btn.clicked.connect(show_progress)
    layout.addWidget(btn)
    
    window.resize(300, 100)
    window.show()
    
    sys.exit(app.exec())
