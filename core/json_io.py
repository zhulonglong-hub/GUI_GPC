"""
GPC Dataset Manager - JSON IO 模块

大JSON流式读/写/偏移量索引工具
核心:避免全量加载 2.7GB refer_train.json
"""

import json
import pickle
from decimal import Decimal
from pathlib import Path
from typing import Generator, Optional, Callable, Dict
import os
import shutil
from datetime import datetime
from filelock import FileLock
try:
    import ijson
    IJSON_AVAILABLE = True
except ImportError:
    IJSON_AVAILABLE = False
    print("警告: ijson 未安装，将使用低效的全量加载模式")


def _json_default(value):
    """兼容 ijson 产生的 Decimal 等类型，统一转成可序列化值。"""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _normalize_json_value(value):
    """递归规范化 ijson 返回的数据，避免 Decimal 落入后续写路径。"""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_json_value(item) for key, item in value.items()}
    return value


def _write_json_array_record(out_f, record: dict, first_record: bool) -> bool:
    """以紧凑格式写入单条记录，兼容 Decimal。"""
    if not first_record:
        out_f.write(',\n')
    json.dump(record, out_f, ensure_ascii=False, default=_json_default, separators=(',', ':'))
    return False


def stream_records(json_path: Path) -> Generator[dict, None, None]:
    """
    流式读取JSON数组文件,逐条yield记录

    P2-1: 使用 ijson 实现真正的流式解析，避免全量加载

    Args:
        json_path: JSON文件路径

    Yields:
        单条记录字典
    """
    if not json_path.exists():
        return

    if IJSON_AVAILABLE:
        # P2-1: 真流式解析
        try:
            with open(json_path, 'rb') as f:
                # ijson.items() 逐条解析数组元素
                parser = ijson.items(f, 'item')
                for record in parser:
                    yield _normalize_json_value(record)
        except Exception as e:
            print(f"ijson 解析失败 {json_path}: {e}，回退到全量加载")
            # 回退到旧方法
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for record in data:
                        yield record
    else:
        # 回退：全量加载（兼容 ijson 未安装的情况）
        with open(json_path, 'r', encoding='utf-8') as f:
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
                json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)

        return True

    except Exception as e:
        print(f"追加记录失败 {json_path}: {e}")
        return False


