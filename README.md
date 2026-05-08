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
