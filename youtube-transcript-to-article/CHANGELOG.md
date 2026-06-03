# youtube-transcript-to-article 版本历史

## v3.0 (2026-06-03)

### 重大重构：加上"防 AI 越权"框架

#### 新增
- **角色定义前置**：SKILL.md 开头明确定义 AI 为"操作员"，限定工作范围为三件事：跑 fetch.py → 跑 parse_clean.py → 调度撰写
- **最高优先级铁律**：4 条禁止行为 + 事故原因（临时脚本缺失回退链、自写清洗丢边界信号、多行 python -c 引号转义失败、无完整性验证导致截断）
- **退出前自检**：3 项检查：是否创建替代脚本、是否嵌入多行 Python 做格式转换、是否执行完整性验证
- **踩坑日志**：4 个真实事故（python -c 转义失败、文章后半段截断、历史缓存单行文件、subagent 绕过 fetch.py）
- **`.gitignore`**：排除 `__pycache__/` + `*.pyc`

#### 架构变更
- **黑盒化**：移除 fetch.py 的回退链细节描述（"yt-dlp web → android → oEmbed API"），改为"内置完整回退链"
- **移除 parse_clean.py 内部实现描述**：删除 TOPIC_BOUNDARY_PATTERNS 等细节
- **步骤 4b 重写**：将 30 行 `python -c` 内联代码替换为一行指令（"重新运行 parse_clean.py"），parse_clean.py v2.1+ 已内置同等逻辑
- **精简**：从 352 行精简到 168 行，删除冗余的分支描述重复内容（分支 A/B 的详细 prompt 模板从正文中移除，保留核心策略表）
- **故障排查表外置**：yt-dlp / youtube_transcript_api 错误表暂不纳入 SKILL.md（已在 fetch.py 中处理）

#### 设计原则（与 skill-sync v2.0 一致）
1. 负向提示词放在正向指令之前
2. 模型身份为"操作员"而非"开发者"
3. 脚本内部实现黑盒化
4. 退出前自检兜底
5. 踩坑日志比抽象规则更有效

---

## v2.2 (2026-05-28)

- 多行格式兜底检测（步骤 4b）
- 完整性验证从目视升级为量化覆盖率检查（≥85%）
- 缓存机制优化

## v2.1 (2026-05-22)

- 规则外置：文章撰写规则提取为 `article-template.md`
- 脚本持久化：`scripts/fetch.py` 和 `scripts/parse_clean.py` 预置在 skill 目录
- 缓存机制：同一视频重复执行时跳过下载和清洗
- 双语话题检测：parse_clean.py 同时支持英文和中文话题边界信号
- 长文本并行：超 6 块时采用并行 make-report subagent 策略
- 完整性验证：文章生成后自动检查话题覆盖

## v2.0 (2026-05-18)

- 初始公开版本
