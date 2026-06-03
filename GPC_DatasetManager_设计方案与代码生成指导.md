# GPC Dataset Manager — 设计方案与代码生成指导文档

> **版本**：v1.0
> **适用数据集**：GeoPCDataset_V1.0（以下简称 GPC 数据集）
> **目标**：为 GPC 数据集提供可迭代的 GUI 管理工具，覆盖"查、增、删、改"全流程

---

## 一、项目定位与设计原则

### 1.1 定位

GPC Dataset Manager 是一个**桌面 GUI 工具**，专门服务于 GeoPCDataset_V1.0 这类大体量遥感分割数据集的日常管理与维护工作。它不是模型训练代码，而是围绕数据集的"人工管理层"。

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **数据一致性优先** | 任何写操作必须同步维护 image、refer_*.json、refer_input_*.json、image_data_split.json 四组文件的联动 |
| **大文件友好** | refer_train.json 达 2.7 GB，绝不可全量加载后回写；所有写操作必须采用追加/流式/局部替换策略 |
| **可迭代架构** | UI 层与数据层严格分离，功能模块化，便于后续迭代 |
| **无破坏性操作** | 删除操作软删除到回收区，写操作先备份再执行 |
| **基于现有逻辑复用** | 数据加载/图像解析/多边形渲染逻辑参照 DataPreview_ProMax.py 与 phrasecut_local.py |

---

## 二、数据集结构速查（开发必读）

```
GeoPCDataset_V1.0/
├── annotations/
│   ├── image_data_split.json       # 5.9 MB  图像元数据索引（image_id→宽高/split）
│   ├── refer_train.json            # 2.7 GB  训练集完整标注，含 Polygons
│   ├── refer_val.json              # 570 MB  验证集完整标注，含 Polygons
│   ├── refer_test.json             # 567 MB  测试集完整标注，含 Polygons
│   ├── refer_all.json              # 3.8 GB  全量合并（通常只读，不写）
│   ├── refer_input_train.json      # 15 MB   训练集无掩膜版（phrase+image_id）
│   ├── refer_input_val.json        # 3.2 MB  验证集无掩膜版
│   ├── refer_input_test.json       # 3.2 MB  测试集无掩膜版
│   └── name_att_rel_count.json     # 3.8 KB  类别/属性/关系频次统计
└── images/
    └── [卫星影像切片 .jpg/.png/.tif]
```

### 2.1 核心 JSON 字段（refer_*.json 单条记录）

```json
{
  "task_id":        "260419143400_0002",
  "image_id":       "100694_sat_0000_0001_part001_cutted",
  "phrase":         "lush Rangeland",
  "phrase_structure": {
    "name":                   "Rangeland",
    "attributes":             ["lush"],
    "type":                   "attribute",
    "relation_descriptions":  [],
    "relation_ids":           []
  },
  "ann_ids":         [2],
  "instance_boxes":  [[0.0, 0.0, 259.0, 1003.0]],
  "Polygons": [ [ [[x,y], [x,y], ...] ] ]
}
```

### 2.2 refer_input_*.json 单条记录（无掩膜，轻量）

```json
{
  "task_id":    "260419143400_0002",
  "image_id":   "100694_sat_0000_0001_part001_cutted",
  "phrase":     "lush Rangeland",
  "phrase_structure": {
    "name": "Rangeland",
    "attributes": ["lush"],
    "relation_descriptions": []
  }
}
```

### 2.3 image_data_split.json 单条记录

```json
{
  "image_id": "100694_sat_0000_0001_part001_cutted",
  "width": 260,
  "height": 1004,
  "split": "train",
  "coco_id": null,
  "flickr_id": null,
  "url": null,
  "refvg_version": null
}
```

> **关键约束**：`task_id` 是增删改的主键；`image_id` 是与图像文件的关联键（文件名去后缀）。
> **一图多膜**：同一 `image_id` 可对应多个 `task_id`（不同地物/标注），删改时须特别处理。

---

## 三、GUI 整体架构设计

