# My Claw Skills

> 个人日常投资研究使用的 AlphaClaw Skill 集合，版本信息见各 Skill 的 Release

## 目录

| Skill | 说明 | 版本 |
|-------|------|------|
| [cross-talk-synthesis](cross-talk-synthesis/) | 当用户需要将多篇已有的对谈文章（不同嘉宾、不同时间但围绕同一主题）汇总为一篇以话题为轴心的交叉分析文... | 2.0 |
| [daily-seller-hotspot](daily-seller-hotspot/) | 当用户需要了解当日卖方/机构关注的热点方向、生成卖方热点选股报告时使用。触发场景包括："今天卖方抱团... | 1.0 |
| [equity-deep-research](equity-deep-research/) | 当用户需要对A股上市公司进行深度研究、分析公司基本面、撰写投研素材时使用。触发场景包括："深度研究 ... | 2.1 |
| [howard-marks-framework](howard-marks-framework/) | 当用户想要用霍华德·马克斯（Howard Marks）的投资框架来评估某个投资标的（股票、债券、基金... | 1.0 |
| [iFinD-Finance-Data](iFinD-Finance-Data/) | "同花顺金融数据查询，查询股票、基金、宏观经济、行业经济及新闻公告数据，同时支持智能选股、选基、宏观... | 1.0.0 |
| [pdf-batch-extract](pdf-batch-extract/) | 当用户需要将文件夹内多个 PDF 统一提取原文和表格为 MD 文件时使用。即使用户说"批量提取 PD... | 1.1 |
| [skill-sync](skill-sync/) | "GitHub Skill 同步工具，支持本地→云端推送，自动维护 README 版本列表" | "1.2" |
| [youtube-transcript-to-article](youtube-transcript-to-article/) | 当用户提供 YouTube 视频链接并要求"生成书面总结文章"时触发。将视频字幕自动下载、解析、生成... | 1.0 |
| [youtube-watcher](youtube-watcher/) | Fetch and read transcripts from YouTube videos. Us... | 1.0.0 |

## 使用方式

在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。

示例：
- "深度研究一下贵州茅台" → 触发 `equity-deep-research`
- "今天机构抱团什么方向" → 触发 `daily-seller-hotspot`
- "用霍华德马克斯框架分析这只股票" → 触发 `howard-marks-framework`
- "同步我的 skill" → 触发 `skill-sync`
- "这几篇都在聊 AI，帮我按话题做个总结" → 触发 `cross-talk-synthesis`

## 版本说明

每个 Skill 独立打 Tag，格式为 `{skill-name}-v{version}`。
如需回溯历史版本，请访问对应 Tag 的 Release 页面。

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。
投资有风险，决策需谨慎。