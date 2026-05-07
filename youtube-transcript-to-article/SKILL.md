---
name: youtube-transcript-to-article
description: 当用户提供 YouTube 视频链接并要求"生成书面总结文章"时触发。将视频字幕自动下载、解析、生成完整书面文章并保存为 .md 文件。
version: v1.0
---

# YouTube 视频字幕转书面文章

## 概述

接收 YouTube 视频链接，一键生成完整书面整理稿，保存至 `D:\AlphaClaw\Podcast\{上传日期\}-{视频标题}.md`。工作流涵盖字幕下载、解析清洗、文字转文章、保存输出、中间文件清理全流程。

## 执行步骤

### 步骤 1：环境检测与依赖安装

**先检测后安装**——每次调用先检查依赖是否就绪，已安装则跳过安装步骤。

Python 路径（Windows）：优先使用系统提醒中的 Python 路径，其次：
```
C:\Program Files\AlphaEngine\resources\python\python\python.exe
```

#### 检测命令

先运行以下命令检查两个库是否已安装：

```bash
python -c "import yt_dlp; import youtube_transcript_api; print('依赖已就绪')"
```

- **输出 "依赖已就绪"** → 跳过安装，直接进入步骤 2
- **报 ModuleNotFoundError** → 执行下方安装命令

#### 安装命令（仅在缺失时执行）

```bash
python -m pip install --user yt-dlp youtube_transcript_api
```

> **依赖说明**：`yt-dlp` 是元信息和字幕下载的主方案；`youtube_transcript_api` 是字幕获取的备选方案（当 yt-dlp 因 YouTube 反爬限制无法下载字幕时启用）。两个库均需安装。

### 步骤 2：获取视频元信息（上传日期 + 标题）

**优先级链**：web client → android client → oEmbed API（标题）+ android client（日期）

#### 主方案：yt-dlp web client

```bash
python -m yt_dlp --print "%(upload_date)s\n%(title)s" --skip-download {视频URL}
```

#### 回退方案 1：切换 Android client

若 web client 报 `"This video is not available"`，切换客户端：

```bash
python -m yt_dlp --print "%(upload_date)s\n%(title)s" --skip-download --extractor-args "youtube:player_client=android" {视频URL}
```

> Android client 可能输出 `"GVS PO Token was not provided"` 警告，但元信息通常仍能正常获取，忽略警告即可。

#### 回退方案 2：oEmbed API（标题）+ yt-dlp android（日期）

若以上均失败，分两步获取：

1. **标题**：通过 YouTube oEmbed API 获取（无需认证，100% 可用）
   ```
   GET https://www.youtube.com/oembed?url={视频URL}&format=json
   ```
   返回 JSON，取 `title` 字段。使用 `webfetch` 工具（region=global）获取。

2. **日期**：用 yt-dlp android client 单独获取（见回退方案 1）。若仍然失败，再用 `webfetch` 抓取页面 `<meta>` 标签中的 `uploadDate`，或回退到当前日期。

- `upload_date` 格式为 `YYYYMMDD`，后续转为 `【YYYYMMDD】` 放入文件名
- `title` 即视频标题，直接用于文件名（特殊字符需清理，见文件命名规则）
- URL 可能带有额外参数（如 `&pp=`），提取视频 ID 时以 `watch?v=` 后的字符串为准

### 步骤 3：下载字幕文件

**双路径策略**：优先 yt-dlp（质量更高），失败时自动切换 youtube_transcript_api。

---

#### 路径 A：yt-dlp 下载 VTT 字幕（优先）

**关键：使用 `--write-sub` 而非 `--write-auto-sub`**

```bash
python -m yt_dlp --write-sub --sub-lang en --convert-subs vtt --skip-download --paths "D:\AlphaClaw\Podcast" {视频URL}
```

若 web client 不可用，追加 `--extractor-args "youtube:player_client=android"`：

```bash
python -m yt_dlp --write-sub --sub-lang en --convert-subs vtt --skip-download --extractor-args "youtube:player_client=android" --paths "D:\AlphaClaw\Podcast" {视频URL}
```

