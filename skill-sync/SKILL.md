---
name: skill-sync
version: v1.2
description: 当用户需要同步本地 Skill 与 GitHub 仓库版本、检查 Skill 更新、或更新本地 Skill 至最新时使用。触发场景包括："同步我的 skill"、"检查 skill 版本"、"更新本地 skill"、"同步 skill 仓库"、"我的 skill 需要更新吗"、"把 GitHub 的 skill 拉下来"、"自动同步 skill"、"把本地 skill 推到云端"、"上传 skill"、"更新 skill 到 GitHub"。即使用户只说"同步"、"更新"（在有 Skill 相关上下文时），也应触发。
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
- **README 自动维护**：任何版本变化后自动更新仓库 README 版本列表

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

### 第一步：读取配置 + 环境预检（并行）

读取 `github-config.json`，同时执行**环境预检**（决定后续用哪种推送路径）：

**预检操作**（同时执行）：
1. 检查 git 是否可用：`git --version`
2. 测试 GitHub API 连通性：快速 GET `/user` 验证 token
3. 测试 git push 基础能力

**路径选择规则**：
- 上述 3 项全部通过 → 使用 **git clone 路径**（最快最可靠）
- 任一失败 → 回退到 **GitHub API 路径**（纯 HTTP，无 git 依赖）

预检完成后，向用户说明当前使用的路径（影响后续推送策略）。

### 第二步：获取远程与本地版本对比

**远程列表**：调用 `GET /repos/{owner}/{repo}/contents`（分支=main），筛选目录类型。
对每个 Skill 子目录读取 `SKILL.md` frontmatter 的 `version` 和 `description`。

**本地列表**：扫描 `~/.alphaclaw/skills/` 下含 `SKILL.md` 的子目录，读取 frontmatter 的 `name`、`version`、`description`。

**生成对比表**：
```
| Skill | 说明 | 本地版本 | 远程版本 | 状态 |
|-------|------|---------|---------|------|
| xxx | 描述... | v1.0 | v1.0 | 已同步 |
| yyy | 描述... | v0.9 | v1.0 | 可更新（远程 > 本地）|
| zzz | 描述... | v1.2 | v1.0 | 可推送（本地 > 远程）|
| www | 描述... | - | v1.0 | 新增 |
```

**版本比较**：使用语义化版本比较（v1.0 < v1.1 < v2.0），纯字符串比较无效。

### 第三步：询问同步方向

向用户展示版本对比表。可用选项：
- **"是，同步"** → 执行全部同步（拉取 + 推送）
- **"具体指定哪些"** → 列出清单让用户勾选
- **"否，跳过"** → 结束

### 第四步：执行同步

#### 4.1 拉取（远程 → 本地）

对每个"新增"和"可更新" Skill：
1. 在本地创建/更新目录
2. 通过 GitHub API 获取文件列表（含 `references/` 子目录）
3. 下载每个文件（base64 解码），写入本地路径
4. 完成后报告

#### 4.2 推送（本地 → 远程）

对每个"可推送" Skill：

**git clone 路径**（首选）：
```
1. 在临时目录执行：git clone --depth=1 https://<token>@github.com/{owner}/{repo}.git
2. 替换/创建 Skill 目录下的所有文件
3. git add . && git commit -m "Update {skill-name} to v{x.y}"
4. git push origin main
5. 验证：检查 push 输出是否包含 "main -> main"
   - 成功 → 继续
   - 失败 → 记录到结果报告，询问用户是否用 API 路径重试
```

**GitHub API 路径**（备选）：
```
1. 获取仓库根目录 SHA（用于创建 commit）
2. 对每个文件调用 GET /contents/{path} 获取 SHA（用于更新）
3. 调用 PUT /contents/{path} 上传每个文件（base64 编码）
4. 全部完成后报告状态
```

#### 4.3 README 自动维护（关键步骤）

**时机**：任何同步操作导致版本变化后执行（推送成功后才执行）。

**维护逻辑**：
1. 扫描 `~/.alphaclaw/skills/` 下所有含 `SKILL.md` 的子目录
2. 读取每个 Skill 的 frontmatter：`name`、`version`、`description`（截取前 50 字符）
3. 生成本地 Skill 版本列表
4. 调用 GitHub API 获取当前 README 的 SHA
5. **用 Python urllib 直接更新 README**（绕过 git，最可靠）：
   - 构造新 README 内容（格式见下方）
   - PUT /repos/{owner}/{repo}/contents/README.md（base64 编码，附 SHA）
