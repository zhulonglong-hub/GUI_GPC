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
from core.json_io import append_record, filter_rewrite, stream_records
from core.polygon_utils import polygon_to_bbox


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
    """构建 phrase 字符串"""
    parts = []
    if attributes:
        parts.extend(attributes)
    parts.append(name)
    if relations:
        parts.extend(relations)
    return ' '.join(parts)


def _next_seq_id() -> str:
    """生成下一个序列号"""
    return datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]


def add_record(img_src_path: Path,
               polygons: List,
               name: str,
               attributes: List[str],
               relations: List[str],
               split: str,
               dry_run: bool = False) -> str:
    """
    新增样本记录
    
    Args:
        img_src_path: 源图像文件路径
        polygons: 多边形数据 [[[[x,y], ...]]]
        name: 地物类别名
        attributes: 属性列表
        relations: 关系描述列表
        split: 数据集划分 (train/val/test)
        dry_run: 是否仅预览不执行
    
    Returns:
        生成的 task_id
    """
    # 生成 task_id 和 image_id
    task_id = f"{_next_seq_id()}_{split[:2]}"
    image_id = img_src_path.stem
    
    if dry_run:
        return task_id
    
    # 获取图像尺寸
    with Image.open(img_src_path) as img:
        width, height = img.size
    
    # 构建 phrase
    phrase = _build_phrase(attributes, name, relations)
    
    # 计算 instance_boxes
    instance_boxes = [polygon_to_bbox(polygons)]
    
    # 构建 refer 记录
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
    
    # 构建 refer_input 记录
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
    
    # 构建 image_data 记录
    image_data_record = {
        "image_id": image_id,
        "width": width,
        "height": height,
        "split": split,
        "coco_id": None,
        "flickr_id": None,
        "url": None,
        "refvg_version": None
    }
    
    # 联动写操作
    # 1. 复制图像文件
    dest_img_path = IMAGES_DIR / img_src_path.name
    if not dest_img_path.exists():
        shutil.copy2(img_src_path, dest_img_path)
    
    # 2. 追加到 refer_{split}.json
    append_record(get_refer_json(split), refer_record)
    
    # 3. 追加到 refer_input_{split}.json
    append_record(get_refer_input_json(split), refer_input_record)
    
    # 4. 追加到 image_data_split.json (检查是否已存在该image_id)
    image_data_path = get_image_data_split_json()
    existing_images = set()
    for rec in stream_records(image_data_path):
        existing_images.add(rec.get('image_id'))
    
    if image_id not in existing_images:
        append_record(image_data_path, image_data_record)
    
    # 5. 记录日志
    _log_operation('add', task_id, {
        'image_id': image_id,
        'split': split,
        'name': name
    })

    return task_id


def delete_record(task_id: str,
                 split: str,
                 delete_image_file: bool = False,
                 dry_run: bool = False) -> dict:
    """
    删除样本记录

    Args:
        task_id: 要删除的任务ID
        split: 数据集划分
        delete_image_file: 是否删除图像文件(仅当该图无其他标注时)
        dry_run: 是否仅预览不执行

    Returns:
        操作结果摘要
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

    # 1. 备份完整记录
    backup_path = RECYCLE_DIR / f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # 从 refer_{split}.json 中读取完整记录
    target_record = None
    for record in stream_records(get_refer_json(split)):
        if record.get('task_id') == task_id:
            target_record = record
            break

    if target_record:
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(target_record, f, ensure_ascii=False, indent=2)
        result['backup_path'] = str(backup_path)

    # 2. 从 refer_{split}.json 删除
    filter_rewrite(
        get_refer_json(split),
        keep_fn=lambda rec: rec.get('task_id') != task_id
    )

    # 3. 从 refer_input_{split}.json 删除
    filter_rewrite(
        get_refer_input_json(split),
        keep_fn=lambda rec: rec.get('task_id') != task_id
    )

    # 4. 检查 image_id 是否还有其他 task_id
    if target_record:
        image_id = target_record.get('image_id')

        # 检查所有split中是否还有该image_id的其他记录
        has_other_tasks = False
        from config import SPLITS
        for s in SPLITS:
            for rec in stream_records(get_refer_input_json(s)):
                if rec.get('image_id') == image_id and rec.get('task_id') != task_id:
                    has_other_tasks = True
                    break
            if has_other_tasks:
                break

        # 如果没有其他任务,删除 image_data_split.json 中的条目
        if not has_other_tasks:
            filter_rewrite(
                get_image_data_split_json(),
                keep_fn=lambda rec: rec.get('image_id') != image_id
            )

            # 如果用户确认,删除图像文件
            if delete_image_file:
                from core.image_utils import resolve_image_path
                img_path = resolve_image_path(image_id)
                if img_path and img_path.exists():
                    img_path.unlink()

    # 5. 记录日志
    _log_operation('delete', task_id, {
        'split': split,
        'backup': str(backup_path)
    })

    result['success'] = True
    result['message'] = f'已删除 task_id: {task_id}'
    return result


def update_fields(task_id: str,
                 split: str,
                 field_updates: dict,
                 dry_run: bool = False) -> dict:
    """
    更新记录字段

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
        'message': ''
    }

    if dry_run:
        result['message'] = '预览模式'
        return result

    # 更新 refer_{split}.json
    def transform_fn(rec):
        if rec.get('task_id') == task_id:
            for field, value in field_updates.items():
                if field == 'phrase':
                    rec['phrase'] = value
                elif field == 'name':
                    rec['phrase_structure']['name'] = value
                elif field == 'attributes':
                    rec['phrase_structure']['attributes'] = value
            result['updated_fields'] = list(field_updates.keys())
        return rec

    filter_rewrite(
        get_refer_json(split),
        keep_fn=lambda rec: True,
        transform_fn=transform_fn
    )

    # 更新 refer_input_{split}.json
    filter_rewrite(
        get_refer_input_json(split),
        keep_fn=lambda rec: True,
        transform_fn=transform_fn
    )

    _log_operation('update', task_id, {'fields': list(field_updates.keys())})

    result['success'] = True
    result['message'] = f'已更新 {len(field_updates)} 个字段'
    return result
