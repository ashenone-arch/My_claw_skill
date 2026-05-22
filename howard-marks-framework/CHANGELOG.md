# howard-marks-framework 版本历史

- **v2.2**：新增双模式架构（深度/浅度）。浅度模式仅 1 个 gather + 主 agent 直接输出简报，不写文件、不调用 make-report、不执行 MECE 和 Acceptance Self-check；深度模式保持原完整 6 步流程。模式由关键词自动判断或用户选择。原"场景路由"简化为"模式判断"。
- **v2.1**：修复增强层弥补核心层缺失的逻辑漏洞，新增证据等级体系（D1/D2/D3），增加陷阱速查表，拆分 references 文件。
- **v2.0**：全面重构。新增执行铁律、金字塔分工模型、3 簇并行 make-report 架构、MECE 维度交叉检查、时间精度规则、Acceptance Self-check、数据缺口章节。文件拆分优化：维度详细评估标准移至 `references/dimensions.md`，输出格式模板移至 `references/output-format.md`，SKILL.md 瘦身 ~50%。
