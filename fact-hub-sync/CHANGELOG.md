# Fact Hub Sync CHANGELOG

> 版本历史记录。

## v2.1 (2026-05-29)

### 性能优化
- **Git blob SHA 对比**（核心）：冲突检测阶段从逐文件 API 调用改为本地计算 Git blob SHA 后直接与 `remote_tree` 对比
  - `scan_local_files()` 新增 `git_blob_sha` 字段（公式：`sha1(b"blob " + len + b"\x00" + content)`）
  - 冲突检测循环：`remote_tree[rel_path] == git_blob_sha` 替代 `get_remote_file_sha1()`
  - N 文件 → 0 次额外 API 调用（v2.0 为 N 次 `GET /contents/{file}`）
- 版本号统一为 2.1（sync.py docstring / print / argparse 共 4 处）

### 文档更新
- SKILL.md：概述、frontmatter version、文件清单 同步更新

## v2.0 (2026-05-22)

### 核心修复
- **时间戳提取 Bug 修复**（致命）：`extract_last_log_time()` 和 `get_remote_log_time_and_sha1()` 中 `matches[-1]` 改为 `max(timestamps)`
  - 旧逻辑取正则匹配的最后一条，如果历史日志在文件末尾则取到最旧时间，导致方向判定完全反向
  - 新逻辑取所有匹配时间戳中的最大值，确保始终获取最新日志时间
  - 函数重命名：`extract_last_log_time` → `extract_latest_log_time`

### 新增功能
- **删除检测（安全保护）**：新增 `remote_deleted_locally` 分类，检测\"远程存在但本地已删除\"的文件
  - 默认不自动删除远程文件（安全考虑），仅在 SUMMARY 中列出
  - 新增 `--allow-delete` CLI 参数，需用户显式确认后才执行远程删除
  - 结果 JSON 新增 `locally_deleted` 统计和 `locally_deleted_files` 列表

### 文档更新
- **Git 交互警告**：新增\"与 Git 的交互\"章节，说明 sync.py (API) 和 git push 混用导致历史分叉的风险及处理方式
- **删除同步章节**：新增\"删除同步\"章节，描述 `--allow-delete` 模式的使用流程和用户确认要求
- 同步逻辑表新增\"远程有、本地已删除\"行

### 改进
- 版本号统一为 2.0（sync.py 从 v2.1 → v2.0，skill.md 从 v1.3 → v2.0）
- User-Agent 版本标识同步更新

---

## v1.3 (2026-05-19)

### 重大改进
- **log.md 优先裁定**（sync.py v2.1）：冲突方向判断从"逐文件查 commit 时间"改为"比较 log.md 最后日志时间"
  - 两边 log.md 内容一致 → 快速路径，全跳过（避免因文件时间戳不可靠导致的误判）
  - 远程日志更新 → 全量拉取覆盖本地
  - 本地日志更新 → 全量推送覆盖远程
  - log.md 不存在 → 回退到逐文件 commit 时间（兜底）
- **效率提升**：冲突裁定从 O(n) 次 API 调用降为 1 次（只查远程 log.md）

### 设计考量
- log.md 是 Fact Hub 的权威变更记录（精确到分钟），比文件 mtime 和 git commit 时间更可靠
- 避免回滚场景下本地 mtime 更新导致误推

---

## v1.2 (2026-05-19)

### 重大更新
- **新增 `sync.py`**：双向同步脚本，支持 sync/push/pull 三种模式，替代旧 push.py 成为推荐工具
- **双向同步逻辑**：远程优先，冲突时比较最后修改时间裁定方向（远程更新→拉取，本地更新→推送）
- **远程独有文件自动拉取**：解决旧版只能推送、不能拉取的缺陷

### 优化
- 执行步骤引用从 push.py 切换为 sync.py
- 快速参考表新增 sync/push/pull 三种模式的命令
- 保留 push.py 向后兼容

### 修复
- 本次同步恢复了远程独有的 `机器人/` 目录 3 个文件到本地

---

## v1.1 (2026-05-19)

### 简化
- **执行步骤从 5 步减为 3 步**：push.py 内部已完成扫描+对比+推送全流程，无需另写临时脚本重复实现

### 新增
- **Windows 环境注意事项**：3 条规则
  1. 禁止 bash heredoc（`<< 'EOF'`），改用 `write` + `run` 文件方式
  2. 不要另写临时扫描脚本，直接跑 push.py
  3. 使用系统内置 Python 绝对路径

### 教训来源
- 实战中连用两次 heredoc 全部 exit code 1，且另写扫描脚本重复实现了 push.py 已有功能，浪费 2 轮工具调用

---

## v1.0

- Fact Hub 同步工具初始版本
- 增量推送（SHA1 hash 对比）
- push.py 脚本实现扫描+对比+推送
- github-config.json 本地配置管理
