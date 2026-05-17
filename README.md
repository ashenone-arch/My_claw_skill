# My Claw Skills

> 个人日常投资研究使用的 AlphaClaw Skill 集合。
> `<!-- SKILL_TABLE_START -->` 到 `<!-- SKILL_TABLE_END -->` 之间的表格由 skill-sync 自动维护，
> 请勿手动编辑表格内容。标记外的区域可自由自定义。

## 目录

<!-- SKILL_TABLE_START -->

| Skill | 说明 | 版本 |
|-------|------|------|
| [skill-sync](skill-sync/) | GitHub Skill 同步工具，支持本地↔云端双向同步；README 版本列表以云端 Skill 为基准生成。 | v1.6 |
| [cross-talk-synthesis](cross-talk-synthesis/) | 当用户需要将多篇已有的对谈文章（不同嘉宾、不同时间但围绕同一主题）汇总为一篇以话题为轴心的交叉分析文章时触发。即使用户说... | v2.4 |
| [daily-seller-hotspot](daily-seller-hotspot/) | 当用户需要了解当日卖方/机构关注的热点方向、生成卖方热点选股报告时使用。触发场景包括："今天卖方抱团什么"、"今天机构热... | v1.0 |
| [dd-qlist](dd-qlist/) | 当用户提供一级市场科技项目的公司介绍材料（BP、产品介绍、技术文档、商业计划书等），要求生成发给公司回答的尽调问题清单时... | v1.0 |
| [equity-deep-research](equity-deep-research/) | 当用户需要对A股上市公司进行深度研究、分析公司基本面、撰写投研素材时使用。触发场景包括："深度研究 XX公司"、"分析一... | v2.9 |
| [fact-hub](fact-hub/) | 当用户需要沉淀信息、追踪认知迭代、拆解研究问题时触发。触发场景包括："帮我整理这些材料"、"把这件事沉淀到知识库"、"最... | v1.10 |
| [fact-hub-sync](fact-hub-sync/) | Fact Hub 知识库同步工具，将本地 Fact Hub 内容推送到 GitHub 仓库。支持增量推送（hash 对比... | v1.0 |
| [howard-marks-framework](howard-marks-framework/) | 当用户想要用霍华德·马克斯（Howard Marks）的投资框架来评估某个投资标的（股票、债券、基金、行业等）或审查投资... | v2.1 |
| [pdf-batch-extract](pdf-batch-extract/) | 当用户需要将文件夹内多个 PDF 统一提取原文和表格为 MD 文件时使用。即使用户说"批量提取 PDF"、"把 PDF ... | v1.1 |
| [youtube-transcript-to-article](youtube-transcript-to-article/) | 当用户提供 YouTube 视频链接并要求"生成书面总结文章"时触发。将视频字幕自动下载、解析、生成完整书面文章并保存为... | v2.2 |

<!-- SKILL_TABLE_END -->

## 使用方式

在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。

示例：
- "同步我的 skill" → 触发对应 Skill
- "深度研究一下某公司" → 触发对应 Skill
- "今天机构抱团什么方向" → 触发对应 Skill

## 版本说明

每个 Skill 独立打 Tag，格式为 `{skill-name}-v{version}`。
如需回溯历史版本，请访问对应 Tag 的 Release 页面。

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。
投资有风险，决策需谨慎。