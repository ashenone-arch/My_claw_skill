---
version: v2.7
name: cross-talk-synthesis
description: 当用户需要将多篇已有的对谈文章（不同嘉宾、不同时间但围绕同一主题）汇总为一篇以话题为轴心的交叉分析文章时触发。即使用户说"把这几篇合并一下""帮我对比一下这几期的观点""这几篇都在聊AI，帮我做个总结""汇总这些对话的核心观点，按话题整理"，也应触发。NOT for：单篇文章的格式转换、从零开始的独立研究。
---

# 多篇对谈交叉汇总

> 版本历史见 [CHANGELOG.md](CHANGELOG.md)

## 概述

将多篇已有对谈文章（不同嘉宾、不同时间、同一主题），按用户选定的话题重新组织为交叉分析文章。

核心设计：**先轻量扫描出内容地图 → 用户选定话题 → 仅对选定话题深度提取和写作**。

## 执行铁律

| # | 规则 | 说明 |
|---|------|------|
| 1 | **并行** | ≥3 个文件/话题/章节/审查时，同一条消息中并行发起全部 subagent |
| 2 | **确认** | 步骤 3（展示内容地图 + 用户选择）不允许跳过 |
| 3 | **溯源** | 每个观点必须标注来源文件 + 证据等级（Q1/Q2/Q3） |
| 4 | **分工** | 编排模式下主 agent 定架构（全文塔尖 + 章塔尖），sub-agent 写正文，禁止主 agent 越权写章节正文 |
| 5 | **纯文本** | 全文只用 markdown 原生格式（文字/表格/列表），禁止生成图片/图表/可视化 |
| 6 | **中文输出** | 全文严格中文；英文 Q1 直接引语必须先翻译为中文再引用，不得直接引用英文原文 |
| 7 | **write-only** | **任何文件写入仅允许使用 `write` 工具**，严禁使用 bash/printf/heredoc/Python/shell 命令写文件。Windows Git Bash 下 shell 对中文编码极不可靠——heredoc 被 `$` 截断、inline Python 语法错误、PowerShell 编码错乱均发生过。此规则适用于主 agent 和所有 sub-agent，无例外 |

## 文件写入铁律（铁律 7 的详细说明）

**为什么这条规则如此重要**：本次 session 的 make-report agent 因用 shell 写中文文件，累计尝试 ~30 次 bash/heredoc/Python/PowerShell 均失败，最终仍需主 agent 用 `write` 工具接管。

- ✅ `write(file_path, content)` — 唯一允许的文件写入方式，支持完整 UTF-8 中文
- ❌ `cat > file << 'EOF' ... EOF` — heredoc 中的 `$` 和中文引号会被误解析
- ❌ `python -c "..."` — Windows Git Bash 下 inline Python 中文引号语法错误频发
- ❌ `printf '%s\n' '...' >> file` — 逐行 append 效率极低且中文可能被转义
- ❌ `powershell -Command "..."` — 跨 shell 转义复杂度高，编码不可控

**Sub-agent 违规处理**：如果 make-report agent 报告文件写入失败，主 agent **不得让 make-report 重试**，应直接自己用 `write` 工具完成最终文章写入。

编排模式（≥4 话题）下，金字塔按层级在主 agent 和 sub-agent 间分工：

```
全文塔尖（主 agent 定，5a）
  ├── 章 1 塔尖（主 agent 定，5a） → 章 1 正文（sub-agent 写，5b）
  ├── 章 2 塔尖（主 agent 定，5a） → 章 2 正文（sub-agent 写，5b）
  ├── ...
  └── 跨章 Q3 + 引言 + 结语（主 agent 写，5c）
```

| 层级 | 负责人 | 产物 | 输入 |
|------|--------|------|------|
| 全文塔尖 + 章塔尖 | 主 agent（5a） | 架构文档 | 步骤 3 内容地图 + 步骤 4 每话题的塔尖候选（一行） |
| 章内证据展开（Q1/Q2/章内 Q3） | sub-agent（5b） | 章节正文 | 章塔尖 + 分配的深度提取文件 |
| 跨章合成 + 引言结语 | 主 agent（5c） | 最终文章 | 全部章节正文 |

**关键约束**：sub-agent 不做跨章判断，只在本章素材范围内写作。跨章 Q3 由主 agent 在 5c 完成。

## 证据分级与金字塔

详见 [WRITING-STANDARDS.md](WRITING-STANDARDS.md)。所有观点按三级标注：**Q1** 直接引语/可验证事实 → **Q2** 归纳转述 → **Q3** 交叉推断。Q3 不得以 Q1 口吻呈现。步骤 4 提取和步骤 5 写作均强制使用金字塔：塔尖 1 句 → 子论点展开 → 交叉分析。禁止平铺。

