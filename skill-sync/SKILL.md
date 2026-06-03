---
name: skill-sync
version: "2.1"
description: "GitHub Skill 同步工具，支持本地↔云端双向同步。v2.1 增加 git clone 路径获取版本列表（零 HTTP），避免 Windows Git Bash 下 curl/管道 exit 49 问题。检测到远程版本更新时拉取，本地领先时推送。"
---

# GitHub Skill 同步工具

## 你的角色

你是 skill-sync 的**操作员**，不是开发者。

你的工作只有三件事：
1. 执行本文档列出的命令
2. 将结果展示给用户
3. 在用户确认后执行同步

你不需要理解脚本内部实现，不需要阅读 `references/` 目录下的文件（那是给人看的文档），**不允许编写任何新代码**。

## 最高优先级铁律

**违反即任务失败。以下行为绝对禁止：**

| 禁止行为 | 曾导致的事故 |
|---------|------------|
| 用 `write` 工具创建 .py / .sh 文件 | AI 写的临时脚本用 `.decode()` 代替 `.hexdigest()` 计算 hash，所有文件被误判"有变化"，触发大量无效 API 调用被 GitHub 限流 |
| 用 `bash` 执行 `python -c "..."` 或多行 heredoc | Windows Git Bash 下 curl 管道 exit 49/23、heredoc exit 1 无输出，浪费多轮排查 |
| 用 `bash` 执行 `curl ... \| python ...` 管道 | 同上，管道在 Git Bash 下不可靠 |
| 跳过已有脚本自己"写个简单的" | `push.py` 已实现完整预检 → 双路径推送 → 自动验证 → README 更新，自写的必然遗漏边界 case |

**允许的操作：**
- 运行已有脚本（见下方脚本索引）
- 读取配置文件
- 执行单行 bash 命令（`git --version`、`curl -s ...`）
- 向用户展示结果、询问确认

## 脚本索引

| 脚本 | 用途 | CLI 命令 |
|------|------|---------|
| `scripts/push.py` | 推送 Skill 到 GitHub（含预检、git clone/API 双路径自动切换、推送后验证、README 更新） | `python scripts/push.py --skill {name} --owner {o} --repo {r} --token {t}` |
| `scripts/readme_ops.py` | 列出远程 Skill 版本 / 更新 README 版本表 | `python scripts/readme_ops.py --action list --mode git --owner {o} --repo {r} --token {t}` |

## 概述

自动检测并同步本地 Skill 与 GitHub 仓库中的版本。支持**双向同步**：远程优先拉取，本地领先时推送到云端。

## 核心行为

- **远程优先**：检测到远程 version > 本地 version 时，下载覆盖本地
- **本地领先时**：推送到 GitHub
- **GitHub 独有 Skill**：下载到本地 Skill 目录
- **本地独有 Skill**（MCP 相关等）：保留不动，不同步
- **Token 验证**：同步前验证 token 有效性，无效则停止

## 配置管理

> **隐私保护**：`github-config.json` 包含 Token，不会被推送到 GitHub（`push.py` 自动排除）。

配置文件格式（`github-config.json`）：

```json
{
  "repo_owner": "<your-github-username>",
  "repo_name": "<your-repo-name>",
  "token": "<your-github-personal-access-token>",
  "branch": "main"
}
```

| 字段 | 说明 |
|------|------|
| `repo_owner` | GitHub 用户名或组织名 |
| `repo_name` | Skill 仓库名称 |
| `token` | GitHub Personal Access Token（需 `repo` 权限） |
| `branch` | 目标分支，默认 `main` |

## 执行步骤

### 第一步：读取配置 + 环境预检

1. 读取 `~/.alphaclaw/skills/skill-sync/github-config.json` 获取 owner、repo、token、branch
2. 运行预检命令：

```bash
git --version
```

```bash
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer {token}" https://api.github.com/user
```

**路径选择**：git 可用 + API 通 + `git config --global user.email` 已配 → git clone 路径；否则 API 路径。两者都不可用 → 停止，提示检查网络/token。

预检完成后向用户说明当前路径。

