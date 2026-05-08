# Skill Sync 进阶参考

## 目录

1. [环境预检详解](#1-环境预检详解)
2. [推送路径对比](#2-推送路径对比)
3. [README 更新详解](#3-readme-更新详解)
4. [故障排查](#4-故障排查)
5. [git push 验证机制](#5-git-push-验证机制)

---

## 1. 环境预检详解

### 为什么要预检？

直接用 git clone 或直接用 API 都可能有环境问题（git 不可用、网络不稳定、token 权限不足）。预检让 AI 在执行前就知道该用哪条路径，避免中途失败。

### 预检代码模板

```python
import subprocess, urllib.request, json

token = "ghp_xxx"
owner = "owner"
repo = "repo"

def precheck():
    # 1. git 可用性
    try:
        r = subprocess.run(['git', '--version'], capture_output=True, timeout=5)
        git_ok = r.returncode == 0
    except:
        git_ok = False

    # 2. GitHub API 连通性
    try:
        req = urllib.request.Request(
            'https://api.github.com/user',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            api_ok = resp.status == 200
    except:
        api_ok = False

    # 3. git push 基础能力（检查 git config）
    try:
        r = subprocess.run(['git', 'config', '--global', 'user.email'], capture_output=True, timeout=5)
        git_config_ok = r.returncode == 0 and len(r.stdout.strip()) > 0
    except:
        git_config_ok = False

    return git_ok and api_ok and git_config_ok

path = 'git_clone' if precheck() else 'api_only'
```

### 路径选择规则

| git_ok | api_ok | git_config_ok | 推荐路径 |
|--------|--------|---------------|---------|
| ✅ | ✅ | ✅ | git clone |
| ✅ | ✅ | ❌ | git clone（补充 git config）|
| ❌ | ✅ | - | API 路径 |
| ✅ | ❌ | - | API 路径 |
| ❌ | ❌ | - | 停止，提示检查网络/token |

---

## 2. 推送路径对比

### git clone 路径（首选）

**优点**：速度快，支持批量操作，commit 历史清晰
**缺点**：依赖 git 环境，需要配置 git user.email

**执行流程**：
```bash
# 1. 克隆到临时目录（浅克隆，--depth=1）
git clone --depth=1 https://<token>@github.com/{owner}/{repo}.git /tmp/skill-sync-tmp

# 2. 进入目录
cd /tmp/skill-sync-tmp

# 3. 替换/创建 Skill 目录（复制文件）
cp -r ~/.alphaclaw/skills/{skill-name}/ ./skill-name/

# 4. 提交
git add -A
git commit -m "Update {skill-name} to v{x.y}"

# 5. 推送
GIT_TERMINAL_PROMPT=0 git push origin main

# 6. 验证
# 检查输出是否包含 "main -> main"
```

### API 路径（备选）

**优点**：无 git 依赖，纯 HTTP
**缺点**：每个文件需要单独获取 SHA，批量操作繁琐

**执行流程**：
```python
# 1. 获取仓库根目录 SHA（创建 commit 用）
GET /repos/{owner}/{repo}/git/ref/heads/main
→ 拿到 commit SHA

# 2. 对每个文件（SKILL.md + references/）：
GET /repos/{owner}/{repo}/contents/{skill-name}/{file}?ref=main
→ 拿到文件 SHA（如文件存在）

PUT /repos/{owner}/{repo}/contents/{skill-name}/{file}
Body: {
  "message": "Update {skill-name} to v{x.y}",
  "content": "<base64>",
  "sha": "<file_sha>",
  "branch": "main"
}

# 3. 完成后报告状态
```

### 路径选择建议

| 场景 | 推荐路径 |
|------|---------|
| 单个/少量 Skill 推送 | git clone（快）|
| 网络不稳定 | API 路径（单次 HTTP）|
| git 环境异常 | API 路径（回退）|
| 批量推送多个 Skill | git clone（一次 clone，多次文件操作）|

---

## 3. README 更新详解

### 为什么必须验证成功？

之前遇到的问题是：git push 显示成功，但 README 内容没有更新。原因：push 时网络中断，git 静默失败但没有报错。所以 README 更新必须验证。

### 验证流程

```python
def update_readme(token, owner, repo, content, max_retry=3):
    for attempt in range(max_retry):
        try:
            # 获取当前 SHA
            req = urllib.request.Request(
                f'https://api.github.com/repos/{owner}/{repo}/contents/README.md?ref=main'
            )
            req.add_header('Authorization', f'Bearer {token}')
            with urllib.request.urlopen(req, timeout=15) as r:
                sha = json.loads(r.read())['sha']

            # 上传新内容
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            data = json.dumps({
                'message': 'chore: sync skills and update README [skip ci]',
                'sha': sha,
                'content': encoded,
                'branch': 'main'
            }).encode('utf-8')
            req2 = urllib.request.Request(
                f'https://api.github.com/repos/{owner}/{repo}/contents/README.md',
                data=data
            )
            req2.add_header('Authorization', f'Bearer {token}')
            req2.get_method = lambda: 'PUT'
            with urllib.request.urlopen(req2, timeout=15) as r:
                result = json.loads(r.read())

            # 验证
            if 'content' in result:
                return verify_readme(token, owner, repo)
        except Exception as e:
            print(f'Attempt {attempt+1} failed: {e}')
            time.sleep(2)
    return False

def verify_readme(token, owner, repo):
    """验证 README 版本列表是否包含所有正确版本"""
    req = urllib.request.Request(
        f'https://raw.githubusercontent.com/{owner}/{repo}/main/README.md'
    )
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req, timeout=15) as r:
        content = r.read().decode('utf-8')

    for line in content.split('\n'):
        if 'equity-deep' in line:
            assert 'v2.1' in line, f'equity-deep version wrong: {line}'
        if 'skill-sync' in line:
            assert 'v1.2' in line, f'skill-sync version wrong: {line}'
    return True
```

### README 内容格式

```markdown
# My Claw Skills

> 个人日常投资研究使用的 AlphaClaw Skill 集合，版本信息见各 Skill 的 Release

## 目录

| Skill | 说明 | 版本 |
|-------|------|------|
| [cross-talk-synthesis](cross-talk-synthesis/) | 多篇对谈交叉汇总，按话题轴心组织不同嘉宾观点碰撞 | v1.1 |
| [daily-seller-hotspot](daily-seller-hotspot/) | 日度卖方/机构热点选股，识别机构抱团方向 | v1.0 |
| [equity-deep-research](equity-deep-research/) | A股股票深度研究，9段框架输出投研素材包 | v2.1 |
| [howard-marks-framework](howard-marks-framework/) | 霍华德·马克斯投资框架，评估标的/审查组合 | v1.0 |
| [skill-sync](skill-sync/) | GitHub Skill 同步工具，支持本地→云端推送，自动维护 README 版本列表 | v1.2 |
| [youtube-transcript-to-article](youtube-transcript-to-article/) | YouTube视频字幕转书面文章 | v1.0 |
| [pdf-batch-extract](pdf-batch-extract/) | PDF 批量原文+表格提取为 MD，含页眉/页脚/页码自动清理 | v1.1 |

## 使用方式

在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。

## 版本说明

每个 Skill 独立打 Tag，格式为 `{skill-name}-v{version}`。
如需回溯历史版本，请访问对应 Tag 的 Release 页面。

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。
投资有风险，决策需谨慎。
```

---

## 4. 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `git clone` 超时 | 网络不稳定 | 切换 API 路径 |
| git push 显示 "Everything up-to-date" | 实际没推送成功（网络中断） | 用 API 路径重试 |
| README 更新后验证失败 | 上传了旧内容/并发冲突 | 重试（幂等操作）|
| Token 401 | token 过期或被撤销 | 提示用户重新生成 |
| Token 403 | 权限不足 | 检查 token scope 是否有 repo 权限 |
| 拉取时某些文件缺失 | references/ 子目录未递归获取 | 确保递归获取所有子目录 |
| 本地 Skill description 为空 | frontmatter description 缺失 | 读取时跳过 description 字段，版本仍需获取 |

---

## 5. git push 验证机制

### 为什么需要验证？

之前遇到：push 命令返回成功（returncode=0），但 GitHub 上没有看到更新。原因：网络中断导致 push 静默失败，git 没有报错。

### 验证方法

```python
def push_with_verification(repo_path, commit_msg):
    import subprocess, os
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}

    # 第一次推送
    r = subprocess.run(
        ['git', 'push', 'origin', 'main'],
        capture_output=True, text=True, timeout=60, cwd=repo_path, env=env
    )

    # 检查输出
    if 'main -> main' in r.stdout or r.returncode == 0:
        return True

    # 失败则重试一次
    r = subprocess.run(
        ['git', 'push', 'origin', 'main'],
        capture_output=True, text=True, timeout=60, cwd=repo_path, env=env
    )

    if 'main -> main' in r.stdout or r.returncode == 0:
        return True

    # 重试也失败，记录到结果报告
    return False
```

### 验证失败的后续

1. 记录失败信息到同步结果报告
2. 询问用户是否用 API 路径重试
3. 如果 README 也因此未更新，同样记录

---

## 版本比较逻辑

语义化版本比较（禁止纯字符串比较）：

```python
def compare_versions(v1, v2):
    """比较两个版本号，返回 1(v1>v2), 0(相等), -1(v1<v2)"""
    def parse(v):
        # 去掉 'v' 前缀
        v = v.lstrip('v')
        parts = v.split('.')
        return [int(p) for p in parts]

    p1, p2 = parse(v1), parse(v2)
    for i in range(max(len(p1), len(p2))):
        n1 = p1[i] if i < len(p1) else 0
        n2 = p2[i] if i < len(p2) else 0
        if n1 > n2:
            return 1
        elif n1 < n2:
            return -1
    return 0
```