### 3.1 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| GUI 框架 | **PyQt6** | 成熟、跨平台、布局灵活，支持自定义控件 |
| 图像渲染 | **matplotlib + FigureCanvasQTAgg** | 直接复用 DataPreview_ProMax.py 渲染逻辑 |
| 大 JSON 流式读 | **ijson** | 避免将 2.7 GB 文件全量加载到内存 |
| 大 JSON 快速定位 | **task_id → 字节偏移量索引** | 按需读取单条记录（含 Polygons） |
| 大 JSON 写入 | **流式过滤 + 临时文件原子替换** | 避免全量序列化回写 |
| 并发 | **QThread + 信号/槽** | IO/索引构建不阻塞 UI |
| 图像缩略图 | **PIL.Image.thumbnail** | 预览时按需缩放，不改动原图 |
| 操作日志 | **JSON Lines (.jsonl)** | 每行一条写操作记录，支持审计回溯 |

### 3.2 项目目录结构

```
GUI_GPC/
├── main.py                          # 程序入口，初始化 QApplication
├── config.py                        # 数据集路径、常量配置（支持外部 .ini 覆盖）
│
├── core/                            # 纯数据层（无 UI 依赖）
│   ├── dataset_index.py             # 内存索引管理器（仅读 input_json，轻量）
│   ├── json_io.py                   # 大 JSON 流式读/写/偏移量索引工具
│   ├── polygon_utils.py             # 多边形→掩膜/BBox，复用 phrasecut_local.py 逻辑
│   ├── image_utils.py               # 图像查找、加载、缩略图生成
│   ├── writer.py                    # 增/删/改原子写操作，维护四文件一致性
│   └── validator.py                 # 导入前数据合法性校验
│
├── ui/                              # UI 层
│   ├── main_window.py               # 主窗口（Tab 容器 + 菜单 + 状态栏）
│   ├── tab_browse.py                # 【查】浏览与预览 Tab
│   ├── tab_add.py                   # 【增】新增样本 Tab
│   ├── tab_delete.py                # 【删】删除样本 Tab
│   ├── tab_edit.py                  # 【改】字段编辑 Tab
│   ├── tab_stats.py                 # 【统计】数据集概览 Tab
│   └── widgets/
│       ├── image_canvas.py          # matplotlib 渲染画布（复用 ProMax 渲染逻辑）
│       ├── mask_overlay.py          # 多边形叠加渲染组件
│       ├── phrase_panel.py          # 文本字段 JSON 树形展示面板
│       └── progress_dialog.py       # 后台任务进度对话框
│
├── workers/                         # QThread 工作线程
│   ├── index_builder.py             # 后台构建内存索引
│   ├── image_loader.py              # 异步图像加载
│   └── batch_editor.py             # 批量字段修改任务
│
├── logs/
│   └── operations.jsonl             # 所有写操作审计日志（JSON Lines）
│
└── .cache/
    ├── offset_index_train.pkl       # refer_train.json 的 task_id→字节偏移缓存
    ├── offset_index_val.pkl
    └── offset_index_test.pkl
```

---

## 四、功能模块详细设计

### 4.1 【查】浏览预览模块（tab_browse.py）

#### 4.1.1 交互流程

```
用户输入 image_id / task_id / 类别名 / phrase 关键字
    ↓
dataset_index 查询（内存索引，毫秒级响应）
    ↓
左侧结果列表：显示命中条目（task_id + phrase + split + image_id）
    ↓
用户点击/键盘选中某条目
    ↓
① image_loader QThread：异步加载原图
② json_io：按偏移量读取该 task_id 的完整记录（含 Polygons）
    ↓
右上：image_canvas 渲染"原图 + 多边形叠加"（复用 ProMax 渲染函数）
右下：phrase_panel 展示完整字段树（可展开/折叠，可复制值）
```

#### 4.1.2 搜索维度

| 搜索方式 | 实现来源 | 响应级别 |
|----------|----------|----------|
| image_id 精确/前缀匹配 | 内存倒排索引 | 毫秒 |
| task_id 精确匹配 | 内存主索引 | 毫秒 |
| 类别名（name）精确/模糊 | 内存倒排索引 | 毫秒 |
| phrase 关键字 | 遍历 refer_input_all.json（22 MB） | <1 秒 |
| split 筛选 | 索引附带 split 字段 | 毫秒 |
| 随机浏览 | `random.choice(all_task_ids)` | 毫秒 |

#### 4.1.3 渲染规范（直接参照 DataPreview_ProMax.py）

- 多边形叠加：`tab20` 色板，`alpha=0.35`，边框 `linewidth=1.5`
- 标签防遮挡：复用 `_rects_overlap` + 螺旋搜索逻辑（与 ProMax 完全一致）
- 原图任意边 > 2048px 先 `thumbnail(2048,2048)` 再渲染（防止大图卡顿）
- 每个 mask 条目对应颜色、短语标签，视觉效果与 ProMax 保持一致