> **输出格式**：全文纯 markdown，禁止图片/图表/可视化，主体内容 bullet point 驱动。详见 [WRITING-STANDARDS.md](WRITING-STANDARDS.md)「输出格式禁止」和「行文风格」节。

## 场景路由

| 条件 | 行动 |
|------|------|
| 文件 > 10 篇 | 加载 [BATCH-STRATEGY.md](BATCH-STRATEGY.md) 按分批策略执行 |
| 选定话题 ≥ 4 个 | 步骤 5 走编排模式（5a→5a-review→5a-final→5b→5c） |
| 选定话题 ≤ 2 个 + ≤8 文件 + 无复杂分歧 | 步骤 5 走快速通道（跳过步骤 4） |
| 其他（3 话题 / 有复杂场景） | 标准模式：步骤 4 完整提取 → task(make-report) 一次写完 |
| 需要决策速查/陷阱速查 | 按需 `read` [QUICK-REF.md](QUICK-REF.md) 对应段落 |

## 核心流程

### 步骤 1：确定输入文件
glob 获取所有 `.md` 文件 → 展示列表确认。>10 篇按 BATCH-STRATEGY.md 分组。

### 步骤 2：轻量内容扫描（并行）
每篇/每组启动 `task(general)`，**sub-agent 自读 EXTRACT-GUIDE.md 获取字段定义和输出格式**。主 agent prompt 只传文件列表 + 关注方向。

### 步骤 3：展示内容地图 + 邀请用户选择（必须执行）
汇总步骤 2 结果，按 BATCH-STRATEGY.md 模板展示话题频次、文件×话题矩阵、嘉宾多样性。邀请用户选 2-5 个话题。

### 步骤 4：深度提取（并行）

**前置（主 agent 执行）**：基于步骤 2 的文件×话题矩阵，对每个选定话题做**相关性分级**，避免 sub-agent 读入大量弱相关文件：
- **Tier 1（强相关）**：必须全读。该文件在步骤 2 的 `topic_tags` 中直接命中当前话题关键词。
- **Tier 2（弱相关）**：可跳过。`topic_tags` 未命中，仅因同一公司/同一领域被纳入。
- 主 agent prompt 中只传 Tier 1 文件列表；Tier 2 文件不传。sub-agent 在提取过程中如发现信息缺口，可自行决定是否 `read` Tier 2 文件做补充。

启动 `task(general)`，**sub-agent 自读 EXTRACT-GUIDE.md 获取步骤 4 提取规范**。主 agent prompt 只传：话题名 + Tier 1 文件列表。输出须含「塔尖候选」（见 EXTRACT-GUIDE.md 步骤 4 输出格式）。

### 步骤 5：分层撰写

主 agent 内部判断体量（不向用户确认）：

| 条件 | 模式 | make-report mode |
|------|------|------------------|
| ≤2 话题 + ≤8 文件 + 无复杂分歧 | **快速通道**（5.1） | `short` |
| 3 话题 + 提取总行数 ≤ 400 | **标准模式**（5.2） | `short` |
| 3 话题 + 提取总行数 > 400 | **标准模式**（5.2） | **`long`**（强制） |
| ≥4 话题 | **编排模式**（5.3） | `subtopic`（5b） |

> **提取总行数** = 步骤 4 所有深度提取文件的 wc -l 总和。步骤 4 完成后，主 agent 先 `bash wc -l` 统计行数再判断 mode。若模式判断为 `short` 但 `make-report` 超时，**禁止重试 `short`**，直接切换 `mode="long"`。

#### 5.1 快速通道（≤2 话题）
步骤 2 轻量扫描已包含 `one_liner` 和 `topic_tags`，足够支撑 2 话题。跳过步骤 4。加载 WRITING-STANDARDS.md 全文，将步骤 2 结果传入 `task(make-report, stream_to_parent=true)` 撰写。make-report agent **仅允许使用 `write` 工具写入文章文件**。严禁使用任何 shell 命令（bash/printf/heredoc/Python/PowerShell），详见铁律 7。Sub-agent 写作时 read 原文中相关段落做定向补充。

#### 5.2 标准模式（3 话题）
加载 WRITING-STANDARDS.md 全文，将步骤 4 所有提取结果传入 `task(make-report, stream_to_parent=true)` 撰写。**提取总行数 > 400 时必须传 `mode="long"`**（见上表）。make-report agent **仅允许使用 `write` 工具写入文章文件**，严禁任何 shell 命令（详见铁律 7）。超时兜底：若 `short` 超时，不重试 short，直接切换 `mode="long"`。**文件写入兜底**：若 make-report 完成报告内容但文件写入失败，主 agent 直接接管，自行用 `write` 工具完成最终写入，不得让 make-report 重试。

