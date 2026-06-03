---
name: youtube-transcript-to-article
description: 当用户提供 YouTube 视频链接并要求"生成书面总结文章"时触发。将视频字幕自动下载、解析、生成完整书面文章并保存为 .md 文件。
version: "3.0"
---

# YouTube 视频字幕转书面文章

## 你的角色

你是 youtube-transcript-to-article 的**操作员**，不是字幕处理库的开发者。

你的工作只有三件事：
1. 运行固定脚本（`fetch.py` → `parse_clean.py`）完成字幕下载和清洗
2. 调用 make-report subagent 或主 agent 直接撰写文章
3. 验证完整性、保存文件、清理中间产物

你不需要理解 fetch.py 的回退链和 parse_clean.py 的话题检测算法，这些脚本内部已处理。**不允许编写新的 Python 处理逻辑**。

## 最高优先级铁律

**违反即任务失败。以下行为绝对禁止：**

| 禁止行为 | 曾导致的事故 |
|---------|------------|
| 用 `write` 工具创建新的 .py 文件替代 fetch.py / parse_clean.py | `fetch.py` 内置 3 层字幕回退链 + 4 层元信息回退，临时脚本必然遗漏降级逻辑 |
| 跳过 parse_clean.py 自己写字幕清洗代码 | parse_clean.py 内置中英文话题边界检测、双语气词去除、多行格式保障，自写清洗必然丢边界信号 |
| 在步骤 4b 中嵌入多行 Python 代码做格式检测 | v2.x 的 30 行 `python -c` 块在 Git Bash 下曾因引号转义失败，parse_clean.py v2.1+ 已内置同等逻辑 |
| 让 make-report subagent 自行读取文件时不做完整性验证 | 单次 read 输出截断导致文章漏掉后半段内容，必须用量化覆盖率检查兜底 |

**允许的操作：**
- 环境检测：`python -c "import yt_dlp; ..."`（单行，仅检测依赖）
- 运行已有脚本：`python scripts/fetch.py`、`python scripts/parse_clean.py`
- 调用 make-report subagent 或主 agent 撰写文章
- 执行固定命令：缓存检查、完整性验证、文件清理

## 概述

接收 YouTube 视频链接，一键生成完整书面整理稿。流程：下载字幕（fetch.py）→ 清洗分块（parse_clean.py）→ 撰写文章（make-report / 主 agent）→ 保存。

> 版本历史见 [CHANGELOG.md](CHANGELOG.md)

---

## 执行步骤

### 步骤 0：提取视频 ID

从 URL 中提取 YouTube 视频 ID（11 位字符，`watch?v=` 后或 `youtu.be/` 后）。

### 步骤 1：环境检测

```bash
python -c "import yt_dlp; import youtube_transcript_api; print('依赖已就绪')"
```

报错则安装：`python -m pip install --user yt-dlp youtube_transcript_api`

### 步骤 2：缓存检查

检查 `D:\AlphaClaw\Podcast\cache\{video_id}\transcript_clean.txt` 是否存在，存在则跳过步骤 3-4 直接进入步骤 5。

### 步骤 3：下载字幕与元信息

运行 `scripts/fetch.py`，一条命令完成（内置完整回退链）：

```bash
python "{SKILL_BASE_DIR}/scripts/fetch.py" "{视频URL}" --output-dir "D:\AlphaClaw\Podcast" --lang en
```

从输出的 JSON 中提取 `video_id`、`title`、`upload_date`、`subtitle_file`。

> `{SKILL_BASE_DIR}` 为当前 skill 的 base directory。`--lang` 可选 `en`/`zh`/`auto`。

### 步骤 4：解析清洗与分块

运行 `scripts/parse_clean.py`（内置话题检测 + 多行格式保障）：

```bash
python "{SKILL_BASE_DIR}/scripts/parse_clean.py" --input-dir "D:\AlphaClaw\Podcast" --video-id "{video_id}" --lang en
```

从输出 JSON 提取 `total_chars`、`chunked`、`chunks`、`clean_file`。

