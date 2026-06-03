"""
GPC Dataset Manager - 数据集索引模块

基于 refer_input_*.json 的轻量内存索引
仅加载轻量级字段(不含Polygons),总大小约22MB
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import pickle

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_refer_input_json, SPLITS, CACHE_DIR
from core.json_io import stream_records


class DatasetIndex:
    """数据集内存索引"""
    
    def __init__(self):
        # 主索引: task_id -> 记录元数据
        self.main: Dict[str, dict] = {}
        
        # 倒排索引: image_id -> [task_id, ...]
        self.by_image: Dict[str, List[str]] = {}
        
        # 倒排索引: name -> [task_id, ...]
        self.by_name: Dict[str, List[str]] = {}
        
        # 统计信息
        self.stats: Dict[str, int] = {
            'train': 0,
            'val': 0,
            'test': 0,
            'total': 0
        }
    
    def build(self, annotations_dir: Path) -> None:
        """
        从 refer_input_*.json 构建索引
        
        Args:
            annotations_dir: annotations目录路径
        """
        self.clear()
        
        for split in SPLITS:
            input_json = annotations_dir / f"refer_input_{split}.json"
            if not input_json.exists():
                continue
            
            count = 0
            for record in stream_records(input_json):
                self._add_record(record, split)
                count += 1
            
            self.stats[split] = count
        
        self.stats['total'] = sum(self.stats[s] for s in SPLITS)
    
    def _add_record(self, record: dict, split: str) -> None:
        """添加单条记录到索引"""
        task_id = record.get('task_id')
        if not task_id:
            return

        # P1-6: 确保 image_id 为字符串类型（防止 JSON 中是数字）
        image_id = str(record.get('image_id', '')) if record.get('image_id') else ''
        phrase_struct = record.get('phrase_structure', {})
        name = phrase_struct.get('name', '')
        attributes = phrase_struct.get('attributes', [])
        phrase = record.get('phrase', '')
        
        # 主索引
        self.main[task_id] = {
            'task_id': task_id,
            'image_id': image_id,
            'split': split,
            'name': name,
            'attributes': attributes,
            'phrase': phrase
        }
        
        # image_id 倒排索引
        if image_id:
            if image_id not in self.by_image:
                self.by_image[image_id] = []
            self.by_image[image_id].append(task_id)
        
        # name 倒排索引
        if name:
            if name not in self.by_name:
                self.by_name[name] = []
            self.by_name[name].append(task_id)
    
    def search(self, 
               query: str, 
               by: str = 'task_id',
               split_filter: Optional[str] = None) -> List[str]:
        """
        搜索记录
        
        Args:
            query: 查询字符串
            by: 搜索维度 ('task_id', 'image_id', 'name', 'phrase')
            split_filter: 可选的split过滤
        
        Returns:
            匹配的 task_id 列表
        """
        results = []
        
        if by == 'task_id':
            if query in self.main:
                results = [query]
        
        elif by == 'image_id':
            if query in self.by_image:
                results = self.by_image[query]
            else:
                # P1-6: 前缀匹配 - 确保 img_id 为字符串类型
                for img_id in self.by_image:
                    img_id_str = str(img_id)  # 转为字符串
                    if img_id_str.startswith(query):
                        results.extend(self.by_image[img_id])
        
        elif by == 'name':
            if query in self.by_name:
                results = self.by_name[query]
            else:
                # 模糊匹配
                query_lower = query.lower()
                for name in self.by_name:
                    if query_lower in name.lower():
                        results.extend(self.by_name[name])
        
        elif by == 'phrase':
            # 短语关键字搜索
            query_lower = query.lower()
            for task_id, meta in self.main.items():
                if query_lower in meta['phrase'].lower():
                    results.append(task_id)
        
        # 应用 split 过滤
        if split_filter:
            results = [tid for tid in results 
                      if self.main.get(tid, {}).get('split') == split_filter]
        
        return results
    
    def get_meta(self, task_id: str) -> Optional[dict]:
        """获取任务元数据"""
        return self.main.get(task_id)
    
    def add_entry(self, meta: dict) -> None:
        """添加新条目到索引"""
        split = meta.get('split', 'train')
        self._add_record(meta, split)
        self.stats[split] += 1
        self.stats['total'] += 1
    
    def remove_entry(self, task_id: str) -> None:
        """从索引移除条目"""
        if task_id not in self.main:
            return
        
        meta = self.main[task_id]
        split = meta['split']
        image_id = meta['image_id']
        name = meta['name']
        
        # 从主索引移除
        del self.main[task_id]
        
        # 从倒排索引移除
        if image_id in self.by_image:
            self.by_image[image_id] = [tid for tid in self.by_image[image_id] 
                                       if tid != task_id]
            if not self.by_image[image_id]:
                del self.by_image[image_id]
        
        if name in self.by_name:
            self.by_name[name] = [tid for tid in self.by_name[name] 
                                  if tid != task_id]
            if not self.by_name[name]:
                del self.by_name[name]
        
        # 更新统计
        self.stats[split] -= 1
        self.stats['total'] -= 1

    def update_entry(self, task_id: str, new_meta: dict) -> None:
        """更新索引中的条目"""
        if task_id not in self.main:
            return

        # 先移除旧条目
        self.remove_entry(task_id)

        # 添加新条目
        self.add_entry(new_meta)

    def clear(self) -> None:
        """清空索引"""
        self.main.clear()
        self.by_image.clear()
        self.by_name.clear()
        for key in self.stats:
            self.stats[key] = 0

    def save_cache(self, cache_path: Path, dataset_root: Path) -> bool:
        """
        保存索引到缓存文件

        Args:
            cache_path: 缓存文件路径
            dataset_root: 数据集根目录（用于校验缓存有效性）
        """
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'dataset_root': str(dataset_root),  # P1-1: 绑定数据集路径
                    'main': self.main,
                    'by_image': self.by_image,
                    'by_name': self.by_name,
                    'stats': self.stats
                }, f)
            return True
        except Exception as e:
            print(f"保存索引缓存失败: {e}")
            return False

    def load_cache(self, cache_path: Path, dataset_root: Path) -> bool:
        """
        从缓存加载索引

        Args:
            cache_path: 缓存文件路径
            dataset_root: 当前数据集根目录

        Returns:
            是否成功加载（校验失败返回False）
        """
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)

            # P1-1: 校验数据集路径，不一致则视为缓存失效
            cached_root = data.get('dataset_root', '')
            if cached_root != str(dataset_root):
                print(f"缓存失效: 数据集路径已变更 {cached_root} -> {dataset_root}")
                return False

            self.main = data['main']
            self.by_image = data['by_image']
            self.by_name = data['by_name']
            self.stats = data['stats']

            return True
        except Exception as e:
            print(f"加载索引缓存失败: {e}")
            return False


if __name__ == "__main__":
    from config import ANNOTATIONS_DIR, DATASET_ROOT

    print("构建索引...")
    index = DatasetIndex()
    index.build(ANNOTATIONS_DIR)

    print(f"统计信息: {index.stats}")
    print(f"总task数: {len(index.main)}")
    print(f"总image数: {len(index.by_image)}")
    print(f"总类别数: {len(index.by_name)}")

    # 测试搜索
    if index.main:
        test_task_id = list(index.main.keys())[0]
        print(f"\n测试task_id: {test_task_id}")
        print(f"元数据: {index.get_meta(test_task_id)}")
