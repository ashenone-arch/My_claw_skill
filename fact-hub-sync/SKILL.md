---
name: fact-hub-sync
version: "1.0"
description: "Fact Hub 知识库同步工具，将本地 Fact Hub 内容推送到 GitHub 仓库。支持增量推送（hash 对比）、自动维护仓库 README。配置通过本地 github-config.json 管理，不上传公开仓库。"
---

# Fact Hub 同步工具

## 概述

将本地 Fact Hub 知识库内容同步到 GitHub 仓库。采用**内容 SHA1 hash 增量对比**机制，仅推送发生变化的文件。所有敏感配置（仓库地址、Token、本地路径）均存储在 `github-config.json` 中，该文件不会上传到公开仓库。

## 触发条件

用户说出以下任一表达时触发：
- "同步 Fact Hub" / "推送 Fact Hub" / "上传 Fact Hub"
- "备份 Fact Hub" / "备份知识库到 GitHub"
- "sync fact hub" / "push fact hub"
- "把知识库推到 GitHub"

## 核心行为

- **增量推送**：对比本地文件与远程文件的 SHA1 hash，仅推送有变化的文件
- **目录结构保持**：本地 `Fact Hub/` 下的目录结构直接映射到 GitHub 仓库根目录
- **README 自动维护**：推送成功后，GitHub 仓库 README 自动与本地 Fact Hub 的 README.md 保持一致
- **Token 验证**：推送前验证 token 有效性，无效则停止并提示

## 配置管理

> **隐私保护**：`github-config.json` 包含 Token 等敏感信息，**不上传到公开仓库**。此文件保留在本地 `~/.alphaclaw/skills/fact-hub-sync/` 中。

首次使用时，复制模板文件并填入真实值：

```bash
cp github-config.example.json github-config.json
```

配置文件格式（`github-config.json`）：

```json
{
  "repo_owner": "<你的 GitHub 用户名>",
  "repo_name": "<仓库名>",
  "token": "<GitHub Personal Access Token>",
  "branch": "main",
  "local_root": "<本地 Fact Hub 根目录路径>"
}
```

| 字段 | 说明 |
|------|------|
| `repo_owner` | GitHub 用户名或组织名 |
| `repo_name` | 目标仓库名称（建议设为私有） |
| `token` | GitHub Personal Access Token（需 `repo` 权限） |
| `branch` | 目标分支，默认 `main` |
| `local_root` | 本地 Fact Hub 根目录的绝对路径 |

## 执行步骤

### 第一步：读取配置 + 环境预检

1. 读取 `~/.alphaclaw/skills/fact-hub-sync/github-config.json`
2. 验证 token 有效性（`GET /user`）
3. 检查 `local_root` 目录是否存在
4. 向用户确认推送目标（owner/repo/branch）

### 第二步：扫描本地文件 + 计算 hash

对 `local_root` 下所有 `.md` 文件递归扫描，计算每个文件的 SHA1 hash，生成本地文件清单。

### 第三步：对比远程文件

通过 GitHub API 获取远程仓库文件树（`GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1`），逐文件对比 SHA1 hash：

- 本地有、远程无 → 新增，需推送
- 本地有、远程有、hash 不同 → 变更，需推送
- 本地有、远程有、hash 相同 → 跳过
- 远程有、本地无 → 记录（不自动删除，由用户手动处理）

### 第四步：执行推送

使用 `scripts/push.py`，从配置文件读取参数后传入：

```bash
python scripts/push.py \
  --local-root "<local_root>" \
  --owner "<repo_owner>" \
  --repo "<repo_name>" \
  --token "<token>" \
  --branch main
```

> 在 AlphaClaw 环境中，Python 路径为系统内置 Python。AI 助手会自动从配置文件中读取参数并执行。

推送完成后展示结果：新增 N 个、更新 M 个、跳过 K 个、失败列表。

### 第五步：报告结果

展示本次同步的变更摘要、失败项及原因。

## 快速参考

| 场景 | 操作 | 工具/脚本 |
|------|------|---------|
| 推送 Fact Hub | 增量上传变更文件 | `scripts/push.py` |
| 检查差异 | 对比本地/远程 SHA1 hash | GitHub API |
| Token 无效 | 提示重新配置 | 停止并提示用户 |
| 首次配置 | 复制 example 并填入真实值 | `github-config.example.json` |

## Token 更新提示

Token 无效时：

> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成（需勾选 `repo` 权限），然后将新 token 告诉我，我会更新本地配置文件。

## 文件清单

```
fact-hub-sync/
├── SKILL.md                      # 本文件（Skill 定义）
├── github-config.example.json    # 配置模板（可公开）
├── github-config.json            # 本地配置（含 Token，不可公开）
└── scripts/
    └── push.py                   # 增量推送脚本
```
