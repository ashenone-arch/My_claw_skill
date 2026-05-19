# README 维护逻辑 (v1.8)

> 本文件描述 README 版本列表的生成和更新逻辑。脚本见 `scripts/readme_ops.py`。

## 核心原则

**工作流分阶段 + 锚点保护模式**：
- README 中 `<!-- SKILL_TABLE_START -->` 到 `<!-- SKILL_TABLE_END -->` 之间的版本表格由脚本自动维护
- 表格按投研工作流阶段分组：**信息收集 → 信息整理 → 分析/决策 → 系统工具**
- 标记外的所有自定义内容永久保留，不会被覆盖

## Skill 元数据

`scripts/readme_ops.py` 内置 `SKILL_META` 字典，维护每个 Skill 的工作流阶段和核心功能描述：

```python
SKILL_META = {
    'daily-seller-hotspot': ('信息收集', '每日扫描卖方抱团方向...'),
    'fact-hub': ('信息整理', '事实、观点、冲突三层知识库...'),
    'equity-deep-research': ('分析/决策', 'A股上市公司9段深度投研框架...'),
    ...
}
```

新增 Skill 时需在此处注册其阶段和功能描述。

## 执行流程

1. 调用 GitHub API 获取远程 Skill 目录列表
2. 遍历每个 Skill 目录，获取 `SKILL.md` frontmatter 中的 `version`
3. 调用 `get_existing_readme()` 获取远程当前 README 文本
4. 调用 `merge_readme()`：
   - 若 README 中存在锚点标记：仅替换标记之间的表格内容
   - 若无标记：生成完整 README（含锚点和分阶段表格）
5. PUT 更新 README
6. 验证：GET README 确认 Skill 链接数量正确（失败重试最多 3 次）

## 锚点标记格式

```markdown
<!-- SKILL_TABLE_START -->

### 信息收集

| Skill | 版本 | 核心功能 |
|-------|------|---------|
| [daily-seller-hotspot](daily-seller-hotspot/) | v1.0 | 每日扫描卖方抱团方向... |
| ...

### 信息整理
...

### 分析/决策
...

### 系统工具
...

<!-- SKILL_TABLE_END -->
```

## 故障场景

| 问题 | 原因 | 处理 |
|------|------|------|
| 验证失败 | 网络中断或并发冲突 | 重试最多 3 次（幂等操作）|
| SHA 失效（422） | README 被他人更新 | 重新 GET SHA 再 PUT |
| 锚点标记被误删 | 用户手动删除了标记 | 自动回退为生成完整 README |
| 新增 Skill 未出现在表格 | SKILL_META 未注册 | 需在 readme_ops.py 中注册新 Skill |
