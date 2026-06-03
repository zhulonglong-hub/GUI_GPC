# GPC Dataset Manager — 问题分析与优化计划

> **文档版本**: v1.0  
> **分析日期**: 2026-06-03  
> **文档定位**: 问题根因分析 + 分阶段改进计划（仅分析，不含代码实施）

---

## 一、用户反馈问题根因分析

### BUG-01 ⚠️ 切换数据集后统计/搜索仍显示旧数据（最严重）

**用户现象**：修改 `config.py` 的 `DATASET_ROOT` 后重启 GUI，统计和搜索结果依然是旧数据集的内容，点击条目弹出 `"无法加载完整记录: 260419192007_3935"` 错误。

#### 根因链条（代码级定位）

```
config.py 修改路径
    ↓
workers/index_builder.py:35 → index.load_cache(self.cache_path)
    ↓ cache_path = CACHE_DIR / "dataset_index.pkl"  ← 固定路径！
    ↓ 缓存只检查 pkl 文件是否存在，未绑定数据集路径
    ↓ 旧 pkl 存在 → 直接命中 → 返回旧数据集的索引对象
        ↓
    UI 搜索基于旧索引，找到旧 task_id
        ↓
    tab_browse.py:153 → stream_records(get_refer_json(split))
    ↓ get_refer_json 读取新的 config.ANNOTATIONS_DIR（新数据集）
    ↓ 新 refer_{split}.json 中根本没有旧 task_id
        ↓
    找不到记录 → "无法加载完整记录"
```

**三处关键缺陷**：

| # | 文件 | 行号 | 缺陷说明 |
|---|------|------|----------|
| 1 | `workers/index_builder.py` | 35 | `load_cache()` 只判断 pkl 是否存在，没有绑定 `DATASET_ROOT` 指纹 |
| 2 | `core/dataset_index.py` | 210–242 | `save_cache/load_cache` 存储内容里没有记录来源数据集路径 |
| 3 | `.cache/dataset_index.pkl` | — | 单一固定文件名，不随数据集路径变化 |

**运行时生成 `.pyc` 文件**：是 Python 正常行为（字节码缓存），与数据集缓存是两回事，不造成数据错误，但与 `.pkl` 旧缓存同时存在时容易混淆。真正的祸根是 `.pkl`。

#### 改进方案

```
方案 A（最简）：缓存文件名包含数据集路径的哈希
  cache_name = f"dataset_index_{hash(str(DATASET_ROOT))}.pkl"
  → 不同 DATASET_ROOT 自动使用不同缓存，互不干扰

方案 B（更健壮）：缓存 pickle 内部记录 dataset_root 字段
  save_cache 时写入 {'dataset_root': str(DATASET_ROOT), ...}
  load_cache 时校验 dataset_root，不一致则视为失效返回 False

推荐：A + B 同时实施，双重保险
```

---

### BUG-02 ⚠️ PhrasePanel 中 task_id / image_id 无法复制

**用户现象**：phrase_panel 中显示的字段值无法用鼠标选中后 Ctrl+C 复制，ID 较长时很不方便。

#### 根因（代码级定位）

```
ui/widgets/phrase_panel.py:34 → self.tree = QTreeWidget()
```

`QTreeWidget` 的单元格默认不可编辑，也不支持文本选中。`QTreeWidgetItem` 的值列是只读 Label 渲染，鼠标无法选中文字，Ctrl+C 无效。

#### 改进方案

```
方案 A（快速）：双击条目弹出 QDialog 显示可选中的 QTextEdit
方案 B（彻底）：将值列改用 QLineEdit 只读模式渲染（setReadOnly=True）
方案 C（推荐）：在树节点上添加右键菜单 "复制值"，触发 QApplication.clipboard().setText(value)
  + 双击行也自动将该行值复制到剪贴板并弹出 Toast 提示
```

---

### BUG-03 ⚠️ 点击浏览列表后图像显示严重卡顿

**用户现象**：搜索结果列表能快速呈现，但点击某条目后界面卡顿很久才显示图像。

#### 根因（代码级定位）

**卡顿点 1：`load_full_record` 在主线程全量流式遍历大文件**

```python
# tab_browse.py:147-157
def load_full_record(self, task_id: str, split: str) -> dict:
    if split not in self.offset_indices:          # 永远不走缓存分支！
        cache_path = CACHE_DIR / ...
        for record in stream_records(get_refer_json(split)):  # ← 主线程！
            if record.get('task_id') == task_id:
                return record
    return None  # ← 走了 offset_indices 分支却直接返回 None！
```