def append_record_streaming(json_path: Path, record: dict) -> bool:
    """
    以流式复制方式追加单条记录，避免对已有 JSON 数组做全量加载。
    """
    lock_path = json_path.parent / f"{json_path.name}.lock"
    lock = FileLock(str(lock_path), timeout=10)
    tmp_path = json_path.with_suffix(json_path.suffix + '.tmp')

    try:
        with lock:
            if not json_path.exists() or json_path.stat().st_size == 0:
                with open(json_path, 'w', encoding='utf-8') as out_f:
                    out_f.write('[\n')
                    _write_json_array_record(out_f, record, True)
                    out_f.write('\n]')
                return True

            with open(json_path, 'rb') as src_f, open(tmp_path, 'w', encoding='utf-8') as out_f:
                content = src_f.read()
                if not content.strip():
                    out_f.write('[\n')
                    _write_json_array_record(out_f, record, True)
                    out_f.write('\n]')
                else:
                    end = len(content) - 1
                    while end >= 0 and chr(content[end]).isspace():
                        end -= 1

                    if end < 0 or content[end:end + 1] != b']':
                        raise ValueError(f'{json_path} 不是合法的 JSON 数组文件')

                    body = content[:end].rstrip()
                    if body.endswith(b'['):
                        out_f.write(body.decode('utf-8'))
                        out_f.write('\n')
                        _write_json_array_record(out_f, record, True)
                        out_f.write('\n]')
                    else:
                        out_f.write(body.decode('utf-8'))
                        out_f.write(',\n')
                        json.dump(record, out_f, ensure_ascii=False, default=_json_default, separators=(',', ':'))
                        out_f.write('\n]')

            shutil.move(str(tmp_path), str(json_path))
            return True

    except Exception as e:
        print(f"流式追加记录失败 {json_path}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        return False


def _find_string_bytes(haystack: bytes, needle: str) -> int:
    target = needle.encode('utf-8')
    start = 0
    while True:
        idx = haystack.find(target, start)
        if idx == -1:
            return -1
        if idx == 0 or haystack[idx - 1:idx] != b'\\':
            return idx
        backslash_count = 0
        cursor = idx - 1
        while cursor >= 0 and haystack[cursor:cursor + 1] == b'\\':
            backslash_count += 1
            cursor -= 1
        if backslash_count % 2 == 0:
            return idx
        start = idx + 1


def _find_object_bounds(content: bytes, task_id: str) -> Optional[tuple[int, int]]:
    marker = f'"task_id":"{task_id}"'
    marker_pos = _find_string_bytes(content, marker)
    if marker_pos == -1:
        return None

    in_string = False
    escape = False
    depth = 0
    start = None

    for i, byte in enumerate(content):
        ch = chr(byte)
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
            if depth == 1 and i <= marker_pos:
                start = i
        elif ch == '}':
            if depth == 1 and start is not None and i >= marker_pos:
                return start, i + 1
            depth -= 1

    return None


def _supports_fast_patch(json_path: Path, field_updates: dict) -> bool:
    if not json_path.name.startswith('refer_'):
        return False
    allowed_fields = {'phrase', 'name', 'attributes', 'relations'}
    return bool(field_updates) and set(field_updates).issubset(allowed_fields)


def _patch_record_fields(record: dict, field_updates: dict) -> dict:
    record = _normalize_json_value(record)
    phrase_structure = record.setdefault('phrase_structure', {})

    if 'phrase' in field_updates:
        record['phrase'] = field_updates['phrase']
    if 'name' in field_updates:
        phrase_structure['name'] = field_updates['name']
    if 'attributes' in field_updates:
        phrase_structure['attributes'] = field_updates['attributes']
    if 'relations' in field_updates:
        phrase_structure['relation_descriptions'] = field_updates['relations']

    return record


def _fast_patch_record_fields(json_path: Path, task_id: str, field_updates: dict) -> bool:
    lock_path = json_path.parent / f"{json_path.name}.lock"
    lock = FileLock(str(lock_path), timeout=10)
    backup_path = json_path.with_suffix(json_path.suffix + '.bak')
    tmp_path = json_path.with_suffix(json_path.suffix + '.tmp')

    try:
        with lock:
            shutil.copy2(json_path, backup_path)
            with open(json_path, 'rb') as src_f:
                content = src_f.read()

            bounds = _find_object_bounds(content, task_id)
            if not bounds:
                return False

            start, end = bounds
            record = json.loads(content[start:end].decode('utf-8'))
            updated_record = _patch_record_fields(record, field_updates)
            updated_bytes = json.dumps(
                updated_record,
                ensure_ascii=False,
                default=_json_default,
                separators=(',', ':')
            ).encode('utf-8')

            with open(tmp_path, 'wb') as out_f:
                out_f.write(content[:start])
                out_f.write(updated_bytes)
                out_f.write(content[end:])

            shutil.move(str(tmp_path), str(json_path))
            backup_path.unlink()
            return True

    except Exception as e:
        print(f"单记录快速补丁失败 {json_path}: {e}")

    if backup_path.exists():
        shutil.copy2(backup_path, json_path)
        backup_path.unlink()
    if tmp_path.exists():
        tmp_path.unlink()
    return False


def patch_fields_rewrite(json_path: Path,
                         task_id: str,
                         field_updates: dict,
                         fallback_transform_fn: Optional[Callable[[dict], dict]] = None) -> bool:
    """
    针对单条记录的字段更新入口。

    优先尝试方案 B+ 的单记录快路径；不满足条件或失败时回退到流式重写。
    """
    if _supports_fast_patch(json_path, field_updates):
        if _fast_patch_record_fields(json_path, task_id, field_updates):
            return True

    if fallback_transform_fn is None:
        return False

    return filter_rewrite(
        json_path,
        keep_fn=lambda rec: True,
        transform_fn=fallback_transform_fn
    )


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

        # 2. P2.2-FIX: 流式写入，不累积到内存
        with open(tmp_path, 'w', encoding='utf-8') as out_f:
            out_f.write('[\n')

            first_record = True
            for record in stream_records(json_path):
                if keep_fn(record):
                    if transform_fn:
                        record = transform_fn(record)

                    # 边读边写，不累积到内存
                    first_record = _write_json_array_record(out_f, record, first_record)

            out_f.write('\n]')

        # 3. 原子替换（tmp → 原文件）
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