---

### 4.2 【增】新增样本模块（tab_add.py）

#### 4.2.1 输入表单字段

| 字段 | UI 控件 | 说明 |
|------|---------|------|
| 原图文件 | 文件选择按钮 | .jpg/.png/.tif，支持多选批量导入 |
| 标签来源 | 下拉选择 | ①手动输入 Polygons JSON ②矩形框快速标注（自动转多边形） |
| `name` | 下拉框 + 可输入 | 从 name_att_rel_count.json 提供候选列表 |
| `attributes` | 标签输入框 | 多属性，逗号分隔，Enter 确认 |
| `relation_descriptions` | 文本输入 | 可为空 |
| `split` | 单选按钮组 | train / val / test |
| `phrase` | 文本框（自动生成可覆盖） | 由 attributes+name+relations 拼接预览 |

#### 4.2.2 自动生成 GPC 记录逻辑（writer.py: add_record() 伪代码）

```python
def add_record(img_src_path, polygons, name, attributes, relations, split):
    task_id  = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{next_seq():04d}"
    image_id = Path(img_src_path).stem
    width, height = Image.open(img_src_path).size
    phrase   = build_phrase(attributes, name, relations)
    instance_boxes = [polygon_to_bbox(polygons)]

    refer_record = {
        "task_id": task_id, "image_id": image_id, "phrase": phrase,
        "phrase_structure": {"name":name, "attributes":attributes,
                             "type":"attribute",
                             "relation_descriptions":relations, "relation_ids":[]},
        "ann_ids": [auto_ann_id()],
        "instance_boxes": instance_boxes, "Polygons": polygons
    }
    refer_input_record = {k: refer_record[k]
                          for k in ("task_id","image_id","phrase","phrase_structure")}
    image_data_record = {
        "image_id": image_id, "width": width, "height": height,
        "split": split, "coco_id": None, "flickr_id": None,
        "url": None, "refvg_version": None
    }

    # 联动写操作（顺序不可打乱）
    copy_image(img_src_path, IMAGES_DIR / Path(img_src_path).name)
    json_io.append_record(f"refer_{split}.json",       refer_record)
    json_io.append_record(f"refer_input_{split}.json", refer_input_record)
    json_io.append_record("image_data_split.json",     image_data_record)
    update_name_count(name, attributes, relations, delta=+1)
    log_operation("add", task_id)
    return task_id
```

---

### 4.3 【删】删除样本模块（tab_delete.py）

#### 4.3.1 一图多膜处理

同一 `image_id` 可能对应多个 `task_id`，删除前展示所有关联条目供用户选择：

```
image_id: 100694_sat_0000_0001_part001_cutted（共 3 条标注）
  ☑ task_id: 260419143400_0001   "dense forest"       [train]
  ☑ task_id: 260419143400_0002   "lush Rangeland"     [train]
  ☐ task_id: 260419143400_0003   "agriculture field"  [train]

  [仅删除选中条目]   [删除该图全部条目]   [取消]
```

#### 4.3.2 删除联动顺序（writer.py: delete_record()）

```
① 二次确认对话框（展示受影响的文件列表、是否存在一图多膜）
② 备份目标 task_id 完整记录 → recycle/{task_id}_{timestamp}.bak.json
③ 流式过滤重写 refer_{split}.json（过滤掉目标 task_id）
④ 全量过滤重写 refer_input_{split}.json（体积小，可接受全量）
⑤ 判断 image_id 是否还有其他 task_id：
     └─ 若无：从 image_data_split.json 删除该图像元数据条目
     └─ 若无且用户确认：物理删除 images/ 中的图像文件
⑥ 更新 name_att_rel_count.json（减少对应计数）
⑦ 刷新内存索引（移除 task_id 相关条目）
⑧ 写操作日志
```

---

### 4.4 【改】字段编辑模块（tab_edit.py）

#### 4.4.1 支持编辑的字段

