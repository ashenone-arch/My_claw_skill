---
name: fact-hub-sync
version: "3.3"
description: "Fact Hub 知识库双向同步工具，支持本地↔云端双向同步。v3.3 新增 .syncstate.json 远程变更哨兵机制，解决多终端并行同步时增量检测漏同步问题。v3.2 自动从系统环境提取 Python 绝对路径。支持 sync/push/pull 三种模式。配置通过本地 github-config.json 管理，不上传公开仓库。"
---

# Fact Hub 同步工具

## 你的角色

你是 fact-hub-sync 的**操作员**，不是开发者。

你的工作只有三件事：
1. 读取配置，运行 `sync.py`（本文档列出的唯一命令）
2. 将 sync.py 的输出结果展示给用户
3. 在用户确认后执行同步（如有需要确认的操作）

你不需要理解 sync.py 的内部实现，**不允许编写任何新代码**。

## 最高优先级铁律

**违反即任务失败。以下行为绝对禁止：**

| 禁止行为 | 曾导致的事故 |
|---------|------------|
| 用 `write` 工具创建 .py / .sh 文件 | `sync.py` 已实现扫描+对比+裁定+双向同步全流程，另写脚本必然遗漏边界 case（如 hash 计算口径、时间戳取 max 而非 last） |
| 用 `bash` 执行 `python -c "..."` 或 heredoc | Windows Git Bash 下 heredoc exit 1 无输出，连用两次全部失败，浪费 2 轮工具调用 |
| 调用 GitHub API 自行对比文件差异 | sync.py 的 Git blob SHA 对比已做到 0 API 调用，自己写 API 调用来对比只能做到 N 次调用，又慢又不准 |
| 跳过 sync.py 自己"写个简单的同步" | sync.py 经过 v1.3→v2.1 三次迭代修复了时间戳 bug、增加了删除保护、优化了性能，自写的脚本不会有这些保障 |

**允许的操作：**
- 读取配置文件：`read ~/.alphaclaw/skills/fact-hub-sync/github-config.json`
- 运行 sync.py（见下方执行步骤）
- 向用户展示结果、询问确认

## 概述

将本地 Fact Hub 知识库与 GitHub 仓库**双向同步**。sync.py 内部完成全部流程，你只需运行一条命令。

核心机制：
- 本地独有 → 推送到远程
- 远程独有 → 下载到本地
- 两边都有、hash 不同 → 比较 log.md 最新日志时间裁定方向
- 远程有、本地已删除 → 默认不删除远程（安全保护），需用户确认
- 两边一致 → 跳过

所有敏感配置存储在 `github-config.json` 中，该文件被 `.gitignore` 保护，不会被推送到 GitHub。

## 触发条件

用户说出以下任一表达时触发：
- "同步 Fact Hub" / "双向同步 Fact Hub" / "推送 Fact Hub" / "上传 Fact Hub"
- "拉取 Fact Hub" / "下载 Fact Hub" / "从云端恢复 Fact Hub"
- "备份 Fact Hub" / "备份知识库到 GitHub"
- "sync fact hub" / "push fact hub" / "pull fact hub"
- "把知识库推到 GitHub" / "从 GitHub 拉取知识库"

## 配置管理

> **隐私保护**：`github-config.json` 包含 Token，已被 `.gitignore` 保护，不会上传到 GitHub。此文件保留在本地 `~/.alphaclaw/skills/fact-hub-sync/` 中。

首次使用时，复制模板：`cp github-config.example.json github-config.json`

配置文件格式：

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

1. `read ~/.alphaclaw/skills/fact-hub-sync/github-config.json` 获取 owner、repo、token、branch、local_root
2. 从当前对话的 `<system-reminder>` 标签中提取 Python 绝对路径（查找 `Python:` 行，取后续的完整路径），记为 `{PYTHON}`。后续所有脚本和 Python 命令都必须用 `{PYTHON}` 替代裸 `python`。
3. 检查 `local_root` 目录是否存在
4. 向用户确认同步目标

### 第二步：运行 sync.py（增量自动处理）

