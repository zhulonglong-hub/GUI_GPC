"""
GPC Dataset Manager - 数据集健康检查模块

提供只读的数据集健康扫描能力，优先覆盖图片缺失、孤儿图片、
refer/refer_input 不一致、关键字段空值等高价值问题。
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import IMAGES_DIR, SPLITS, get_refer_input_json, get_refer_json
from core.dataset_index import DatasetIndex
from core.image_utils import resolve_image_path
from core.json_io import stream_records


def check_missing_images(index: DatasetIndex) -> list[dict]:
    """检查索引中的记录是否缺少对应图片文件。"""
    issues = []

    for task_id, meta in index.main.items():
        image_id = str(meta.get('image_id', '') or '')
        if not image_id:
            issues.append({
                'task_id': task_id,
                'split': meta.get('split', ''),
                'image_id': image_id,
                'issue_type': 'missing_image',
                'message': 'image_id 为空'
            })
            continue

        image_path = resolve_image_path(image_id)
        if image_path is None:
            issues.append({
                'task_id': task_id,
                'split': meta.get('split', ''),
                'image_id': image_id,
                'issue_type': 'missing_image',
                'message': f'对应图片不存在: {image_id}'
            })

    return issues


def check_orphan_images(index: DatasetIndex) -> list[dict]:
    """检查图片目录中存在但未被任何记录引用的孤儿图片。"""
    referenced = {str(image_id) for image_id in index.by_image.keys() if str(image_id)}
    issues = []

    if not IMAGES_DIR.exists():
        return issues

    for image_path in IMAGES_DIR.iterdir():
        if not image_path.is_file():
            continue

        image_id = image_path.stem
        if image_id not in referenced:
            issues.append({
                'task_id': '',
                'split': '',
                'image_id': image_id,
                'issue_type': 'orphan_image',
                'message': f'图片未被任何记录引用: {image_path.name}'
            })

    return issues


def check_refer_consistency(split: str) -> list[dict]:
    """检查 refer 与 refer_input 中 task_id 是否一致。"""
    refer_task_ids = set()
    refer_input_task_ids = set()

    for record in stream_records(get_refer_json(split)):
        task_id = record.get('task_id')
        if task_id:
            refer_task_ids.add(str(task_id))

    for record in stream_records(get_refer_input_json(split)):
        task_id = record.get('task_id')
        if task_id:
            refer_input_task_ids.add(str(task_id))

    issues = []

    for task_id in sorted(refer_task_ids - refer_input_task_ids):
        issues.append({
            'task_id': task_id,
            'split': split,
            'image_id': '',
            'issue_type': 'refer_mismatch',
            'message': '仅存在于 refer 文件'
        })

    for task_id in sorted(refer_input_task_ids - refer_task_ids):
        issues.append({
            'task_id': task_id,
            'split': split,
            'image_id': '',
            'issue_type': 'refer_mismatch',
            'message': '仅存在于 refer_input 文件'
        })

    return issues


def check_empty_fields(index: DatasetIndex) -> list[dict]:
    """检查关键字段是否为空。"""
    issues = []

    for task_id, meta in index.main.items():
        phrase = str(meta.get('phrase', '') or '').strip()
        name = str(meta.get('name', '') or '').strip()

        if not phrase:
            issues.append({
                'task_id': task_id,
                'split': meta.get('split', ''),
                'image_id': str(meta.get('image_id', '') or ''),
                'issue_type': 'empty_field',
                'message': 'phrase 为空'
            })

        if not name:
            issues.append({
                'task_id': task_id,
                'split': meta.get('split', ''),
                'image_id': str(meta.get('image_id', '') or ''),
                'issue_type': 'empty_field',
                'message': 'phrase_structure.name 为空'
            })

    return issues


def summarize_issues(issues: list[dict]) -> dict[str, int]:
    """按 issue_type 汇总数量。"""
    summary: dict[str, int] = defaultdict(int)
    for issue in issues:
        summary[issue.get('issue_type', 'unknown')] += 1
    return dict(summary)


def run_health_checks(
    index: DatasetIndex,
    selected_checks: Optional[dict[str, bool]] = None,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> dict:
    """
    执行健康检查并返回聚合结果。

    selected_checks keys:
    - missing_images
    - orphan_images
    - refer_consistency
    - empty_fields
    """
    checks = {
        'missing_images': True,
        'orphan_images': True,
        'refer_consistency': True,
        'empty_fields': True,
    }
    if selected_checks:
        checks.update(selected_checks)

    total_steps = 0
    if checks.get('missing_images'):
        total_steps += 1
    if checks.get('orphan_images'):
        total_steps += 1
    if checks.get('refer_consistency'):
        total_steps += len(SPLITS)
    if checks.get('empty_fields'):
        total_steps += 1
    current_step = 0

    def advance(label: str):
        nonlocal current_step
        current_step += 1
        if progress_cb:
            progress_cb(label, current_step, total_steps)

    results = {
        'issues': [],
        'by_check': {},
        'summary': {},
    }

    if checks.get('missing_images'):
        issues = check_missing_images(index)
        results['by_check']['missing_images'] = issues
        results['issues'].extend(issues)
        advance('检查图片缺失')

    if checks.get('orphan_images'):
        issues = check_orphan_images(index)
        results['by_check']['orphan_images'] = issues
        results['issues'].extend(issues)
        advance('检查孤儿图片')

    if checks.get('refer_consistency'):
        all_issues = []
        for split in SPLITS:
            split_issues = check_refer_consistency(split)
            all_issues.extend(split_issues)
            advance(f'检查 {split} refer 一致性')
        results['by_check']['refer_consistency'] = all_issues
        results['issues'].extend(all_issues)

    if checks.get('empty_fields'):
        issues = check_empty_fields(index)
        results['by_check']['empty_fields'] = issues
        results['issues'].extend(issues)
        advance('检查关键字段空值')

    results['summary'] = summarize_issues(results['issues'])
    return results
