"""
GPC Dataset Manager - 写操作模块

实现增/删/改原子写操作,维护四文件一致性
"""

import sys
import json
from pathlib import Path
from typing import Dict, Optional, List, Callable
from datetime import datetime
from PIL import Image
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (IMAGES_DIR, get_refer_json, get_refer_input_json,
                   get_image_data_split_json, get_name_count_json,
                   LOG_DIR, RECYCLE_DIR)
from core.json_io import append_record_streaming, filter_rewrite, patch_fields_rewrite, stream_records
from core.polygon_utils import polygon_to_bbox


def _write_result(success: bool, message: str, **extra) -> dict:
    result = {'success': success, 'message': message}
    result.update(extra)
    return result


def _refresh_image_data_entry(image_id: str, split: str, width: int, height: int) -> bool:
    image_data_path = get_image_data_split_json()
    exists = False

    for rec in stream_records(image_data_path):
        if rec.get('image_id') == image_id:
            exists = True
            break

    if exists:
        return True

    return append_record_streaming(image_data_path, {
        "image_id": image_id,
        "width": width,
        "height": height,
        "split": split,
        "coco_id": None,
        "flickr_id": None,
        "url": None,
        "refvg_version": None
    })


def _log_operation(op_type: str, task_id: str, details: dict = None) -> None:
    """记录操作日志到 operations.jsonl"""
    log_file = LOG_DIR / "operations.jsonl"
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'operation': op_type,
        'task_id': task_id,
        'details': details or {}
    }
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def _build_phrase(attributes: List[str], name: str, relations: List[str]) -> str:
    """构建 phrase 字符串

    注意: attributes / relations 元素可能是嵌套 list（数据集制作遗留问题），
    统一打平为 str，避免 join 时报 'expected str instance, list found'。
    """
    def _flatten(seq) -> List[str]:
        result = []
        for item in (seq or []):
            if isinstance(item, list):
                result.extend(str(x) for x in item)
            else:
                result.append(str(item))
        return result

    parts = _flatten(attributes)
    parts.append(str(name))
    parts.extend(_flatten(relations))
    return ' '.join(parts)


def transform_record_fields(rec: dict, field_updates: dict, include_geometry: bool = False) -> dict:
    phrase_structure = rec.setdefault('phrase_structure', {})
    current_name = phrase_structure.get('name', '')
    current_attributes = phrase_structure.get('attributes', []) or []
    current_relations = phrase_structure.get('relation_descriptions', []) or []

    final_name = field_updates.get('name', current_name)
    final_attributes = field_updates.get('attributes', current_attributes)
    final_relations = field_updates.get('relations', current_relations)
    normalized_updates = dict(field_updates)

    if 'phrase' not in normalized_updates and any(
        key in normalized_updates for key in ('name', 'attributes', 'relations')
    ):
        normalized_updates['phrase'] = _build_phrase(final_attributes, final_name, final_relations)

    if 'phrase' in normalized_updates:
        rec['phrase'] = normalized_updates['phrase']
    if 'name' in normalized_updates:
        phrase_structure['name'] = normalized_updates['name']
    if 'attributes' in normalized_updates:
        phrase_structure['attributes'] = normalized_updates['attributes']
    if 'relations' in normalized_updates:
        phrase_structure['relation_descriptions'] = normalized_updates['relations']

    if include_geometry:
        if 'Polygons' in normalized_updates:
            rec['Polygons'] = normalized_updates['Polygons']
        if 'instance_boxes' in normalized_updates:
            rec['instance_boxes'] = normalized_updates['instance_boxes']

    return rec


def build_updated_meta(record: dict, split: str) -> dict:
    phrase_structure = record.get('phrase_structure', {})
    return {
        'task_id': record.get('task_id'),
        'image_id': str(record.get('image_id', '')),
        'split': split,
        'name': phrase_structure.get('name', ''),
        'attributes': phrase_structure.get('attributes', []) or [],
        'phrase': record.get('phrase', ''),
        'data_source': str(record.get('data_source', '') or ''),
        'mask_path': str(record.get('mask_path', '') or ''),
    }


