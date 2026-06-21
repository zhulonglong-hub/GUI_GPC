"""
GPC Dataset Manager - 健康检查修复模块

基于健康检查结果生成 dry-run 修复计划，并执行受控的数据修复。
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RECYCLE_DIR, SPLITS, get_image_data_split_json, get_refer_input_json, get_refer_json
from core.image_utils import resolve_image_path
from core.json_io import append_record_streaming, filter_rewrite, stream_records
from core.writer import build_updated_meta


def _now_tag() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def _write_recycle_json(name: str, records: list[dict]) -> str | None:
    if not records:
        return None

    path = RECYCLE_DIR / f"{name}_{_now_tag()}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return str(path)


def build_missing_image_repair_plan(issues: list[dict], index) -> dict:
    task_ids = set()
    items = []

    for issue in issues:
        if issue.get('issue_type') != 'missing_image':
            continue
        task_id = issue.get('task_id')
        meta = index.get_meta(task_id) if task_id else None
        if not meta:
            continue

        task_ids.add(task_id)
        items.append({
            'task_id': task_id,
            'split': meta.get('split', ''),
            'image_id': str(meta.get('image_id', '') or ''),
            'phrase': str(meta.get('phrase', '') or ''),
        })

    image_ids_to_check = {item['image_id'] for item in items if item['image_id']}
    image_data_remove = []
    for image_id in sorted(image_ids_to_check):
        remaining = [tid for tid in index.by_image.get(image_id, []) if tid not in task_ids]
        if not remaining:
            image_data_remove.append(image_id)

    return {
        'action': 'missing_image',
        'items': items,
        'task_ids': sorted(task_ids),
        'image_data_remove': image_data_remove,
        'summary': f"将删除 {len(task_ids)} 条缺失图片对应的 task 记录",
    }


def apply_missing_image_repair(plan: dict, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> dict:
    task_ids = set(plan.get('task_ids', []))
    image_data_remove = set(plan.get('image_data_remove', []))
    total = len(SPLITS) * 2 + (1 if image_data_remove else 0)
    current = 0
    failed = []
    deleted_records = []

    if not task_ids:
        return {'success': True, 'deleted_task_ids': [], 'failed': [], 'backup_path': None}

    for split in SPLITS:
        split_deleted = []

        def keep_refer(rec):
            task_id = rec.get('task_id')
            if task_id in task_ids:
                split_deleted.append(rec)
                return False
            return True

        if not filter_rewrite(get_refer_json(split), keep_fn=keep_refer):
            failed.append(f'{split}: 删除 refer 记录失败')
        deleted_records.extend(split_deleted)
        current += 1
        if progress_cb:
            progress_cb(current, total, f'删除 {split} refer 记录')

        if not filter_rewrite(get_refer_input_json(split), keep_fn=lambda rec: rec.get('task_id') not in task_ids):
            failed.append(f'{split}: 删除 refer_input 记录失败')
        current += 1
        if progress_cb:
            progress_cb(current, total, f'删除 {split} refer_input 记录')

    backup_path = _write_recycle_json('missing_image_deleted_tasks', deleted_records)

    if image_data_remove:
        if not filter_rewrite(
            get_image_data_split_json(),
            keep_fn=lambda rec: str(rec.get('image_id', '') or '') not in image_data_remove,
        ):
            failed.append('删除 image_data_split.json 条目失败')
        current += 1
        if progress_cb:
            progress_cb(current, total, '更新 image_data_split.json')

    return {
        'success': len(failed) == 0,
        'deleted_task_ids': sorted(task_ids),
        'image_data_removed': sorted(image_data_remove),
        'failed': failed,
        'backup_path': backup_path,
    }


def build_orphan_image_repair_plan(issues: list[dict]) -> dict:
    items = []
    seen = set()

    for issue in issues:
        if issue.get('issue_type') != 'orphan_image':
            continue
        image_id = str(issue.get('image_id', '') or '')
        if not image_id or image_id in seen:
            continue
        seen.add(image_id)
        image_path = resolve_image_path(image_id)
        if image_path and image_path.exists():
            items.append({
                'image_id': image_id,
                'path': str(image_path),
                'filename': image_path.name,
            })

    return {
        'action': 'orphan_image',
        'items': items,
        'summary': f"将移动 {len(items)} 张孤儿图片到回收目录",
    }


def apply_orphan_image_repair(plan: dict, index, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> dict:
    items = plan.get('items', [])
    recycle_dir = RECYCLE_DIR / 'orphan_images' / _now_tag()
    recycle_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    failed = []
    total = len(items)

    for current, item in enumerate(items, 1):
        image_id = item.get('image_id', '')
        if image_id in index.by_image:
            failed.append(f'{image_id}: 当前索引中已有引用，跳过')
            continue

        src = Path(item.get('path', ''))
        if not src.exists():
            failed.append(f'{image_id}: 图片文件不存在，跳过')
            continue

        dest = recycle_dir / src.name
        if dest.exists():
            dest = recycle_dir / f'{src.stem}_{current}{src.suffix}'

        try:
            shutil.move(str(src), str(dest))
            moved.append({'image_id': image_id, 'from': str(src), 'to': str(dest)})
        except Exception as e:
            failed.append(f'{image_id}: {e}')

        if progress_cb:
            progress_cb(current, total, f'移动孤儿图片: {image_id}')

    return {
        'success': len(failed) == 0,
        'moved': moved,
        'failed': failed,
        'recycle_dir': str(recycle_dir),
    }


def build_refer_mismatch_repair_plan(issues: list[dict]) -> dict:
    refer_only = []
    input_only = []

    for issue in issues:
        if issue.get('issue_type') != 'refer_mismatch':
            continue
        item = {
            'task_id': issue.get('task_id', ''),
            'split': issue.get('split', ''),
            'message': issue.get('message', ''),
        }
        message = issue.get('message', '')
        if '仅存在于 refer_input' in message:
            input_only.append(item)
        elif '仅存在于 refer' in message:
            refer_only.append(item)

    return {
        'action': 'refer_mismatch',
        'refer_only': refer_only,
        'input_only': input_only,
        'summary': f"可重建 refer_input {len(refer_only)} 条；可删除孤立 refer_input {len(input_only)} 条",
    }


def _build_refer_input_record(record: dict) -> dict:
    return {
        'task_id': record.get('task_id'),
        'image_id': record.get('image_id'),
        'phrase': record.get('phrase', ''),
        'phrase_structure': record.get('phrase_structure', {}) or {},
    }


def apply_refer_mismatch_repair(plan: dict, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> dict:
    refer_only_by_split: dict[str, set[str]] = {}
    input_only_by_split: dict[str, set[str]] = {}

    for item in plan.get('refer_only', []):
        refer_only_by_split.setdefault(item.get('split', ''), set()).add(item.get('task_id'))
    for item in plan.get('input_only', []):
        input_only_by_split.setdefault(item.get('split', ''), set()).add(item.get('task_id'))

    total = len(refer_only_by_split) + len(input_only_by_split)
    current = 0
    rebuilt_meta = {}
    deleted_task_ids = []
    failed = []

    for split, task_ids in refer_only_by_split.items():
        existing_input_ids = {str(rec.get('task_id')) for rec in stream_records(get_refer_input_json(split)) if rec.get('task_id')}
        found = {}
        for rec in stream_records(get_refer_json(split)):
            task_id = rec.get('task_id')
            if task_id in task_ids:
                found[task_id] = rec

        for task_id in sorted(task_ids):
            record = found.get(task_id)
            if not record:
                failed.append(f'{task_id}: refer 记录不存在，无法重建')
                continue
            if task_id in existing_input_ids:
                continue
            input_record = _build_refer_input_record(record)
            if append_record_streaming(get_refer_input_json(split), input_record):
                rebuilt_meta[task_id] = build_updated_meta(input_record, split)
            else:
                failed.append(f'{task_id}: 追加 refer_input 失败')

        current += 1
        if progress_cb:
            progress_cb(current, total, f'重建 {split} refer_input')

    for split, task_ids in input_only_by_split.items():
        deleted_task_ids.extend(sorted(task_ids))
        if not filter_rewrite(get_refer_input_json(split), keep_fn=lambda rec, ids=task_ids: rec.get('task_id') not in ids):
            failed.append(f'{split}: 删除孤立 refer_input 记录失败')

        current += 1
        if progress_cb:
            progress_cb(current, total, f'删除 {split} 孤立 refer_input')

    return {
        'success': len(failed) == 0,
        'rebuilt_meta': rebuilt_meta,
        'deleted_task_ids': deleted_task_ids,
        'failed': failed,
    }
