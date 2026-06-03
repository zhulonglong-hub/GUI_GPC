# GPC Dataset Manager - 项目状态更新

> **当前版本**: v1.1 (Phase 1 完成)  
> **更新日期**: 2026-06-03  
> **项目状态**: ✅ 可用（关键Bug已修复）

---

## 📊 版本历史

| 版本 | 发布日期 | 状态 | 主要内容 |
|------|----------|------|----------|
| v1.0 | 2024-06-02 | 已废弃 | 初始版本，存在3个严重Bug |
| v1.1 | 2026-06-03 | 已升级 | Phase 1: 修复关键Bug |
| **v1.1.1** | **2026-06-03** | **当前** | **补丁: 修复 image_id 类型Bug** |
| v1.2 | 计划中 | 规划 | Phase 2: 性能优化（流式IO） |
| v1.3 | 计划中 | 规划 | Phase 3: 用户体验优化 |
| v2.0 | 计划中 | 规划 | Phase 4: 健壮性增强 |

---

## ✅ v1.1.1 已修复的问题

### 🔴 严重Bug修复（v1.1）

| Bug ID | 问题 | 状态 | 影响 |
|--------|------|------|------|
| BUG-01 | 切换数据集后统计/搜索仍显示旧数据 | ✅ 已修复 | 数据错乱，最严重 |
| BUG-02 | PhrasePanel 字段值无法复制 | ✅ 已修复 | 操作效率低 |
| BUG-03a | load_full_record 逻辑Bug导致报错 | ✅ 已修复 | 浏览功能不可用 |

### 🟡 中等Bug修复（v1.1.1 补丁）

| Bug ID | 问题 | 状态 | 影响 |
|--------|------|------|------|
| BUG-06 | image_id 为数字时搜索崩溃 | ✅ 已修复 | image_id 搜索不可用 |

### 🛡️ 防护加固

- ✅ 索引未就绪时的防护判断
- ✅ 缓存文件名包含数据集哈希（多数据集隔离）
- ✅ 缓存校验数据集路径（自动失效）
- ✅ image_id 类型统一为字符串（v1.1.1）

---

## ⚠️ 已知限制（待优化）

### 性能问题（Phase 2 修复）

| 问题 | 现状 | 计划 |
|------|------|------|
| 点击列表卡顿 | 30-60秒 | Phase 2: 真流式IO + 异步加载 |
| 删改操作卡顿 | UI冻结 | Phase 2: QThread后台执行 |
| stream_records 伪流式 | 全量加载 | Phase 2: ijson 改造 |

### 功能限制（Phase 3 & 4）

- 无GUI内切换数据集功能（需手动改 config.py）
- 无随机浏览功能
- 无数据集健康检查
- 无回收站管理界面

---

## 📁 当前文件结构

```
GUI_GPC/
├── main.py                          # 程序入口
├── config.py                        # 配置文件
├── requirements.txt                 # 依赖清单
│
├── core/                            # ✅ 核心层（已优化）
│   ├── dataset_index.py             # v1.1: 缓存绑定路径
│   ├── json_io.py                   # ⚠️ 待优化：伪流式
│   ├── writer.py                    # ⚠️ 待优化：主线程执行
│   ├── validator.py
│   ├── polygon_utils.py
│   └── image_utils.py
│
├── ui/                              # ✅ UI层（已优化）
│   ├── main_window.py               # v1.1: 防护判断
│   ├── tab_browse.py                # v1.1: 逻辑Bug修复
│   ├── tab_add.py
│   ├── tab_delete.py
│   ├── tab_edit.py
│   ├── tab_stats.py
│   └── widgets/
│       ├── image_canvas.py
│       ├── phrase_panel.py          # v1.1: 右键复制
│       └── progress_dialog.py
│
├── workers/                         # ✅ 线程层（已优化）
│   ├── index_builder.py             # v1.1: 缓存文件名哈希
│   └── image_loader.py
│
├── todo/                            # 📋 规划文档
│   └── GPC_OptimizationPlan.md     # Phase 1-4 完整规划
│
├── docs/                            # 📚 文档（新增）
│   ├── Phase1_BugFix_Report.md     # v1.1 详细报告
│   └── Phase1_改动总结.md           # v1.1 快速参考
│
├── .cache/                          # 缓存目录
│   └── dataset_index_{hash}.pkl    # v1.1: 多数据集隔离
│
├── logs/                            # 日志目录
│   └── operations.jsonl
│
└── recycle/                         # 回收站
```

---

## 🚀 快速开始（v1.1）

### 安装

```bash
pip install -r requirements.txt
```

### 配置

编辑 `config.py`:
```python
DATASET_ROOT = Path(r"D:\你的数据集路径")
```

### 运行

```bash
python main.py
```

### 首次使用

1. 程序启动后会自动构建索引（约10秒）
2. 索引完成后可使用所有功能
3. 切换数据集需修改 config.py 后重启

---

## 📝 使用注意事项

### v1.1 新功能

✅ **右键复制**: 在 phrase_panel 中右键点击字段值 → "📋 复制值"  
✅ **双击复制**: 双击任意字段行，值自动复制到剪贴板  
✅ **多数据集支持**: 切换 DATASET_ROOT 后缓存自动隔离

### 性能建议

⚠️ **点击预览时会卡顿**: 当前版本点击列表条目后需等待 30-60 秒，这是正常现象（Phase 2 修复）  
⚠️ **删改操作会冻结UI**: 删除/编辑操作期间 UI 暂时无响应（Phase 2 修复）

### 故障排查

**问题**: 切换数据集后仍显示旧数据  
**解决**: 删除 `.cache/` 目录后重启

**问题**: 点击条目报"无法加载完整记录"  
**解决**: 确认 task_id 确实存在于当前数据集的 refer_{split}.json

**问题**: 右键菜单不显示  
**解决**: 确认点击的是值列（第二列）且值非空

---

## 📅 开发路线图

### Phase 2: 性能优化（下一步）

**目标**: 消除主线程卡顿，让操作流畅

**核心改动**:
- ✅ `stream_records()` 改为 ijson 真流式
- ✅ `load_full_record()` 移入 QThread
- ✅ 写操作异步化（删改有进度条）

**预期收益**:
- 点击列表条目后 ≤500ms 响应
- 删改操作不冻结 UI
- 内存占用降低（不再全量加载 2.7GB）

### Phase 3: 用户体验优化

**计划功能**:
- GUI 内切换数据集
- 随机预览按钮
- settings.ini 持久化配置
- 搜索结果虚拟列表（解决 1000 条重绘延迟）

### Phase 4: 健壮性增强

**计划功能**:
- 磁盘空间检查
- 数据集健康检测（孤立文件）
- 回收站管理界面
- 操作日志查看器

---

## 🤝 贡献指南

### 报告问题

1. 在 GitHub Issues 中描述问题
2. 附上错误截图和终端日志
3. 说明数据集规模和操作步骤

### 提交代码

1. Fork 项目
2. 创建 feature 分支
3. 遵循 gui-dev-agents-template 规范
4. 提交 Pull Request

---

## 📄 许可证

MIT License

---

## 📞 技术支持

- **完整文档**: `Phase1_BugFix_Report.md`
- **快速参考**: `Phase1_改动总结.md`
- **规划文档**: `todo/GPC_OptimizationPlan.md`

---

**当前状态**: ✅ v1.1 可用，关键Bug已修复  
**推荐**: 生产环境可使用 v1.1，Phase 2 完成后性能将大幅提升
