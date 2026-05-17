# 数据源映射与检索指南

> 本文档供 gather sub-agent（步骤 2）和主 agent（步骤 3）使用。参考 equity-deep-research 的数据源分工原则。

## 数据源分工原则

| 数据类型 | 工具 | 调用方式 |
|---------|------|---------|
| 结构化财务、估值、风险、行情 | iFinD stock MCP（`hexin-ifind-ds-stock-mcp.*`） | `mcporter call tool="hexin-ifind-ds-stock-mcp.<方法>"` |
| 行业宏观（产销量/价格/指数） | iFinD EDB MCP（`hexin-ifind-ds-edb-mcp.*`） | `mcporter call tool="hexin-ifind-ds-edb-mcp.<方法>"` |
| 新闻、公告 | iFinD news MCP（`hexin-ifind-ds-news-mcp.*`） | `mcporter call tool="hexin-ifind-ds-news-mcp.<方法>"` |
| 研报观点、纪要、行业策略 | AlphaClaw `search_finance_reports` | 直接调用 |
| 通用金融数据查询 | `query_finance_data` | 直接调用，可作为 iFinD 补充 |
| 实时资讯、网络热点 | `websearch` / `webfetch` | 直接调用 |

**核心纪律**：
- 定量数据（财务指标、估值、行情、风险指标）优先用 iFinD MCP 或 `query_finance_data`，禁止用 AlphaClaw 替代
- 定性数据（研报观点、市场情绪、分析师共识）优先用 AlphaClaw `search_finance_reports`，禁止用 iFinD 替代
- 实时动态（突发新闻、政策变化、媒体热度）优先用 `websearch` + iFinD news MCP 组合

## 维度 × 数据源 × 优先级映射

### 否决层

| 维度 | P0（缺失则无法评估） | P1（重要增强） | P2（有则更好） |
|------|---------------------|---------------|---------------|
| **维度 1：价格与价值** | PE/PB/PS 当前值 + 5 年历史分位（`get_stock_financials` 估值字段 / `query_finance_data`） | DCF 关键参数（WACC、永续增长率）、可比公司估值对比（`get_stock_financials` 批量） | 研报估值逻辑（`search_finance_reports` 国内研报:公司研究） |
| **维度 4：风险与下行保护** | 资产负债率、流动比率、利息覆盖率（`get_stock_financials` 资产负债表字段） | 波动率、最大回撤、Beta（`get_risk_indicators` / `get_stock_performance`）；自由现金流趋势 | 压力测试情景、研报风险讨论（`search_finance_reports` 国内研报:公司研究） |

### 核心层

| 维度 | P0（缺失则无法评估） | P1（重要增强） | P2（有则更好） |
|------|---------------------|---------------|---------------|
| **维度 2：市场周期** | 行业指数近 1-3 年走势（`get_edb_data` 行业指数 / `get_stock_performance` 板块指数）；行业资金流向（`get_stock_performance` 资金流向字段） | 策略报告周期判断（`search_finance_reports` 国内研报:策略研究） | 宏观指标（PMI/社融/利率）（`get_edb_data`） |
| **维度 3：第二层次思维** | 近 3 个月卖方一致预期（`query_finance_data` 预测类指标 / `search_finance_reports` 国内研报:公司研究 + 点评:公司点评） | 卖方观点分歧度（研报目标价离散度、评级分布） | 买方纪要中的非共识观点（`search_finance_reports` 会议纪要:买方纪要） |
| **维度 5：逆向思维** | 近 3 个月分析师覆盖数量变化（`search_finance_reports` 按日期统计覆盖频次） | 媒体/会议热度（`websearch` 新闻量 + `search_finance_reports` 会议纪要数量趋势） | 机构持仓变化（`get_stock_shareholders` 机构/外资持仓变动） |

### 增强层

| 维度 | P0（缺失则无法评估） | P1（重要增强） | P2（有则更好） |
|------|---------------------|---------------|---------------|
| **维度 6：信息优势** | 研报覆盖密度 vs 同业（`search_finance_reports` 本标的 + 可比标的报告数量对比） | 研报内容深度评估（是否有独家的产业链调研/专家纪要） | — |
| **维度 7：杠杆** | 资产负债率、有息负债率、利息覆盖率（`get_stock_financials`） | 融资融券余额变化（`get_stock_performance` 两融字段）；股权质押比例（`get_stock_shareholders`） | 研报杠杆分析（`search_finance_reports`） |
| **维度 8：行为心理学** | 近 1 年股价走势 vs 基本面趋势对比（`get_stock_performance` + `get_stock_financials` 利润趋势） | 纪要中的情绪词频/语调变化（`search_finance_reports` 会议纪要:业绩会） | 近因效应指标（近期涨跌幅 vs 远期涨跌幅对比） |
| **维度 9：时间与耐心** | 分析师目标价对应的时间框架（`search_finance_reports` 国内研报:公司研究） | 公司经营周期长度（`get_stock_financials` 多年度趋势） | — |
| **维度 10：不对称性** | 卖方乐观/悲观情景盈利预测（`query_finance_data` 预测类字段 / `search_finance_reports` 国内研报:公司研究） | 历史最大回撤 vs 最大涨幅对比（`get_stock_performance`） | 期权隐含波动率偏斜（如有） |

## Gather Prompt 模板（工具感知版）

### gather A — 定量数据

