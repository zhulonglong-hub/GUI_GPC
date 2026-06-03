"""
GPC Dataset Manager - JSON IO 模块

大JSON流式读/写/偏移量索引工具
核心:避免全量加载 2.7GB refer_train.json
"""

import json
import pickle
from pathlib import Path
from typing import Generator, Optional, Callable, Dict
import shutil
from datetime import datetime
from filelock import FileLock


def stream_records(json_path: Path) -> Generator[dict, None, None]:
    """
    流式读取JSON数组文件,逐条yield记录
    
    Args:
        json_path: JSON文件路径
    
    Yields:
        单条记录字典
    """
    if not json_path.exists():
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        content = f.read(1)
        if content != '[':
            raise ValueError(f"{json_path} 不是JSON数组格式")
        
        f.seek(0)
        data = json.load(f)
        
        if isinstance(data, list):
            for record in data:
                yield record


def build_offset_index(json_path: Path) -> Dict[str, int]:
    """
    构建 task_id -> 字节偏移量索引
    
    扫描JSON数组文件,记录每个task_id对应的字节起始位置
    注意:这是简化版,适用于格式化JSON数组
    
    Args:
        json_path: JSON文件路径
    
    Returns:
        {task_id: byte_offset}
    """
    offset_index = {}
    
    if not json_path.exists():
        return offset_index
    
    with open(json_path, 'rb') as f:
        content = f.read()
    
    # 解析整个文件获取偏移量(简化实现)
    try:
        data = json.loads(content.decode('utf-8'))
        if not isinstance(data, list):
            return offset_index
        
        # 将文件转为字符串再定位
        content_str = content.decode('utf-8')
        
        for record in data:
            task_id = record.get('task_id')
            if task_id:
                # 查找该task_id在文件中的位置
                record_str = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
                offset = content_str.find(f'"{task_id}"')
                if offset != -1:
                    # 回退到记录起始的 {
                    start = content_str.rfind('{', 0, offset)
                    if start != -1:
                        offset_index[task_id] = start
        
    except Exception as e:
        print(f"构建偏移量索引失败 {json_path}: {e}")
    
    return offset_index


def save_offset_index(index: Dict[str, int], 
                      cache_path: Path,
                      src_mtime: float,
                      src_size: int) -> None:
    """
    保存偏移量索引到缓存文件
    
    Args:
        index: 偏移量索引字典
        cache_path: 缓存文件路径
        src_mtime: 源文件修改时间
        src_size: 源文件大小
    """
    cache_data = {
        'index': index,
        'mtime': src_mtime,
        'size': src_size,
        'created_at': datetime.now().isoformat()
    }
    
    with open(cache_path, 'wb') as f:
        pickle.dump(cache_data, f)


def load_offset_index(cache_path: Path,
                      src_path: Path) -> Optional[Dict[str, int]]:
    """
    从缓存加载偏移量索引,自动校验mtime和size
    
    Args:
        cache_path: 缓存文件路径
        src_path: 源JSON文件路径
    
    Returns:
        偏移量索引字典,失效则返回None
    """
    if not cache_path.exists() or not src_path.exists():
        return None
    
    try:
        with open(cache_path, 'rb') as f:
            cache_data = pickle.load(f)
        
        # 校验源文件是否变化
        src_stat = src_path.stat()
        if (cache_data['mtime'] == src_stat.st_mtime and 
            cache_data['size'] == src_stat.st_size):
            return cache_data['index']
        else:
            return None
            
    except Exception:
        return None


def read_record_at_offset(json_path: Path, offset: int) -> Optional[dict]:
    """
    按字节偏移量读取单条完整记录(含Polygons)

    Args:
        json_path: JSON文件路径
        offset: 字节偏移量

    Returns:
        单条记录字典,失败返回None
    """
    try:
        with open(json_path, 'rb') as f:
            f.seek(offset)
            content = f.read()

            # 找到完整的JSON对象
            bracket_count = 0
            start = content.find(b'{')
            if start == -1:
                return None

            for i in range(start, len(content)):
                if content[i:i+1] == b'{':
                    bracket_count += 1
                elif content[i:i+1] == b'}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        record_bytes = content[start:i+1]
                        return json.loads(record_bytes.decode('utf-8'))

    except Exception as e:
        print(f"读取记录失败 offset={offset}: {e}")

    return None


def append_record(json_path: Path, record: dict) -> bool:
    """
    线程安全地追加记录到JSON数组文件

    Args:
        json_path: JSON文件路径
        record: 要追加的记录

    Returns:
        是否成功
    """
    lock_path = json_path.parent / f"{json_path.name}.lock"
    lock = FileLock(str(lock_path), timeout=10)

    try:
        with lock:
            # 读取现有数据
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []

            # 追加新记录
            data.append(record)

            # 写回文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"追加记录失败 {json_path}: {e}")
        return False


def filter_rewrite(json_path: Path,
                   keep_fn: Callable[[dict], bool],
                   transform_fn: Optional[Callable[[dict], dict]] = None) -> bool:
    """
    流式过滤重写JSON文件,遵循"备份→写tmp→原子替换"安全策略

    Args:
        json_path: JSON文件路径
        keep_fn: 判断是否保留该记录的函数
        transform_fn: 可选的记录转换函数

    Returns:
        是否成功
    """
    if not json_path.exists():
        return False

    backup_path = json_path.with_suffix(json_path.suffix + '.bak')
    tmp_path = json_path.with_suffix(json_path.suffix + '.tmp')

    try:
        # 1. 备份原文件
        shutil.copy2(json_path, backup_path)

        # 2. 流式过滤写入临时文件
        filtered_data = []
        for record in stream_records(json_path):
            if keep_fn(record):
                if transform_fn:
                    record = transform_fn(record)
                filtered_data.append(record)

        # 3. 写入临时文件
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)

        # 4. 原子替换
        shutil.move(str(tmp_path), str(json_path))

        # 5. 删除备份
        backup_path.unlink()

        return True

    except Exception as e:
        print(f"过滤重写失败 {json_path}: {e}")

        # 失败时回滚
        if backup_path.exists():
            shutil.copy2(backup_path, json_path)
            backup_path.unlink()

        if tmp_path.exists():
            tmp_path.unlink()

        return False
