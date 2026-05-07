# 快速参考表

> 本文件为 equity-deep-research v2.0 的快速参考，AI 在执行研究任务时可随时查阅。
> 不需要全部读完，按需查阅即可。

**相关文件索引**：
- 命令模板（bash 命令、AlphaClaw 参数）→ `data-commands.md`
- 故障排查（数据异常、工具报错、报告写不动）→ `troubleshooting.md`
- 框架工具箱（VRIO/DuPont/波特五力等分析框架选择）→ `framework-toolkit.md`

---

## 工具快速参考

| 研究需求 | 优先工具 | 备选工具 | 数据优先级 |
|---------|---------|---------|-----------|
| 公司财务数据（利润表/资产负债/比率） | `hexin-ifind-ds-stock-mcp.get_stock_financials` | AlphaClaw `query_finance_data` | P0 |
| 预测数据（FY1-FY3 净利润/EPS/PE/ROE） | `hexin-ifind-ds-stock-mcp.get_stock_financials` | — | P0 |
| 分红进度（预案公告日/派息日） | `hexin-ifind-ds-stock-mcp.get_stock_events` | — | P1 |
| 公司基本概况（行业/主营/TTM摘要） | `hexin-ifind-ds-stock-mcp.get_stock_summary` | — | P0 |
| 上市时间/所属行业/主营业务简介 | `hexin-ifind-ds-stock-mcp.get_stock_info` | — | P0 |
| 股权结构（十大股东/机构数/北向） | `hexin-ifind-ds-stock-mcp.get_stock_shareholders` | — | P0 |
| 风险指标（Beta/波动率/夏普比率） | `hexin-ifind-ds-stock-mcp.get_risk_indicators` | — | P1 |
| 分红/回购/增减持/股权激励事件 | `hexin-ifind-ds-stock-mcp.get_stock_events` | — | P1 |
| 行情数据（涨跌幅/换手率） | `hexin-ifind-ds-stock-mcp.get_stock_info` | — | P2 |
| 行业宏观（产销量/价格指数） | `hexin-ifind-ds-edb-mcp.get_edb_data` | AlphaClaw `websearch` | P1 |
| 公司新闻 | `hexin-ifind-ds-news-mcp.search_news` | websearch | P0 |
| 热门新闻（带情绪方向） | `hexin-ifind-ds-news-mcp.search_trending_news` | — | P0 |
| 公告原文（年报/半年报/年报摘要） | `hexin-ifind-ds-news-mcp.search_notice` | — | P1 |
| 研报观点（投资逻辑/护城河） | AlphaClaw `search_finance_reports`（国内研报:公司研究） | — | P0 |
| 会议纪要（分析师/公司交流/业绩会/调研） | AlphaClaw `search_finance_reports`（会议纪要全类） | — | P0 |
| 公告全文（管理层讨论与分析） | AlphaClaw `search_finance_reports`（公告:财务经营报告） | — | P1 |
| 卖方盈利预测 | AlphaClaw `search_finance_reports`（国内研报） | — | P1 |
| 研报摘要不足时 | AlphaClaw `get_document_detail` | — | — |

---

## 数据源分工原则（按类型）

| 数据类型 | 负责方 | 说明 |
|---------|-------|------|
| 结构化财务、估值、风险、ESG、股权、事件、行情 | `hexin-ifind-ds-stock-mcp.*` | 全量覆盖 AlphaClaw 定量查询 |
| 行业宏观（产销量/价格） | `hexin-ifind-ds-edb-mcp.get_edb_data` | — |
| 新闻、公告 | `hexin-ifind-ds-news-mcp.*` | 时效性优于 AlphaClaw 研报库 |
| 研报观点、纪要、公告原文 | `search_finance_reports`（AlphaClaw） | iFinD 不覆盖卖方观点 |

