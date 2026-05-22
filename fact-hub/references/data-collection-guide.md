# 信息收集策略指南 v2.0

> 步骤 1 执行前读取。v2.0：新增公司级 knowledge 补充搜索策略（通过 iFinD/alphaengine 研报等）。v1.5：新增 iFinD/alphaengine 交叉验证命令模板（借鉴 equity-deep-research data-commands.md）。

---

## 核心原则

1. **仅检索冲突项**：步骤 0 标记为 ✅ 的内容不检索
2. **并行发起**：所有检索命令必须在同一条消息中发出
3. **遵守时间精度**：根据用户时间表述选择对应精度（见下方时间精度规则表），禁止为"多召回"而扩大范围
4. **按维度分组**：检索结果按子Agent 维度（地缘/产业/技术/财务）分组，方便步骤 2 组装"已知数据包"

## 时间精度规则

> 在构造所有数据查询时，必须根据用户的时间表述选择正确的精度。

| 用户表述 | 查询精度 | AlphaClaw date_range | query_finance_data / websearch |
|---------|---------|---------------------|-------------------------------|
| "今天/盘后/盘中/这两天" | 日级别 | `past_day` | 当日日期 |
| "本周/这周/过去一周" | 周级别 | `past_week` | 本周一 ~ 当日 |
| "本月/这个月/近一个月" | 月级别 | `past_month` | 本月1日 ~ 当日 |
| "最近/近期/最新"（无明确时间单位） | 季度级别 | `past_quarter`（默认） | 近3个月 |
| "本季度/近三个月" | 季度级别 | `past_quarter` | 当前季度起始 |
| "近半年" | 半年级别 | `past_half_year` | 近6个月 |
| "近一年/去年" | 年级别 | `past_year` | 对应年份 |

**原则**：用户说了具体时间单位 → 必须用对应精度，禁止扩大范围。

## 数据优先级

| 优先级 | 含义 | 说明 |
|-------|------|------|
| P0 | 缺失则判断无法完成 | 冲突项涉及的核心事实数据，优先保障 |
| P1 | 重要增强 | 冲突项涉及的补充验证数据 |
| P2 | 有则更好 | 背景信息、趋势数据，时间允许时补充 |

> 若 P0 级数据全部缺失，向用户报告后暂停，不自作判断。

## 工具选择速查

| 冲突项类型 | 首选工具 | 备选 | 原则 |
|-----------|---------|------|------|
| 财务数据/股价/指标精确值 | `query_finance_data` | `search_finance_reports` | 定量数据不从研报里找数字 |
| 研报观点/行业分析/纪要 | `search_finance_reports` | `websearch` | 定性判断不用数据库替代 |
| 新闻/政策/市场动态 | `websearch` | `search_finance_reports` | 实时信号不用滞后的研报 |
| 企业工商/股权/风险 | 企业信息类 MCP | `websearch` | 结构化企业数据不用通用搜索 |

## 检索量控制

| 步骤 0 冲突项数量 | 最大检索命令数 | 说明 |
|-----------------|-------------|------|
| 1-3 项 🔴/❓ | ≤ 5 条命令 | 每项 1-2 条查询 |
| 4-6 项 🔴/❓ | ≤ 8 条命令 | 每项 1-2 条查询 |
| 7+ 项或知识库为空 | ≤ 12 条命令 | 按主题分组查询 |

## 检索结果整理

检索完成后，主Agent 将结果按维度整理为"已知数据包"：

```
【地缘维度数据包】
- [数据条目]：来源 + 日期 + 证据等级
- ...

【产业维度数据包】
- ...

【技术维度数据包】
- ...

【财务维度数据包】
- ...
```

该数据包将在步骤 3 传给对应子Agent，子Agent 禁止再检索这些数据。

---

## 交叉验证命令模板（v1.5 新增）

> v1.7 起，半快速通道/轻量通道/步骤 5 写入 facts 前必须执行此交叉验证环节。借鉴 equity-deep-research 第二步的 mcporter call 并行取数模式。

### 调用方式

使用 `mcporter call` 调用 iFinD MCP。`tool` 参数格式为 `"服务器.工具"`（点号连接为单个字符串），嵌套在 `args` 内部。

