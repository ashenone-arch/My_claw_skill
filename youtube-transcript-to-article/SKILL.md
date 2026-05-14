---
name: youtube-transcript-to-article
description: 当用户提供 YouTube 视频链接并要求"生成书面总结文章"时触发。将视频字幕自动下载、解析、生成完整书面文章并保存为 .md 文件。
version: v2.1
---

# YouTube 视频字幕转书面文章 v2.1

## 概述

接收 YouTube 视频链接，一键生成完整书面整理稿，保存至 `D:\AlphaClaw\Podcast\【{上传日期}】-{标题}.md`。

v2.1 核心改进（基于 v2.0 的基础上）：
- **规则外置**：文章撰写规则提取为 `article-template.md`，分支 A / B 共享，消除重复
- **脚本持久化**：`scripts/fetch.py` 和 `scripts/parse_clean.py` 预置在 skill 目录，无需每次写入
- **缓存机制**：同一视频重复执行时跳过下载和清洗步骤
- **双语话题检测**：parse_clean.py 同时支持英文和中文话题边界信号
- **长文本并行**：超 6 块时采用并行 make-report subagent 策略
- **完整性验证**：文章生成后自动检查是否覆盖所有话题
- **多行格式保障**：parse_clean.py 输出自动检测并修复单行文件，防止下游读取截断
- **兜底格式检测**：步骤 4b 独立多行格式兜底，覆盖历史缓存文件
- **验证强化**：步骤 6 从目视检查升级为量化覆盖率检查（≥85% 阈值）

---

## 执行步骤

### 步骤 0：提取视频 ID

从用户提供的 URL 中提取 YouTube 视频 ID（11 位字符，`watch?v=` 后或 `youtu.be/` 后）。
URL 可能带有额外参数（如 `&pp=`），以 `watch?v=` 后的字符串为准。

### 步骤 1：环境检测与依赖安装

**先检测后安装**。优先使用系统提醒中的 Python 路径。

```bash
python -c "import yt_dlp; import youtube_transcript_api; print('依赖已就绪')"
```

- 输出 "依赖已就绪" → 跳到步骤 2
- 报 ModuleNotFoundError → 执行安装：

```bash
python -m pip install --user yt-dlp youtube_transcript_api
```

### 步骤 2：缓存检查

