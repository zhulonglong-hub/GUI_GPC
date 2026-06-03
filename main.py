"""
GPC Dataset Manager - 程序入口

启动 GUI 应用程序
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow
from config import validate_dataset_structure, DATASET_ROOT


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("GPC Dataset Manager")
    app.setOrganizationName("GPC")
    
    # 验证数据集结构
    valid, errors = validate_dataset_structure()
    
    if not valid:
        error_text = '\n'.join(f"• {err}" for err in errors)
        QMessageBox.critical(
            None,
            "数据集验证失败",
            f"数据集目录结构不完整:\n\n{error_text}\n\n"
            f"当前数据集根目录: {DATASET_ROOT}\n\n"
            f"请检查 config.py 中的 DATASET_ROOT 配置是否正确。"
        )
        return 1
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