说明：
- `--write-auto-sub`（自动字幕）产生的 VTT 格式复杂，带有 `<c>` 内联标签和渐进式显示格式，同一条字幕会在文件中重复出现多遍，导致解析困难、文本暴增数倍
- `--write-sub`（手动字幕/上传字幕）产生的 VTT 格式干净整洁，无重复，是高质量的转录来源
- 字幕文件保存为 `{视频ID}.en.vtt`（若手动字幕存在）或 `{视频ID}.en.auto.vtt`（只有自动字幕时）
- 若下载成功 → 跳至步骤 4（走 VTT 解析流程）

---

#### 路径 B：youtube_transcript_api 直接获取（备用）

当 yt-dlp 字幕下载失败（如视频不可用、无字幕等）时，使用此路径。

**关键：v1.x API 用法（与旧版不同）**

```python
from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()
result = api.fetch(video_id, languages=['en'])

# result 是 FetchedTranscript 对象，迭代得到 FetchedTranscriptSnippet
# 每个 snippet 是 dataclass，用属性访问：snippet.text, snippet.start, snippet.duration
segments = list(result)

# 保存为每行一段的原始文本
with open(r'D:\AlphaClaw\Podcast\transcript_raw.txt', 'w', encoding='utf-8') as f:
    for s in segments:
        f.write(f'{s.text}\n')
```

> **常见 API 错误**：
> - ❌ `YouTubeTranscriptApi.get_transcript()` → v1.x 已移除，用 `api.fetch()` 替代
> - ❌ `YouTubeTranscriptApi.fetch(video_id)` → `fetch()` 是实例方法，需先 `api = YouTubeTranscriptApi()`
> - ❌ `s['text']` → `FetchedTranscriptSnippet` 不是 dict，用 `s.text` 属性访问

若此路径成功 → 跳至步骤 4（走 raw text 解析流程，见下方说明）

### 步骤 4：解析并清洗字幕（Python 脚本）

编写并执行 Python 脚本（如 `D:\AlphaClaw\Podcast\parse_clean.py`）。

**自动检测输入格式**：脚本需同时支持两种输入——
- **VTT 格式**（来自 yt-dlp 路径 A）：文件扩展名 `.vtt`，包含时间戳和 HTML 标签
- **Raw text 格式**（来自 youtube_transcript_api 路径 B）：文件名为 `transcript_raw.txt`，每行一个字幕段，无时间戳无标签

处理逻辑（两种格式共有）：

```
1. 检测输入文件类型：优先找 .vtt（路径 A），若无则找 transcript_raw.txt（路径 B）
   - VTT 路径：解析时间戳、去 HTML 标签、合并同 cue 多行
   - Raw 路径：直接按行读取，每行即一个段落
2. 段间去重：若本段文本与上一段完全相同则跳过
3. 去除语气词：\bum\b, \buh\b, \ber\b, \bmm\b, \bhm\b, \bah\b（全小写，regex 边界匹配）
4. 合并多余空格
5. 保存清洗后的完整文本到 transcript_clean.txt（供分支 A 使用）
6. 话题边界检测：对去重后的段落逐一扫描，用正则匹配话题转换信号（提问句式、显式过渡语、广告插入、话题重置语等），标记话题边界段
7. 基于话题边界智能分块：以段为单位累积文本，当接近目标块大小（约 2 万字）时，向前回溯到最近一个已标记的话题边界处切分——确保每块以完整话题开头，而非在句子中间截断
8. 将每个块保存为 c00.txt, c01.txt, ...，文件头部写入该块的话题摘要行
9. 打印清洗统计信息（总字符数、段落数、输入格式、是否拆分、分块数量、每块的话题标签）
```

参考脚本 `parse_clean.py`：

