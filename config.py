"""
GPC Dataset Manager - 配置管理模块

提供数据集路径、常量配置,支持外部 .ini 文件覆盖
"""

from pathlib import Path
from typing import Optional
import configparser

# ==================== 默认路径配置 ====================
# 注意: 以下路径需要根据实际数据集位置修改
DATASET_ROOT = Path(r"D:\dataset\GeoPCDataset_V1.0")  # 数据集根目录
#DATASET_ROOT = Path(r"D:\dataset\PhraseCut_Dataset")  # 数据集根目录
ANNOTATIONS_DIR = DATASET_ROOT / "annotations"
IMAGES_DIR = DATASET_ROOT / "images"

# 工具生成的目录
RECYCLE_DIR = Path(__file__).parent / "recycle"
CACHE_DIR = Path(__file__).parent / ".cache"
LOG_DIR = Path(__file__).parent / "logs"

# ==================== 常量定义 ====================
SUPPORTED_IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".tif", ".tiff"]
SPLITS = ["train", "val", "test"]

# 渲染配置
MAX_RENDER_SIZE = 2048  # 图像渲染前缩略图最大边长
POLYGON_ALPHA = 0.35
POLYGON_LINEWIDTH = 1.5

# 缓存配置
LRU_CACHE_SIZE = 50  # Polygons记录LRU缓存数量

# ==================== 目录初始化 ====================
RECYCLE_DIR.mkdir(exist_ok=True, parents=True)
CACHE_DIR.mkdir(exist_ok=True, parents=True)
LOG_DIR.mkdir(exist_ok=True, parents=True)


# ==================== 辅助函数 ====================
def get_refer_json(split: str) -> Path:
    """获取 refer_{split}.json 完整路径"""
    if split == "all":
        return ANNOTATIONS_DIR / "refer_all.json"
    return ANNOTATIONS_DIR / f"refer_{split}.json"


def get_refer_input_json(split: str) -> Path:
    """获取 refer_input_{split}.json 完整路径"""
    return ANNOTATIONS_DIR / f"refer_input_{split}.json"


def get_image_data_split_json() -> Path:
    """获取 image_data_split.json 完整路径"""
    return ANNOTATIONS_DIR / "image_data_split.json"


def get_name_count_json() -> Path:
    """获取 name_att_rel_count.json 完整路径"""
    return ANNOTATIONS_DIR / "name_att_rel_count.json"


def list_available_splits() -> list[str]:
    """扫描实际存在的 split 文件,返回 split 列表"""
    available = []
    for split in SPLITS:
        if get_refer_json(split).exists() and get_refer_input_json(split).exists():
            available.append(split)
    return available


def load_config(ini_path: Optional[Path] = None) -> None:
    """
    从外部 .ini 文件加载配置,覆盖默认路径
    
    Args:
        ini_path: .ini 配置文件路径,为None则跳过
    
    .ini 示例:
    [Paths]
    dataset_root = D:\MyDataset
    """
    if ini_path is None or not ini_path.exists():
        return
    
    config = configparser.ConfigParser()
    config.read(ini_path, encoding="utf-8")
    
    global DATASET_ROOT, ANNOTATIONS_DIR, IMAGES_DIR
    
    if config.has_section("Paths"):
        if config.has_option("Paths", "dataset_root"):
            DATASET_ROOT = Path(config.get("Paths", "dataset_root"))
            ANNOTATIONS_DIR = DATASET_ROOT / "annotations"
            IMAGES_DIR = DATASET_ROOT / "images"


def validate_dataset_structure() -> tuple[bool, list[str]]:
    """
    验证数据集目录结构完整性
    
    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []
    
    if not DATASET_ROOT.exists():
        errors.append(f"数据集根目录不存在: {DATASET_ROOT}")
        return False, errors
    
    if not ANNOTATIONS_DIR.exists():
        errors.append(f"annotations 目录不存在: {ANNOTATIONS_DIR}")
    
    if not IMAGES_DIR.exists():
        errors.append(f"images 目录不存在: {IMAGES_DIR}")
    
    # 检查必要的JSON文件
    required_files = [get_image_data_split_json(), get_name_count_json()]
    for split in SPLITS:
        required_files.append(get_refer_json(split))
        required_files.append(get_refer_input_json(split))
    
    for file_path in required_files:
        if not file_path.exists():
            errors.append(f"必要文件缺失: {file_path.name}")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    # 测试配置
    print(f"数据集根目录: {DATASET_ROOT}")
    print(f"Annotations: {ANNOTATIONS_DIR}")
    print(f"Images: {IMAGES_DIR}")
    print(f"可用的 splits: {list_available_splits()}")
    
    valid, errors = validate_dataset_structure()
    if valid:
        print("✓ 数据集结构验证通过")
    else:
        print("✗ 数据集结构验证失败:")
        for err in errors:
            print(f"  - {err}")