两个致命问题：
- **逻辑 Bug**：`if split not in self.offset_indices` 内部只执行流式遍历然后 return，else 分支（即 split 在 offset_indices 中）直接 `return None`，永远无法走到偏移量读取逻辑
- **主线程阻塞**：`stream_records()` 调用了 `json.load(f)` 全量加载（见 `json_io.py:36`），对于 2.7GB 的 `refer_train.json` 在主线程执行，必然严重卡顿

**卡顿点 2：`stream_records` 并非真正流式**

```python
# core/json_io.py:30-40
def stream_records(json_path: Path):
    with open(json_path, 'r', encoding='utf-8') as f:
        f.seek(0)
        data = json.load(f)   # ← 全量加载到内存！！
        for record in data:
            yield record
```

名为"流式"，实为全量 `json.load`。对 2.7GB 文件：读取时间约 30–60 秒，内存占用 4–8GB。

**卡顿点 3：`filter_rewrite`（改操作）同样调用 `stream_records`**

```python
# core/json_io.py:246
for record in stream_records(json_path):  # 全量加载 refer_train.json
    ...
```

"改"操作时全量重写 refer_train.json，在主线程执行，必然卡死 UI。

#### 改进方案

```
改进 1：修复 load_full_record 的逻辑 Bug（if/else 反向问题）
改进 2：stream_records 改为真正的流式：使用 ijson.items() 逐条解析
改进 3：load_full_record 移到 QThread，完成后通过信号更新 UI
改进 4：filter_rewrite 写操作也必须移到 QThread（batch_editor）
改进 5：实现偏移量索引的完整逻辑，用于 seek 定位单条记录
```

---

## 二、架构层面额外发现的问题

### ARCH-01 `stream_records` 伪流式设计

- **影响范围**：`json_io.py` 全部调用方，包括 `dataset_index.build()`、`writer.delete_record()`、`writer.update_fields()`
- **后果**：所有操作都在暗中全量加载 GB 级文件

### ARCH-02 `append_record` 也是全量重写

```python
# json_io.py:200-211
if json_path.exists():
    data = json.load(f)   # 全量读！
data.append(record)
json.dump(data, f, ...)   # 全量写！
```

即使是"新增一条"，也要把整个 refer_train.json 读进内存再写出去。

### ARCH-03 写操作在主线程执行，UI 完全冻结

`tab_edit.py:169` → `update_fields()` → `filter_rewrite()` → `stream_records()`，整条链路在主线程同步执行，操作期间 UI 完全无响应。

### ARCH-04 `build_offset_index` 同样全量加载后才定位偏移

```python
# json_io.py:61-83
with open(json_path, 'rb') as f:
    content = f.read()          # 全量读入内存
data = json.loads(content...)  # 全量解析
content_str = content.decode() # 二次内存拷贝
for record in data:
    offset = content_str.find(f'"{task_id}"')  # 字符串搜索定位
```

本意是精准定位字节偏移，实际做法是先全量加载再全量扫描，等于做了两遍全量工作。

### ARCH-05 删除操作全量读取并全量回写大文件

`writer.delete_record()` 删一条记录 → `filter_rewrite()` → 全量加载 refer_train.json → 过滤掉一条 → 全量回写。删除一条记录对 2.7GB 文件的开销等于完整复制该文件一次。

### ARCH-06 缺少全局加载状态提示

索引构建期间（进度对话框关闭前），如果用户切换 Tab 执行搜索，`self.dataset_index` 可能为 None 导致 AttributeError，缺少防护判断。

### ARCH-07 `tab_browse.load_full_record` 的逻辑 Bug

`if split not in self.offset_indices` 分支内遍历完成后 return，导致 `offset_indices` 字段实际上永远不会被使用，始终走的是全量流式路径。

---

## 三、用户体验层面补充建议

| # | 场景 | 当前问题 | 建议 |
|---|------|----------|------|
| UX-01 | 数据集切换 | 修改 config.py 需重启才生效，无 GUI 入口 | 主窗口工具栏添加"切换数据集"按钮，选择目录后热重载 |
| UX-02 | 搜索结果 | 每次搜索都清空列表重绘，1000 条的渲染有延迟 | 使用 QAbstractItemModel 虚拟列表，按需渲染可见行 |
| UX-03 | 字段复制 | 无法复制任何字段值 | 右键菜单"复制值"；双击自动复制并提示 |
| UX-04 | 浏览预览 | 点击条目后无任何等待反馈，直接卡顿 | 点击后立即显示"加载中…"占位，完成后刷新 |
| UX-05 | 写操作卡顿 | 删改期间 UI 冻结，用户无法感知进度 | 所有写操作移至 QThread + 进度条 |
| UX-06 | 错误提示 | "无法加载完整记录"含义不明 | 补充原因说明：文件不存在 / 缓存失效 / task_id 不在当前数据集 |
| UX-07 | 统计 Tab | 类别分布用纯文字条形图，可读性差 | 集成 matplotlib 柱状图（FigureCanvas） |
| UX-08 | 随机浏览 | 无随机抽样功能 | 浏览 Tab 添加"随机预览"按钮 |
| UX-09 | 数据集路径 | 仅在 config.py 中配置，无持久化 GUI 设置 | 将上次使用的路径写入 user_settings.ini，下次启动自动加载 |
| UX-10 | 操作反馈 | 成功/失败仅弹 QMessageBox，不在状态栏留痕 | 状态栏底部显示最近一次操作结果及时间戳 |

