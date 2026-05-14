#!/usr/bin/env python3
"""YouTube 字幕解析、清洗与智能分块 v2.1

增强项:
- 双语话题边界检测（英文 + 中文）
- 讲座/教育类视频信号
- 双输入格式自动检测（VTT / raw text）
- CLI 参数化 + JSON 结构化输出
- 中文语气词处理
- v2.1: 多行格式自动保障，防止单行文件导致下游读取截断

用法:
    python parse_clean.py --input-dir <dir> --video-id <id> [--lang zh|en]
"""

import re
import glob
import os
import sys
import json
import argparse


# ═══════════════════════════════════════════════════════
# 话题边界检测模式（双语）
# ═══════════════════════════════════════════════════════

TOPIC_BOUNDARY_PATTERNS = [
    # ── 英文：广告/赞助插入（强边界） ──
    r'(?i)\b(quick pause|thank you to our sponsors|check them out in the description|back to my conversation|now back to|and now.*back to|a word from our|this episode is brought to|support for this)\b',

    # ── 英文：主持人明确引入新话题的提问句式 ──
    r'(?i)\b((so|and|now|alright|okay)\s*[,.]*\s*(tell me about|can (you|we) (talk|speak|discuss)|let me ask|I (want|wanted|gotta|have) to (ask|mention|talk|bring up)|what (do|did) you think|how (did|do) you|before I forget|I wanted to mention|let\'s (talk|discuss|go|get into|dive into)))\b',

    # ── 英文：显式话题过渡 ──
    r'(?i)\b(let\'s move on|switching gears|on a different note|one more (thing|question)|moving on|to change the subject|let\'s go back|I want to go back|going back to|you mentioned (earlier|before)|that reminds me|speaking of)\b',

    # ── 英文：讲座/教育类信号 ──
    r'(?i)\b((so )?that\'s (the|my) (first|second|third|next|last) (point|thing|topic|area)|now let\'s (look at|talk about|discuss|move to|turn to|get into)|the (next|second|third|fourth|fifth) (point|thing|topic|area|question) is|in (conclusion|summary)|to (summarize|wrap up|conclude))\b',

    # ── 英文：引用前文引入新角度 ──
    r'(?i)\b(you (said|mentioned|talked about|described|brought up)|earlier you|you\'ve (talked|spoken|written|mentioned)|(coming|going) back to (what|something) you said)\b',

    # ── 英文：结束语/告别 ──
    r'(?i)\b(thank you (so much|for (everything|talking|being|coming|having|your time)|guys)|thanks for listening|let me leave you with|hope to see you next time|that\'s all (the time|we have)|(we\'re|I\'m) out of time)\b',

    # ═══════════════════════════════════════════════════
    # ── 中文：提问句式/话题引入 ──
    r'(?i)(我想问|我想请教|你(怎么|如何)看|能不能(谈谈|聊聊|说一下)|(谈谈|聊聊|说说)\s*(你|这个|那个|我们)|(接下来|下面|那么)\s*(我们|来)?\s*(聊聊|谈谈|讨论|说一下|换个话题)|回到(刚才|之前)|你(刚才|前面|之前)(提到|说到|讲的|说))',

    # ── 中文：显式话题过渡 ──
    r'(?i)(换个(话题|方向|角度)|(我们|那)\s*(接下来|继续|接着)|下一个(话题|问题|环节)|再(问|说|聊|讲)(一个|一下)|还有(一个|件事|一点)|另外(一件事|一点|一个))',

    # ── 中文：结束语 ──
    r'(?i)((今天|这次|本期)\s*(的)?\s*(节目|播客|访谈|对话|聊天|分享|讨论)\s*(就|到|先)?\s*(到这里|到这|结束)|感谢(大家|各位|收听|收看|关注)|谢谢(大家|各位|收听|收看)|下期(再见|再会)|我们下(期|次|回)(再见|见))',
]


def is_topic_boundary(segment_text):
    """判断段落是否可能是话题转换点。"""
    for pattern in TOPIC_BOUNDARY_PATTERNS:
        if re.search(pattern, segment_text):
            return True
    return False


def extract_topic_label(segment_text, max_len=60):
    """从话题边界段提取简短话题标签。"""
    label = segment_text.strip()[:max_len]
    if len(segment_text.strip()) > max_len:
        # 在最后一个完整词处截断
        label = label.rsplit(' ', 1)[0] + '...'
    return label


# ═══════════════════════════════════════════════════════
# 语气词列表（双语）
# ═══════════════════════════════════════════════════════

FILLERS_EN = ['um', 'uh', 'er', 'mm', 'hm', 'ah', 'like', 'you know', 'i mean', 'sort of', 'kind of']
FILLERS_ZH = ['那个', '就是', '然后', '嗯', '啊', '呃', '嘛', '吧', '呢']