```python
import re
import glob
import os

# === 话题边界检测模式 ===
# 这些正则匹配访谈中的话题转换信号，按优先级排列
TOPIC_BOUNDARY_PATTERNS = [
    # 广告/赞助插入（强边界，前后话题通常无关）
    r'(?i)\b(quick pause|thank you to our sponsors|check them out in the description|back to my conversation|now back to|and now.*back to)\b',
    # 主持人明确引入新话题的提问句式
    r'(?i)\b((so|and|now|alright|okay)\s*[,.]*\s*(tell me about|can (you|we) (talk|speak|discuss)|let me ask|I (want|wanted|gotta|have) to (ask|mention|talk|bring up)|what (do|did) you think|how (did|do) you|before I forget|I wanted to mention|let\'s (talk|discuss|go)))\b',
    # 显式话题过渡
    r'(?i)\b(let\'s move on|switching gears|on a different note|one more (thing|question)|moving on|to change the subject|let\'s go back|I want to go back|going back to|you mentioned (earlier|before))\b',
    # 采访者引用受访者之前的话来引入新话题
    r'(?i)\b(you (said|mentioned|talked about|described)|earlier you|you\'ve (talked|spoken|written))\b',
    # 结束语/告别
    r'(?i)\b(thank you (so much|for (everything|talking|being|coming)|Jeff)|thanks for listening|let me leave you with|hope to see you next time)\b',
]

def is_topic_boundary(segment_text):
    """判断一个段落是否可能是话题转换点"""
    for pattern in TOPIC_BOUNDARY_PATTERNS:
        if re.search(pattern, segment_text):
            return True
    return False

def extract_topic_label(segment_text, max_len=60):
    """从话题边界段提取简短话题标签"""
    # 截取前 max_len 字符作为标签，去除多余空格
    label = segment_text.strip()[:max_len]
    # 如果截断了，补省略号
    if len(segment_text.strip()) > max_len:
        label = label.rsplit(' ', 1)[0] + '...'
    return label

# === 找到 VTT 文件 ===
vtt_files = glob.glob(r'D:\AlphaClaw\Podcast\*.vtt')
if not vtt_files:
    print("ERROR: No VTT file found")
    exit(1)

vtt_path = vtt_files[0]
print(f"Processing: {os.path.basename(vtt_path)}")

with open(vtt_path, 'r', encoding='utf-8') as f:
    content = f.read()

# === 解析 VTT → 段落列表 ===
lines = content.split('\n')
segments = []
current_text = []
in_cue = False

for line in lines:
    line = line.strip()
    if not line or line in ('WEBVTT', 'Kind: captions', 'Language: en'):
        continue
    if '-->' in line:
        if current_text:
            joined = ' '.join(current_text)
            if joined.strip():
                segments.append(joined.strip())
            current_text = []
        in_cue = True
    elif in_cue:
        clean = re.sub(r'<[^>]*>', '', line)
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&')
        clean = clean.strip()
        if clean:
            current_text.append(clean)

if current_text:
    joined = ' '.join(current_text)
    if joined.strip():
        segments.append(joined.strip())

# === 段间去重 ===
deduped = []
prev = None
for s in segments:
    s = s.strip()
    if s and s != prev:
        deduped.append(s)
        prev = s

# === 去除语气词 ===
fillers = ['um', 'uh', 'er', 'mm', 'hm', 'ah']
cleaned_segments = []
for s in deduped:
    for f in fillers:
        s = re.sub(r'\b' + f + r'\b\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if s:
        cleaned_segments.append(s)

# === 标记话题边界段 ===
topic_boundaries = []  # 列表，存储 (段落索引, 话题标签)
for i, seg in enumerate(cleaned_segments):
    if is_topic_boundary(seg):
        label = extract_topic_label(seg)
        topic_boundaries.append((i, label))

print(f"Total segments: {len(cleaned_segments)}")
print(f"Detected topic boundaries: {len(topic_boundaries)}")
for idx, label in topic_boundaries:
    print(f"  [段{idx}] {label}")

# === 拼接完整文本（供短文本分支使用）===
full = ' '.join(cleaned_segments)
full = re.sub(r'\s+', ' ', full).strip()

output_path = r'D:\AlphaClaw\Podcast\transcript_clean.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(full)

print(f"\nCleaned transcript saved to: {output_path}")
print(f"Total characters: {len(full)}")

# === 话题感知智能分块 ===
CHUNK_THRESHOLD = 100000
TARGET_CHUNK_SIZE = 20000  # 目标块大小（字符）
LOOKBACK_WINDOW = 8000     # 回溯窗口：在目标大小前最多回溯多少字符找边界

if len(full) > CHUNK_THRESHOLD:
    print(f"\nTranscript exceeds {CHUNK_THRESHOLD} chars, performing topic-aware chunking...")
    
    # 将 topic_boundaries 转为字典方便查找: 段索引 → 标签
    boundary_map = {idx: label for idx, label in topic_boundaries}
    
    chunks = []           # 每个元素: (chunk_text, topic_label)
    current_chunk_segs = []
    current_char_count = 0
    current_topic_label = "对话开始"
    
    for i, seg in enumerate(cleaned_segments):
        seg_len = len(seg)
        
        # 如果当前累积已接近目标大小，且当前段是话题边界 → 切分
        if current_char_count > 0 and (current_char_count + seg_len) >= TARGET_CHUNK_SIZE:
            # 在当前段之前，找到最近的话题边界作为实际切分点
            # 回溯：从当前已累积的段中找最后一个话题边界
            split_point = len(current_chunk_segs)  # 默认在当前段前切
            found_boundary = False
            
            # 计算回溯字符量（不能超过 LOOKBACK_WINDOW）
            backtrack_chars = 0
            for j in range(len(current_chunk_segs) - 1, -1, -1):
                backtrack_chars += len(current_chunk_segs[j])
                if backtrack_chars > LOOKBACK_WINDOW:
                    break
                # current_chunk_segs[j] 在原始列表中的索引
                orig_idx = i - len(current_chunk_segs) + j
                if orig_idx in boundary_map:
                    # 在这个话题边界之后切分
                    split_point = j + 1
                    found_boundary = True
                    break
            
            if found_boundary:
                # 切分：split_point 之前的部分成为一个块
                chunk_segs_to_save = current_chunk_segs[:split_point]
                remaining_segs = current_chunk_segs[split_point:]
                
                chunk_text = ' '.join(chunk_segs_to_save)
                chunks.append((chunk_text, current_topic_label))
                
                # 新块从剩余段 + 当前段开始
                current_chunk_segs = remaining_segs + [seg]
                current_char_count = sum(len(s) for s in current_chunk_segs)
                # 新块的话题标签：取剩余段中第一个话题边界
                current_topic_label = "对话继续"
                for j, s in enumerate(remaining_segs):
                    orig_idx = i - len(current_chunk_segs) + j + 1
                    if orig_idx in boundary_map:
                        current_topic_label = boundary_map[orig_idx]
                        break
                if current_topic_label == "对话继续" and i in boundary_map:
                    current_topic_label = boundary_map[i]
            else:
                # 回溯窗口内没找到话题边界，在目标大小处直接切（兜底）
                current_chunk_segs.append(seg)
                current_char_count += seg_len
                chunk_text = ' '.join(current_chunk_segs)
                chunks.append((chunk_text, current_topic_label))
                current_chunk_segs = []
                current_char_count = 0
                current_topic_label = boundary_map.get(i, "对话继续")
            
            # 更新话题标签（如果当前段是话题边界）
            if i in boundary_map and current_chunk_segs and current_chunk_segs[-1] == seg:
                current_topic_label = boundary_map[i]
        else:
            current_chunk_segs.append(seg)
            current_char_count += seg_len
            # 如果当前段是话题边界且是块中的第一个段，更新话题标签
            if i in boundary_map and len(current_chunk_segs) == 1:
                current_topic_label = boundary_map[i]
    
    # 保存最后一块
    if current_chunk_segs:
        chunk_text = ' '.join(current_chunk_segs)
        chunks.append((chunk_text, current_topic_label))
    
    # === 写入分块文件 ===
    for i, (chunk_text, topic_label) in enumerate(chunks):
        chunk_path = f'D:\\AlphaClaw\\Podcast\\c{i:02d}.txt'
        with open(chunk_path, 'w', encoding='utf-8') as f:
            # 文件头写入话题标签
            f.write(f"# 话题: {topic_label}\n\n")
            f.write(chunk_text)
        print(f"  [块{i:02d}] {topic_label}  →  {chunk_path}  ({len(chunk_text)} chars)")
    
    print(f"\nTotal chunks: {len(chunks)}")
else:
    print("Transcript is within limits, no splitting needed.")
```