```
# 正确格式
mcporter call
  command: "call"
  tool: "hexin-ifind-ds-edb-mcp.get_edb_data"
  args: {"query": "..."}

# 错误：tool 放在 args 同级（top-level）→ 报"缺少必需参数: tool"
```

### 按事实类型的验证命令

| 事实类型 | mcporter call 命令 | 用途 |
|---------|-------------------|------|
| 价格/产能/出货量 | `mcporter call tool="hexin-ifind-ds-edb-mcp.get_edb_data" args={"query":"<指标名称> <时间范围>"}` | EDB 经济数据库取数 |
| 无明确指标名时先搜索 | `mcporter call tool="hexin-ifind-ds-edb-mcp.search_edb" args={"query":"<关键词>"}` | 模糊搜索可用指标 |
| 公司财务数据 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_financials" args={"query":"<公司名> <指标> <时间>"}` | 股票财务指标 |
| 股票概况 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_summary" args={"query":"<公司名> <信息类型>"}` | 财务摘要+估值 |
| 企业新闻事件 | `mcporter call tool="hexin-ifind-ds-news-mcp.search_news" args={"query":"<公司名>"}` | 近期新闻 |
| 选股/搜证券代码 | `mcporter call tool="hexin-ifind-ds-stock-mcp.search_stocks" args={"query":"<公司名称>"}` | 模糊搜索股票 |

### 验证命令数量控制

| 验证事实数 | 最大 iFinD 命令数 | 说明 |
|----------|-----------------|------|
| 1-3 条 | ≤ 5 条 | 每事实 1-2 条查询，优先 EDB |
| 4-6 条 | ≤ 8 条 | 按数据类型分组查询 |
| 7+ 条 | ≤ 12 条 | 优先验证 P0 级事实 |

### 验证结果写入规范

验证完成后，在 facts.md 的"验证状态"字段中按以下格式标注：

```
验证状态: 已交叉验证（iFinD EDB 2026-05-16 + websearch 2026-05-16）
验证状态: 框架类事实，无需交叉验证
验证状态: 单一信源待确认（iFinD EDB 未覆盖，仅 websearch 2026-05-16）
验证状态: 已验证但存疑（iFinD EDB 2026-05-16 与文章数据偏差 >15%）
```

### alphaengine 辅助验证

对涉及 A 股公司/行业的 fact，补充使用 alphaengine 进行验证：

```
# 提取文章中的公司名称
alphaengine nlp company_extraction --text '<文章内容>'

# 查询自选股分组
alphaengine watchlist list
```

### 并行执行铁律

> 所有交叉验证的 iFinD 命令必须在同一条消息中并行发出，不得逐条串行。豁免类 fact（框架/方法论）跳过验证，不占命令数。

---

## 公司级 knowledge 补充搜索策略（v2.0 新增）

> 当用户请求沉淀公司级知识时，除了基础事实提取，必须通过 iFinD/alphaengine 补充搜索公司深度信息。

### 搜索触发条件

- 用户提交涉及具体公司的材料（研报、BP、新闻、纪要等）
- 步骤 0a 发现知识库中该公司的 knowledge.md 为空或不完整
- 用户明确要求"研究这家公司"

### 搜索流程

1. **公司识别**：从用户材料中提取目标公司名称（使用 `alphaengine nlp company_extraction`）
2. **并行检索**：在同一条消息中发起以下查询：
   - `search_finance_reports`：搜索该公司近 3 个月研报/公司深度（report_types=["国内研报:公司研究","点评:公司点评"]）
   - `mcporter call` iFinD stock `get_stock_financials`：获取核心财务指标
   - `mcporter call` iFinD stock `get_stock_summary`：获取财务摘要+估值
   - `mcporter call` iFinD news `search_news`：获取近期新闻/公告
   - `websearch`：搜索公司近期动态（如适用）
3. **结果整合**：将检索结果整合到已知数据包中，供步骤 3 子Agent 使用

### 搜索量控制

| 公司数量 | 最大检索命令数 | 说明 |
|---------|-------------|------|
| 1 家公司 | ≤ 8 条 | 研报 + 财务 + 新闻 + 网络搜索 |
| 2-3 家公司 | ≤ 15 条 | 按公司分组并行查询 |
| 4+ 家公司 | ≤ 20 条 | 优先覆盖步骤 0a 标记为 🔴/❓ 的公司 |
