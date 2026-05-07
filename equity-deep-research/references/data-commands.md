# iFinD 数据命令模板集

> 本文件集中存放 equity-deep-research 第二步所需的所有 iFinD 数据调用模板和 AlphaClaw 参数表。
> SKILL.md 在"第二步：并行取数"节点应读取本文件，获取最新命令模板。
> 不需要全部读完，按标签索引即可。

---

## 调用方式选择

**首选：mcporter call（推荐）**

使用 `mcporter call` 工具直接调用 iFinD MCP 接口。参数为 JSON 对象，无 bash 转义风险。

> ⚠️ **关键格式规则**：`tool` 参数必须是 `"服务器.工具"` 格式（点号连接为**单个字符串**），禁止拆分为 `server` + `tool` 两个参数。
>
> ✅ 正确：`tool="hexin-ifind-ds-stock-mcp.get_stock_financials"`
> ❌ 错误：`server="hexin-ifind-ds-stock-mcp" tool="get_stock_financials"` → 报 "tool 格式错误，应为 server.tool"

**备选：bash + call.py**

仅在 mcporter 不可用时使用。需在 `D:\Alphaclaw\` 目录下执行，JSON 参数需单引号包裹。

---

## 第二步全部命令（13条，mcporter call 格式）

将 `<公司名>`、`<今日日期>`、`<近3个月日期>` 替换为实际值后，在同一条消息中全部并行发出。

### iFinD 股票数据（7条，mcporter call）

| # | mcporter call | 用途 |
|---|-------------|------|
| 1 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_info" args={"query":"<公司名> 上市时间 所属行业 主营业务"}` | 基本信息 |
| 2 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_financials" args={"query":"<公司名> 2025年报 2026Q1 营收 净利润 毛利率 ROE 资产负债率"}` | 财务数据 |
| 3 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_summary" args={"query":"<公司名> 财务状况 估值 PE PB ROE"}` | 财务摘要 |
| 4 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_shareholders" args={"query":"<公司名> 十大股东 北向持股 机构持股"}` | 股权结构 |
| 5 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_risk_indicators" args={"query":"<公司名> Beta 波动率 夏普比率"}` | 风险指标 |
| 6 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_events" args={"query":"<公司名> 分红 回购 增减持 股权激励"}` | 重大事件 |
| 7 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_info" args={"query":"<公司名> <今日日期> 股价 涨跌幅 市值 成交量"}` | 行情快照 |

### iFinD 新闻公告（2条，mcporter call）

| # | mcporter call | 用途 |
|---|-------------|------|
| 8 | `mcporter call tool="hexin-ifind-ds-news-mcp.search_news" args={"query":"<公司名>", "time_start":"<近3个月日期>", "time_end":"<今日日期>", "size":10}` | 近期新闻 |
| 9 | `mcporter call tool="hexin-ifind-ds-news-mcp.search_notice" args={"query":"<公司名> 2025年年报 2026年一季报 业绩", "time_start":"<近3个月日期>", "time_end":"<今日日期>", "size":5}` | 公告原文 |

### 趋势新闻（1条，mcporter call）

| # | mcporter call | 用途 |
|---|-------------|------|
| 10 | `mcporter call tool="hexin-ifind-ds-news-mcp.search_trending_news" args={"keyword":"<公司名>", "time_scope":"近一周", "size":10}` | 热门新闻（含情绪） |

### AlphaClaw 定性分析（4条，与 iFinD 命令并行）

| # | 工具 | 参数 | 用途 |
|---|------|------|------|
| 11 | `search_finance_reports` | `report_types:["国内研报:公司研究"]`, `query:<公司名>` | 投资逻辑/护城河 |
| 12 | `search_finance_reports` | `report_types:["会议纪要"]`, `query:<公司名>` | 分析师/公司交流/业绩会/调研 |
| 13 | `search_finance_reports` | `report_types:["公告:财务经营报告"]`, `query:<公司名>` | 管理层讨论与分析 |
| 14 | `search_finance_reports` | `report_types:["国内研报"]`, `query:<公司名>+"盈利预测"` | 卖方盈利预测 |

---

## 备选：bash + call.py 命令模板

> 仅在 mcporter 不可用时使用。需在 `D:\Alphaclaw\` 目录下执行。

### iFinD 股票数据（7条）

```bash
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_stock_info '{"query": "<公司名> 上市时间 所属行业 主营业务"}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_stock_financials '{"query": "<公司名> 2025年报 2026Q1 营收 净利润 毛利率 ROE 资产负债率"}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_stock_summary '{"query": "<公司名> 财务状况 估值 PE PB ROE"}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_stock_shareholders '{"query": "<公司名> 十大股东 北向持股 机构持股"}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_risk_indicators '{"query": "<公司名> Beta 波动率 夏普比率"}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_stock_events '{"query": "<公司名> 分红 回购 增减持 股权激励"}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" stock get_stock_info '{"query": "<公司名> <今日日期> 股价 涨跌幅 市值 成交量"}'
```

### iFinD 新闻公告（2条）

```bash
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" news search_news '{"query": "<公司名>", "time_start": "<近3个月日期>", "time_end": "<今日日期>", "size": 10}'
python "C:\Users\Jonathan Jin\.alphaclaw\skills\iFinD-Finance-Data\call.py" news search_notice '{"query": "<公司名> 2025年年报 2026年一季报 业绩", "time_start": "<近3个月日期>", "time_end": "<今日日期>", "size": 5}'
```

---

## 可选补充命令（mcporter call 格式）

以下命令在特定场景下按需使用：

| 场景 | mcporter call | 优先级 |
|------|-------------|--------|
| 行业宏观数据 | `mcporter call tool="hexin-ifind-ds-edb-mcp.get_edb_data" args={"query":"<公司所属行业> 产销量 价格指数 市场规模"}` | P1 |
| 可比公司批量财务 | `mcporter call tool="hexin-ifind-ds-stock-mcp.get_stock_financials" args={"query":"<可比A> <可比B> <可比C> 2025年报 营收 净利润 ROE PE PB"}` | P0 |
| 证券代码搜索 | `mcporter call tool="hexin-ifind-ds-stock-mcp.search_stocks" args={"query":"<公司名称>"}` | P0 |

---

## 数据优先级速查

| 优先级 | 含义 | 命令范围 |
|-------|------|---------|
| P0 | 缺失则报告无法完成 | 财务数据（7条）+ 新闻（2条）+ 研报观点（#11, #12） |
| P1 | 重要增强 | 行业宏观 + 卖方盈利预测 + 公告全文 |
| P2 | 有则更好 | 行情数据（已包含在 stock info 中） |