执行：

```bash
python "D:\AlphaClaw\Podcast\parse_clean.py"
```

### 步骤 5：生成书面文章

**根据步骤 4 的输出判断走哪个分支：**

#### 分支 A：短文本（未分块，≤10 万字）—— 使用 make-report subagent

调用 make-report subagent，将清洗文本作为 prompt 主体：

```
Task(
    subagent_type="make-report",
    description="生成 YouTube 视频书面整理稿",
    prompt="用户发来了一个 YouTube 视频的完整字幕内容。请将其整理成书面文章，遵循以下规则：\n\n1. 保真底线：不凭空编造任何事实、数据或观点；不歪曲嘉宾立场和原意。允许在同一段内对纯粹的口语重复（同一观点换措辞重说多遍）进行压缩合并——但不允许跨位置合并同主题内容，不允许削去携带新信息维度的表述。\n2. 时间线忠实：严格遵循播客对话的时间线顺序。不将对话中不同时间点讨论的内容合并或重新编排。文章的章节划分反映播客自然的话题切换节奏，而非按主题归类。读者的阅读顺序应等于播客的收听顺序。\n3. 主持人话语处理：功能性互动（简短附和如「对」「有意思」「继续说」）去除；内容性提问/评论（引出嘉宾核心观点的问题、主持人分享的实质感受、引用的他人言论等）保留，但转为叙事引导句形式，避免 Q&A 格式。示例：原文「分手有多痛？Lex 问道。它击垮了我。」→ 叙事式「当被问到离开暴雪有多痛苦时，Kaplan 的回答直接而沉重：'它击垮了我。'」\n4. 叙事性 vs 说明性双轨：叙事性内容（嘉宾亲述的个人经历、关键转折时刻、情绪高峰表达）尽量使用直接引语，保留原话的冲击力；说明性内容（概念解释、背景介绍、系统原理）用精炼书面语准确归纳。精炼遵循「信息增量测试」——携带新事实数据、新分析维度、新限定条件、新因果解释、具象化场景的关键例子均必须保留；纯粹口语填充、同观点换措辞复述、自我修正过程中的中间表述可压缩。兜底原则：拿不准是否携带新信息时默认保留。\n5. 极简过渡句：章节或段落之间可添加极简过渡句（1-2 句），仅用于消除因去除主持人过渡语而造成的上下文跳跃，不凭空编造话题间关系。\n6. 专有名词标注：人名、公司名、游戏名、产品名、技术术语、特定概念等在首次出现时，用中文翻译后括号注明英文原文（如：暴雪娱乐（Blizzard Entertainment）、任务驱动升级（Quest-Driven Leveling））。后续再次出现同一名词时可只写中文。\n7. 最终直接输出整理后的文章内容，不需要说明你做了什么\n\n视频标题：{title}\n上传日期：{upload_date_formatted}\n\n字幕文件路径：D:\AlphaClaw\Podcast\transcript_clean.txt\n请先读取该文件获取完整字幕内容，然后整理为书面文章。",
    stream_to_parent=True
)
```

