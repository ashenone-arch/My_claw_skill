# My Claw Skills

> 个人投资研究使用的 AlphaClaw Skill 集合，覆盖信息收集、整理、处理/决策的完整投研链路。

---

## 投资研究工作流

### 1. 信息收集 — 从多元渠道获取原始材料

在研究启动前，先确保信息获取渠道覆盖到位：

| Skill | 版本 | 解决什么问题 |
|-------|------|------------|
| [daily-seller-hotspot](daily-seller-hotspot/) | v1.0 | 每日扫描卖方抱团方向，识别机构注意力集中在哪些赛道和个股 |
| [youtube-transcript-to-article](youtube-transcript-to-article/) | v2.1 | 视频/播客字幕自动转书面文章，碎片化口语内容变为可检索、可引用的文本 |
| [pdf-batch-extract](pdf-batch-extract/) | v1.1 | 批量提取研报、公告、招股书 PDF 的原文和表格，统一转为 Markdown |

### 2. 信息整理 — 碎片信息结构化沉淀

收集到的材料需要去重、串联、沉淀，否则看过就忘：

| Skill | 版本 | 解决什么问题 |
|-------|------|------------|
| [fact-hub](fact-hub/) | v1.5 | 事实、观点、冲突三层知识库，追踪你的认知迭代，标记待验证的矛盾点 |
| [cross-talk-synthesis](cross-talk-synthesis/) | v2.3 | 多篇对谈交叉汇总，按话题轴心组织不同嘉宾的观点碰撞，发现共识与分歧 |

### 3. 信息处理 / 决策 — 形成可执行的投资判断

信息整理到位后，用框架化工具输出可操作的结论：

| Skill | 版本 | 解决什么问题 |
|-------|------|------------|
| [equity-deep-research](equity-deep-research/) | v2.8 | A 股上市公司 9 段深度投研框架，覆盖商业模式、财务、估值、风险等维度 |
| [howard-marks-framework](howard-marks-framework/) | v2.0 | 用霍华德-马克斯投资框架评估标的或审查组合，聚焦第二层次思维 |
| [dd-qlist](dd-qlist/) | v1.0 | 一级市场科技项目尽调清单生成，假设驱动提问，覆盖 6 大维度 |

### 系统工具

| Skill | 版本 | 说明 |
|-------|------|------|
| [skill-sync](skill-sync/) | v1.6 | Skill 同步工具，本地与 GitHub 双向同步 |
| [fact-hub-sync](fact-hub-sync/) | v1.0 | Fact Hub 知识库 GitHub 同步备份 |

---

## 使用方式

在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。例如：

- "帮我深度研究一下贵州茅台" → 触发 `equity-deep-research`
- "用马克斯框架评估这只股票" → 触发 `howard-marks-framework`
- "今天机构抱团什么方向" → 触发 `daily-seller-hotspot`
- "帮我整理这些材料到知识库" → 触发 `fact-hub`

## 版本说明

每个 Skill 独立维护版本号，格式 `{skill-name}-v{version}`。版本号标注在各 Skill 的 `SKILL.md` frontmatter 中。

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。投资有风险，决策需谨慎。
