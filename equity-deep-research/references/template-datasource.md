# 数据源映射 · 证据等级表
> 所有 sub-agent 和主 agent 执行写作前必须读取本文件。
> 本文件为共享基础内容，每个独立模板文件中不再重复引用。

---

## 输出格式禁止（所有 agent 强制遵守）

- **禁止生成图片/图表/可视化**：全文仅用 markdown 原生格式（文字、表格、列表）
- **表格替代图表、嵌套列表替代流程图**
- **bullet point 优先**：主体内容用 bullet point 短句，段落体仅限引言/结语
- **每点独立可扫**：一个 bullet 一个信息维度，展开用子级缩进

---

## 数据源映射

| 段落 | iFinD 优先 | AlphaClaw 补充 | 数据优先级 |
|------|-----------|---------------|-----------|
| 段1 | `get_stock_summary` / `get_stock_info` / `get_edb_data` | — | P0 |
| 段2 | `get_stock_financials`（主营拆解） | — | P0 |
| 段3 | `get_stock_financials` + `get_edb_data` + `get_stock_shareholders` | — | P0 |
| 段4 | `get_stock_financials`（利润表 + FY1-FY3 预测指标） | `search_finance_reports`（盈利预测观点） | P0 |
| 段5 | `get_stock_shareholders` + `get_risk_indicators` + `get_stock_events` | `search_finance_reports`（投资逻辑） | P0 |
| 段6 | `get_stock_info` + `get_stock_shareholders` + `search_news` | `search_finance_reports`（会议纪要全类） | P0 |
| 段7 | `get_stock_financials`（批量）+ `get_risk_indicators` | — | P0 |
| 段8 | `get_stock_financials`（分红）+ `get_stock_events` + `search_notice` | `search_finance_reports`（公告:财务经营报告） | P0 |
| 段9 | 基于前 8 段缺失判断 | 基于前 8 段缺失判断 | — |

---

## 证据等级表

| 标签 | 含义 | 示例 |
|------|------|------|
| F1 | 公开可验证事实 | 交易所披露 |
| F2 | 财报/金融数据库/公告 | 年报、iFinD 数据 |
| M1 | 市场一致预期 + 管理层公开发言 | 卖方预测、业绩会发言 |
| C1 | 合理推演 | 需附推演链路 |
| H1 | 待核验假设 | 必须标"未经核验" |

**约束**：没有证据等级 = 不能写。关键结论必须有 F1/F2 支撑。管理层公开发言 = M1，不是 F2。