def _next_seq_id() -> str:
    """生成下一个序列号"""
    return datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]


def add_record(img_src_path: Path,
               polygons: List,
               name: str,
               attributes: List[str],
               relations: List[str],
               split: str,
               dry_run: bool = False) -> dict:
    """
    新增样本记录
    """
    task_id = f"{_next_seq_id()}_{split[:2]}"
    image_id = img_src_path.stem

    if dry_run:
        return _write_result(True, '预览模式', task_id=task_id)

    with Image.open(img_src_path) as img:
        width, height = img.size

    phrase = _build_phrase(attributes, name, relations)
    instance_boxes = [polygon_to_bbox(polygons)]

    refer_record = {
        "task_id": task_id,
        "image_id": image_id,
        "phrase": phrase,
        "phrase_structure": {
            "name": name,
            "attributes": attributes,
            "type": "attribute",
            "relation_descriptions": relations,
            "relation_ids": []
        },
        "ann_ids": [int(datetime.now().timestamp() * 1000) % 1000000],
        "instance_boxes": instance_boxes,
        "Polygons": polygons
    }

    refer_input_record = {
        "task_id": task_id,
        "image_id": image_id,
        "phrase": phrase,
        "phrase_structure": {
            "name": name,
            "attributes": attributes,
            "relation_descriptions": relations
        }
    }

    dest_img_path = IMAGES_DIR / img_src_path.name
    if not dest_img_path.exists():
        shutil.copy2(img_src_path, dest_img_path)

    if not append_record_streaming(get_refer_json(split), refer_record):
        return _write_result(False, '追加 refer 文件失败')

    if not append_record_streaming(get_refer_input_json(split), refer_input_record):
        return _write_result(False, '追加 refer_input 文件失败')

    if not _refresh_image_data_entry(image_id, split, width, height):
        return _write_result(False, '更新 image_data_split.json 失败')

    _log_operation('add', task_id, {
        'image_id': image_id,
        'split': split,
        'name': name
    })

    return _write_result(True, f'成功新增记录: {task_id}', task_id=task_id, updated_meta={
        'task_id': task_id,
        'image_id': image_id,
        'split': split,
        'name': name,
        'attributes': attributes,
        'phrase': phrase
    })


def delete_record(task_id: str,
                 split: str,
                 delete_image_file: bool = False,
                 dry_run: bool = False) -> dict:
    """
    删除样本记录
    """
    result = {
        'success': False,
        'task_id': task_id,
        'backup_path': None,
        'message': ''
    }

    if dry_run:
        result['message'] = '预览模式,不执行实际删除'
        return result

    refer_path = get_refer_json(split)
    refer_input_path = get_refer_input_json(split)

    target_record = None
    for record in stream_records(refer_path):
        if record.get('task_id') == task_id:
            target_record = record
            break

    if not target_record:
        result['message'] = f'未找到记录: {task_id}'
        return result

    backup_path = RECYCLE_DIR / f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(target_record, f, ensure_ascii=False, indent=2)
    result['backup_path'] = str(backup_path)

    refer_ok = filter_rewrite(
        refer_path,
        keep_fn=lambda rec: rec.get('task_id') != task_id
    )
    if not refer_ok:
        result['message'] = f'删除 refer 文件失败: {refer_path.name}'
        return result

    refer_input_ok = filter_rewrite(
        refer_input_path,
        keep_fn=lambda rec: rec.get('task_id') != task_id
    )
    if not refer_input_ok:
        result['message'] = f'删除 refer_input 文件失败: {refer_input_path.name}'
        return result

    image_id = target_record.get('image_id')
    has_other_tasks = False
    from config import SPLITS
    for s in SPLITS:
        for rec in stream_records(get_refer_input_json(s)):
            if rec.get('image_id') == image_id and rec.get('task_id') != task_id:
                has_other_tasks = True
                break
        if has_other_tasks:
            break

    if not has_other_tasks:
        image_data_ok = filter_rewrite(
            get_image_data_split_json(),
            keep_fn=lambda rec: rec.get('image_id') != image_id
        )
        if not image_data_ok:
            result['message'] = '删除 image_data_split.json 条目失败'
            return result

        if delete_image_file:
            from core.image_utils import resolve_image_path
            img_path = resolve_image_path(image_id)
            if img_path and img_path.exists():
                img_path.unlink()

    _log_operation('delete', task_id, {
        'split': split,
        'backup': str(backup_path)
    })

    result['success'] = True
    result['message'] = f'已删除 task_id: {task_id}'
    result['deleted_image_id'] = image_id
    return result