---

## 四、分阶段实施计划（Phrases）

> 原则：**优先修 Bug → 再提性能 → 最后增功能**，每个 Phrase 独立可验证。

---

### Phase 1：修复关键 Bug（阻断性缺陷）

**目标**：让工具基本可用，消除错误和数据错乱  
**预期工作量**：中（改动集中，风险低）

| 编号 | 改动文件 | 改动内容 |
|------|----------|----------|
| P1-1 | `core/dataset_index.py` | `save_cache` 内写入 `dataset_root` 字段；`load_cache` 内校验 `dataset_root`，不一致返回 False |
| P1-2 | `workers/index_builder.py` | 缓存文件名改为 `dataset_index_{hash(DATASET_ROOT)}.pkl`，实现多数据集缓存隔离 |
| P1-3 | `ui/tab_browse.py` | 修复 `load_full_record` 的 if/else 逻辑 Bug，确保偏移量路径可达 |
| P1-4 | `ui/widgets/phrase_panel.py` | 树节点添加右键菜单"复制值"；双击行写入剪贴板并在状态栏提示 |
| P1-5 | `ui/main_window.py` | 索引未就绪时对所有 Tab 的操作入口加 `if self.dataset_index is None` 防护 |

**验收标准**：  
- 切换数据集重启后，统计/搜索显示新数据集内容  
- 点击条目不再报"无法加载完整记录"（即使很慢）  
- phrase_panel 中右键可复制 task_id / image_id

---

### Phase 2：修复性能核心问题（流式 IO 改造）

**目标**：消除主线程卡顿，让操作流畅可用  
**预期工作量**：大（改动核心 IO 层，需充分测试）

| 编号 | 改动文件 | 改动内容 |
|------|----------|----------|
| P2-1 | `core/json_io.py` | `stream_records` 改用 `ijson.items(path, 'item')` 实现真正流式，不再 `json.load` |
| P2-2 | `core/json_io.py` | `build_offset_index` 改为状态机逐字节扫描，不全量加载 |
| P2-3 | `core/json_io.py` | `append_record` 改为真正追加：读文件最后几字节找到 `]`，替换为 `,{新记录}]` |
| P2-4 | `ui/tab_browse.py` | `load_full_record` 移入新 `RecordLoader(QThread)`，完成后 signal 更新 UI；点击条目立即显示"加载中…" |
| P2-5 | `ui/tab_edit.py` | `save_changes` 调用 `update_fields` 时改为在 `QThread` 中执行，添加进度对话框 |
| P2-6 | `ui/tab_delete.py` | `delete_record` 移至 QThread，显示进度 |
| P2-7 | `workers/` | 新增 `record_loader.py`（单条记录加载线程）、`write_worker.py`（统一写操作线程） |

**验收标准**：  
- 点击列表条目后 ≤500ms 出现"加载中"占位，图像异步刷新  
- 删改操作有进度条，UI 不冻结  
- 索引构建期间状态栏实时更新进度百分比

---

### Phase 3：用户体验优化

**目标**：让工具"好用"，减少摩擦  
**预期工作量**：中

| 编号 | 改动文件 | 改动内容 |
|------|----------|----------|
| P3-1 | `ui/main_window.py` | 工具栏添加"📂 切换数据集"按钮，选择目录后更新 config + 触发索引重建 |
| P3-2 | `config.py` + `main.py` | 引入 `user_settings.ini`，保存/读取上次使用的 `DATASET_ROOT`，启动时自动加载 |
| P3-3 | `ui/tab_browse.py` | 添加"🎲 随机预览"按钮，`random.choice(list(index.main))` |
| P3-4 | `ui/tab_browse.py` | 搜索结果改用 `QAbstractListModel` + 延迟渲染，解决 1000 条重绘延迟 |
| P3-5 | `ui/tab_stats.py` | 类别分布改为 matplotlib 柱状图（FigureCanvas 复用 `ImageCanvas` 模式） |
| P3-6 | `ui/main_window.py` | 状态栏增加"最近操作"区域，写操作完成后显示结果 + 时间戳 |
| P3-7 | `ui/tab_browse.py` | 点击列表条目同时在浏览Tab右下角显示"快捷复制"区，含 task_id 和 image_id 的可选中文本 |