def remove_fillers(text, lang_hint='en'):
    """去除语气词。"""
    # 英文语气词：词边界匹配
    fillers = FILLERS_EN[:]
    if lang_hint in ('zh', 'auto'):
        fillers += FILLERS_ZH
    
    for filler in fillers:
        if ' ' in filler or any('\u4e00' <= c <= '\u9fff' for c in filler):
            # 多词或中文填充词：直接替换
            text = re.sub(re.escape(filler), '', text)
        else:
            # 单英文词：词边界匹配
            text = re.sub(r'\b' + re.escape(filler) + r'\b\s*', '', text)
    
    # 合并多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ═══════════════════════════════════════════════════════
# VTT 解析
# ═══════════════════════════════════════════════════════

def parse_vtt(file_path):
    """解析 VTT 字幕文件，返回段落列表。"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    segments = []
    current_text = []
    in_cue = False

    for line in lines:
        line = line.strip()
        if not line or line in ('WEBVTT', 'Kind: captions', 'Language: en', 'Language: zh', 'Language: en-US'):
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
            clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            clean = clean.strip()
            if clean:
                current_text.append(clean)

    if current_text:
        joined = ' '.join(current_text)
        if joined.strip():
            segments.append(joined.strip())

    return segments


def parse_raw(file_path):
    """解析 raw text 字幕文件（youtube_transcript_api 输出），返回段落列表。"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    segments = [line.strip() for line in lines if line.strip()]
    return segments


# ═══════════════════════════════════════════════════════
# 智能分块
# ═══════════════════════════════════════════════════════

CHUNK_THRESHOLD = 100000       # 超过此字符数才分块
TARGET_CHUNK_SIZE = 20000      # 目标块大小（字符）
LOOKBACK_WINDOW = 8000         # 回溯窗口


def chunk_transcript(cleaned_segments, topic_boundaries):
    """话题感知智能分块。返回 [(chunk_text, topic_label), ...] 列表。"""
    full = ' '.join(cleaned_segments)
    full = re.sub(r'\s+', ' ', full).strip()

    if len(full) <= CHUNK_THRESHOLD:
        return None  # 不需要分块

    boundary_map = {idx: label for idx, label in topic_boundaries}

    chunks = []
    current_chunk_segs = []
    current_char_count = 0
    current_topic_label = "开始"

    for i, seg in enumerate(cleaned_segments):
        seg_len = len(seg)

        if current_char_count > 0 and (current_char_count + seg_len) >= TARGET_CHUNK_SIZE:
            split_point = len(current_chunk_segs)
            found_boundary = False

            backtrack_chars = 0
            for j in range(len(current_chunk_segs) - 1, -1, -1):
                backtrack_chars += len(current_chunk_segs[j])
                if backtrack_chars > LOOKBACK_WINDOW:
                    break
                orig_idx = i - len(current_chunk_segs) + j
                if orig_idx in boundary_map:
                    split_point = j + 1
                    found_boundary = True
                    break

            if found_boundary:
                chunk_segs_to_save = current_chunk_segs[:split_point]
                remaining_segs = current_chunk_segs[split_point:]

                chunk_text = ' '.join(chunk_segs_to_save)
                chunks.append((chunk_text, current_topic_label))

                current_chunk_segs = remaining_segs + [seg]
                current_char_count = sum(len(s) for s in current_chunk_segs)
                current_topic_label = "继续"
                for j, s in enumerate(remaining_segs):
                    orig_idx_rem = i - len(current_chunk_segs) + j + 1
                    if orig_idx_rem in boundary_map:
                        current_topic_label = boundary_map[orig_idx_rem]
                        break
                if current_topic_label == "继续" and i in boundary_map:
                    current_topic_label = boundary_map[i]
            else:
                current_chunk_segs.append(seg)
                current_char_count += seg_len
                chunk_text = ' '.join(current_chunk_segs)
                chunks.append((chunk_text, current_topic_label))
                current_chunk_segs = []
                current_char_count = 0
                current_topic_label = boundary_map.get(i, "继续")

            if i in boundary_map and current_chunk_segs and current_chunk_segs[-1] == seg:
                current_topic_label = boundary_map[i]
        else:
            current_chunk_segs.append(seg)
            current_char_count += seg_len
            if i in boundary_map and len(current_chunk_segs) == 1:
                current_topic_label = boundary_map[i]

    if current_chunk_segs:
        chunk_text = ' '.join(current_chunk_segs)
        chunks.append((chunk_text, current_topic_label))

    return chunks


