---
name: skill-sync
version: "1.11"
description: "GitHub Skill 同步工具，支持本地↔云端双向同步。检测到远程版本更新时拉取，本地领先时推送。"
---

# GitHub Skill 同步工具

## 概述

自动检测并同步本地 Skill 与 GitHub 仓库中的版本。支持**双向同步**：远程优先拉取，本地领先时推送到云端。

## 核心行为

- **远程优先**：检测到远程 version > 本地 version 时，下载覆盖本地
- **本地领先时**：推送到 GitHub
- **GitHub 独有 Skill**：下载到本地 Skill 目录
- **本地独有 Skill**（MCP 相关等）：保留不动，不同步
- **Token 验证**：每次同步前验证 token 有效性，无效则停止

## 版本提取铁律（v1.6 新增）

> 以下规则基于国内网络环境下的实战教训，必须遵守。

| # | 规则 | 说明 |
|---|------|------|
| 1 | **API 优先** | 版本提取优先使用 `GET /repos/{owner}/{repo}/contents/{skill}/{file}`（返回 base64 内容），raw.githubusercontent.com 仅作最后兜底 |
| 2 | **先列目录，再取文件** | 获取远程 skill 列表后，对每个 skill 先 `GET /repos/{owner}/{repo}/contents/{skill}` 列出实际文件名，处理大小写差异（如 `skill.md` vs `SKILL.md`） |
| 3 | **交叉验证** | raw URL 返回 404 时，必须用 API 目录内容接口确认文件是否真的不存在，禁止单来源下结论 |
| 4 | **并行获取** | 所有远程 skill 的版本号在同一条消息中并行获取，禁止串行 curl |
| 5 | **语义化版本比较** | `v1.0 < v1.1 < v2.0`，禁止纯字符串比较；版本号格式不一时（如 `1.0` vs `"1.0"` vs `v1.0`），统一去掉引号和 v 前缀后比较 |

## Python 调用规范（v1.6 新增）

> Windows Git Bash 环境下 Python 调用有特定约束。

| # | 规则 |
|---|------|
| 1 | 使用系统内置 Python（AI 助手自动定位），不用系统默认的 `python` 或 `python3` |
| 2 | 禁止 `python -c "..."` + stdin pipe（exit code 49），改用文件读取方式 |
| 3 | `/tmp/` 路径在 Windows Python 中不可见，临时文件使用 `$HOME/.alphaclaw/tmp/` 替代 |
| 4 | API 响应优先用 Python `urllib.request` 直接调用，不经过 curl/heredoc 中转。curl 管道（exit 49/23）和 bash heredoc（`<< 'EOF'`）在 Windows Git Bash 下均不可靠，**禁止反复试**。需要跑脚本时优先用 `write` 工具写 `.py` 文件再用 Python 运行 |

## 下载执行铁律（v1.10 新增）

> 以下规则基于实战踩坑教训，必须遵守。

| # | 规则 | 说明 |
|---|------|------|
| 1 | **curl 只试一次，不通即切 Python** | Windows Git Bash 下 curl 管道/重定向频繁失败（exit 49/23），一旦发现管道错误，立即改用 Python `urllib.request` 直接调用 API，禁止换参数/换姿势反复试 curl |
| 2 | **先探查再执行** | 拼接 API URL、解析 JSON 响应前，先用 `print()` 打印关键字段（如 `f['url']` 是否已含 `?ref=main`）确认实际格式，禁止凭猜测拼接字符串 |
| 3 | **脚本必有错误处理** | 每个 Python 脚本必须包含 `try/except + traceback.print_exc()`，不允许裸函数调用。exit code 1 且无任何输出的脚本浪费一整轮排查轮次 |
| 4 | **有现成脚本直接跑，不重复造轮子** | 如果 Skill 自带脚本（如 `push.py`）已实现全流程（扫描+对比+推送），直接传参运行即可，不要另写临时脚本重复实现。临时脚本不仅浪费轮次，还容易因 hash 计算口径不一致导致误判 |

## 配置管理

> **隐私保护**：`github-config.json` 包含 Token 等敏感信息，**不会被推送到 GitHub 仓库**（`scripts/push.py` 自动排除）。首次使用时复制模板：

```bash
cd ~/.alphaclaw/skills/skill-sync/
cp github-config.example.json github-config.json
```

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

> **v1.10+ 优化**：版本对比 + 文件下载尽量用一个 Python 脚本完成，减少工具调用轮次。注意：`f['url']` 返回的 API URL 已含 `?ref=main`，不要重复拼接。**如果 Skill 自带可复用的脚本（如 push.py），直接用它，不要另写临时脚本。**

#### 4.2 推送（本地 → 远程）

对每个"可推送" Skill，使用 **scripts/push.py**：

```
python scripts/push.py \
  --skill {skill-name} --owner {owner} --repo {repo} --token {token} --branch main
```

推送后自动验证，验证失败重试（最多 1 次）。

> 推送路径详解（git clone vs API）→ `references/troubleshooting.md` 第二节

### 第五步：报告结果

展示本次同步的变更：新增、更新、推送列表，失败项及原因。

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
| Token 无效 | 提示重新配置 | 停止并提示用户 |
| 远程版本取不到 | 先 API 目录内容确认文件名 → API base64 解码 → raw URL 兜底 | 见"版本提取铁律" |

## 进阶参考

| 文件 | 内容 |
|------|------|
| `references/sync-workflow.md` | 完整执行步骤详解（第一步~第五步）|
| `references/version-compare.md` | 版本对比表模板 + 语义化版本比较逻辑 |
| `references/troubleshooting.md` | 预检规则 + 推送路径对比 + 故障排查表 |