**原则**：`hexin-ifind-ds-stock-mcp` 能查的结构化数据，优先用它，不走 AlphaClaw 定量查询。`hexin-ifind-ds-news-mcp` 查新闻/公告时效性更强。AlphaClaw 专责定性内容（研报/纪要/公告观点）。

---

## 段落 × 数据类型速查

| 段落 | 核心数据类型 | 必须包含的证据等级 | 禁止出现 |
|------|-----------|-----------------|---------|
| 段1 公司定位 | 主营业务、行业分类 | F1/F2 | 无量化支撑的"行业领先" |
| 段2 业务拆分 | 收入/占比/YoY/毛利率 | F2 必需 | 空白单元格（应用[需补]标注） |
| 段3 收入驱动 | 量/价/结构/客户四维 | F2+M1 | 管理层发言当F2使用 |
| 段4 利润驱动 | 盈利能力+一致预期 | F2+M1 | 缺失ROE/净利率数字 |
| 段5 竞争力/风险 | 量化支撑（Beta/ESG/分红/股权） | F2 必需 | 纯定性描述 |
| 段6 市场焦点 | 催化/担忧/预期差 | M1+C1 | 直接复制研报原文 |
| 段7 可比差异 | 至少3家可比公司指标 | F2 | 少于3家可比公司 |
| 段8 跟踪指标 | 事件日历、分红节点、硬触发 | F2 | "关注政策变化"等废话 |
| 段9 待补资料 | — | — | 空白 |

---

## 常见问题速查

### Q1：查不到某公司分红数据怎么办？
A：分红数据从 `hexin-ifind-ds-stock-mcp.get_stock_events` 获取（预案公告日/派息日）。若该字段为空：
1. 查 `get_stock_events` 的历史分红记录（近3年）
2. 段9 列出"需从年报原文获取"作为必需项

### Q2：可比公司不足 3 家怎么办？
A：用 `hexin-ifind-ds-stock-mcp.search_stocks` 按行业搜索补充：
1. 调用 `get_stock_info` 获取公司所属行业
2. 用 `search_stocks` 按行业搜索
3. 优先选规模相近的主板公司
4. 若行业确实无可比公司，说明原因，在段7 注释中标注

### Q4：研报摘要信息不足怎么办？
A：使用 `get_document_detail` 获取研报全文：
1. 研报摘要无法支撑段5 核心竞争力分析时
2. 调用 `get_document_detail`，file_id 从 search_finance_reports 结果中获取
3. 不靠摘要写报告

### Q5：预测数据（FY2/FY3）缺失怎么办？
A：
1. 检查 `get_stock_financials` 预测字段是否返回空
2. 若为空，查 AlphaClaw `search_finance_reports`（国内研报）的盈利预测
3. 若仍为空，在一致预期表格中标注"暂无机构覆盖"，段9 注明"建议补充卖方预测"
4. 禁止自行估算 FY2/FY3 数字

### Q6：用户要求覆盖港股/美股怎么办？
A：本框架专为 A 股设计。
1. 判断公司是否在 A 股上市（创业板/科创板/主板/北交所）
2. 若为港股/美股，提示用户"本框架为 A 股设计，可改用 `ae:company-one-pager` 处理港美股"
3. 港股可尝试用 iFinD 的港股数据（`search_stocks` 支持港股），但输出格式仍按 9 段结构

---

## 执行检查点

研究过程中遇到以下情况时，立即检查：

1. **数据获取异常**：某 P0 级数据工具返回空 → 查看 Q1-Q5 速查
   - **注意**：调用时必须用完全限定名 `服务器名.工具名`（如 `hexin-ifind-ds-stock-mcp.get_stock_financials`），不能只写裸函数名
2. **段5 写不动**：缺少量化支撑 → 回头补充 Beta/股权/分红数据
3. **可比公司不够**：段7 可比 < 3 家 → 见 Q3
4. **研报内容不足**：摘要信息不够 → 调用 `get_document_detail`
5. **数据时间存疑**：财报数据不是最新一期 → 标注数据截止时间