**验收标准**：  
- GUI 内可完成数据集切换，无需手动改 config.py  
- 统计 Tab 有 matplotlib 柱状图  
- 浏览界面有快捷复制区

---

### Phase 4：健壮性与数据安全增强

**目标**：防止异常操作破坏数据，增加审查手段  
**预期工作量**：小-中

| 编号 | 改动文件 | 改动内容 |
|------|----------|----------|
| P4-1 | `core/json_io.py` | 启动时扫描并清理残留 `.tmp` / `.bak` 文件，记录到日志 |
| P4-2 | `core/writer.py` | 写操作前检查磁盘可用空间（目标文件 × 1.2），不足时拒绝并提示 |
| P4-3 | `ui/tab_stats.py` | 添加"健康检查"功能：孤立图像检测（有图无标注）、孤立条目检测（有标注无图）|
| P4-4 | `ui/main_window.py` | 菜单"数据集 → 查看操作日志"：打开 `logs/operations.jsonl` 的只读查看器 |
| P4-5 | `ui/` | 添加回收站管理页（查看 recycle/ 内容，支持恢复）|

**验收标准**：  
- 磁盘不足时友好提示而非崩溃  
- 统计 Tab 有孤立检测按钮  
- 可查看并恢复回收站中的条目

---

## 五、问题优先级总览

```
┌──────────────────────────────────────────────────────────────────────┐
│  严重性 ↑                                                             │
│                                                                      │
│  致命 │ BUG-01 缓存失效（数据错乱）                                   │
│       │ BUG-03 主线程卡顿（stream_records 全量加载）                  │
│       │ ARCH-01 stream_records 伪流式（影响所有 IO）                  │
│  ─────┼──────────────────────────────────────────────────────────── │
│  重要 │ ARCH-03 写操作主线程执行                                      │
│       │ BUG-03b load_full_record 逻辑 Bug（返回 None 的分支错误）     │
│       │ BUG-02 无法复制字段值                                         │
│  ─────┼──────────────────────────────────────────────────────────── │
│  优化 │ ARCH-02 append_record 全量重写                               │
│       │ UX-01 ~ UX-10 用户体验改进                                   │
│       │ ARCH-04 build_offset_index 低效                              │
└──────────────────────────────────────────────────────────────────────┘
                              → 紧迫性
```

---

## 六、各 Phase 改动文件速查表

| 文件 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| `config.py` | — | — | ✅ user_settings | — |
| `core/json_io.py` | — | ✅ 流式/偏移/追加 | — | ✅ 残留清理 |
| `core/dataset_index.py` | ✅ 缓存绑定路径 | — | — | — |
| `core/writer.py` | — | — | — | ✅ 磁盘检查 |
| `workers/index_builder.py` | ✅ 缓存文件名哈希 | — | — | — |
| `workers/record_loader.py` | — | ✅ 新增 | — | — |
| `workers/write_worker.py` | — | ✅ 新增 | — | — |
| `ui/main_window.py` | ✅ 防护 | — | ✅ 切换/状态栏 | ✅ 日志查看 |
| `ui/tab_browse.py` | ✅ 逻辑Bug | ✅ 异步加载 | ✅ 随机/复制区 | — |
| `ui/tab_edit.py` | — | ✅ 写操作异步 | — | — |
| `ui/tab_delete.py` | — | ✅ 写操作异步 | — | — |
| `ui/tab_stats.py` | — | — | ✅ 柱状图 | ✅ 健康检查 |
| `ui/widgets/phrase_panel.py` | ✅ 右键复制 | — | — | — |

---

## 七、实施注意事项

1. **Phase 2 是核心难点**：`stream_records` 的真流式改造会影响 `dataset_index.build()`，需要同步适配 `DatasetIndex` 中的 `_add_record` 调用方式，确保 ijson 遍历时能正确提取字段。

2. **ijson 与 json 的行为差异**：ijson 返回的数字类型可能是 `Decimal`，需要注意序列化时转换为 `float`/`int`。

3. **真正的追加写入（P2-3）**：需要处理原 JSON 文件末尾格式（可能有尾空白、`\n` 等），建议维护一个"已知末尾格式"的标记位。

4. **Phase 2 的 QThread 改造**：`load_full_record` 转 QThread 后，`on_item_selected` 不能立即获取 `full_record`，需要用信号槽的回调模式重构，注意避免重复点击时多个线程并发。

5. **Phase 1 可独立上线**：Phase 1 的改动互相独立，每项均可单独实施验证，无需等待 Phase 2。

6. **缓存迁移**：实施 P1-2 后，旧的 `dataset_index.pkl` 不会被自动清理（新文件名变了），可在 Phase 1 完成后手动清空 `.cache/` 目录。

---

*文档结束 — 下一步：按 Phase 1 → 2 → 3 → 4 顺序实施代码改动*