#### 分支 B：长文本（已分块，>10 万字）—— 主 agent 并行读取分块后直接撰写

当步骤 4 打印了分块信息（如 "Total chunks: 13"）时，执行以下操作：

1. **并行读取所有分块文件**：在同一条消息中，对所有 c00.txt ~ cXX.txt 并行调用 `read` 工具
2. **主 agent 直接撰写文章**：基于并行读取到的全部内容，使用 `write` 工具直接撰写 Markdown 文章。文章要求：
   - 保真底线：不凭空编造事实/数据/观点，不歪曲嘉宾立场。允许在同段内压缩纯粹的口语重复（同观点换措辞重说多遍），但不跨位置合并同主题内容，不削去携带新信息维度的表述
   - 时间线忠实：严格遵循播客对话的时间线顺序，章节划分反映自然话题切换节奏，读者阅读顺序等于收听顺序
   - 主持人话语处理：功能性互动去除；内容性提问/评论转为叙事引导句，避免 Q&A 格式
   - 叙事性 vs 说明性双轨：叙事性内容（个人经历、转折时刻、情绪高峰）用直接引语；说明性内容（概念解释、背景、系统原理）用精炼书面语归纳，遵循「信息增量测试」——新事实/新维度/新限定/因果解释/具象化例子必须保留，纯复述/填充词可压缩。拿不准时默认保留
   - 极简过渡句：章节/段落之间可加 1-2 句过渡，仅消除因去除主持人口头过渡造成的上下文跳跃，不凭空编造话题间关系
   - 专有名词标注：人名、公司名、游戏名、产品名、技术术语等首次出现时用中文后括号注明英文原文
   - 输出完整的 Markdown 格式