检查是否存在该视频的缓存。缓存目录：`D:\AlphaClaw\Podcast\cache\{video_id}\`

若 `transcript_clean.txt` 已存在于缓存目录：
- 直接复用，跳到步骤 5
- 跳过步骤 3 和 4

否则继续步骤 3。

### 步骤 3：下载字幕与元信息（scripts/fetch.py）

调用持久化脚本 `scripts/fetch.py`，一条命令完成元信息获取和字幕下载。

脚本内置完整回退链：
- **元信息**：yt-dlp web → yt-dlp android → oEmbed API（标题）+ yt-dlp android（日期）
- **字幕**：yt-dlp VTT(web) → yt-dlp VTT(android) → youtube_transcript_api

```bash
python "{SKILL_BASE_DIR}/scripts/fetch.py" "{视频URL}" --output-dir "D:\AlphaClaw\Podcast" --lang en
```

> `{SKILL_BASE_DIR}` 为当前 skill 的 base directory（见对话开头的 skill 加载信息）。

输出为 JSON，提取关键字段：
- `video_id` / `title` / `upload_date`
- `subtitle_file`（字幕文件路径）
- `subtitle_type`（`vtt` 或 `raw`）

若脚本返回 error：
- 根据错误信息判断原因（无字幕 / 视频不可用 / 网络问题）
- 向用户报告具体原因

### 步骤 4：解析清洗与智能分块（scripts/parse_clean.py）

调用持久化解析脚本，清洗字幕并做话题感知分块。

```bash
python "{SKILL_BASE_DIR}/scripts/parse_clean.py" --input-dir "D:\AlphaClaw\Podcast" --video-id "{video_id}" --lang en
```

> `--lang` 参数：`en`（英语为主）、`zh`（中文为主）、`auto`（自动检测）。根据视频语言选择。

脚本输出 JSON，提取关键字段：
- `total_chars`：清洗后文本总字符数
- `chunked`：是否已分块（true/false）
- `chunks`：分块列表（若 chunked=true），每项含 `file`、`topic_label`、`chars`
- `clean_file`：清洗后完整文本路径

**保存缓存**：将 `transcript_clean.txt` 复制到 `D:\AlphaClaw\Podcast\cache\{video_id}\`

脚本内置增强的话题检测（见 `parse_clean.py` 中的 `TOPIC_BOUNDARY_PATTERNS`）：
- 英文：提问句式、过渡语、广告插入、讲座信号、结束语
- 中文：提问句式、话题过渡、结束语
- 双语气词去除（en + zh）

### 步骤 4b：多行格式兜底检测

> **关键步骤**：无论是否命中缓存，在进入步骤 5 之前必须执行此检查。

此步骤防御两类单行文件问题：
1. `parse_clean.py` 历史版本（v2.0 及之前）输出的单行文件（缓存中可能存在旧文件）
2. 任何因写入异常导致的单行文件

**检查方法**：

```bash
python -c "
import os, re
path = r'D:\AlphaClaw\Podcast\cache\{video_id}\transcript_clean.txt'
paths = [path]
work_path = r'D:\AlphaClaw\Podcast\transcript_clean.txt'
if os.path.exists(work_path):
    paths.append(work_path)
for p in paths:
    if not os.path.exists(p): continue
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.count(chr(10)) + 1 if content else 0
    chars = len(content)
    if chars > 30000 and lines < 100:
        multiline = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', chr(10), content)
        multiline = re.sub(r'(?<=[\u3002\uff01\uff1f])\s*', chr(10), multiline)
        multiline = re.sub(r'\s*>>\s*', chr(10), multiline)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(multiline)
        new_lines = multiline.count(chr(10)) + 1
        print(f'多行格式化: {lines} 行 -> {new_lines} 行')
    else:
        print(f'格式正常: {lines} 行, {chars} 字符')
