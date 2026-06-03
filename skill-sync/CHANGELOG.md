# Skill Sync CHANGELOG

> 版本历史记录。

## v2.1 (2026-06-03)

### Added
- `readme_ops.py` 新增 `get_remote_skills_via_git()` 函数：通过 `git clone --depth 1` 获取远程仓库到临时目录，遍历读取 `SKILL.md` 提取版本号，完成后自动清理。零 HTTP 请求，彻底避开 Windows Git Bash 下 curl/管道 exit 49 问题
- `--action list` 新增 `--mode git` 参数：优先走 git clone，失败自动 fallback 到 API 路径
- `--action update` 保持不变（写 README 需要 API sha）

### Changed
- SKILL.md 脚本索引和第二步命令改为 `--mode git`

### Rationale
- v2.0 的执行步骤虽然脚本化，但 `readme_ops.py --action list` 内部仍走 GitHub API（Python `urllib` / `requests`），在 Windows Git Bash 下同样会 exit 49
- 预检阶段已确认 git 可用 → git clone 是更稳定的版本获取路径
- `--action update` 保留 API 路径，因为写 README 需要 API 返回的文件 sha

---

## v2.0 (2026-06-03)

### 重大重构：从"教材"到"操作手册"

v1.x 系列的核心问题是 SKILL.md 混合了"怎么做"（代码模板、API URL、实现细节）和"用什么做"（脚本命令），导致 AI 倾向于选择前者——自己写代码而非运行已有脚本。

v2.0 从根本上重构了 SKILL.md 的设计哲学：

#### 架构变更

- **角色定义前置**：SKILL.md 开头明确定义 AI 的角色是"操作员"而非"开发者"，限定其工作范围为三件事：执行命令、展示结果、确认同步
- **最高优先级铁律**：将分散在全文的防御性规则（禁止自写脚本、禁止 python -c、禁止 heredoc）集中为一张表，并附上每个规则对应的历史事故原因，让 AI 理解"为什么不能这样做"
- **黑盒化**：从 SKILL.md 中删除所有 API URL 实现细节、Python 代码模板、版本提取流程描述，改为"运行脚本 X，拿到结果 Y"。references/ 目录明确标注"操作员不需要阅读"
- **执行步骤脚本化**：每一步从"描述怎么做"改为"运行这条命令"。第二步从"调用 GitHub API 获取远程 Skill 列表"改为 `python scripts/readme_ops.py --action list ...`
- **退出前自检锁**：第五步后新增强制自检，要求 AI 在报告结果前检查自己是否违规
- **踩坑日志**：将抽象规则改写为具体事故案例（hash 误判、curl 死循环、URL 拼接错误、heredoc 无输出），每个都标注了实际损失

#### 脚本增强

- **readme_ops.py 新增 `--action list`**：原先只有 `--action update`（更新 README），现在支持 `--action list` 获取远程 Skill 版本列表，供第二步版本对比使用。参数校验逻辑提升到 action 分支之前

#### 文档变更

- SKILL.md 从 158 行精简到 194 行（含新增的自检和踩坑日志），核心行为描述密度大幅降低
- 移除所有代码模板和 API URL，消除 AI "学习-复制"的源头
- 快速参考表改为脚本索引表，只列出已有脚本和 CLI 命令

#### 设计原则

v2.0 的修改遵循以下原则（来自 skill-sync 使用者的反馈分析）：
1. 负向提示词必须放在正向指令之前
2. 模型身份应为"调度员/操作员"而非"程序员"
3. 代码逻辑应黑盒化——只给接口不给实现
4. 退出前自检利用 Chain-of-Thought 延迟纠正行为
5. 踩坑日志比抽象规则更有效（AI 对因果故事的遵守率高于对规则列表的遵守率）

---

## v1.11 (2026-06-01)

### Fixed
- 修复 Windows Git Bash 下 Python 脚本执行路径问题
- push.py 增加 SSL 降级重试机制

### Changed
- 下载执行铁律新增"有现成脚本直接跑，不重复造轮子"

---

## v1.10 (2026-05-30)

### Added
- 下载执行铁律：curl 只试一次、先探查再执行、脚本必有错误处理、有现成脚本直接跑

### Changed
- 版本对比 + 文件下载优化为单 Python 脚本完成，减少工具调用轮次

---

## v1.9 (2026-05-28)

### Fixed
- push.py hash 变更检测：`sha1.decode()` 改为 `sha1.hexdigest()`，修复误判

### Changed
- push.py 增加 API 路径文件变化检测（本地内容 hash vs 远程内容 hash），避免无变化文件重复上传

---

## v1.8 (2026-05-26)

### Added
- README 自动维护逻辑（readme_ops.py）：工作流分阶段表格 + 锚点保护模式
- SKILL_META 字典维护各 Skill 的阶段归属和功能描述

---

## v1.7 (2026-05-25)

### Changed
- push.py 重构：git clone 路径优化为浅克隆（--depth=1），提升速度

---

## v1.6 (2026-05-23)

### Added
- 版本提取铁律 5 条（API 优先、先列目录再取文件、交叉验证、并行获取、语义化版本比较）
- Python 调用规范 4 条（内置 Python、禁止 python -c、/tmp/ 不可见、API 优先用 urllib）

---

## v1.5 (2026-05-20)

### Added
- push.py 增加 API 路径（备选），当 git clone 不可用时自动切换

---

## v1.4 (2026-05-18)

### Added
- Token 验证：每次同步前验证 token 有效性

---

## v1.3 (2026-05-16)

### Added
- README.md 同步功能
- 本地独有 Skill 保留逻辑

---

## v1.2 (2026-05-14)

### Fixed
- git push 验证机制：检查 stdout 含 "main -> main" 确认推送成功

---

## v1.1 (2026-05-12)

### Added
- 双向同步支持：远程优先拉取 + 本地领先推送
- github-config.json 配置管理

---

## v1.0 (2026-05-10)

### Added
- 初始版本，支持从 GitHub 拉取 Skill 到本地
- 基础 GitHub API 调用和版本比较
