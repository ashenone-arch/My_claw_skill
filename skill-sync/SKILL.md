---
version: "1.4"
description: "GitHub Skill 同步工具，支持本地↔云端双向同步；README 版本列表以云端 Skill 为基准生成。"
---

# GitHub Skill 同步工具

## 概述

自动检测并同步本地 Skill 与 GitHub 仓库中的版本。支持**双向同步**：远程优先拉取，本地领先时推送到云端。每次同步后自动维护仓库 README 版本列表。

## 核心行为

- **远程优先**：检测到远程 version > 本地 version 时，下载覆盖本地
- **本地领先时**：推送到 GitHub + 自动更新 README
- **GitHub 独有 Skill**：下载到本地 Skill 目录
- **本地独有 Skill**（MCP 相关等）：保留不动，不同步
- **Token 验证**：每次同步前验证 token 有效性，无效则停止
- **README 以云端为基准**：README 版本列表从 GitHub API 获取远程仓库中的 Skill 版本，不再扫描本地目录

## 配置管理

配置文件：`~/.alphaclaw/skills/skill-sync/github-config.json`

```json
{
  "repo_owner": "ashenone-arch",
  "repo_name": "My_claw_skill",
  "token": "ghp_xxx",
  "branch": "main"
}
```

## 执行步骤

完整执行细节 → 见 `references/sync-workflow.md`

### 第一步：读取配置 + 环境预检

读取 `github-config.json`，执行预检（git 可用性、API 连通性、git push 能力），决定使用 git clone 路径或 API 路径。预检完成后向用户说明当前使用的路径。

> 预检规则详细说明 → `references/troubleshooting.md` 第一节

### 第二步：获取远程与本地版本对比

调用 GitHub API 获取远程 Skill 列表，扫描本地 `~/.alphaclaw/skills/` 获取本地版本，生成对比表。

> 版本比较逻辑（含语义化版本比较）→ `references/version-compare.md`

### 第三步：询问同步方向

向用户展示版本对比表。可用选项：

- **"是，同步"** → 执行全部同步（拉取 + 推送）
- **"具体指定哪些"** → 列出清单让用户勾选
- **"否，跳过"** → 结束

### 第四步：执行同步

#### 4.1 拉取（远程 → 本地）

对每个"新增"和"可更新" Skill，通过 GitHub API 下载所有文件（含 `references/` 子目录）到本地。

#### 4.2 推送（本地 → 远程）

对每个"可推送" Skill，使用 **scripts/push.py**：

```
python "D:\AlphaEngine\resources\python\python\python.exe" scripts/push.py \
  --skill {skill-name} --owner {owner} --repo {repo} --token {token} --branch main
```

推送后自动验证，验证失败重试（最多 1 次）。

> 推送路径详解（git clone vs API）→ `references/troubleshooting.md` 第二节

#### 4.3 README 自动维护

推送成功后才执行。使用 **scripts/readme_ops.py**：

```
python "D:\AlphaEngine\resources\python\python\python.exe" scripts/readme_ops.py \
  --action update --owner {owner} --repo {repo} --token {token}
```

> README 维护逻辑详解 → `references/readme-logic.md`

### 第五步：报告结果

展示本次同步的变更：新增、更新、推送列表，README 状态，失败项及原因。

## Token 更新提示

Token 无效时：

> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成，然后将新 token 告诉我，我会更新配置文件。

## 配置保存规则

用户提供 GitHub 信息后自动保存到 `github-config.json`，无需每次询问。新仓库地址/token → 询问是否覆盖（"确认用新的替换？"）。

## 快速参考

| 场景 | 操作 | 工具/脚本 |
|------|------|---------|
| 检查版本差异 | 同步前对比 | 自动生成对比表 |
| 拉取远程更新 | 下载新/可更新 Skill | GitHub API |
| 推送本地 Skill | 上传可推送 Skill | scripts/push.py |
| 维护 README | 版本变化后自动更新 | scripts/readme_ops.py |
| Token 无效 | 提示重新配置 | 停止并提示用户 |

## 进阶参考

| 文件 | 内容 |
|------|------|
| `references/sync-workflow.md` | 完整执行步骤详解（第一步~第五步）|
| `references/version-compare.md` | 版本对比表模板 + 语义化版本比较逻辑 |
| `references/readme-logic.md` | README 维护逻辑 + 执行命令 |
| `references/troubleshooting.md` | 预检规则 + 推送路径对比 + 故障排查表 |