| 字段 | 编辑粒度 | 同步写入的文件 |
|------|----------|----------------|
| `phrase` | 单条 / 批量 | refer_*.json + refer_input_*.json |
| `phrase_structure.name` | 单条 / 批量 | refer_*.json + refer_input_*.json + name_count |
| `phrase_structure.attributes` | 单条 / 批量 | refer_*.json + refer_input_*.json |
| `phrase_structure.relation_descriptions` | 单条 | refer_*.json + refer_input_*.json |
| `split`（数据集间迁移） | 单条 / 批量 | refer_*.json 跨文件移动 |
| `Polygons` | 单条（v2 阶段多边形编辑器） | refer_*.json 仅大文件 |

#### 4.4.2 批量修改流程

```
用户设置过滤条件（如：name="agriculture" AND split="train"）
    ↓
预览受影响条目列表（分页只读展示，告知条目总数）
    ↓
用户输入新值（支持：字符串替换 / 追加属性 / 清空）
    ↓
batch_editor QThread 流式遍历目标 refer_{split}.json：
  → 命中 task_id：修改目标字段，写入 .tmp 临时文件
  → 完成后原子替换
  → 同步修改 refer_input_{split}.json
    ↓
进度条实时展示（已处理条数 / 总条数）
    ↓
完成后刷新内存索引
```

---

### 4.5 【统计】数据集概览模块（tab_stats.py）

| 展示内容 | 数据来源 | 更新时机 |
|----------|----------|----------|
| 各 split 条目数 | 内存索引统计 | 启动后 / 刷新后 |
| TOP-N 类别分布柱状图 | name_att_rel_count.json | 启动后 / 写操作后 |
| 图像文件数 vs 标注引用数 | images/ 目录遍历 vs 索引 | 按需刷新 |
| 孤立图像检测（有图无标注） | 交叉核查 | 按需刷新 |
| 孤立条目检测（有标注无图） | 交叉核查 | 按需刷新 |
| 最近写操作记录 | logs/operations.jsonl | 实时 |

---

## 五、大文件性能优化方案（核心）

### 5.1 分层内存策略

```
【第一层：始终驻留内存（轻量索引）】
  来源：refer_input_*.json（三个文件合计约 22 MB，可接受全量加载）
  结构：
    main_index:   { task_id  → {image_id, split, name, phrase, attributes} }
    image_index:  { image_id → [task_id, ...] }
    name_index:   { name     → [task_id, ...] }
  构建：程序启动后台线程，完成前 UI 显示加载进度

【第二层：按需流式读取（Polygons 数据）】
  来源：refer_{split}.json，仅当用户点击预览时读取对应条目
  方式：task_id → 字节偏移量 → seek + 读单条 JSON 对象
  缓存：LRU 缓存最近 50 条 Polygons 记录，避免反复 IO

【第三层：永不全量驻留】
  refer_train.json（2.7 GB）/ refer_all.json（3.8 GB）
  绝不执行 json.load()，只允许流式遍历或偏移量随机访问
```

### 5.2 task_id → 字节偏移量索引设计（json_io.py 核心）

```python
def build_offset_index(json_path: Path) -> dict[str, int]:
    """
    扫描 JSON 数组文件，记录每个 task_id 对应的字节起始偏移。
    前提：文件为紧凑 JSON 数组，每条记录的 task_id 字段出现在靠前位置。
    实现：状态机逐字节扫描 '{' → 匹配 '}' → 提取 task_id → 记录起始偏移。
    """
    offset_index = {}
    with open(json_path, 'rb') as f:
        while True:
            record_start = f.tell()
            raw = read_next_json_object(f)   # 状态机读一个完整 {} 对象
            if raw is None:
                break
            record = json.loads(raw)
            if task_id := record.get("task_id"):
                offset_index[task_id] = record_start
    return offset_index

def read_record_at_offset(json_path: Path, offset: int) -> dict:
    """按偏移量随机访问单条完整记录（含 Polygons）。"""
    with open(json_path, 'rb') as f:
        f.seek(offset)
        return json.loads(read_next_json_object(f))
```

**缓存策略**：
- 缓存位置：`.cache/offset_index_{split}.pkl`（同时记录原文件 mtime + size）
- 缓存失效：读取前对比 mtime/size，变化则后台重建
- 增量更新：`append_record` 后同步将新 task_id 的偏移追加到缓存

### 5.3 写操作安全策略（所有写方法必须遵守）

```
① 检查磁盘可用空间 ≥ 目标文件大小 × 1.2
② 原文件 rename → {filename}.bak（OS 原子操作）
③ 流式处理写入 {filename}.tmp
④ rename {filename}.tmp → {filename}（OS 原子替换）
⑤ 删除 {filename}.bak（确认成功后）
⑥ 若步骤③/④失败：rename {filename}.bak → {filename}（自动回滚）

启动时：自动清理残留的 .tmp 文件（上次异常退出的遗留）
```