**保存缓存**：将 `transcript_clean.txt` 复制到 `D:\AlphaClaw\Podcast\cache\{video_id}\`。

### 步骤 4b：多行格式兜底（仅缓存命中时）

> parse_clean.py v2.1+ 输出已默认为多行格式。此步骤仅防御历史缓存中的旧版单行文件。

若读取的缓存文件字符数 > 30000 但行数 < 100（即单行文件），重新运行步骤 4 的 `parse_clean.py` 即可解决。不要嵌入 Python 代码做手动格式转换。

### 步骤 5：生成书面文章

**先读取文章撰写规则**：`read {SKILL_BASE_DIR}/article-template.md`（7 条规则）。

**根据步骤 4 的 `chunked` 选择分支：**

#### 分支 A：短文本（chunked=false）

| 子策略 | 字数 | 方式 |
|--------|------|------|
| A1：极短 | < 3 万字 | 将字幕内容直接嵌入 make-report prompt |
| A2：中等 | 3-10 万字 | 让 make-report subagent 分多次 read 读取文件后撰写 |
| A3：备选 | 任意 | 步骤 4b 修复失败或用户反馈截断时，主 agent 直接分多次 read 后撰写 |

A2 prompt 必须包含 `{total_chars}` 信息 + "分多次读取"指令，防止单次 read 截断。

#### 分支 B：长文本（chunked=true）

| 子策略 | 分块数 | 方式 |
|--------|--------|------|
| B1：中等 | ≤ 6 块 | 主 agent 并行读取所有分块后直接撰写 |
| B2：大量 | > 6 块 | 两阶段：① 并行 make-report 写各块草稿 → ② 主 agent 拼接 + 统一文风 + 写头部 |

> 所有分支均使用 `article-template.md` 的相同 7 条规则。make-report prompt 中逐条列出规则，主 agent 直接撰写时引用模板文件。

### 步骤 6：完整性验证

量化覆盖率检查（防截断）：

1. 分多次 read 完整读取 `transcript_clean.txt`
2. 提取 10-15 个主要话题
3. 检查每个话题在生成文章中的覆盖情况
4. 覆盖率 ≥ 85% → 通过；60-84% → 检查缺失位置，若在末尾则回退到 A3；< 60% → 回退到 A3

### 步骤 7：保存文章

用 write 工具写入 `D:\AlphaClaw\Podcast\【{YYYYMMDD}】-{标题}.md`。特殊字符替换或截断至 80 字符。

### 步骤 8：清理中间文件

删除中间产物（.vtt、transcript_*.txt、c*.txt、临时 .py），**保留** `cache\{video_id}\transcript_clean.txt`。

---

## 退出前自检

在向用户报告结果之前，必须完成：

1. 本次任务中是否用 `write` 创建了新的 .py 文件替代 fetch.py / parse_clean.py？→ 是则**任务失败**。
2. 步骤 4b 中是否嵌入了多行 Python 代码做格式转换（而非重新运行 parse_clean.py）？→ 是则**任务失败**。
3. 步骤 6 完整性验证是否执行？→ 未执行则**任务失败**，必须先验证再报告。

全部通过后，正常报告结果。

---

## 踩坑日志

| 事故 | 原因 | 教训 |
|------|------|------|
| 步骤 4b 30 行 python -c 引号转义失败 | Git Bash 下多行 inline Python 中引号嵌套导致语法错误 | parse_clean.py 已内置同等逻辑，直接重新运行脚本即可 |
| 文章漏掉后半段内容 | make-report subagent 单次 read 截断，未验证完整性 | 步骤 6 量化覆盖率检查（≥85%）捕获此类问题 |
| 历史缓存单行文件导致读取截断 | 旧版 parse_clean.py 输出单行文件 | 步骤 4b 兜底检测 + 重新运行 parse_clean.py |
| subagent 自行下载字幕 | prompt 中描述了 yt-dlp API，subagent 绕过 fetch.py | prompt 中只给脚本命令，不给 API 细节 |

---

## 依赖与路径

- **Python 路径**：`C:\Program Files\AlphaEngine\resources\python\python\python.exe`
- **Python 库**：`yt-dlp`、`youtube_transcript_api`
- **工作目录**：`D:\AlphaClaw\Podcast`
- **脚本**：`{SKILL_BASE_DIR}/scripts/fetch.py`、`{SKILL_BASE_DIR}/scripts/parse_clean.py`
- **模板**：`{SKILL_BASE_DIR}/article-template.md`
- **子代理**：`make-report`（分支 A 和 B2）
