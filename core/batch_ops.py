"""
GPC Dataset Manager - 批量操作核心逻辑

提供批量字段替换与按索引筛选批量删除的 dry-run 预览与执行辅助函数。
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_refer_input_json, get_refer_json
from core.json_io import filter_rewrite
from core.writer import build_updated_meta, transform_record_fields


NAME_MATCH_NONE = 'none'
NAME_MATCH_EXACT = 'exact'
NAME_MATCH_SUBSTR = 'substr'
PHRASE_MATCH_NONE = 'none'
PHRASE_MATCH_SUBSTR = 'substr'

NAME_EXACT = 'name_exact'
NAME_SUBSTR = 'name_substr'
DELETE_BY_NAME = 'delete_by_name'
DELETE_BY_DATA_SOURCE = 'delete_by_data_source'
SUPPORTED_REPLACE_TYPES = {NAME_EXACT, NAME_SUBSTR}
SUPPORTED_DELETE_FILTERS = {DELETE_BY_NAME, DELETE_BY_DATA_SOURCE}


def build_new_name(old_name: str, replace_type: str, find_value: str, replace_value: str) -> Optional[str]:
    if replace_type == NAME_EXACT:
        if old_name == find_value:
            return replace_value
        return None

    if replace_type == NAME_SUBSTR:
        if find_value in old_name:
            return old_name.replace(find_value, replace_value)
        return None

    raise ValueError(f'不支持的替换类型: {replace_type}')


def find_batch_targets(
    index,
    replace_type: str,
    find_value: str,
    replace_value: str,
    split_filter: str | None = None,
    name_filter: str | None = None,
) -> list[dict]:
    """dry-run 查找批量替换目标。"""
    if replace_type not in SUPPORTED_REPLACE_TYPES:
        raise ValueError(f'不支持的替换类型: {replace_type}')

    find_value = find_value.strip()
    replace_value = replace_value.strip()
    name_filter = name_filter.strip() if name_filter else None

    if not find_value:
        return []

    targets = []
    for task_id, meta in index.main.items():
        split = meta.get('split', '')
        if split_filter and split != split_filter:
            continue

        old_name = str(meta.get('name', '') or '')
        if name_filter and old_name != name_filter:
            continue

        new_name = build_new_name(old_name, replace_type, find_value, replace_value)
        if new_name is None or new_name == old_name:
            continue

        targets.append({
            'task_id': task_id,
            'split': split,
            'image_id': str(meta.get('image_id', '') or ''),
            'old': old_name,
            'new': new_name,
            'old_phrase': str(meta.get('phrase', '') or ''),
            'replace_type': replace_type,
        })

    return targets


def filter_batch_targets(index, filters: dict) -> list[dict]:
    """按组合条件从索引中过滤批量操作目标。所有已填写条件按 AND 生效。"""
    split_filter = filters.get('split') or None
    name_mode = filters.get('name_match_mode', NAME_MATCH_NONE)
    name_value = str(filters.get('name_value', '') or '').strip()
    data_source = str(filters.get('data_source', '') or '').strip()
    phrase_mode = filters.get('phrase_match_mode', PHRASE_MATCH_NONE)
    phrase_value = str(filters.get('phrase_value', '') or '').strip()

    targets = []
    for task_id, meta in index.main.items():
        split = str(meta.get('split', '') or '')
        name = str(meta.get('name', '') or '')
        phrase = str(meta.get('phrase', '') or '')
        source = str(meta.get('data_source', '') or '')

        if split_filter and split != split_filter:
            continue

        if name_mode == NAME_MATCH_EXACT and name_value and name != name_value:
            continue
        if name_mode == NAME_MATCH_SUBSTR and name_value and name_value not in name:
            continue

        if data_source and source != data_source:
            continue

        if phrase_mode == PHRASE_MATCH_SUBSTR and phrase_value and phrase_value.lower() not in phrase.lower():
            continue

        targets.append({
            'task_id': task_id,
            'split': split,
            'image_id': str(meta.get('image_id', '') or ''),
            'name': name,
            'phrase': phrase,
            'data_source': source,
        })

    return targets


def build_replace_targets(
    filtered_targets: list[dict],
    replace_type: str,
    find_value: str,
    replace_value: str,
) -> list[dict]:
    """基于已筛选目标集合，构建真正会发生修改的批量替换目标。"""
    if replace_type not in SUPPORTED_REPLACE_TYPES:
        raise ValueError(f'不支持的替换类型: {replace_type}')

    find_value = find_value.strip()
    replace_value = replace_value.strip()
    if not find_value:
        return []

    targets = []
    for meta in filtered_targets:
        old_name = str(meta.get('name', '') or '')
        new_name = build_new_name(old_name, replace_type, find_value, replace_value)
        if new_name is None or new_name == old_name:
            continue
        targets.append({
            'task_id': meta['task_id'],
            'split': meta['split'],
            'image_id': meta['image_id'],
            'old': old_name,
            'new': new_name,
            'old_phrase': str(meta.get('phrase', '') or ''),
            'replace_type': replace_type,
            'data_source': str(meta.get('data_source', '') or ''),
        })
    return targets


def build_delete_targets(filtered_targets: list[dict]) -> list[dict]:
    """基于已筛选目标集合，构建批量删除目标。"""
    return [dict(item) for item in filtered_targets]


def find_delete_targets(
    index,
    filter_type: str,
    filter_value: str,
    split_filter: str | None = None,
) -> list[dict]:
    """dry-run 查找批量删除目标。"""
    if filter_type not in SUPPORTED_DELETE_FILTERS:
        raise ValueError(f'不支持的删除筛选类型: {filter_type}')

    filter_value = filter_value.strip()
    if not filter_value:
        return []

    targets = []
    for task_id, meta in index.main.items():
        split = meta.get('split', '')
        if split_filter and split != split_filter:
            continue

        matched = False
        if filter_type == DELETE_BY_NAME:
            matched = str(meta.get('name', '') or '') == filter_value
        elif filter_type == DELETE_BY_DATA_SOURCE:
            matched = str(meta.get('data_source', '') or '') == filter_value

        if not matched:
            continue

        targets.append({
            'task_id': task_id,
            'split': split,
            'image_id': str(meta.get('image_id', '') or ''),
            'name': str(meta.get('name', '') or ''),
            'phrase': str(meta.get('phrase', '') or ''),
            'data_source': str(meta.get('data_source', '') or ''),
        })

    return targets


def group_targets_by_split(targets: list[dict]) -> dict[str, dict[str, dict]]:
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for target in targets:
        grouped[target['split']][target['task_id']] = target
    return dict(grouped)


def apply_batch_replace(
    targets: list[dict],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """执行批量 name 替换，按 split 分组重写 refer 与 refer_input。"""
    grouped = group_targets_by_split(targets)
    total = len(targets)
    current = 0
    updated_meta: dict[str, dict] = {}
    failed = []

    for split, split_targets in grouped.items():
        def transform_refer_record(rec):
            nonlocal current
            task_id = rec.get('task_id')
            if task_id not in split_targets:
                return rec

            target = split_targets[task_id]
            try:
                transform_record_fields(rec, {'name': target['new']}, include_geometry=True)
                updated_meta[task_id] = build_updated_meta(rec, split)
                current += 1
                if progress_cb:
                    progress_cb(current, total, task_id)
                return rec
            except Exception as e:
                failed.append(f"{task_id}: {e}")
                return rec

        refer_ok = filter_rewrite(
            get_refer_json(split),
            keep_fn=lambda rec: True,
            transform_fn=transform_refer_record
        )
        if not refer_ok:
            failed.append(f'{split}: 更新 refer 文件失败')
            continue

        def transform_input_record(rec):
            task_id = rec.get('task_id')
            if task_id not in split_targets:
                return rec
            target = split_targets[task_id]
            transform_record_fields(rec, {'name': target['new']}, include_geometry=False)
            return rec

        input_ok = filter_rewrite(
            get_refer_input_json(split),
            keep_fn=lambda rec: True,
            transform_fn=transform_input_record
        )
        if not input_ok:
            failed.append(f'{split}: 更新 refer_input 文件失败')

    return {
        'success': len(failed) == 0,
        'success_count': len(updated_meta),
        'failed': failed,
        'updated_meta': updated_meta,
    }
