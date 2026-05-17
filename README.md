# My Claw Skills

> 一套完整的A股投研工作流——将信息收集、整理、分析到决策的闭环，通过结构化Skill固化为自动化、标准化的投研操作系统。

---

## 仓库总览：完整的投研工作流

10 个 Skill 系统性地覆盖投研各环节：

<!-- SKILL_TABLE_START -->

### 信息收集

| Skill | 版本 | 核心功能 |
|-------|------|---------|
| [daily-seller-hotspot](daily-seller-hotspot/) | v1.0 | 每日扫描卖方抱团方向，识别机构注意力焦点 |
| [youtube-transcript-to-article](youtube-transcript-to-article/) | v2.2 | 视频/播客字幕自动转为书面文章 |
| [pdf-batch-extract](pdf-batch-extract/) | v1.1 | 批量提取研报、公告PDF原文和表格为Markdown |

### 信息整理

| Skill | 版本 | 核心功能 |
|-------|------|---------|
| [fact-hub](fact-hub/) | v1.10 | 事实、观点、冲突三层知识库，追踪认知迭代 |
| [cross-talk-synthesis](cross-talk-synthesis/) | v2.4 | 多篇对谈交叉汇总，按话题轴心组织观点碰撞 |

### 分析/决策

| Skill | 版本 | 核心功能 |
|-------|------|---------|
| [equity-deep-research](equity-deep-research/) | v2.9 | A股上市公司9段深度投研框架 |
| [howard-marks-framework](howard-marks-framework/) | v2.1 | 霍华德·马克斯投资框架评估标的 |
| [dd-qlist](dd-qlist/) | v1.0 | 一级市场科技项目尽调问题清单生成 |

### 系统工具

| Skill | 版本 | 核心功能 |
|-------|------|---------|
| [skill-sync](skill-sync/) | v1.7 | Skill本地与GitHub双向同步 |
| [fact-hub-sync](fact-hub-sync/) | v1.0 | Fact Hub知识库GitHub同步备份 |

<!-- SKILL_TABLE_END -->

---

## 方法论设计

**投资哲学的内化**：将投资大师的思想工程化为具体指令。`howard-marks-framework` 将"第二层次思维"、"周期定位"等抽象概念转化为可执行的分析维度。

**认知过程的外化**：这套Skill体系作为"外部大脑"，将投研中的隐性知识显性化。`fact-hub` 通过事实→观点→冲突三层结构，清晰展示个人认知如何迭代更新。

**工作流的管线化**：投研流程拆解为 **信息收集 → 信息整理 → 分析/决策** 三个阶段，每个环节可独立优化、复用和迭代。

---

## 使用方式

在 AlphaClaw 中直接向助理描述需求即可自动触发对应 Skill：

- "今天机构抱团什么方向" → `daily-seller-hotspot`
- "把这几篇对谈合并一下" → `cross-talk-synthesis`
- "深度研究一下贵州茅台" → `equity-deep-research`
- "用霍华德·马克斯的框架评估这个标的" → `howard-marks-framework`
- "同步我的 Skill" → `skill-sync`

---

## 免责声明

本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。投资有风险，决策需谨慎。
