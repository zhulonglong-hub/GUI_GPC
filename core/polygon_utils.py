"""
GPC Dataset Manager - 多边形工具模块

复用 phrasecut_local.py 的多边形处理逻辑
"""

import numpy as np
from typing import List, Tuple, Optional
from skimage import draw
import warnings

# 抑制 skimage 的警告
warnings.filterwarnings('ignore', category=UserWarning)


def polygon_to_bbox(polygons: List[List[List[List[float]]]]) -> List[float]:
    """
    从多边形坐标计算边界框
    
    Args:
        polygons: GPC格式的多边形数据 [[[[x,y], [x,y], ...]]]
    
    Returns:
        [x_min, y_min, x_max, y_max]
    """
    if not polygons or not polygons[0] or not polygons[0][0]:
        return [0.0, 0.0, 0.0, 0.0]
    
    all_points = []
    for poly_group in polygons:
        for poly in poly_group:
            all_points.extend(poly)
    
    if not all_points:
        return [0.0, 0.0, 0.0, 0.0]
    
    xs = [pt[0] for pt in all_points]
    ys = [pt[1] for pt in all_points]
    
    return [min(xs), min(ys), max(xs), max(ys)]


def polygon_to_mask(polygons: List[List[List[List[float]]]], 
                    width: int, 
                    height: int) -> np.ndarray:
    """
    将多边形转换为二值掩膜
    
    Args:
        polygons: GPC格式的多边形数据 [[[[x,y], [x,y], ...]]]
        width: 图像宽度
        height: 图像高度
    
    Returns:
        shape为(height, width)的bool数组
    """
    mask = np.zeros((height, width), dtype=bool)
    
    if not polygons:
        return mask
    
    for poly_group in polygons:
        for poly in poly_group:
            if len(poly) < 3:
                continue
            
            # 提取 x, y 坐标
            xs = np.array([pt[0] for pt in poly])
            ys = np.array([pt[1] for pt in poly])
            
            # 边界检查并裁剪
            xs = np.clip(xs, 0, width - 1)
            ys = np.clip(ys, 0, height - 1)
            
            # 使用 skimage.draw.polygon 填充多边形
            rr, cc = draw.polygon(ys, xs, shape=(height, width))
            mask[rr, cc] = True
    
    return mask


def bbox_to_polygon(bbox: List[float]) -> List[List[List[List[float]]]]:
    """
    将边界框转换为GPC格式的多边形(矩形)
    
    Args:
        bbox: [x_min, y_min, x_max, y_max]
    
    Returns:
        GPC格式的多边形 [[[[x,y], [x,y], [x,y], [x,y]]]]
    """
    x_min, y_min, x_max, y_max = bbox
    polygon = [
        [x_min, y_min],
        [x_max, y_min],
        [x_max, y_max],
        [x_min, y_max]
    ]
    return [[polygon]]


def calculate_polygon_area(polygons: List[List[List[List[float]]]]) -> float:
    """
    计算多边形总面积(像素)
    
    Args:
        polygons: GPC格式的多边形数据
    
    Returns:
        面积(像素数量)
    """
    total_area = 0.0
    
    for poly_group in polygons:
        for poly in poly_group:
            if len(poly) < 3:
                continue
            
            # Shoelace公式计算多边形面积
            xs = [pt[0] for pt in poly]
            ys = [pt[1] for pt in poly]
            
            area = 0.0
            n = len(xs)
            for i in range(n):
                j = (i + 1) % n
                area += xs[i] * ys[j]
                area -= xs[j] * ys[i]
            
            total_area += abs(area) / 2.0
    
    return total_area


def validate_polygon(polygons: List[List[List[List[float]]]], 
                     width: int, 
                     height: int) -> Tuple[bool, Optional[str]]:
    """
    验证多边形数据的合法性
    
    Args:
        polygons: GPC格式的多边形数据
        width: 图像宽度
        height: 图像高度
    
    Returns:
        (是否有效, 错误信息)
    """
    if not polygons:
        return False, "多边形数据为空"
    
    if not isinstance(polygons, list):
        return False, "多边形格式错误: 顶层必须是列表"
    
    for i, poly_group in enumerate(polygons):
        if not isinstance(poly_group, list):
            return False, f"多边形格式错误: poly_group[{i}] 必须是列表"
        
        for j, poly in enumerate(poly_group):
            if not isinstance(poly, list):
                return False, f"多边形格式错误: polygon[{i}][{j}] 必须是列表"
            
            if len(poly) < 3:
                return False, f"多边形顶点不足: polygon[{i}][{j}] 仅有 {len(poly)} 个顶点"
            
            for k, pt in enumerate(poly):
                if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                    return False, f"顶点格式错误: polygon[{i}][{j}][{k}] = {pt}"
                
                x, y = pt
                if not (0 <= x < width and 0 <= y < height):
                    return False, f"顶点越界: ({x}, {y}) 超出图像范围 ({width}x{height})"
    
    return True, None


if __name__ == "__main__":
    # 测试代码
    test_polygon = [[[[10, 10], [100, 10], [100, 100], [10, 100]]]]
    
    bbox = polygon_to_bbox(test_polygon)
    print(f"BBox: {bbox}")
    
    mask = polygon_to_mask(test_polygon, 200, 200)
    print(f"Mask shape: {mask.shape}, True pixels: {mask.sum()}")
    
    area = calculate_polygon_area(test_polygon)
    print(f"Polygon area: {area}")
    
    valid, error = validate_polygon(test_polygon, 200, 200)
    print(f"Valid: {valid}, Error: {error}")
