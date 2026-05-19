---
name: fact-hub-sync
version: "1.3"
description: "Fact Hub 知识库双向同步工具，支持本地↔云端双向同步。远程优先：比较最后修改时间，更新者覆盖旧者。支持 sync/push/pull 三种模式。配置通过本地 github-config.json 管理，不上传公开仓库。"
---

# Fact Hub 同步工具

## 概述

将本地 Fact Hub 知识库与 GitHub 仓库**双向同步**。采用 **SHA1 hash 增量对比 + log.md 优先裁定**机制：
- 本地独有 → 推送到远程
- 远程独有 → 下载到本地
- 两边都有、hash 不同 → 比较 `log.md` 最后日志时间判定全局方向，更新者覆盖旧者
- `log.md` 不存在时 → 回退到逐文件 commit 时间比较

所有敏感配置存储在 `github-config.json` 中，该文件不会上传到公开仓库。

## 触发条件

用户说出以下任一表达时触发：
- "同步 Fact Hub" / "双向同步 Fact Hub" / "推送 Fact Hub" / "上传 Fact Hub"
- "拉取 Fact Hub" / "下载 Fact Hub" / "从云端恢复 Fact Hub"
- "备份 Fact Hub" / "备份知识库到 GitHub"
- "sync fact hub" / "push fact hub" / "pull fact hub"
- "把知识库推到 GitHub" / "从 GitHub 拉取知识库"

## 双向同步逻辑（v1.2 新增）

| 差异类型 | 判定方式 | 操作 |
|---------|---------|------|
| 本地独有 | 远程树中不存在 | **推送到远程** |
| 远程独有 | 本地文件中不存在 | **下载到本地** |
| 两边都有，hash 不同 | **比较 log.md 最后日志时间**（v1.3） | 远程日志更新 → 全量拉取；本地日志更新 → 全量推送；log.md 一致 → 快速跳过 |
| 两边都有，log.md 不存在 | 逐文件 commit 时间（兜底） | 远程 commit 更新 → 拉取；本地 mtime 更新 → 推送 |
| 两边都有，hash 相同 | — | 跳过 |

## 核心行为

- **双向同步（默认）**：`sync.py --mode sync`，log.md 优先裁定方向（v2.1）
- **纯推送**：`sync.py --mode push`，仅本地→远程（兼容旧 push.py 行为）
- **纯拉取**：`sync.py --mode pull`，仅远程→本地
- **目录结构保持**：本地 `Fact Hub/` 下的目录结构直接映射到 GitHub 仓库根目录
- **Token 验证**：同步前验证 token 有效性，无效则停止并提示

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

## Windows 环境注意事项（v1.1 新增）

> 以下基于 Windows Git Bash 实战踩坑。

| # | 规则 |
|---|------|
| 1 | 跑 Python 脚本用 `write` 工具写 `.py` 文件再用 Python 运行，**禁止用 bash heredoc（`<< 'EOF'`）**，heredoc 在 Git Bash 下经常 exit code 1 且无输出 |
| 2 | **不要另写临时扫描脚本**：`sync.py` 内部已做扫描+对比+双向同步全流程，直接传参运行即可，无需自己实现 |
| 3 | 系统内置 Python 路径为 `D:\AlphaEngine\resources\python\python\python.exe`，不要用 `python` 或 `python3` 命令 |

## 执行步骤

### 第一步：读取配置 + 环境预检

1. 读取 `~/.alphaclaw/skills/fact-hub-sync/github-config.json`
2. 验证 token 有效性（`GET /user`）
3. 检查 `local_root` 目录是否存在
4. 向用户确认同步目标（owner/repo/branch）

### 第二步：直接运行 sync.py

> **关键**：`sync.py` 内部已完成扫描+对比+裁定+双向同步全流程。不要另写临时脚本。

从配置文件读取参数，传入 `scripts/sync.py`（默认双向同步模式）：

```bash
D:\AlphaEngine\resources\python\python\python.exe \
  "$HOME/.alphaclaw/skills/fact-hub-sync/scripts/sync.py" \
  --local-root "<local_root>" \
  --owner "<repo_owner>" \
  --repo "<repo_name>" \
  --token "<token>" \
  --branch main \
  --mode sync
```

> `--mode` 可选 `sync`（默认，双向）、`push`（仅推送）、`pull`（仅拉取）。

脚本输出包含：差异分类（LOCAL/REMOTE/CONFLICT）、每个冲突文件的时间裁定结果、拉取/推送执行状态、最终 JSON 汇总。

### 第三步：报告结果

从 sync.py 输出的 JSON 汇总中提取：拉取/推送成功失败数、冲突裁定明细、变更文件清单。

## 快速参考

| 场景 | 操作 | 工具/脚本 |
|------|------|---------|
| 双向同步 Fact Hub | 自动裁定差异方向 | `scripts/sync.py --mode sync` |
| 仅推送到远程 | 本地→云端 | `scripts/sync.py --mode push` |
| 仅拉取到本地 | 云端→本地 | `scripts/sync.py --mode pull` |
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
    ├── sync.py                   # 双向同步脚本（v1.2，推荐使用）
    └── push.py                   # 旧版推送脚本（向后兼容）
```
