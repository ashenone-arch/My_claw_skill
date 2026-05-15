# 投研素材分析模板 · 9段结构

> 本模板用于 AI 生成公司深度投研素材，非客户路演报告。
> 素材包帮分析师快速建框架、拿数据、知道缺什么。

---

## 数据源映射

| 段落 | iFinD 优先 | AlphaClaw 补充 |
|------|-----------|---------------|
| 段1 | `get_stock_summary` / `get_stock_info` / `get_edb_data` | — |
| 段2 | `get_stock_financials`（主营拆解） | — |
| 段3 | `get_stock_financials`（利润表/资产负债表）+ `get_edb_data`（行业量价）+ `get_stock_shareholders`（客户结构） | — |
| 段4 | `get_stock_financials`（利润表 + 预测指标：预测净利润/营收/EPS/PE/ROE FY1-FY3） | `search_finance_reports`（国内研报 盈利预测观点） |
| 段5 | `get_stock_shareholders`（股权集中度）+ `get_risk_indicators`（Beta）+ `get_esg_data`（ESG 评级）+ `get_stock_events`（分红/回购） | `search_finance_reports`（国内研报:公司研究 投资逻辑） |
| 段6 | `get_stock_performance`（涨跌幅/换手率）+ `get_stock_shareholders`（外资/机构变化）+ `search_news` / `search_trending_news` | `search_finance_reports`（会议纪要全类） |
| 段7 | `get_stock_financials`（批量可比）+ `get_risk_indicators`（风险调整对比）+ `get_esg_data`（ESG 对比） | — |
| 段8 | `get_stock_financials`（分红进度）+ `get_stock_events`（事件日历）+ `search_notice` | `search_finance_reports`（公告:财务经营报告） |
| 段9 | 基于前 8 段缺失判断 | 基于前 8 段缺失判断 |

---

## 证据等级表

| 标签 | 含义 | 示例 |
|------|------|------|
| F1 | 公开可验证事实 | 交易所披露 |
| F2 | 财报/金融数据库/公告 | 年报、iFinD 数据 |
| M1 | 市场一致预期 + 管理层公开发言 | 卖方预测、业绩会发言 |
| C1 | 合理推演 | 需附推演链路 |
| H1 | 待核验假设 | 必须标"未经核验" |

**约束**：没有证据等级 = 不能写。关键结论必须有 F1/F2 支撑。

---

## 9段结构与写作规范

### 段1 · 公司定位

**所需数据**：公司基本信息（iFinD `get_stock_summary` / `get_stock_info`）+ 可比公司（iFinD `search_stocks`）

```
### 产业链位置
（一句话，带证据等级）

### 产品结构
（按收入占比排序，列出主要产品/业务线，带具体数字）

### 差异化 vs 同业
（与 3-5 家可比公司逐项对比）
- vs [可比公司A]：[具体差异，如"负债成本低Xbp"]
```

**证据**：F2 优先，C1 需附推演链路

---

### 段2 · 业务拆分

**所需数据**：主营构成拆解、利润表（iFinD `get_stock_financials`）

```
| 业务线 | 收入（亿） | 占比 | YoY | 毛利率 | 证据 |
|--------|-----------|------|-----|--------|------|
| [业务A] | XX | XX% | +X% | XX% | F2 |

⚠️ 数据缺失说明（如有）
```

**规则**：元→亿，保留2位小数；缺失数据标 `[需补]`

---

### 段3 · 收入驱动

**所需数据**：利润表、资产负债表、主营构成（iFinD `get_stock_financials`）+ 行业宏观数据（iFinD `get_edb_data`）+ 股东结构（iFinD `get_stock_shareholders`）

```
按"量/价/结构/客户"四维拆解：

- **[维度]**：[结论]（[证据等级]-[来源]）

禁止把管理层公开发言当 F2 事实使用（发言 = M1）
```

---

### 段4 · 利润驱动

**所需数据**：利润表（iFinD `get_stock_financials`）+ 盈利预测（iFinD `get_stock_financials` 预测类指标：预测净利润/营收/EPS/PE/ROE FY1-FY3）

```
### 盈利能力
- 毛利率/净利率：[数字]（F2）
- ROE：[数字]，同比+/-XXbp（F2）

### 弹性分析
- 若[变量]变动X%，则利润变动约XX亿（C1-基于历史数据回归）

### 一致预期
| 机构 | 2025E净利润 | 2026E净利润 | 预测日期 |
```