"
```

> 检测逻辑与 `parse_clean.py` v2.1 内置的 `_ensure_multiline` 一致。此步骤作为独立兜底，覆盖历史缓存、v2.0 输出和任何边缘情况。检测到单行文件时自动按句子边界格式化为多行。

### 步骤 5：生成书面文章

**先读取文章撰写规则模板**（所有分支均需）：

```markdown
读取文件: {SKILL_BASE_DIR}/article-template.md
获取 7 条撰写规则。
```

**然后根据步骤 4 的 `chunked` 字段选择分支：**

---

#### 分支 A：短文本（chunked=false，≤10 万字）

**前提**：步骤 4b 已确保 `transcript_clean.txt` 为多行格式（行数 ≥ 100）。若步骤 4b 检测到单行文件且自动修复失败，不要走此分支——改用下方 **A3 备选路径**。

根据文本长度选择子策略：

##### A1：极短文本（<3 万字）

将字幕内容直接嵌入 prompt，省去一次文件读取：

```
Task(
    subagent_type="make-report",
    description="生成 YouTube 视频书面整理稿",
    prompt="你是一位专业播客整理编辑。请将以下 YouTube 视频的完整字幕整理为书面文章。

**文章撰写规则**（详见下方，已从 article-template.md 加载）：
[此处逐条列出 7 条规则]

视频标题：{title}
上传日期：{upload_date_formatted}

完整字幕内容如下：
---
{从 transcript_clean.txt 读取的完整文本}
---
请严格按规则整理为 Markdown 书面文章，直接输出最终内容。",
    stream_to_parent=True
)
```

##### A2：中等文本（3-10 万字）

让 make-report subagent 自行读取文件。**prompt 中必须明确指示分多次 read 完整文件**：

```
Task(
    subagent_type="make-report",
    description="生成 YouTube 视频书面整理稿",
    prompt="你是一位专业播客整理编辑。请将以下 YouTube 视频的完整字幕整理为书面文章。

**重要**：字幕文件路径为 D:\AlphaClaw\Podcast\cache\{video_id}\transcript_clean.txt。
该文件约 {total_chars} 字符（多行格式），请使用 read 工具**分多次读取完整文件**（例如 read(path, limit=2000) 然后 read(path, offset=2000, limit=2000) 继续...），确保覆盖全文后再开始撰写。不完整读取会导致文章严重截断。

**文章撰写规则**：
[此处逐条列出 7 条规则]

视频标题：{title}
上传日期：{upload_date_formatted}

请严格按规则整理为 Markdown 书面文章，直接输出最终内容。",
    stream_to_parent=True
)
```

> **关键**：prompt 中的"分多次读取"指令和 {total_chars} 信息让 subagent 知道文件大小，避免单次 read 输出截断。

##### A3：备选——主 agent 直接撰写（B1 降级）

当以下任一情况发生时，改用主 agent 直接撰写（与 B1 相同流程）：

- 步骤 4b 检测到单行文件且自动修复失败
- 用户反馈文章被截断，需要重新生成

操作：主 agent 分多次 `read` 读取完整 `transcript_clean.txt`，按照 `article-template.md` 的 7 条规则直接撰写完整 Markdown 文章，使用 `write` 工具输出。

---

#### 分支 B：长文本（chunked=true，>10 万字）

**根据分块数量选择子策略：**

##### B1：中等分块（≤6 块）—— 主 agent 直接撰写

1. 并行读取所有分块文件（c00.txt ~ cXX.txt）
2. 主 agent 基于全部内容，按照 `article-template.md` 的 7 条规则直接撰写 Markdown 文章
3. 使用 `write` 工具输出完整文章

##### B2：大量分块（>6 块）—— 两阶段并行

**阶段 1（并行）**：为每个分块发起独立 make-report subagent，输出该块的"章节草稿"：

```
对每个 cXX.txt 分别调用（同一条消息中并行发出所有 Task 调用）：
Task(
    subagent_type="make-report",
    description=f"处理分块 {i}: {topic_label}",
    prompt="你是一位播客编辑。请将以下分块字幕整理为连贯的章节草稿。

规则（来自 article-template.md）：
[逐条列出 7 条规则——与分支 A 相同]

本块话题：{topic_label}
分块内容：
---
{从 cXX.txt 读取的文本}
---
请直接输出本块的章节草稿（Markdown 格式，## 用于章节标题）。",
)
```

**阶段 2（合并）**：主 agent 收集所有章节草稿后：
1. 按分块顺序拼接
2. 统一文风（消除不同 subagent 之间的表述差异）
3. 添加跨章节过渡句
4. 添加文章头部（标题、日期）
5. 输出完整 Markdown 文章

---

> **撰写规则引用说明**：分支 A、B1、B2 均使用 `article-template.md` 中的相同 7 条规则。在 make-report prompt 中逐条列出规则（因 subagent 无法读取 skill 目录文件），在 B1 主 agent 直接撰写时引用模板文件。

### 步骤 6：完整性验证

文章生成后，执行量化覆盖率检查，拦截"漏掉后半段"的严重错误。

**6.1 提取话题列表**：

读取 `transcript_clean.txt` 的**完整内容**（分多次 read 确保覆盖全文），用一段极简 prompt 让模型提取 10-15 个主要话题/关键词：

```
读取上述文件的完整内容（分多次 read 确保完整覆盖），列出这段对话中讨论的主要话题和关键词（10-15个），每行一个。格式：`- 话题描述`。不需要解释。
```

**6.2 覆盖率计算**：

对 6.1 中提取的每个话题，在生成的文章中检查是否出现。判定标准：
- 话题的核心关键词（或其同义表达）在文章中出现 → 匹配
- 话题完全未提及或仅有标题而无实质内容 → 缺失

计算覆盖率 = 匹配话题数 / 总话题数。

**6.3 判定与处理**：

| 覆盖率 | 判定 | 动作 |
|--------|------|------|
| ≥ 85% | 通过 | 继续步骤 7 |
| 60%-84% | 部分截断 | 检查缺失话题集中在文章哪个位置（前 1/3、中间、末尾）。若集中在末尾则确认为读取截断，回到步骤 5 选用 **A3（主 agent 直接撰写）** 重新生成 |
| < 60% | 严重截断 | 回到步骤 5 选用 **A3（主 agent 直接撰写）**，确保分多次 read 读取完整文件后撰写 |

> 此步骤将验证从不可靠的目视检查升级为可量化的覆盖率判定（≥85% 通过阈值），能有效捕获因单行文件或 subagent 读取不完整导致的话题遗漏。

### 步骤 7：保存文章文件

将最终文章写入文件：

- 路径：`D:\AlphaClaw\Podcast\【{YYYYMMDD}】-{标题}.md`
- 上传日期格式从 `YYYYMMDD` 转为 `【YYYYMMDD】`
- 使用 write 工具写入
- 写入完成后向用户确认

**文件命名规则**：
- 特殊字符（`/`、`\`、`:`、`?`、`*`）替换为 `-` 或移除
- 引号 `'` `"` 移除
- 标题过长时截断至 80 字符

