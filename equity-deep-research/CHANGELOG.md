# equity-deep-research 版本历史

- **v2.11**：修复编排模式 4b→4c 数据流断裂。4b 子 agent 必须用 write 写入磁盘文件；失败时重试子 agent（非主 agent 接管）。
- **v2.9**：段6新增情绪位置判断（卖方分歧度/持仓拥挤度/媒体热度）和不对称性赔率量化；段7新增安全边际子节（调整后内在价值锚定/历史分位/当前安全边际判断）。方法论借鉴 Howard Marks 框架的"价格与价值"、"逆向思维"和"不对称性"三个维度。
- **v2.7**：Acceptance Self-check 改为主 agent 内部自检（仍执行检查并修正问题，但自检表格不输出到最终报告）；Step 5 新增自动删除中间文件（cluster-A/B/C.md）。
- **v2.6**：新增输出格式禁止规范（纯 markdown、禁止图片/图表/可视化、bullet point 优先），格式合规加入陷阱速查表和 Acceptance Self-check。
- **v2.5**：文件命名规则优化，输出文件名格式从 `{yyyymmdd}-{最新一季财报日期}` 改为 `{yyyymmdd}-{证券代码}-{最新一季财报日期}`（如 `20260508-603986-2026Q1.md`）。
- **v2.4**：新增 Step 3.5「MECE + 逻辑链验证」。动笔前必做：三维检查（MECE / 逻辑链 / 对齐），问题直接在框架层面修正。≤ 2 处直接修正后动笔。
- **v2.2**：Step 4 从单 agent 写全 9 段改为 3 簇 sub-agent 并行写作 + 主 agent 拼接收尾。Step 3 预研框架新增段级论点（每段一句塔尖）。新增金字塔分工模型。analysis-template.md 增加 cluster 分区标记（cluster-A/B/C + main-agent）。快速通道保留给简单场景。
