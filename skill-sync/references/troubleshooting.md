# 故障排查

## 推送路径对比

### git clone 路径（首选）

**优点**：速度快，支持批量操作，commit 历史清晰
**缺点**：依赖 git 环境，需要配置 git user.email

```bash
git clone --depth=1 https://{token}@github.com/{owner}/{repo}.git /tmp/skill-sync
cd /tmp/skill-sync
cp -r ~/.alphaclaw/skills/{skill-name}/ ./{skill-name}/
git add -A
git commit -m "Update {skill-name} to v{x.y}"
GIT_TERMINAL_PROMPT=0 git push origin main
```

### API 路径（备选）

**优点**：无 git 依赖，纯 HTTP
**缺点**：每个文件需单独获取 SHA

```python
# 推送流程（单文件 PUT）
GET /repos/{owner}/{repo}/contents/{skill}/{file}?ref=main  # 获取 SHA
PUT /repos/{owner}/{repo}/contents/{skill}/{file}           # 上传
  Body: { "message": "...", "content": "base64...", "sha": "...", "branch": "main" }
```

### 路径选择建议

| 场景 | 推荐 |
|------|------|
| 单个/少量 Skill 推送 | git clone（快）|
| 网络不稳定 | API 路径 |
| git 环境异常 | API 路径（自动回退）|

## 故障排查表

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `git clone` 超时 | 网络不稳定 | 切换 API 路径（自动）|
| git push 显示 "Everything up-to-date" 但实际没更新 | 网络中断静默失败 | 用 API 路径重试 |
| README 更新后验证失败 | 上传了旧内容/并发冲突 | 重试（幂等，最多 3 次）|
| Token 401 | token 过期或被撤销 | 提示用户重新生成 |
| Token 403 | 权限不足 | 检查 token scope 是否有 `repo` 权限 |
| 拉取时某些文件缺失 | references/ 子目录未递归获取 | 确保递归获取所有子目录 |
| 本地 Skill description 为空 | frontmatter description 缺失 | 跳过 description 字段，版本仍需获取 |
| SSL EOF violation | SSL 握手不稳定 | 全局 SSL 降级重试 |
| HTTP 422 Unprocessable | SHA 引用失效（README 被他人更新）| 重新 GET SHA 再 PUT |
| `req` KeyError | Python 循环内变量遮蔽 | 检查脚本中的变量名是否唯一 |
| hash 变化检测误判 | Python sha1 对象用了 `.decode()` | 确认用 `.hexdigest()` |
| curl pipe exit 49 / 重定向 exit 23 | Windows Git Bash 管道/文件重定向兼容性 | **禁止换姿势重试 curl**，立即改为 Python `urllib.request` 直接调用 API |
| 下载文件全部 404 | API URL 重复拼接 `?ref=main`（`f['url']` 已自带） | 拼接前先用 `print()` 查看实际 URL 格式，不要假设 |
| Python 脚本 exit 1 无输出 | 脚本没有 try/except + traceback | 每段脚本必须包含错误处理，`traceback.print_exc()` 输出具体错误 |
| heredoc `<< 'EOF'` exit 1 无输出 | Windows Git Bash heredoc 兼容性差 | 用 `write` 工具写 `.py` 文件再用 Python 运行，不依赖 heredoc |
| 临时脚本重复实现自带脚本功能 | 忽略了 Skill 已有的完整脚本 | 先检查 Skill 是否有现成脚本（如 push.py），有则直接传参运行 |

## Token 更新提示

Token 无效时：

> 检测到 GitHub token 无效（已过期或被撤销）。请访问 https://github.com/settings/tokens 重新生成，然后将新 token 告诉我，我会更新配置文件。

## 配置保存规则

- GitHub 信息自动保存到 `github-config.json`，无需每次询问
- 新仓库地址/token → 询问是否覆盖（"确认用新的替换？"）
