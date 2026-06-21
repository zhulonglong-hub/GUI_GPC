"""
GPC Dataset Manager - 统计概览Tab

显示数据集统计信息
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import IMAGES_DIR, get_name_count_json, LOG_DIR


class StatsTab(QWidget):
    """统计概览Tab"""
    
    def __init__(self, dataset_index, parent=None):
        super().__init__(parent)
        self.dataset_index = dataset_index
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 标题和刷新按钮
        header_layout = QHBoxLayout()
        title = QLabel("数据集统计概览")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_stats)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # 基本统计
        stats_group = QGroupBox("基本统计")
        stats_layout = QVBoxLayout()

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 12px; padding: 10px;")
        stats_layout.addWidget(self.stats_label)

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # 数据来源分布
        source_group = QGroupBox("数据来源分布")
        source_layout = QVBoxLayout()
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(120)
        source_layout.addWidget(self.source_text)
        source_group.setLayout(source_layout)
        main_layout.addWidget(source_group)
        
        # 类别分布
        category_group = QGroupBox("TOP-20 类别分布")
        category_layout = QVBoxLayout()
        
        self.category_text = QTextEdit()
        self.category_text.setReadOnly(True)
        self.category_text.setMaximumHeight(300)
        category_layout.addWidget(self.category_text)
        
        category_group.setLayout(category_layout)
        main_layout.addWidget(category_group)
        
        # 最近操作
        log_group = QGroupBox("最近操作记录 (最新20条)")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        main_layout.addStretch()
        
        # 初始加载
        self.refresh_stats()
    
    def refresh_stats(self):
        """刷新统计信息"""
        # 基本统计
        stats = self.dataset_index.stats
        
        # 统计图像文件数
        image_count = 0
        if IMAGES_DIR.exists():
            image_count = len(list(IMAGES_DIR.glob("*")))
        
        stats_text = f"""
训练集: {stats.get('train', 0):,} 条
验证集: {stats.get('val', 0):,} 条
测试集: {stats.get('test', 0):,} 条
总计: {stats.get('total', 0):,} 条

图像文件: {image_count} 张
唯一图像ID: {len(self.dataset_index.by_image)} 个
类别总数: {len(self.dataset_index.by_name)} 个
        """
        
        self.stats_label.setText(stats_text.strip())

        # 类别分布 TOP-20
        self.update_category_distribution()

        # 数据来源分布
        self.update_source_distribution()

        # 最近操作
        self.update_recent_logs()
    
    def update_source_distribution(self):
        """按 data_source 字段统计各来源的 task 数量。"""
        source_counts: dict = {}
        for meta in self.dataset_index.main.values():
            src = str(meta.get('data_source', '') or '') or '（未标注）'
            source_counts[src] = source_counts.get(src, 0) + 1

        if not source_counts:
            self.source_text.setText('暂无数据')
            return

        total = sum(source_counts.values())
        lines = []
        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            bar = '█' * int(pct / 2)
            lines.append(f"{src:20s} {bar} {count:,} ({pct:.1f}%)")
        self.source_text.setText('\n'.join(lines))

    def update_category_distribution(self):
        """更新类别分布"""
        # 统计每个类别的数量
        category_counts = {}
        for name, task_ids in self.dataset_index.by_name.items():
            category_counts[name] = len(task_ids)
        
        # 排序并取TOP-20
        sorted_categories = sorted(category_counts.items(), 
                                  key=lambda x: x[1], 
                                  reverse=True)[:20]
        
        # 生成文本
        text_lines = []
        max_count = sorted_categories[0][1] if sorted_categories else 1
        
        for name, count in sorted_categories:
            # 简单的文本条形图
            bar_length = int((count / max_count) * 40)
            bar = '█' * bar_length
            text_lines.append(f"{name:20s} {bar} {count}")
        
        self.category_text.setText('\n'.join(text_lines))
    
    def update_recent_logs(self):
        """更新最近操作记录"""
        log_file = LOG_DIR / "operations.jsonl"
        
        if not log_file.exists():
            self.log_text.setText("暂无操作记录")
            return
        
        # 读取最后20行
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            recent_lines = lines[-20:]
            recent_lines.reverse()  # 最新的在前
            
            log_entries = []
            for line in recent_lines:
                try:
                    entry = json.loads(line)
                    timestamp = entry.get('timestamp', '')[:19]  # 去掉毫秒
                    operation = entry.get('operation', '')
                    task_id = entry.get('task_id', '')
                    log_entries.append(f"{timestamp} | {operation:8s} | {task_id}")
                except:
                    pass
            
            self.log_text.setText('\n'.join(log_entries))
            
        except Exception as e:
            self.log_text.setText(f"读取日志失败: {e}")


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
    tab = StatsTab(index)
    window.setCentralWidget(tab)
    window.setWindowTitle("统计Tab测试")
    window.resize(800, 600)
    window.show()
    
    sys.exit(app.exec())