6. **验证**：更新后立即 GET README 内容，确认版本列表中包含所有正确版本号
   - 验证成功 → 继续
   - 验证失败 → 重试（最多 3 次），仍失败则记录到结果报告

**README 格式**：
```markdown
# My Claw Skills

> 个人日常投资研究使用的 AlphaClaw Skill 集合，版本信息见各 Skill 的 Release

## 目录

| Skill | 说明 | 版本 |
|-------|------|------|
| [skill-name](skill-name/) | 描述... | v1.0 |
...

## 使用方式

在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。

## 版本说明

每个 Skill 独立打 Tag，格式为 `{skill-name}-v{version}`。
如需回溯历史版本，请访问对应 Tag 的 Release 页面。

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。
投资有风险，决策需谨慎。
```

### 第五步：报告结果

展示本次同步的变更：
- 新增（远程 → 本地）：哪些 Skill
- 更新（远程 → 本地）：哪些 Skill，版本变化
- 推送（本地 → 远程）：哪些 Skill，版本变化
- README 更新状态
- 失败项及原因 + 重试建议

## 配置保存规则

用户提供 GitHub 信息后自动保存到 `github-config.json`，无需每次询问。
新仓库地址/token → 询问是否覆盖（"确认用新的替换？"）。

## Token 更新提示

Token 无效时：
> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成，然后将新 token 告诉我，我会更新配置文件。

## 技术细节（执行时内部使用）

### 环境预检代码模板

```python
# 预检：git 可用性
import subprocess
try:
    result = subprocess.run(['git', '--version'], capture_output=True, timeout=5)
    git_ok = result.returncode == 0
except:
    git_ok = False

# 预检：GitHub API 连通性
import urllib.request
try:
    req = urllib.request.Request('https://api.github.com/user', headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=10) as r:
        api_ok = r.status == 200
except:
    api_ok = False

# 路径选择
if git_ok and api_ok:
    path = 'git_clone'
else:
    path = 'api_only'
```

### README 更新代码模板（最可靠）

```python
import urllib.request, json, base64

def update_readme(token, owner, repo, content):
    # 获取当前 SHA
    req = urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo}/contents/README.md?ref=main')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req) as r:
        sha = json.loads(r.read())['sha']
    
    # 上传新内容
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = json.dumps({
        'message': 'chore: sync skills and update README [skip ci]',
        'sha': sha, 'content': encoded, 'branch': 'main'
    }).encode('utf-8')
    req2 = urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo}/contents/README.md', data=data)
    req2.add_header('Authorization', f'Bearer {token}')
    req2.get_method = lambda: 'PUT'
    with urllib.request.urlopen(req2) as r:
        result = json.loads(r.read())
    
    # 验证
    return 'content' in result

def verify_readme(token, owner, repo, expected_versions):
    req = urllib.request.Request(f'https://raw.githubusercontent.com/{owner}/{repo}/main/README.md')
    with urllib.request.urlopen(req, timeout=15) as r:
        content = r.read().decode('utf-8')
    for skill, ver in expected_versions.items():
        if f'| {skill} |' in content and f'| v{ver} |' in content:
            continue
        else:
            return False
    return True
```

### git push 验证代码模板

```python
result = subprocess.run(
    ['git', 'push', 'origin', 'main'],
    capture_output=True, text=True, timeout=60,
    env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
)
# 验证成功：检查输出是否包含 "main -> main"
push_ok = 'main -> main' in result.stdout or result.returncode == 0
if not push_ok:
    # 重试一次
    result = subprocess.run(['git', 'push', 'origin', 'main'], ...)
```

## 注意事项

- GitHub API 认证：`Authorization: Bearer {token}`
- GitHub API 返回文件内容为 base64，需解码
- 仓库只同步含 `SKILL.md` 的目录形式 Skill，根目录文件不下载
- `references/` 子目录随 Skill 一起同步
- 本地 Skill 目录中如有 `github-config.json`，上传时排除（不在 GitHub 暴露）
- README 更新必须验证成功才算完成，未验证视为失败需重试