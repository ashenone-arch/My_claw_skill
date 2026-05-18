# cross-talk-synthesis 版本历史

- **v2.5**：执行铁律新增第 6 条「中文输出」（英文 Q1 引语必须先翻译为中文再引用）；步骤 5.1/5.2/5.3(5b) 追加 `write` 工具文件写入约束，禁止 make-report agent 使用 shell 写文件；步骤 6 重写为「保存与清理」（最终文章输出至源文件文件夹，中间文件在用户确认后统一清理）；WRITING-STANDARDS.md 新增「英文引语翻译」规则；EXTRACT-GUIDE.md Q1 标注格式追加英文翻译说明。
- **v2.4**：新增 BATCH-STRATEGY.md（大批量文件分组策略，>10 篇时触发）；大批量场景步骤 2 只提取最小信息集；内容地图模板增加话题频次、文件×话题矩阵、嘉宾多样性展示。
- **v2.3**：执行铁律新增纯文本约束（禁止图片/图表/可视化），SKILL.md 增加输出格式快速引用。
- **v2.2**：编排模式新增 MECE 审查轮（5a-review），主 agent 与 sub-agent 按金字塔层级分工，增加快速通道（≤2 话题），5a 主 agent 只读塔尖候选不读提取文件全文，WRITING-STANDARDS.md 增加显式 sub-agent 分区标记。
