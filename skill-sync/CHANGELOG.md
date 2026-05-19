# Skill Sync CHANGELOG

> 版本历史记录。

## v1.11 (2026-05-19)

### 新增
- **下载执行铁律 #4：有现成脚本直接跑，不重复造轮子** — Skill 自带脚本（如 push.py）已实现全流程时，直接传参运行，禁止另写临时脚本重复实现。临时脚本浪费轮次且容易因 hash 口径不一致导致误判

### 优化
- Python 调用规范 #4 扩展：heredoc（`<< 'EOF'`）在 Windows Git Bash 下与 curl pipe 同样不可靠，一并纳入禁止范围。需要跑脚本时优先 `write` + `run` 文件方式
- 第四步 4.1 提示扩展：强调复用自带脚本

### 教训来源
- fact-hub-sync 实战：连用两次 heredoc 全部 exit code 1，且另写扫描脚本重复实现了 `push.py` 已有功能

---

## v1.10 (2026-05-19)

### 新增
- **下载执行铁律**：新增 3 条强制执行规则，基于 Windows Git Bash 实战踩坑
  1. **curl 只试一次，不通即切 Python** — 管道 exit 49 或重定向 exit 23 后禁止换姿势重试，立即改用 `urllib.request`
  2. **先探查再执行** — 拼接 API URL 前先用 `print()` 确认实际字段格式，禁止凭猜测拼接
  3. **脚本必有错误处理** — 每段 Python 必须 `try/except + traceback.print_exc()`，禁止裸函数调用

### 优化
- Python 调用规范 #4 强化：从 "curl 保存文件再 Python 读取" 改为 "Python 直接调用 API，curl 失败后禁止重试 curl"
- 第二步"获取版本对比"建议合并为单 Python 脚本，减少工具调用轮次
- 第四步 4.1 新增注意事项：`f['url']` 已含 `?ref=main`，不要重复拼接

### 文档
- `references/troubleshooting.md` 故障排查表新增 3 条：curl exit 49/23、API 404（URL 重复拼接）、脚本 exit 1 无输出
- `references/sync-workflow.md` 第二步和 4.1 新增 v1.10 提示

---

## v1.9

- Skill 同步工具初始发布版本，支持拉取 + 推送双向同步
- README 以云端为基准自动维护
- 版本提取铁律 + Python 调用规范