#### 5.3 编排模式（≥4 话题）

**5a：主 agent 产出架构草案**

- **不读**步骤 4 提取文件全文——只读每文件开头的「塔尖候选」（一行）
- 产出架构草案：

```
全文塔尖（1 句，草案）
  ├── 章 1：{标题} 塔尖：{1 句} ← 文件：[A, B] 权重：1x
  ├── 章 2：{标题} 塔尖：{1 句} ← 文件：[B, C, D] 权重：1.5x
  ├── 章 N：{标题} 塔尖：{1 句} ← 文件：[X, Y] 权重：1x
  └── 跨章关系速记：章 1 ↔ 章 4（可能形成对照）；章 2 ↔ 章 3（共享嘉宾 C 的视角）
```

- 跨章关系速记只标注"可能形成对照"，不做 Q3

**5a-review：MECE 审查轮**（条件触发）

触发条件：章节数 ≥ 5，或存在易交叉的软性话题（如"竞争力分析""未来展望""核心挑战"等）。

不触发则跳过此轮，架构草案即终稿。

触发后：并行启动 `task(general)` × 章节数。每个审查 sub-agent 的 prompt：

```
审查「{章标题}」在以下架构草案中的 MECE 质量。

你的章塔尖：{一句话}
素材文件：读取 {话题}_深度提取.md

完整架构草案（所有章塔尖）：
[列出全部章标题 + 塔尖]

审查任务：
1. 塔尖是否被素材中的证据支撑？（找反例或支撑不足的点）
2. 你的章与相邻章边界是否清晰？标出重叠风险
3. 素材中是否有重要维度未被任何章覆盖？（E 检测）
4. 如有问题，给出具体修改建议（改塔尖措辞 / 拆分 / 合并）

输出：审查结论（通过/有条件通过/需重架构）+ 具体问题列表 + 修改建议
```

**5a-final：主 agent 汇总审查 → 架构终稿**

逐条处理审查问题：合并/拆分/重写塔尖，调整边界，更新权重。架构终稿的章节数可能 ≠ 原话题数（合并或拆分后）。

**5b：并行章节写作**

每章启动 `task(make-report, mode="subtopic")`。prompt 传「章节简报」：

```
撰写章节「{章标题}」
章塔尖：{一句话}
素材文件：{文件路径列表}
权重：{1x/1.5x/2x}
格式规范：自读 WRITING-STANDARDS.md 的 <!-- sub-agent --> 节（从该标记读到 /sub-agent 标记为止）
**仅允许使用 `write` 工具写入章节文件**，严禁 shell 命令（铁律 7）。
```

**全部章节同一条消息并行发起**。

**5c：主 agent 拼接**

读取所有章节 → 校验一致性（同一嘉宾的观点在不同章中是否矛盾？术语是否统一？）→ 注入跨章 Q3（基于 5a 跨章关系速记 + 章节实际内容）→ 补写引言和结语 → 统一术语和 bullet 风格 → 写入最终文件。

### 步骤 6：保存与清理
- 最终文章保存至步骤 1 确定的源文件所在文件夹，文件名 `{主题}-多篇对谈交叉汇总.md`
- 步骤 2 扫描结果保存至 `.alphaclaw/tmp/{主题}_内容地图.md`
- 步骤 4 深度提取结果保存至 `.alphaclaw/tmp/{话题}_深度提取.md`
- 所有文件写入**仅允许使用 `write` 工具**，严禁任何 shell 命令（铁律 7）
- 步骤 6 完成且用户确认后，删除 `.alphaclaw/tmp/` 下的所有中间文件（`{主题}_内容地图.md` 及 `{话题}_深度提取.md`）

## 引用文件

| 文件 | 用途 | 加载方式 |
|------|------|---------|
| [BATCH-STRATEGY.md](BATCH-STRATEGY.md) | 大批量文件分组策略 | 主 agent 按需 `read` |
| [WRITING-STANDARDS.md](WRITING-STANDARDS.md) | 写作规范（含 full/main-agent/sub-agent 分区标记） | 按标记分段读 |
| [EXTRACT-GUIDE.md](EXTRACT-GUIDE.md) | 步骤 2/4 sub-agent 模板 | sub-agent 自读 |
| [QUICK-REF.md](QUICK-REF.md) | 决策速查 + 陷阱速查 | 主 agent 按需 `read` |
| [references/cross-analysis-frameworks.md](references/cross-analysis-frameworks.md) | 交叉分析框架 | 按需加载 |