```
用户问题：{用户原始问题}
当前日期：{current_date}
标的代码：{如有}
市场：{A股/港股/美股}

聚焦方向：获取标的的定量数据，按以下维度检索：

1. 估值与价格锚点（维度 1 + 维度 10）
   - 优先用 query_finance_data 查询：当前 PE/PB/PS、5 年历史估值分位（均值/中位数/当前值）
   - 补充 iFinD mcporter call: get_stock_financials 获取估值相关字段
   - 卖方情景：乐观/中性/悲观盈利预测和对应估值

2. 财务健康与杠杆（维度 4 + 维度 7）
   - query_finance_data 查询：近 3-5 年营收、净利润、ROE、毛利率、净利率趋势
   - iFinD mcporter call: get_stock_financials 查询资产负债率、流动比率、利息覆盖率、有息负债率、自由现金流
   - iFinD mcporter call: get_stock_shareholders 查询股权质押比例

3. 行情与风险指标（维度 2 + 维度 4 + 维度 8 + 维度 10）
   - iFinD mcporter call: get_stock_performance 查询近 1-3 年股价走势、波动率、最大回撤、最大涨幅
   - iFinD mcporter call: get_risk_indicators 查询 Beta、VaR 等风险指标
   - iFinD mcporter call: get_stock_shareholders 查询机构/外资持仓变化

4. 行业宏观（维度 2）
   - iFinD mcporter call: get_edb_data 查询标的所处行业指数走势、行业资金流向
   - 如标的为制造业公司，补充查询关键原材料/产品价格趋势
```

### gather B — 定性分析

```
用户问题：{用户原始问题}
当前日期：{current_date}
标的代码：{如有}

聚焦方向：获取标的的定性分析内容，全部使用 AlphaClaw search_finance_reports：

1. 公司研究与估值逻辑（维度 1 + 维度 3 + 维度 6）
   - search_finance_reports(query="{标的名称} 投资逻辑 估值", report_types=["国内研报:公司研究", "海外研报:公司研究"], date_range="past_quarter", recall_num=15)
   - 提取：卖方核心投资论点、估值方法、目标价及依据
   - 关注：不同券商之间的观点分歧（目标价离散度、评级分布）

2. 业绩点评与一致预期（维度 3 + 维度 8）
   - search_finance_reports(query="{标的名称} 业绩 点评", report_types=["点评:公司点评"], date_range="past_quarter", recall_num=10)
   - 提取：超预期/低于预期的维度、市场情绪变化

3. 会议纪要与管理层信号（维度 3 + 维度 5 + 维度 8）
   - search_finance_reports(query="{标的名称}", report_types=["会议纪要:业绩会", "会议纪要:公司交流"], date_range="past_quarter", recall_num=10)
   - 提取：管理层语气变化、对行业的判断、资本配置计划
   - 关注：纪要中的情绪信号词频（"谨慎"/"乐观"/"不确定"等）

4. 行业策略与周期判断（维度 2 + 维度 5）
   - search_finance_reports(query="{行业名称} 策略 周期", report_types=["国内研报:策略研究", "国内研报:行业研究"], date_range="past_quarter", recall_num=10)
   - 提取：行业当前周期位置判断、主流观点

5. 风险讨论与下行情景（维度 4 + 维度 10）
   - 从以上检索结果中提取所有风险因素和下行情景讨论
   - 特别关注：研报中"风险提示"章节、悲观情景假设
```

### gather C — 实时动态

```
用户问题：{用户原始问题}
当前日期：{current_date}
标的代码：{如有}

聚焦方向：获取标的的实时动态和市场情绪信号：

1. 近期新闻与事件（维度 2 + 维度 4 + 维度 5）
   - websearch(query="{标的名称} 最新消息 {当前年月}", count=15, freshness="Month")
   - iFinD mcporter call: search_news 查询近 1 个月公司相关新闻
   - 提取：重大事件、政策变化、行业动态

2. 市场热度与情绪（维度 5 + 维度 8）
   - websearch(query="{标的名称} 分析 观点", count=10)
   - search_finance_reports(query="{标的名称}", report_types=["资讯"], date_range="past_month", recall_num=15)
   - 提取：媒体覆盖密度变化、网络讨论热度、舆情倾向

3. 监管与政策（维度 2 + 维度 4）
   - websearch(query="{行业名称} 政策 监管 {当前年份}", count=10)
   - 提取：可能影响标的的监管政策变化
```

## iFinD MCP 常用命令速查

以下为 howard-marks-framework 评估场景中常用的 iFinD 工具调用：

**股票财务与估值**：
```
mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_financials" args={"code": "{证券代码}", "fields": ["营收","净利润","ROE","毛利率","净利率","资产负债率","流动比率","PE","PB","PS"]}
```

**行情与风险**：
```
mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_performance" args={"code": "{证券代码}", "period": "1y"}
mcporter call tool="hexin-ifind-ds-stock-mcp.get_risk_indicators" args={"code": "{证券代码}"}
```

**股东与机构**：
```
mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_shareholders" args={"code": "{证券代码}"}
```

**行业宏观**：
```
mcporter call tool="hexin-ifind-ds-edb-mcp.get_edb_data" args={"indicator": "{行业指数/产销量/价格等}"}
```

**新闻资讯**：
```
mcporter call tool="hexin-ifind-ds-news-mcp.search_news" args={"keyword": "{标的名称}", "time_range": "1m"}
```

## Gather 调用参数

每个 gather 必须设置：
- `subagent_type="gather"`
- `save_to_file=True`
- `file_path` 格式：
  - 单标的：`.alphaclaw/tmp/{标的名称}_定量数据_检索结果.md`
  - 单标的：`.alphaclaw/tmp/{标的名称}_定性分析_检索结果.md`
  - 单标的：`.alphaclaw/tmp/{标的名称}_实时动态_检索结果.md`
- `score_threshold=3`

**快速通道**：合并为 1 个 gather，file_path `.alphaclaw/tmp/{标的名称}_全维度_检索结果.md`。
