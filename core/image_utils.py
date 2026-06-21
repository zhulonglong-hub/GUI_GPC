"""
GPC Dataset Manager - 图像工具模块

图像查找、加载、缩略图生成
复用 DataPreview_ProMax.py 的图像解析逻辑
"""

import sys
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import numpy as np

# 导入配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import IMAGES_DIR, SUPPORTED_IMAGE_EXTS, MAX_RENDER_SIZE, DATASET_ROOT


def resolve_image_path(image_id: str) -> Optional[Path]:
    """
    根据 image_id 查找实际图像文件路径
    
    Args:
        image_id: 图像ID (不含扩展名)
    
    Returns:
        图像文件完整路径,找不到则返回None
    """
    if not IMAGES_DIR.exists():
        return None
    
    # 尝试各种支持的扩展名
    for ext in SUPPORTED_IMAGE_EXTS:
        candidate = IMAGES_DIR / f"{image_id}{ext}"
        if candidate.exists():
            return candidate
    
    return None


def load_image(image_path: Path, 
               max_size: Optional[int] = None,
               as_array: bool = False) -> Optional[Image.Image | np.ndarray]:
    """
    加载图像文件,可选缩略图
    
    Args:
        image_path: 图像文件路径
        max_size: 最大边长限制,超过则缩略图,None表示不缩放
        as_array: 是否返回numpy数组,否则返回PIL Image
    
    Returns:
        PIL Image对象或numpy数组,加载失败返回None
    """
    if not image_path.exists():
        return None
    
    try:
        img = Image.open(image_path)
        
        # 转换为RGB (处理灰度图和RGBA)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 缩略图处理
        if max_size is not None:
            width, height = img.size
            if width > max_size or height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        if as_array:
            return np.array(img)
        else:
            return img
            
    except Exception as e:
        print(f"加载图像失败 {image_path}: {e}")
        return None


def load_image_by_id(image_id: str,
                     max_size: Optional[int] = None,
                     as_array: bool = False) -> Optional[Image.Image | np.ndarray]:
    """
    根据 image_id 查找并加载图像
    
    Args:
        image_id: 图像ID
        max_size: 最大边长限制
        as_array: 是否返回numpy数组
    
    Returns:
        图像对象,失败返回None
    """
    image_path = resolve_image_path(image_id)
    if image_path is None:
        return None
    
    return load_image(image_path, max_size=max_size, as_array=as_array)


def get_image_size(image_id: str) -> Optional[Tuple[int, int]]:
    """
    获取图像尺寸 (width, height)
    
    Args:
        image_id: 图像ID
    
    Returns:
        (width, height) 或 None
    """
    image_path = resolve_image_path(image_id)
    if image_path is None:
        return None
    
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None


def create_thumbnail(image_path: Path, 
                     output_path: Path,
                     size: Tuple[int, int] = (256, 256)) -> bool:
    """
    生成缩略图并保存
    
    Args:
        image_path: 原图路径
        output_path: 缩略图保存路径
        size: 缩略图尺寸 (width, height)
    
    Returns:
        是否成功
    """
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(output_path, 'JPEG', quality=85)
        return True
    except Exception as e:
        print(f"生成缩略图失败: {e}")
        return False


def validate_image_file(image_path: Path) -> Tuple[bool, Optional[str]]:
    """
    验证图像文件的合法性
    
    Args:
        image_path: 图像文件路径
    
    Returns:
        (是否有效, 错误信息)
    """
    if not image_path.exists():
        return False, f"文件不存在: {image_path}"
    
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTS:
        return False, f"不支持的图像格式: {image_path.suffix}"
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width <= 0 or height <= 0:
                return False, f"图像尺寸无效: {width}x{height}"
            
            # 检查是否可以转换为RGB
            img.convert('RGB')
            
        return True, None
        
    except Exception as e:
        return False, f"图像文件损坏: {str(e)}"


def resolve_mask_path(mask_path: str) -> Optional[Path]:
    """
    根据记录中的 mask_path 字段解析掩膜文件绝对路径。
    mask_path 是相对数据集根目录的路径，如 "mask_json/xxx.png"。
    """
    if not mask_path:
        return None
    full = DATASET_ROOT / mask_path
    return full if full.exists() else None


def load_mask_as_rgba(mask_path: str,
                      color: Tuple[int, int, int] = (255, 80, 0),
                      alpha: float = 0.45) -> Optional[np.ndarray]:
    """
    加载二值掩膜 PNG 并转换为 RGBA 叠加数组。

    掩膜 PNG 为单通道二值图（前景像素值 > 0）。
    返回 RGBA uint8 数组 (H, W, 4)，可直接用 matplotlib imshow 叠加。

    Args:
        mask_path: 相对数据集根目录的掩膜路径
        color: 叠加颜色 (R, G, B)，默认橙红色
        alpha: 叠加透明度 0-1
    """
    path = resolve_mask_path(mask_path)
    if path is None:
        return None
    try:
        img = Image.open(path).convert('L')
        mask = np.array(img)
        foreground = mask > 0
        h, w = mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[foreground, 0] = color[0]
        rgba[foreground, 1] = color[1]
        rgba[foreground, 2] = color[2]
        rgba[foreground, 3] = int(alpha * 255)
        return rgba
    except Exception as e:
        print(f"加载掩膜失败 {path}: {e}")
        return None


if __name__ == "__main__":
    # 测试代码
    print(f"图像目录: {IMAGES_DIR}")
    
    # 测试查找图像
    test_id = "test_image"
    path = resolve_image_path(test_id)
    print(f"查找 {test_id}: {path}")
    
    # 列出图像目录的前10个文件
    if IMAGES_DIR.exists():
        files = list(IMAGES_DIR.glob("*"))[:10]
        print(f"\n图像目录前10个文件:")
        for f in files:
            print(f"  {f.name}")