sync.py 内部自动完成增量检测——通过 `.syncstate.json` 判断远程是否有变更，通过 log.md 识别本地变更文件。你只需传基础参数，无需手动提取文件列表。

```bash
{PYTHON} "$HOME/.alphaclaw/skills/fact-hub-sync/scripts/sync.py" \
  --local-root "<local_root>" \
  --owner "<repo_owner>" \
  --repo "<repo_name>" \
  --token "<token>" \
  --branch main \
  --mode sync
```

参数说明：
- `--mode sync`（默认）：双向同步，log.md 裁定冲突方向
- `--mode push`：仅本地 → 远程
- `--mode pull`：仅远程 → 本地
- `--files`（可选）：逗号分隔的本地变更文件列表。sync.py 仅在本地变更检查阶段使用此列表（跳过明确没变的文件），远程变更检测由 `.syncstate.json` 独立完成。不传此参数时回退全量扫描。

> **增量原理（v3.3）**：sync.py 读取知识库根目录的 `.syncstate.json`（上次同步时的远程 tree SHA + 文件 blob SHA 快照），与当前远程 tree SHA 对比。若远程 tree SHA 未变 → 仅扫描本地变更文件；若远程 tree SHA 变化 → 自动从快照中 diff 出远程变更文件加入扫描列表。两终端场景下，终端B 的 sync 会检测到终端A 推送导致的 tree SHA 变化并精准拉取差异文件。

### 第三步：报告结果

从 sync.py 输出的 JSON 汇总中提取结果，展示给用户。sync.py 会在同步成功后自动更新 `.syncstate.json`，无需手动追加任何标记。

## 退出前自检

在向用户报告结果之前，必须完成：

1. 本次任务中是否用 `write` 创建了 .py/.sh 文件？→ 是则**任务失败**。删除文件，重新按流程执行。
2. 是否使用了 `{PYTHON} -c "..."` 或 heredoc？→ 是则**任务失败**。
3. 是否自行调用了 GitHub API 而非运行 sync.py？→ 是则**任务失败**。sync.py 已完成所有 API 调用。

全部通过后，正常报告结果。

## Token 无效处理

检测到 GitHub token 无效时停止，提示：

> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成（需勾选 `repo` 权限），然后将新 token 告诉我，我会更新本地配置文件。

## 踩坑日志

以下事故均因 AI 不遵守规则导致：

| 事故 | 原因 | 教训 |
|------|------|------|
| heredoc 连续失败 | Git Bash 下 heredoc exit 1 无输出，AI 连用两次全部失败 | 用 `write` 写文件再 Python 运行，不用 heredoc |
| 重复实现 sync.py | AI 另写临时扫描脚本，重复实现 sync.py 已有功能，浪费 2 轮工具调用 | sync.py 已做全流程，直接传参运行 |
| 时间戳取最后一条导致方向反向 | 旧版用 `matches[-1]` 取最后匹配，历史日志在末尾时取到最旧时间 | 已修复为 `max(timestamps)`，取最新时间 |
| git push 与 sync.py 混用导致分叉 | sync.py 通过 API 直接推送绕过 git，事后手动 git push 导致历史分叉 | 统一用 sync.py 管理同步，避免混用 git push |
| 多终端增量漏同步（v3.1 致命缺陷） | v3.1 增量仅依赖本地 log.md 提取变更文件，终端A 的变更记录不在终端B 的 log.md 中，导致终端B sync 时远程文件被"假定一致跳过"而漏拉取 | v3.3 新增 .syncstate.json 远程 tree SHA 哨兵 + 文件 blob 快照 diff，两终端并行同步时自动检测远程变更 |

## 文件清单

```
fact-hub-sync/
├── SKILL.md                   # 本文件
├── .gitignore                 # 排除 github-config.json + .syncstate.json + __pycache__
├── github-config.example.json # 配置模板（可公开）
├── github-config.json         # 本地配置（含 Token，不可公开）
├── CHANGELOG.md               # 版本历史
└── scripts/
    ├── sync.py                # 双向同步脚本（v2.2，推荐）
    └── push.py                # 旧版推送脚本（向后兼容）
```
