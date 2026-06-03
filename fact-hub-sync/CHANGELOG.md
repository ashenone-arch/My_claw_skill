# Fact Hub Sync CHANGELOG

> 版本历史记录。

## v3.1 (2026-06-03)

### 新增：log.md 驱动的增量同步

知识库文件增多后，全量扫描所有 .md 文件计算 hash 的耗时线性增长。v3.1 利用 fact-hub v2.2 升级后的 log.md（含 `文件:` 字段），实现增量同步：

- **sync.py 新增 `--files` 参数**：逗号分隔的文件路径列表，仅对指定文件做扫描和 hash 计算（+ log.md 和 README.md 始终包含），其余文件假定与远程一致跳过
- **`scan_local_files()` 增加 `filter_files` 参数**：增量模式下跳过非目标文件
- **SKILL.md 执行步骤重构**：从 3 步（读配置→全量 sync→报告）升级为 4 步（读配置→读 log.md 提取变更→增量 sync→报告 + 追加 SYNC_MARK）
- **SYNC_MARK 机制**：每次同步完成后向 log.md 追加 `<!-- SYNC YYYY-MM-DD HH:MM | push: N, pull: M -->` 标记，作为下次增量同步的起点

#### 效果

| 场景 | v3.0 | v3.1 |
|------|------|------|
| 200 文件，2 个变更 | 200 次 read + 200 次 SHA | 4 次 read + 4 次 SHA |
| 200 文件，无变更 | 200 次 read + 200 次 SHA | 1 次 read log.md → 跳过 |
| 首次同步 | 全量扫描 | 回退全量（无 SYNC_MARK） |

### 依赖

- **fact-hub v2.2**：log.md 新增 `文件:` 字段记录每次写入的变更文件路径

---

## v3.0 (2026-06-03)

### 重大重构：加上"防 AI 越权"框架

v2.x 系列的 SKILL.md 执行步骤已经是脚本化指令（"直接运行 sync.py"），比 skill-sync v1.x 好得多。但缺少 skill-sync v2.0 引入的那套防止 AI 越权的框架。

v3.0 补上了完整的防护：

#### 新增

- **角色定义前置**：SKILL.md 开头明确定义 AI 为"操作员"，限定工作范围为三件事：读配置、跑 sync.py、展示结果
- **最高优先级铁律**：4 条禁止行为 + 对应的事故原因（heredoc 连续失败、重复实现 sync.py、时间戳取 last 导致方向反向、git 混用导致分叉）
- **退出前自检**：报告结果前检查 3 项：是否 write .py/.sh、是否 python -c/heredoc、是否自行调 API
- **踩坑日志**：4 个真实事故案例（来自 v1.1 和 v2.0 的实战教训）
- **`.gitignore`**：排除 `github-config.json`（含 Token）和 `__pycache__/`，提供 Git 层面的兜底保护

#### 架构变更

- **黑盒化**：从"快速参考"表中移除"GitHub API"作为检查差异的方式，改为全部依赖 sync.py
- **规则集中化**：将散落在"Windows 环境注意事项"中的规则整合进最高优先级铁律和踩坑日志
- **冗余精简**：移除"双向同步逻辑"详细表格（sync.py 内部已处理，AI 不需要知道细节）和"与 Git 的交互"章节（合并到踩坑日志）
- **触发条件保留**：保持不变，确保 skill 正常触发

#### 设计原则

与 skill-sync v2.0 一致：
1. 负向提示词放在正向指令之前
2. 模型身份为"操作员"而非"开发者"
3. 实现细节黑盒化——只给接口不给实现
4. 退出前自检利用 Chain-of-Thought 延迟纠正
5. 踩坑日志比抽象规则更有效

---

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