### 5.4 UI 响应优化要点

| 问题 | 措施 |
|------|------|
| 索引构建阻塞 UI | `index_builder QThread`，进度信号实时更新状态栏 |
| 图像加载延迟 | `image_loader QThread`，先显示占位符再替换 |
| 结果列表渲染卡顿 | `QAbstractItemModel` 虚拟滚动，不渲染全部条目 |
| 大图渲染卡顿 | `thumbnail(2048,2048)` + matplotlib blitting 加速 |
| 批量操作期间无响应 | `batch_editor QThread` + 进度对话框 + 支持取消 |

---

## 六、代码生成指导（AI 编写代码时的规范）

### 6.1 模块生成顺序（依赖顺序，建议按批次生成）

```
第 1 批（无依赖，可并行生成）：
  config.py
  core/polygon_utils.py       ← 复用 phrasecut_local.py 的 polygon2mask 逻辑
  core/image_utils.py         ← 复用 DataPreview_ProMax.py 的 _resolve_image_path 逻辑

第 2 批（依赖第 1 批）：
  core/json_io.py             ← ijson 流式读 + 偏移量索引 + 安全写
  core/validator.py           ← 导入前字段合法性检查

第 3 批（依赖第 2 批）：
  core/dataset_index.py       ← 基于 refer_input_*.json 的轻量内存索引
  ui/widgets/image_canvas.py  ← 继承 FigureCanvasQTAgg，移植 ProMax 渲染逻辑

第 4 批（依赖第 3 批）：
  core/writer.py              ← 增/删/改原子写操作，维护四文件一致性
  workers/index_builder.py    ← QThread，后台构建 dataset_index
  workers/image_loader.py     ← QThread，异步加载图像

第 5 批（UI Tab，依赖第 3-4 批）：
  ui/widgets/phrase_panel.py
  ui/widgets/progress_dialog.py
  ui/tab_browse.py
  ui/tab_stats.py

第 6 批（写操作 Tab）：
  ui/tab_add.py
  workers/batch_editor.py
  ui/tab_delete.py
  ui/tab_edit.py

第 7 批（组装）：
  ui/main_window.py
  main.py
```

### 6.2 各模块关键约束（AI 生成时提示词必须包含）

#### config.py

```
约束：
- 所有路径使用 pathlib.Path，不硬编码字符串
- 提供 load_config(ini_path) 支持外部 .ini 文件覆盖默认路径
- 必须包含常量：DATASET_ROOT, ANNOTATIONS_DIR, IMAGES_DIR,
                RECYCLE_DIR, CACHE_DIR, LOG_DIR
- RECYCLE_DIR / CACHE_DIR / LOG_DIR 在模块导入时自动 mkdir(exist_ok=True)
- 提供 get_refer_json(split) / get_refer_input_json(split) 辅助函数
- 提供 list_available_splits() → list[str] 扫描实际存在的 split 文件
```

#### core/json_io.py

```
约束：
- stream_records(json_path) → Generator[dict, None, None]
    基于 ijson 的流式生成器，不全量加载
- build_offset_index(json_path) → dict[str, int]
    扫描文件建 task_id→字节偏移量索引（状态机实现）
- save_offset_index(index, cache_path, src_mtime, src_size) / load_offset_index(...)
    pickle 缓存，load 时校验 mtime+size，过期返回 None
- read_record_at_offset(json_path, offset) → dict
    随机访问单条完整记录（含 Polygons）
- append_record(json_path, record: dict)
    线程安全追加，使用 filelock；完成后追加更新偏移量缓存
- filter_rewrite(json_path, keep_fn, transform_fn=None)
    流式过滤重写，遵循"备份→写tmp→原子替换"安全策略
- 所有函数必须有完整 docstring 和 Python 类型注解
```

#### core/dataset_index.py

```
约束：
- 类名：DatasetIndex
- 构建来源：仅 refer_input_{split}.json（三个文件，合计 22 MB，不读大文件）
- 内存数据结构：
    self.main:      dict[str, dict]        # task_id → meta
    self.by_image:  dict[str, list[str]]   # image_id → [task_id]
    self.by_name:   dict[str, list[str]]   # name → [task_id]
- 公开方法：
    build(annotations_dir) → None
    search(query, by: str, split_filter=None) → list[str]  # 返回 task_id 列表
    get_meta(task_id) → dict
    save_cache(path) / load_cache(path) → bool
    add_entry(meta) / remove_entry(task_id) / update_entry(task_id, new_meta)
      （供 writer.py 调用，内存与磁盘同步）
```

