# README 维护逻辑

> 本文件描述 README 版本列表的生成和更新逻辑。脚本见 `scripts/readme_ops.py`。

## 核心原则

**以云端 Skill 为基准**：README 版本列表从 GitHub API 获取远程仓库中的 Skill 版本，不再扫描本地目录。这确保 README 始终反映仓库实际状态。

## 执行流程

scripts/readme_ops.py 维护逻辑（6 步）：

1. 调用 GitHub API `GET /repos/{owner}/{repo}/contents` 获取远程 Skill 目录列表
2. 遍历每个目录，获取 `SKILL.md` 内容（base64 解码），解析 frontmatter `name`、`version`、`description`
3. **skill-sync 自身版本**：从 GitHub API 获取 `skill-sync/SKILL.md` 的 version 字段（不写死在代码中）
4. 生成 README 内容（以远程版本为准）
5. 调用 API 获取 README SHA，更新 README（base64 编码）
6. **验证**：GET README 确认版本列表正确（失败重试最多 3 次）

## 为什么必须验证成功？

git push/push API 返回成功不等于 README 实际已更新（网络中断时静默失败）。README 更新后必须验证，未验证视为失败。

## README 内容格式

```markdown
# My Claw Skills

> 个人日常投资研究使用的 AlphaClaw Skill 集合，版本信息见各 Skill 的 Release

## 目录

| Skill | 说明 | 版本 |
|-------|------|------|
| [skill-sync](skill-sync/) | GitHub Skill 同步工具... | v1.3 |
| [equity-deep-research](equity-deep-research/) | A股股票深度研究... | v2.4 |
| ...

## 使用方式

在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。

示例：
- "深度研究一下贵州茅台" → 触发 `equity-deep-research`
- "同步我的 skill" → 触发 `skill-sync`
- ...

## 版本说明

每个 Skill 独立打 Tag，格式为 `{skill-name}-v{version}`。

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。
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
