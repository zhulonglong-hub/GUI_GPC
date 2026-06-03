"""
GPC Dataset Manager - 数据验证模块

导入前数据合法性校验
"""

import sys
from pathlib import Path
from typing import Tuple, List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.polygon_utils import validate_polygon
from core.image_utils import validate_image_file


def validate_record_structure(record: dict) -> Tuple[bool, Optional[str]]:
    """
    验证单条记录的字段完整性
    
    Args:
        record: 单条GPC记录
    
    Returns:
        (是否有效, 错误信息)
    """
    required_fields = ['task_id', 'image_id', 'phrase', 'phrase_structure']
    
    for field in required_fields:
        if field not in record:
            return False, f"缺少必要字段: {field}"
    
    # 验证 task_id 格式
    task_id = record.get('task_id', '')
    if not isinstance(task_id, str) or not task_id:
        return False, f"task_id 格式错误: {task_id}"
    
    # 验证 phrase_structure
    phrase_struct = record.get('phrase_structure', {})
    if not isinstance(phrase_struct, dict):
        return False, "phrase_structure 必须是字典"
    
    if 'name' not in phrase_struct:
        return False, "phrase_structure 缺少 name 字段"
    
    if 'attributes' not in phrase_struct:
        phrase_struct['attributes'] = []
    
    if not isinstance(phrase_struct['attributes'], list):
        return False, "attributes 必须是列表"
    
    return True, None


def validate_refer_record(record: dict, 
                         width: int, 
                         height: int) -> Tuple[bool, List[str]]:
    """
    验证完整的refer记录(含Polygons)
    
    Args:
        record: refer_*.json 的单条记录
        width: 图像宽度
        height: 图像高度
    
    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    
    # 基础结构验证
    valid, error = validate_record_structure(record)
    if not valid:
        errors.append(error)
        return False, errors
    
    # 验证 Polygons
    if 'Polygons' not in record:
        errors.append("缺少 Polygons 字段")
    else:
        polygons = record['Polygons']
        if not polygons:
            errors.append("Polygons 为空")
        else:
            valid, error = validate_polygon(polygons, width, height)
            if not valid:
                errors.append(f"Polygons 验证失败: {error}")
    
    # 验证 instance_boxes
    if 'instance_boxes' not in record:
        errors.append("缺少 instance_boxes 字段")
    else:
        boxes = record['instance_boxes']
        if not isinstance(boxes, list):
            errors.append("instance_boxes 必须是列表")
        else:
            for i, box in enumerate(boxes):
                if not isinstance(box, list) or len(box) != 4:
                    errors.append(f"instance_boxes[{i}] 格式错误: {box}")
    
    return len(errors) == 0, errors


def validate_import_data(image_path: Path,
                        record: dict) -> Tuple[bool, List[str]]:
    """
    验证待导入数据的完整性
    
    Args:
        image_path: 图像文件路径
        record: 标注记录
    
    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    
    # 验证图像文件
    valid, error = validate_image_file(image_path)
    if not valid:
        errors.append(f"图像文件验证失败: {error}")
        return False, errors
    
    # 获取图像尺寸
    from PIL import Image
    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception as e:
        errors.append(f"无法读取图像尺寸: {e}")
        return False, errors
    
    # 验证记录
    valid, record_errors = validate_refer_record(record, width, height)
    if not valid:
        errors.extend(record_errors)
    
    return len(errors) == 0, errors


def validate_split_value(split: str) -> Tuple[bool, Optional[str]]:
    """
    验证 split 值的合法性
    
    Args:
        split: split值
    
    Returns:
        (是否有效, 错误信息)
    """
    valid_splits = ['train', 'val', 'test']
    if split not in valid_splits:
        return False, f"split 必须是 {valid_splits} 之一,当前为: {split}"
    
    return True, None


if __name__ == "__main__":
    # 测试代码
    test_record = {
        "task_id": "test_001",
        "image_id": "test_image",
        "phrase": "test object",
        "phrase_structure": {
            "name": "object",
            "attributes": ["test"],
            "type": "attribute",
            "relation_descriptions": [],
            "relation_ids": []
        },
        "ann_ids": [1],
        "instance_boxes": [[10, 10, 100, 100]],
        "Polygons": [[[[10, 10], [100, 10], [100, 100], [10, 100]]]]
    }
    
    valid, errors = validate_refer_record(test_record, 200, 200)
    print(f"记录验证: {valid}")
    if not valid:
        for err in errors:
            print(f"  - {err}")
