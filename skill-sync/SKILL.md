---
name: skill-sync
version: v1.0
description: 当用户需要同步本地 Skill 与 GitHub 仓库版本、检查 Skill 更新、或更新本地 Skill 至最新时使用。触发场景包括："同步我的 skill"、"检查 skill 版本"、"更新本地 skill"、"同步 skill 仓库"、"我的 skill 需要更新吗"、"把 GitHub 的 skill 拉下来"、"自动同步 skill"。即使用户只说"同步"、"更新"（在有 Skill 相关上下文时），也应触发。
---

# GitHub Skill 同步工具

## 概述

自动检测并同步本地 Skill 与 GitHub 仓库中的版本。远程优先：检测到远程有新版本时自动下载覆盖本地。每次同步完成后报告版本对比结果。如检测到 token 无效，提示用户更新。

## 核心行为

- **远程优先**：检测到远程版本 > 本地版本时，下载覆盖本地
- **GitHub 独有 Skill**：下载到本地 Skill 目录
- **本地独有 Skill**（如 MCP 相关）：保留不动，不同步
- **Token 验证**：每次同步前验证 token 有效性，无效则提示更新

## 配置管理

配置信息保存在 `~/.alphaclaw/skills/skill-sync/github-config.json`，结构如下：

```json
{
  "repo_owner": "ashenone-arch",
  "repo_name": "My_claw_skill",
  "token": "ghp_xxx",
  "branch": "main"
}
```

## 执行步骤

### 第一步：检查配置文件

读取 `~/.alphaclaw/skills/skill-sync/github-config.json`：
- 文件存在 → 读取配置，跳到第二步
- 文件不存在 → 询问用户提供 GitHub 仓库地址和 token

### 第二步：验证 Token

调用 GitHub `/user` API 验证 token：
- 返回 200 → Token 有效，继续同步
- 返回 401 → Token 无效/已过期，向用户展示 Token 更新说明并停止
- 返回 403 → Token 有效但权限不足，提示检查 token scope

### 第三步：获取仓库 Skill 列表

调用 `GET /repos/{owner}/{repo}/contents`（分支=main）获取仓库根目录下的所有 Skill 目录。

对每个 Skill 子目录，调用 `GET /repos/{owner}/{repo}/contents/{skill-name}/SKILL.md` 获取其 frontmatter 中的 `version` 字段。

### 第四步：获取本地 Skill 列表

读取 `~/.alphaclaw/skills/` 下所有子目录，对每个 Skill 读取其 `SKILL.md` 的 frontmatter 中的 `version` 字段。

### 第五步：生成版本对比表

```
| Skill | 本地版本 | 远程版本 | 状态 |
|-------|---------|---------|------|
| xxx   | v1.0    | v1.0    | 已同步 |
| yyy   | v0.9    | v1.0    | 可更新 |
| zzz   | -       | v1.0    | 新增 |
```

状态判断：
- `已同步`：version 相同
- `可更新`：远程 version > 本地 version
- `新增`：本地不存在该 Skill，GitHub 有
- `无需处理`：本地独有，不在 GitHub 中（不展示在对比表中）

### 第六步：询问用户是否执行同步

向用户展示版本对比表，询问是否同步。可用选项：
- "是，同步" → 执行同步
- "具体指定哪些" → 列出 Skill 让用户勾选
- "否，跳过" → 结束

### 第七步：执行同步（用户确认后）

按以下顺序执行：

1. **下载远程新增 Skill**：对"新增"状态的 Skill，在本地创建目录，下载 SKILL.md 和 references/ 目录（如有）
2. **更新可更新 Skill**：对"可更新"状态的 Skill，覆盖本地对应文件
3. **更新本地 frontmatter version**：所有被更新的 Skill，在本地 SKILL.md 的 frontmatter 中将 version 字段更新为远程版本号

下载文件时：GitHub API 获取文件内容（返回 base64 编码），解码后写入本地路径。

### 第八步：报告同步结果

展示本次同步的变更：
- 新增了哪些 Skill
- 更新了哪些 Skill
- 同步失败（如有）的 Skill 及原因

## 配置保存规则

用户提供 GitHub 信息后，自动保存到 `github-config.json`，无需每次询问。

若用户提出新的仓库地址和 token，询问是否覆盖现有配置（"确认用新的替换？"）。

## Token 更新提示

当检测到 token 无效时，提示用户：

> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成，然后将新 token 告诉我，我会更新配置文件。

## 注意事项

- GitHub API 认证 Header 格式：`Authorization: Bearer {token}`
- 获取文件内容后需 base64 解码（GitHub 返回的是 base64）
- 仓库只同步目录形式的 Skill（含有 SKILL.md 的目录），根目录的 README.md 等文件不下载
- `references/` 子目录如果有，也一并下载
- 配置文件中不存储明文 token 的说明：token 以加密或 base64 形式存储（实际存储明文，但文件名和内容不对外暴露）