### 第二步：获取版本对比表

运行：

```bash
python scripts/readme_ops.py --action list --mode git --owner {o} --repo {r} --token {t}
```

获得远程 Skill 版本列表（JSON 格式）。同时扫描本地 `~/.alphaclaw/skills/` 下含 `SKILL.md` 的子目录，读取 frontmatter 中的 `version`。

生成对比表：

```
| Skill | 说明 | 本地版本 | 远程版本 | 状态 |
|-------|------|---------|---------|------|
```

状态枚举：`已同步` / `可更新` / `可推送` / `新增` / `本地独有`

> 版本比较由脚本内置的语义化版本比较逻辑完成，你只需展示结果。

### 第三步：询问同步方向

展示对比表，使用 AskUserQuestion 询问：

- **"是，同步"** → 执行全部（拉取 + 推送）
- **"具体指定哪些"** → 列出清单让用户勾选
- **"否，跳过"** → 结束

### 第四步：执行同步

#### 4.1 拉取（远程 → 本地）

对每个"新增"和"可更新" Skill，用 curl 从 GitHub Contents API 下载文件到本地。每个文件一条命令：

```bash
curl -s -H "Authorization: Bearer {token}" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/{owner}/{repo}/contents/{skill}/{file}?ref={branch}" | python -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode(), end='')" > ~/.alphaclaw/skills/{skill}/{file}
```

> 注意：`python -c` 在此处是管道消费端的必要操作，属于本文档明确列出的命令，不是自由发挥。不要扩展到其他场景。

#### 4.2 推送（本地 → 远程）

对每个"可推送" Skill：

```bash
python scripts/push.py --skill {skill-name} --owner {owner} --repo {repo} --token {token} --branch main
```

`push.py` 内部已完成全部流程（预检 → 路径选择 → 推送 → 验证），直接运行即可，无需额外操作。

### 第五步：报告结果

展示同步变更：新增/更新/推送列表、版本变化、失败项及原因。

## 退出前自检

在向用户报告结果之前，必须完成：

1. 本次任务中是否用 `write` 创建了 .py/.sh 文件？→ 是则**任务失败**，删除文件，重新按流程执行。
2. 是否使用了本文档未列出的 `python -c "..."` 或 heredoc？→ 是则**任务失败**。
3. 是否"简化"为自写脚本来绕过已有脚本？→ 是则**任务失败**。已有脚本经过完整测试，自写的会遗漏边界 case。

全部通过后，正常报告结果。

## Token 无效处理

检测到 GitHub token 无效时停止，提示：

> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成，然后将新 token 告诉我，我会更新配置文件。

## 配置保存规则

- 用户提供 GitHub 信息后自动保存到 `github-config.json`
- 新仓库地址/token → 询问是否覆盖

## 踩坑日志

以下事故均因 AI 不遵守规则导致，每个都造成了实际损失：

| 事故 | 原因 | 教训 |
|------|------|------|
| 临时脚本 hash 误判 | AI 写临时脚本替代 `push.py`，`.decode()` 代替 `.hexdigest()` 算 hash | 有现成脚本就用，不重复造轮子 |
| curl 反复重试死循环 | Git Bash 下 curl 管道 exit 49，AI 换 3 种姿势重试 | curl 管道不行就停，不要反复试 |
| API URL 重复拼接 `?ref=main` | AI 凭猜测拼接 URL，未先探查实际格式 | API 返回的 URL 已含参数，不要重复拼接 |
| heredoc 无输出浪费轮次 | Git Bash 下 heredoc exit 1 无输出 | 用 `write` + Python 运行文件，不用 heredoc |

## 进阶参考

以下文件仅供人类查阅，**操作员不需要阅读**：

| 文件 | 内容 |
|------|------|
| `references/sync-workflow.md` | 完整执行步骤详解 |
| `references/version-compare.md` | 版本对比表模板 + 语义化版本比较逻辑 |
| `references/troubleshooting.md` | 预检规则 + 推送路径对比 + 故障排查表 |
| `references/readme-logic.md` | README 版本列表维护逻辑 |
