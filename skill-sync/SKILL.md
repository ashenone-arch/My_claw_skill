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

### 第一步：读取配置 + 环境预检

读取 `github-config.json`，同时执行环境预检（决定推送路径）：

**预检操作**：
1. 检查 git 是否可用
2. 测试 GitHub API 连通性
3. 测试 git push 基础能力

**路径选择**：
- 全部通过 → **git clone 路径**（最快）
- 任一失败 → 回退到 **GitHub API 路径**

> 预检完成后，向用户说明当前使用的路径。

### 第二步：获取远程与本地版本对比

**远程列表**：调用 `GET /repos/{owner}/{repo}/contents`（分支=main），筛选目录类型，读取 frontmatter `version` 和 `description`。

**本地列表**：扫描 `~/.alphaclaw/skills/` 下含 `SKILL.md` 的子目录，读取 frontmatter。

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

#### 4.2 推送（本地 → 远程）

对每个"可推送" Skill，使用 **scripts/push.py**：
```
python "D:\AlphaEngine\resources\python\python\python.exe" scripts/push.py \
  --skill {skill-name} --owner {owner} --repo {repo} --token {token} --branch main
```

**路径选择**：
- git clone 路径（首选）：快，完整 git 操作
- API 路径（备选）：无 git 依赖，仅 HTTP

> 推送后自动验证，验证失败重试（最多 1 次），仍失败则记录到结果报告。

#### 4.3 README 自动维护

**时机**：任何同步导致版本变化后执行（推送成功后才执行）。

执行 **scripts/readme_ops.py**：
```
python "D:\AlphaEngine\resources\python\python\python.exe" scripts/readme_ops.py \
  --action update --owner {owner} --repo {repo} --token {token}
```

**维护逻辑**：
1. 扫描 `~/.alphaclaw/skills/` 下所有含 `SKILL.md` 的子目录
2. 读取每个 Skill 的 frontmatter：`name`、`version`、`description`
3. 生成本地 Skill 版本列表
4. 调用 API 获取 README SHA
5. 更新 README（base64 编码）
6. **验证**：GET README 确认版本列表正确（失败重试最多 3 次）

> 验证成功才算完成，未验证视为失败。

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

## 快速参考

| 场景 | 操作 | 工具/脚本 |
|------|------|---------|
| 检查版本差异 | 同步前对比 | 自动生成对比表 |
| 拉取远程更新 | 下载新/可更新 Skill | GitHub API |
| 推送本地 Skill | 上传可推送 Skill | scripts/push.py |
| 维护 README | 版本变化后自动更新 | scripts/readme_ops.py |
| Token 无效 | 提示重新配置 | 停止并提示用户 |

## 进阶参考

> 高级用法、故障排查、API 路径详细说明 → 见 `REFERENCE.md`