---

### 段5 · 核心竞争力 / 主要风险

**所需数据**：投资逻辑研报（AlphaClaw `search_finance_reports` 国内研报:公司研究）+ 可比公司财务（iFinD）+ 股东结构（iFinD `get_stock_shareholders`）+ 风险定量（iFinD `get_risk_indicators`）+ ESG 评级（iFinD `get_esg_data`）+ 分红回购（iFinD `get_stock_events`）

```
### 核心竞争力（2-3条）
- **[竞争力名称]**：[具体描述]（[证据等级]-[来源]）
  验证路径：[如何跟踪验证]

### 主要风险（2-3条）
- **[风险名称]**：[具体描述]（[证据等级]-[来源]）
  触发条件：[如何观察]
```

**规则**：必须指名道姓对比，不能写"行业领先"等废话。竞争力必须有量化支撑（如分红总额、Beta、ESG 评级、股权集中度等），不能纯定性描述。

---

### 段6 · 市场焦点

**所需数据**：市场观点/纪要（AlphaClaw `search_finance_reports` 会议纪要全类）+ 新闻情绪（iFinD `search_news` / `search_trending_news`）+ 行情数据（iFinD `get_stock_performance`）+ 股东变化（iFinD `get_stock_shareholders`）

```
### 市场在交易什么
- [催化逻辑]（M1-[来源]-[日期]）

### 核心担忧
- [担忧内容]（M1-[来源]-[日期]）

### 预期差在哪
- [市场共识] vs [我们的判断]（C1）
```

**规则**：禁止复制 KB 原文，必须提炼观点

---

### 段7 · 可比与差异

**所需数据**：可比公司财务指标（iFinD `get_stock_financials` 批量）+ 风险调整后指标（iFinD `get_risk_indicators`）+ ESG 对比（iFinD `get_esg_data`）

```
### 关键指标横向对比
（表格，含公司、代码、收入、净利润、YoY、ROE、PB/PE）

### 核心差异分析
- [维度A]：[公司] vs [可比] → [结论]（C1）
```

**规则**：至少 3 家可比公司

---

### 段8 · 跟踪指标

**所需数据**：管理层讨论（AlphaClaw `search_finance_reports` 公告:财务经营报告）+ 纪要 + 分红进度（iFinD `get_stock_financials` 分红字段）+ 事件日历（iFinD `get_stock_events`）

```
### 下次财报重点看
- [指标名]：[当前值] → [关注方向]（F2）

### 三个月内关键变量
1. [变量名] — 跟踪方式：[怎么查] — 触发条件：[X则Y]（C1）
2. [...]
3. [...]
```

**规则**：禁止"关注政策变化"等废话，必须具体到可操作

---

### 段9 · 仍需补的资料

```
**必需**（影响核心判断）：
- [缺失数据] — 应从 [数据源] 获取

**建议**（提升分析质量）：
- [...]

**不确定但影响判断**：
- [假设性问题]
```

**规则**：此段不能为空

---

## Acceptance Self-check（报告末尾必须执行）

```
## 📋 Acceptance Self-check

[段1 · 公司定位]
- 产业链位置有（F1/F2）支撑？ → ✅/❌
- 差异化 vs 至少3家可比公司？ → ✅/❌

[段2 · 业务拆分]
- 表格完整（收入/占比/YoY/毛利率）？ → ✅/❌
- 缺失数据有标注？ → ✅/❌

[段3 · 收入驱动]
- 量/价/结构/客户四维拆解完整？ → ✅/❌
- 每条带证据等级？ → ✅/❌

[段4 · 利润驱动]
- 有ROE/净利率具体数字？ → ✅/❌

[段5 · 核心竞争力/风险]
- 竞争力 vs 可比公司逐项对比？ → ✅/❌
- 风险有触发条件？ → ✅/❌

[段6 · 市场焦点]
- 有催化/担忧/分歧三类？ → ✅/❌

[段7 · 可比与差异]
- 至少3家可比公司？ → ✅/❌

[段8 · 跟踪指标]
- 至少3个具体可操作指标？ → ✅/❌
- 有硬触发条件？ → ✅/❌

[段9 · 仍需补的资料]
- 非空？ → ✅/❌

[合规]
- 无违禁表述？ → ✅/❌

**结论**：✅ 通过 / ❌ 未通过（需补充XXX）
```

**没过 = 没做完，不允许交付。**