> 不要再次调用 make-report——长文本场景下 make-report 无法一次性处理完整内容。主 agent 的上下文窗口足以容纳所有分块内容，直接撰写比经过 subagent 中转更高效可靠。

### 步骤 6：保存文章文件

将 subagent 输出的文章写入文件：

- 路径：`D:\AlphaClaw\Podcast\【{上传日期}】-{title}.md`
- 例：`D:\AlphaClaw\Podcast\【20260415】-Jensen Huang – Will Nvidia's moat persist?.md`
- 使用 write 工具直接写入（write 会覆盖已有文件）
- 文件写入完成后向用户确认

### 步骤 7：清理中间文件

使用 glob 工具确认 `D:\AlphaClaw\Podcast` 目录下的中间文件列表（包括 .vtt、.txt、.py 等），然后逐一删除：

```
保留：最终 .md 文件
删除：所有 .vtt、transcript_*.txt、parse_*.py 等中间文件
```

删除后再次 glob 确认只剩 .md 文件。

## 文件命名规则

- 格式：`【YYYYMMDD】-{视频标题}.md`
- 上传日期从 yt-dlp 元信息获取
- 视频标题中含有的特殊字符（`/`、`\`、`:`、`?、`*` 等）替换为 `-` 或直接移除
- 标题中的引号 `' "` 建议移除，避免文件系统问题

## 分块处理机制（话题感知）

对于长视频（1.5 小时以上，清洗后文本超 10 万字），步骤 4 的 Python 脚本会进行**话题感知智能分块**，而非简单的按字符数切分。

### 为什么需要话题感知

原始按固定字符数切分的方式会在句子中间截断，导致：
- 同一话题的上下文被拆分到两个块中，翻译/整理时缺乏连贯性
- 主 agent 并行读取后需要跨块推断上下文，增加理解成本
- 关键数据和论点可能被切碎

### 话题边界检测

脚本内置了针对访谈类视频的话题转换信号检测，包括：
- **提问句式**：主持人的"tell me about"、"can you talk about"、"let me ask"、"what do you think"等
- **显式过渡语**："let's move on"、"switching gears"、"one more thing"
- **广告插入**："quick pause"、"thank you to our sponsors"——前后话题通常无关，是天然强边界
- **话题重置**："you mentioned earlier"、"going back to"——引用前文引入新角度
- **结束语**："thank you so much"、"thanks for listening"

### 切分策略

1. 以段（VTT 字幕块）为最小单位累积文本，不做段内截断
2. 当累积字符数接近目标大小（约 2 万字）时，向前回溯最多 8000 字符
3. 在回溯窗口内找到最近一个话题边界段，在此处切分
4. 回溯窗口内无话题边界时，在目标大小处直接切分（兜底）
5. 每块以完整话题段落开头，文件头部标注该块的话题摘要

### 效果

- 每块内容自成一个或多个完整的话题讨论单元
- 并行读取时，主 agent 可通过文件头的话题标签快速理解每块内容范围
- 最终文章中的章节划分与分块边界自然对齐，翻译一致性更好

## 故障排查与回退策略

本节总结了常见失败场景及应对方案，确保在 YouTube 反爬措施变化时工作流仍可完成。

