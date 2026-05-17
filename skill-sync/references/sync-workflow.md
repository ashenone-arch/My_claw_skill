# 同步工作流详解

> 本文件为 skill-sync 的完整执行步骤参考。SKILL.md 中的"第一步"至"第五步"对应此处。

---

## 第一步：读取配置 + 环境预检

读取 `github-config.json`，同时执行环境预检（决定推送路径）：

**预检操作**：

1. 检查 git 是否可用 → `git --version`
2. 测试 GitHub API 连通性 → `GET /repos/{owner}/{repo}`
3. 测试 git push 基础能力 → `git config --global user.email`

**路径选择**：

| git_ok | api_ok | git_config_ok | 路径 |
|--------|--------|---------------|------|
| ✅ | ✅ | ✅ | **git clone**（最快） |
| ✅ | ✅ | ❌ | git clone（git config 补充后更快） |
| ❌ | ✅ | - | **API 路径** |
| ✅ | ❌ | - | **API 路径** |
| ❌ | ❌ | - | 停止，提示检查网络/token |

预检完成后，向用户说明当前使用的路径。

---

## 第二步：获取远程与本地版本对比

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

版本比较使用语义化版本比较（`v1.0 < v1.1 < v2.0`），禁止纯字符串比较。

---

## 第三步：询问同步方向

向用户展示版本对比表。可用选项：

- **"是，同步"** → 执行全部同步（拉取 + 推送）
- **"具体指定哪些"** → 列出清单让用户勾选
- **"否，跳过"** → 结束

---

## 第四步：执行同步

### 4.1 拉取（远程 → 本地）

对每个"新增"和"可更新" Skill：

1. 在本地创建/更新目录
2. 通过 GitHub API 获取文件列表（含 `references/` 子目录）
3. 下载每个文件（base64 解码），写入本地路径

### 4.2 推送（本地 → 远程）

对每个"可推送" Skill，使用 **scripts/push.py**：

```
python scripts/push.py \
  --skill {skill-name} --owner {owner} --repo {repo} --token {token} --branch main
```

推送后自动验证，验证失败重试（最多 1 次），仍失败则记录到结果报告。

### 4.3 README 自动维护

**时机**：任何同步导致版本变化后执行（推送成功后才执行）。

执行 **scripts/readme_ops.py**：

```
python scripts/readme_ops.py \
  --action update --owner {owner} --repo {repo} --token {token}
```

README 版本列表始终以云端 Skill 为基准。验证成功才算完成，未验证视为失败。

---

## 第五步：报告结果

展示本次同步的变更：

- 新增（远程 → 本地）：哪些 Skill
- 更新（远程 → 本地）：哪些 Skill，版本变化
- 推送（本地 → 远程）：哪些 Skill，版本变化
- README 更新状态
- 失败项及原因 + 重试建议