#### core/writer.py

```
约束：
- 每个写方法最后一个参数均为 dry_run: bool = False
  dry_run=True 时返回操作计划 dict，不执行任何实际 IO
- add_record(img_src, polygons, name, attrs, relations, split, dry_run) → str
- delete_record(task_id, delete_image_file=False, dry_run) → dict
- update_fields(task_id, field_updates: dict, dry_run) → dict
- batch_update(condition_fn, field_updates, progress_cb, dry_run) → dict
- 所有写操作完成后：调用 _log_operation() 写 logs/operations.jsonl
- 所有写操作完成后：调用 index.add/remove/update_entry() 同步内存索引
- 私有方法 _safe_rewrite(json_path, ...) 封装"备份→tmp→原子替换"逻辑
```

#### ui/widgets/image_canvas.py

```
约束：
- 继承 FigureCanvasQTAgg
- 公开方法：
    render(image_np: np.ndarray, masks_records: list[dict]) → None
      masks_records 每项：{"phrase": str, "Polygons": [...], "instance_boxes": [...]}
    clear() → None   显示占位文字"请选择一个样本预览"
- 多边形渲染逻辑直接移植 DataPreview_ProMax.py：
    _mask_color（tab20 色板）/ PathPatch / _rects_overlap 标签防遮挡
- 支持鼠标滚轮缩放、左键拖拽平移
- 图像超过 2048px 任意边时先 thumbnail 再渲染
```

#### workers/index_builder.py

```
约束：
- 继承 QThread
- 信号：
    progress_updated = pyqtSignal(int, int)   # 已处理 / 总计
    index_ready      = pyqtSignal(object)     # DatasetIndex 对象
    error_occurred   = pyqtSignal(str)        # 错误消息
- 先调用 index.load_cache()，mtime 一致则直接 emit index_ready
- 否则全量构建后 save_cache() 再 emit index_ready
- 支持 cancel() 方法（设置标志位，run() 内循环检查）
```

#### workers/batch_editor.py

```
约束：
- 继承 QThread
- 接收：condition_fn（判断是否命中）, field_updates（新值字典）
- 信号：
    progress_updated = pyqtSignal(int, int)   # 已处理 / 总条数
    finished         = pyqtSignal(dict)       # 结果摘要
    error_occurred   = pyqtSignal(str)
- 支持 cancel()
- 内部调用 writer.batch_update()，不直接操作 IO
```

---

## 七、UI 布局规范

### 7.1 主窗口结构