# ═══════════════════════════════════════════════════════
# v2.1: 多行格式保障
# ═══════════════════════════════════════════════════════

def _ensure_multiline(filepath, min_lines=50):
    """若文件行数过少（单行或少量行但字符数大），按句子边界重新格式化为多行。
    
    这解决了 transcript_clean.txt 为单行文件时下游 read 工具只能读到开头部分、
    导致 make-report subagent 基于不完整输入生成截断文章的问题。
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    if len(lines) >= min_lines:
        return  # 已经足够多行，无需处理
    
    # 按句子边界分割：英文句号/问号/感叹号后空格接大写字母
    multiline = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', '\n', content)
    # 中文句号/感叹号/问号后
    multiline = re.sub(r'(?<=[。！？])\s*', '\n', multiline)
    # 也处理 >> 分隔符（主持人/嘉宾切换标记）
    multiline = re.sub(r'\s*>>\s*', '\n', multiline)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(multiline)
    
    new_lines = multiline.count('\n') + 1
    print(f"[parse_clean] 多行格式化: {filepath} ({len(lines)} 行 → {new_lines} 行, {len(content)} 字符)", file=sys.stderr)


# ═══════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='YouTube 字幕解析清洗与分块')
    parser.add_argument('--input-dir', '-i', required=True, help='输入目录（含字幕文件）')
    parser.add_argument('--video-id', '-v', required=True, help='视频 ID')
    parser.add_argument('--lang', default='en', choices=['en', 'zh', 'auto'], help='语言提示')
    args = parser.parse_args()

    input_dir = args.input_dir
    video_id = args.video_id
    lang_hint = args.lang

    # ── 检测输入格式 ──
    vtt_files = glob.glob(os.path.join(input_dir, f'{video_id}*.vtt'))
    raw_path = os.path.join(input_dir, 'transcript_raw.txt')

    if vtt_files:
        vtt_path = vtt_files[0]
        print(f"[parse_clean] 输入: VTT ({os.path.basename(vtt_path)})", file=sys.stderr)
        segments = parse_vtt(vtt_path)
        input_type = 'vtt'
    elif os.path.exists(raw_path):
        print(f"[parse_clean] 输入: Raw text ({os.path.basename(raw_path)})", file=sys.stderr)
        segments = parse_raw(raw_path)
        input_type = 'raw'
    else:
        result = {'error': '未找到字幕文件（.vtt 或 transcript_raw.txt）'}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    if not segments:
        result = {'error': '字幕文件为空'}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # ── 段间去重 ──
    deduped = []
    prev = None
    for s in segments:
        s = s.strip()
        if s and s != prev:
            deduped.append(s)
            prev = s

    # ── 去除语气词 ──
    cleaned_segments = []
    for s in deduped:
        s = remove_fillers(s, lang_hint)
        if s:
            cleaned_segments.append(s)

    # ── 话题边界检测 ──
    topic_boundaries = []
    for i, seg in enumerate(cleaned_segments):
        if is_topic_boundary(seg):
            label = extract_topic_label(seg)
            topic_boundaries.append((i, label))

    print(f"[parse_clean] 总段数: {len(cleaned_segments)}, 话题边界: {len(topic_boundaries)}", file=sys.stderr)

    # ── 拼接完整文本 ──
    full = ' '.join(cleaned_segments)
    full = re.sub(r'\s+', ' ', full).strip()

    clean_path = os.path.join(input_dir, 'transcript_clean.txt')
    with open(clean_path, 'w', encoding='utf-8') as f:
        f.write(full)

    # ── v2.1: 多行格式保障 ──
    # 检测并修复单行文件问题：若文件行数过少但字符数较大，
    # 按句子边界重新格式化为多行，防止下游 read 工具读取截断
    _ensure_multiline(clean_path, min_lines=50)

    # ── 智能分块 ──
    chunks = chunk_transcript(cleaned_segments, topic_boundaries)

    result = {
        'total_chars': len(full),
        'segment_count': len(cleaned_segments),
        'input_type': input_type,
        'topic_boundary_count': len(topic_boundaries),
        'clean_file': clean_path,
        'chunked': False,
        'chunks': [],
    }

    if chunks:
        result['chunked'] = True
        for i, (chunk_text, topic_label) in enumerate(chunks):
            chunk_path = os.path.join(input_dir, f'c{i:02d}.txt')
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(f"# 话题: {topic_label}\n\n")
                f.write(chunk_text)
            result['chunks'].append({
                'file': chunk_path,
                'index': i,
                'topic_label': topic_label,
                'chars': len(chunk_text),
            })
            print(f"  [块{i:02d}] {topic_label[:50]}  →  {len(chunk_text)} 字符", file=sys.stderr)

    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
