# youtube-transcript-to-article 版本历史

- **v2.1** 核心改进（基于 v2.0）：
  - 规则外置：文章撰写规则提取为 `article-template.md`，分支 A / B 共享，消除重复
  - 脚本持久化：`scripts/fetch.py` 和 `scripts/parse_clean.py` 预置在 skill 目录，无需每次写入
  - 缓存机制：同一视频重复执行时跳过下载和清洗步骤
  - 双语话题检测：parse_clean.py 同时支持英文和中文话题边界信号
  - 长文本并行：超 6 块时采用并行 make-report subagent 策略
  - 完整性验证：文章生成后自动检查是否覆盖所有话题
  - 多行格式保障：parse_clean.py 输出自动检测并修复单行文件，防止下游读取截断
  - 兜底格式检测：步骤 4b 独立多行格式兜底，覆盖历史缓存文件
  - 验证强化：步骤 6 从目视检查升级为量化覆盖率检查（≥85% 阈值）
