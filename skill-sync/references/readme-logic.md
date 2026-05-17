# README 维护逻辑 (v1.7)

> 本文件描述 README 版本列表的生成和更新逻辑。脚本见 `scripts/readme_ops.py`。

## 核心原则

**锚点保护模式**：README 中 `<!-- SKILL_TABLE_START -->` 到 `<!-- SKILL_TABLE_END -->` 之间的版本表格由脚本自动维护，**标记外的所有自定义内容永久保留，不会被覆盖**。

## 执行流程

scripts/readme_ops.py 维护逻辑（6 步）：

1. 调用 GitHub API `GET /repos/{owner}/{repo}/contents` 获取远程 Skill 目录列表
2. 遍历每个目录，获取 `SKILL.md` 内容（base64 解码），解析 frontmatter `name`、`version`、`description`
3. 调用 `get_existing_readme()` 获取远程当前 README 文本
4. 调用 `merge_readme()`：
   - 若 README 中存在 `<!-- SKILL_TABLE_START -->` 和 `<!-- SKILL_TABLE_END -->` 标记：
     **仅替换两个标记之间的表格内容**，标记前后的自定义内容完整保留
   - 若无标记（首次运行或旧格式 README）：
     生成完整 README，**带锚点标记**（此后即受保护）
5. 调用 API 获取 README SHA，更新 README（base64 编码）
6. **验证**：GET README 确认版本列表正确（失败重试最多 3 次）

## 锚点标记格式

```markdown
<!-- SKILL_TABLE_START -->

| Skill | 说明 | 版本 |
|-------|------|------|
| [skill-sync](skill-sync/) | GitHub Skill 同步工具... | v1.7 |
| ...

<!-- SKILL_TABLE_END -->
```

**用户可在标记外自由编辑 README**（添加介绍、项目说明、自定义章节等），脚本永远不会覆盖这些内容。

## 为什么必须验证成功？

git push/push API 返回成功不等于 README 实际已更新（网络中断时静默失败）。README 更新后必须验证，未验证视为失败。

## README 内容格式

```markdown
# My Claw Skills

> 个人日常投资研究使用的 AlphaClaw Skill 集合。
> `<!-- SKILL_TABLE_START -->` 到 `<!-- SKILL_TABLE_END -->` 之间的表格由 skill-sync 自动维护，
> 请勿手动编辑表格内容。标记外的区域可自由自定义。

## 目录

<!-- SKILL_TABLE_START -->

| Skill | 说明 | 版本 |
|-------|------|------|
| [skill-sync](skill-sync/) | GitHub Skill 同步工具... | v1.7 |
| ...

<!-- SKILL_TABLE_END -->

## 使用方式
...
```

**排序规则**：skill-sync 排第一位，其余按名称字母顺序排列。

## 执行命令

```bash
python scripts/readme_ops.py \
  --action update \
  --owner <owner> \
  --repo <repo> \
  --token <token>
```

## 故障场景

| 问题 | 原因 | 处理 |
|------|------|------|
| 验证失败 | 网络中断或并发冲突 | 重试最多 3 次（幂等操作）|
| SHA 失效（422） | README 在这期间被其他人更新 | 重新 GET SHA 再 PUT |
| SSL EOF 错误 | SSL 握手不稳定 | 全局 SSL 降级重试 |
| 部分 skill 读取失败 | 网络抖动 | 静默跳过（不影响已成功的）|
| 锚点标记被误删 | 用户手动删除了标记 | 自动回退为生成完整 README（含锚点），不影响同步 |