def update_fields(task_id: str,
                 split: str,
                 field_updates: dict,
                 dry_run: bool = False) -> dict:
    """
    更新记录字段，保证 refer 与 refer_input 的字段一致性。

    Args:
        task_id: 任务ID
        split: 数据集划分
        field_updates: 要更新的字段字典,如 {'phrase': 'new phrase'}
        dry_run: 是否仅预览

    Returns:
        操作结果
    """
    result = {
        'success': False,
        'task_id': task_id,
        'updated_fields': [],
        'message': '',
        'updated_meta': None
    }

    if dry_run:
        result['message'] = '预览模式'
        return result

    refer_path = get_refer_json(split)
    refer_input_path = get_refer_input_json(split)
    target_record = None

    for record in stream_records(refer_path):
        if record.get('task_id') == task_id:
            target_record = record
            break

    if not target_record:
        result['message'] = f'未找到记录: {task_id}'
        return result

    phrase_struct = target_record.get('phrase_structure', {})
    current_name = phrase_struct.get('name', '')
    current_attributes = phrase_struct.get('attributes', []) or []
    current_relations = phrase_struct.get('relation_descriptions', []) or []

    normalized_updates = dict(field_updates)
    final_name = normalized_updates.get('name', current_name)
    final_attributes = normalized_updates.get('attributes', current_attributes)
    final_relations = normalized_updates.get('relations', current_relations)

    if 'phrase' not in normalized_updates and any(
        key in normalized_updates for key in ('name', 'attributes', 'relations')
    ):
        normalized_updates['phrase'] = _build_phrase(final_attributes, final_name, final_relations)

    def transform_refer_record(rec):
        if rec.get('task_id') != task_id:
            return rec
        return transform_record_fields(rec, normalized_updates, include_geometry=True)

    def transform_refer_input_record(rec):
        if rec.get('task_id') != task_id:
            return rec
        return transform_record_fields(rec, normalized_updates, include_geometry=False)

    refer_ok = patch_fields_rewrite(
        refer_path,
        task_id,
        normalized_updates,
        fallback_transform_fn=transform_refer_record
    )
    if not refer_ok:
        result['message'] = f'更新 refer 文件失败: {refer_path.name}'
        return result

    refer_input_ok = filter_rewrite(
        refer_input_path,
        keep_fn=lambda rec: True,
        transform_fn=transform_refer_input_record
    )
    if not refer_input_ok:
        result['message'] = f'更新 refer_input 文件失败: {refer_input_path.name}'
        return result

    updated_fields = list(normalized_updates.keys())
    updated_meta = {
        'task_id': task_id,
        'image_id': str(target_record.get('image_id', '')),
        'split': split,
        'name': final_name,
        'attributes': final_attributes,
        'phrase': normalized_updates.get('phrase', target_record.get('phrase', ''))
    }

    _log_operation('update', task_id, {'fields': updated_fields})

    result['success'] = True
    result['updated_fields'] = updated_fields
    result['updated_meta'] = updated_meta
    result['message'] = f'已更新 {len(updated_fields)} 个字段'
    return result
