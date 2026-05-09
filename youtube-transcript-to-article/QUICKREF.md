# YouTube 视频字幕转书面文章 — 快速参考 v2.0

## 触发条件
用户提供 YouTube 视频链接 + 要求"生成书面总结文章"。

## 工作流总览
1. 环境检测 → 2. 缓存检查 → 3. 下载（fetch.py）→ 4. 清洗分块（parse_clean.py）
→ 5. 生成文章（分支 A/B）→ 6. 完整性验证 → 7. 保存 → 8. 清理

## 关键文件
- `scripts/fetch.py`：持久化下载脚本（元信息 + 字幕）
- `scripts/parse_clean.py`：持久化解析清洗脚本（双语话题检测 + 智能分块）
- `article-template.md`：文章撰写规则模板（7条规则，分支 A/B 共用）

## 双分支策略
| 条件 | 分支 | 策略 |
|------|------|------|
| 未分块（≤10万字） | A | make-report subagent 直接撰写 |
| 已分块（>10万字），≤6块 | B1 | 主 agent 并行读取后直接撰写 |
| 已分块（>10万字），>6块 | B2 | 并行 make-report subagent 处理每块 → 主 agent 合并 |

## 缓存机制
`D:\AlphaClaw\Podcast\cache\{video_id}\` 下缓存清洗后文本。
同一视频重复执行时跳过下载和清洗步骤。

## 依赖
- Python 库：`yt-dlp`、`youtube_transcript_api`
- 工具：`make-report` subagent（分支 A / B2）