```
┌─────────────────────────────────────────────────────────────────────┐
│ 菜单栏：文件(F) | 数据集(D) | 工具(T) | 帮助(H)                     │
├─────────────────────────────────────────────────────────────────────┤
│ 工具栏：[数据集路径框] [加载▶] [● 索引就绪 / ⏳ 构建中...]          │
├───────────────┬─────────────────────────────────────────────────────┤
│               │                                                     │
│  [📷 浏览]   │                                                     │
│  [➕ 新增]   │              各 Tab 内容区（QStackedWidget）         │
│  [🗑️ 删除]   │                                                     │
│  [✏️ 编辑]   │                                                     │
│  [📊 统计]   │                                                     │
│               │                                                     │
├───────────────┴─────────────────────────────────────────────────────┤
│ 状态栏：[train:7万+ | val:2万+ | test:2万+]  [当前操作提示]          │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 【查】Tab 布局

```
┌──────────────────────┬──────────────────────────────────────────────┐
│ 左侧：搜索+结果列表   │ 右上：image_canvas（matplotlib）              │
│                      │   原图 + 多边形叠加 + 标签（可缩放/平移）     │
│  [🔍 搜索框]         ├──────────────────────────────────────────────┤
│  [搜索维度▼][Split▼] │ 右下：phrase_panel（字段树）                  │
│  ─────────────────── │   task_id / image_id / split                 │
│  结果列表（虚拟滚动） │   phrase / phrase_structure（可展开）         │
│  ┌─────────────────┐ │   instance_boxes / Polygons 顶点总数          │
│  │ task_id         │ │                                               │
│  │ phrase          │ │                                               │
│  │ [train]         │ │                                               │
│  └─────────────────┘ │                                               │
│  共 N 条结果          │                                               │
└──────────────────────┴──────────────────────────────────────────────┘
```

### 7.3 【删】Tab 布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  [task_id 或 image_id 搜索框]    [搜索]                             │
├─────────────────────────────────────────────────────────────────────┤
│  image_id: 100694_sat_0000_0001_part001_cutted（共 3 条标注）        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ☑ 260419143400_0001  "dense forest"       [train]  [缩略图]   │ │
│  │ ☑ 260419143400_0002  "lush Rangeland"     [train]  [缩略图]   │ │
│  │ ☐ 260419143400_0003  "agriculture field"  [train]  [缩略图]   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  [全选] [反选]                                                       │
│  ☐ 同时删除图像文件（仅当该图所有标注均被删除时生效）                  │
│  [🗑️ 删除选中条目（需二次确认）]                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.4 【统计】Tab 布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  数据集概览                                         [🔄 刷新]        │
│  ─────────────────────────────────────────────────────────────────  │
│  train: 7万+ 条     val: 2万+ 条     test: 2万+ 条                  │
│  图像文件: N 张      孤立图像: 0     孤立条目: 0                      │
│  ─────────────────────────────────────────────────────────────────  │
│  TOP-20 类别分布（matplotlib 柱状图）                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ agriculture ████████████████ 9985                           │   │
│  │ tree        ████████████     6533                           │   │
│  │ ...                                                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ─────────────────────────────────────────────────────────────────  │
│  最近操作记录（logs/operations.jsonl 最后 20 条）                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 八、迭代计划

现在需要你完成到至少有增删查改的功能版本。

| 版本 | 里程碑 | 核心功能 |
|------|--------|----------|
| **v0.1** | MVP 骨架 | config + 内存索引（input_json）+ 主窗口框架 + 统计 Tab |
| **v0.2** | 查看完整 | 偏移量索引 + image_canvas 多边形渲染 + 浏览 Tab 完整 |
| **v0.3** | 删除功能 | writer.delete_record + 软删除回收 + 删除 Tab |
| **v0.4** | 字段编辑 | writer.update_fields + 单条编辑 Tab + 操作日志查看 |
| **v0.5** | 新增导入 | writer.add_record + 导入表单 + Polygon 输入 + 批量导入 |
| **v0.6** | 批量编辑 | batch_editor QThread + 批量字段修改 + 进度对话框 |
| **v1.0** | 稳定版 | 回收站管理 + 数据集健康检查 + 配置持久化 + 帮助文档 |

---

## 九、关键风险与应对

| 风险 | 触发场景 | 应对措施 |
|------|----------|----------|
| 大文件写操作中途崩溃 | 系统断电 / 强退 | 写前备份 .bak，失败自动回滚；启动时清理残留 .tmp |
| 偏移量索引与文件不同步 | 外部工具修改 JSON | 对比 mtime+size，不一致则重建缓存 |
| 图像 ID 与 JSON 记录不一致 | 手动重命名图像文件 | validator 导入前强校验；tab_stats 提供孤立检测 |
| 多线程并发写同一 JSON | 用户快速连续操作 | filelock 跨平台文件锁 + 写操作串行化队列 |
| 大图渲染卡顿（>30 MB TIF） | 遥感超大影像 | 渲染前 thumbnail ≤ 2048px；matplotlib blitting |
| refer_input 与 refer 字段不一致 | 写操作半途失败 | 日志记录每步；提供"一致性修复"工具（v1.0） |

---

## 十、依赖环境

```ini
# requirements_gui.txt（GUI 工具专用，可与训练环境共用 conda base）
PyQt6>=6.4.0
matplotlib>=3.7.0
Pillow>=9.0.0
numpy>=1.24.0
ijson>=3.2.0           # 大 JSON 流式解析（核心依赖）
filelock>=3.12.0       # 跨平台文件锁（写安全保证）
scikit-image>=0.20.0   # polygon2mask（与训练代码保持一致）
```

> **说明**：GUI 工具不依赖 `torch` / `torchvision`，可在轻量环境独立运行。
> 若使用 conda base 环境，`scikit-image` 和 `Pillow` 通常已安装，
> 只需额外安装 `PyQt6`、`ijson`、`filelock` 三个包。
