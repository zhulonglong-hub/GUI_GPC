# Phase 1 改动总结 - 快速参考

## 改动文件清单

```
core/dataset_index.py       (+35/-17)  缓存绑定数据集路径
workers/index_builder.py    (+9/-5)    缓存文件名加哈希
ui/tab_browse.py            (+12/-10)  修复逻辑Bug
ui/widgets/phrase_panel.py  (+42/-2)   右键复制功能
ui/main_window.py           (+3/-0)    防护判断
```

## 关键改动点

### 1. 缓存机制修复（BUG-01）

**问题**: 切换数据集后仍显示旧数据

**解决**:
- `dataset_index.py`: save/load_cache 新增 dataset_root 参数并校验
- `index_builder.py`: 缓存文件名改为 `dataset_index_{hash}.pkl`

**验证**: 修改 config.py 的 DATASET_ROOT 后重启，统计信息应显示新数据集内容

---

### 2. 逻辑Bug修复（BUG-03）

**问题**: `load_full_record` 的 if 分支 return 导致 else 分支不可达

**解决**:
```python
# 旧代码（错误）
if split not in self.offset_indices:
    for record in stream_records(...):
        return record  # 这里return了
return None  # else永远执行这个

# 新代码（正确）
for record in stream_records(get_refer_json(split)):
    if record.get('task_id') == task_id:
        return record
return None
```

**验证**: 点击浏览列表条目，不再报"无法加载完整记录"错误

---

### 3. 复制功能（BUG-02）

**问题**: QTreeWidget 值列无法复制

**解决**:
- 右键菜单: "📋 复制值"
- 双击行: 自动复制值到剪贴板，状态栏显示提示

**验证**: phrase_panel 中右键点击 task_id 值，查看是否有复制菜单

---

### 4. 防护加固（BUG-03补充）

**解决**: `create_tabs()` 和 `refresh_index()` 添加 `if not self.dataset_index` 判断

**验证**: 启动时快速切换Tab，无异常崩溃

---

## 使用变化

### 用户可见变化

✅ **数据集切换正常**: 修改 config.py 后重启，显示正确数据  
✅ **字段可复制**: 右键或双击即可复制 task_id/image_id  
✅ **不再报错**: 点击条目不会提示"无法加载完整记录"

⚠️ **卡顿仍存在**: 点击后仍需等待 30-60 秒（Phase 2 修复）

### 开发者注意

- 旧的 `dataset_index.pkl` 不再使用，会生成 `dataset_index_{hash}.pkl`
- 首次运行会重建索引（因为缓存文件名变了）
- 可手动删除 `.cache/` 目录清理旧缓存

---

## 测试检查项

- [ ] 修改 DATASET_ROOT 后重启，统计数据正确
- [ ] 搜索并点击条目，能正常显示（虽然卡顿）
- [ ] phrase_panel 右键可见"复制值"菜单
- [ ] 双击字段行，Ctrl+V 能粘贴出值
- [ ] `.cache/` 目录有 `dataset_index_xxxxxxxx.pkl` 文件

---

## 下一步

Phase 2 将修复性能问题（卡顿），核心改动：
- `stream_records()` 改为 ijson 真流式
- `load_full_record()` 移至 QThread 异步加载
- 写操作（删改）移至后台线程

预期效果：点击条目后 ≤500ms 响应，删改操作有进度条不冻结UI。

---

*完整报告见: Phase1_BugFix_Report.md*