### 步骤 8：清理中间文件

仅保留最终的 `.md` 文件，删除所有中间文件：

使用 glob 确认 `D:\AlphaClaw\Podcast` 下文件列表，然后删除：
- 所有 `.vtt` 文件
- `transcript_raw.txt`、`transcript_clean.txt`
- 所有分块文件 `c*.txt`
- 任何 `.py` 文件（如果执行过程中写入了临时脚本）

**保留**：`cache\{video_id}\transcript_clean.txt`（供后续复用）

删除后再次 glob 确认清理完成。

---

## 故障排查与回退策略

### yt-dlp 常见错误

| 错误信息 | 原因 | 方案 |
|----------|------|------|
| `"This video is not available"` | web client 被限制 | fetch.py 自动切换 android client |
| `"GVS PO Token was not provided"` | Android client 缺 PO Token | 警告可忽略 |
| 字幕下载返回空 | 无手动字幕或反爬限制 | fetch.py 自动切换 youtube_transcript_api |

### youtube_transcript_api 常见错误

| 错误信息 | 原因 | 方案 |
|----------|------|------|
| `TranscriptsDisabled` | 视频禁用了字幕 | 向用户报告，无法继续 |
| `NoTranscriptFound` | 视频无英文/指定语言字幕 | 尝试 `--lang` 切换语言代码 |

### 关键原则

1. **不依赖单一路径**：fetch.py 内置完整回退链，3 层字幕获取 + 4 层元信息获取
2. **缓存优先**：同一视频重复处理时跳过下载和清洗
3. **分块不丢信息**：话题感知分块确保每块从完整话题开始，不做句子截断

---

## 依赖与路径

- **Python 路径**：优先系统提醒中的 Python 路径，其次 `C:\Program Files\AlphaEngine\resources\python\python\python.exe`
- **Python 库**：`yt-dlp`、`youtube_transcript_api`
- **工作目录**：`D:\AlphaClaw\Podcast`
- **Skill 脚本**：`{SKILL_BASE_DIR}/scripts/fetch.py`、`{SKILL_BASE_DIR}/scripts/parse_clean.py`
- **规则模板**：`{SKILL_BASE_DIR}/article-template.md`
- **子代理**：`make-report`（分支 A 和 B2）