### yt-dlp 常见错误及处理

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `"This video is not available"` | 默认 web client 被限制 | 切换 android/ios client（见步骤 2 回退方案 1） |
| `"No supported JavaScript runtime could be found"` | 缺少 JS 运行时（EJS） | 该警告通常不致命；若影响功能，安装 deno 或 node |
| `"GVS PO Token was not provided"` | Android client 缺少 PO Token | **警告可忽略**，元信息通常仍可正常获取 |
| 字幕下载返回空或失败 | 视频无手动字幕或反爬限制 | 切换路径 B（youtube_transcript_api） |

### youtube_transcript_api 常见错误及处理

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `AttributeError: 'get_transcript'` | v1.x 已移除该方法 | 使用 `api.fetch(video_id)` |
| `TypeError: missing 'video_id'` | 调用了类方法而非实例方法 | 先 `api = YouTubeTranscriptApi()` |
| `TypeError: not subscriptable` | 试图用 dict 方式访问 dataclass | 用属性访问：`s.text` 而非 `s['text']` |
| `TranscriptsDisabled` | 视频禁用了字幕 | 无法获取，向用户报告 |
| `NoTranscriptFound` | 视频无英文字幕 | 尝试其他语言代码或报告失败 |

### 总体回退链

```
获取元信息:
  yt-dlp web → yt-dlp android → oEmbed + yt-dlp android → oEmbed + webfetch

获取字幕:
  yt-dlp VTT (web) → yt-dlp VTT (android) → youtube_transcript_api → 报告失败
```

### 关键原则

1. **永不死磕单一路径**：每个外部依赖（yt-dlp、youtube_transcript_api）都有独立的失败模式，不能假设任一路径永远畅通
2. **oEmbed API 是元信息的银弹**：标题获取 100% 可靠，无需认证，应作为终极回退
3. **youtube_transcript_api 是字幕的银弹**：不依赖 JS 运行时，不受 yt-dlp 的 YouTube 反爬限制影响
4. **Android client 比 web client 更宽松**：YouTube 对移动端的反爬限制通常更弱

---

## 注意事项

- **字幕路径选择**：优先 `--write-sub`（手动字幕，质量高），失败则 `--write-auto-sub`（自动字幕，需增强去重），再失败则 `youtube_transcript_api`
- 视频 URL 可能带有额外参数（如 `&pp=`），提取视频 ID 时以 `watch?v=` 后的字符串为准
- 节目中的广告插入段落（如 Crusoe、Cursor 等赞助广告内容），属于结构性内容，可按节目结构性开场白/过渡语的方式处理：保留事实性信息，去除明显的赞助商格式语
- **文章撰写标准**（分支 A 和分支 B 通用）：(1) 保真底线——不编造事实/数据/观点，不歪曲嘉宾立场，允许同段内压缩纯粹口语重复但不跨位置合并同主题内容，不削去携带新信息维度的表述。(2) 时间线忠实——严格遵循播客对话时间线顺序，章节划分反映自然话题切换，读者阅读顺序等于收听顺序。(3) 主持人话语——功能性互动去除，内容性提问/评论转为叙事引导句避免 Q&A 格式。(4) 叙事性 vs 说明性双轨——叙事性内容（个人经历、转折时刻、情绪高峰）用直接引语；说明性内容（概念解释、背景、系统原理）用精炼书面语归纳，遵循「信息增量测试」：新事实/新维度/新限定/因果解释/具象化例子必须保留，纯复述/填充词/自我修正中间表述可压缩，拿不准时默认保留。(5) 极简过渡句——章节/段落间可加 1-2 句过渡，仅消除去除主持人口头过渡造成的上下文跳跃。(6) 专有名词标注——人名、公司名、游戏名、产品名、技术术语、特定概念等首次出现时用中文后括号注明英文原文（如「暴雪娱乐（Blizzard Entertainment）」「体素（Voxel）」），后续同一名词可只写中文
- 工作目录：`D:\AlphaClaw`
- Python 路径：优先使用系统提醒中的 Python 路径（如 `D:\AlphaEngine\resources\python\python\python.exe`），其次使用 `C:\Program Files\AlphaEngine\resources\python\python\python.exe`
