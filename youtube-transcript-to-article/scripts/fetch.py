#!/usr/bin/env python3
"""YouTube 视频元信息与字幕获取器 v2.0

合并原 skill 步骤 2（元信息获取）和步骤 3（字幕下载），
统一处理回退链，输出 JSON 结构化结果。

用法:
    python fetch.py <video_url> --output-dir <dir>

输出 (stdout):
    JSON: {video_id, title, upload_date, subtitle_file, subtitle_type, lang}
"""

import sys
import json
import re
import subprocess
import os
import argparse

# ── 工具函数 ──────────────────────────────────────────

def extract_video_id(url):
    """从 URL 提取 YouTube 视频 ID。"""
    patterns = [
        r'(?:watch\?v=|youtu\.be/|/embed/|/shorts/|/v/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/live/([a-zA-Z0-9_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    # 去除 URL 尾部参数（&pp= 等）
    clean = url.split('&')[0]
    for pat in patterns:
        m = re.search(pat, clean)
        if m:
            return m.group(1)
    # 尝试作为原始 ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
        return url.strip()
    return None


def run_ytdlp(args, timeout=120):
    """运行 yt-dlp 命令，返回 (success, stdout, stderr)。"""
    cmd = [sys.executable, '-m', 'yt_dlp'] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, '', 'timeout'
    except Exception as e:
        return False, '', str(e)


# ── 元信息获取（原步骤 2） ──────────────────────────

def get_metadata(url):
    """
    获取视频标题和上传日期。
    回退链: web client → android client → oEmbed(标题) + android(日期) → oEmbed + webfetch(日期)
    返回: dict {title, upload_date} 或 None
    """
    # 方案 1: web client
    ok, out, err = run_ytdlp([
        '--print', '%(upload_date)s\n%(title)s',
        '--skip-download', url
    ])
    if ok and out:
        lines = out.split('\n')
        if len(lines) >= 2 and lines[0] and lines[1]:
            return {'title': lines[1].strip(), 'upload_date': lines[0].strip()}

    # 方案 2: android client
    ok, out, err = run_ytdlp([
        '--print', '%(upload_date)s\n%(title)s',
        '--skip-download',
        '--extractor-args', 'youtube:player_client=android',
        url
    ])
    if ok and out:
        lines = out.split('\n')
        if len(lines) >= 2 and lines[0] and lines[1]:
            return {'title': lines[1].strip(), 'upload_date': lines[0].strip()}

    # 方案 3: oEmbed (标题) + yt-dlp android (日期)
    title = None
    try:
        import urllib.request
        oembed_url = f'https://www.youtube.com/oembed?url={url}&format=json'
        req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            title = data.get('title')
    except Exception:
        pass

    # 日期：再试一次 android client
    upload_date = None
    ok, out, err = run_ytdlp([
        '--print', '%(upload_date)s', '--skip-download',
        '--extractor-args', 'youtube:player_client=android',
        url
    ])
    if ok and out:
        upload_date = out.strip()

    if title or upload_date:
        return {'title': title or 'Unknown Title', 'upload_date': upload_date or 'Unknown'}

    return None


# ── 字幕下载（原步骤 3） ──────────────────────────

def download_subtitles_ytdlp(video_id, output_dir, client='web', lang='en'):
    """用 yt-dlp 下载 VTT 字幕。"""
    args = [
        '--write-sub', '--sub-lang', lang,
        '--convert-subs', 'vtt',
        '--skip-download',
        '--paths', output_dir,
    ]
    if client == 'android':
        args.extend(['--extractor-args', 'youtube:player_client=android'])

    url = f'https://www.youtube.com/watch?v={video_id}'
    ok, out, err = run_ytdlp(args + [url])
    if not ok:
        return None

    # 查找下载的 VTT 文件
    vtt_pattern = os.path.join(output_dir, f'{video_id}*.vtt')
    import glob
    vtt_files = glob.glob(vtt_pattern)
    if vtt_files:
        return vtt_files[0]
    return None


def download_subtitles_api(video_id, output_dir, lang='en'):
    """用 youtube_transcript_api 获取字幕（备用路径）。"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        result = api.fetch(video_id, languages=[lang])
        segments = list(result)

        output_path = os.path.join(output_dir, 'transcript_raw.txt')
        with open(output_path, 'w', encoding='utf-8') as f:
            for s in segments:
                f.write(f'{s.text}\n')

        return output_path
    except Exception:
        return None


def get_subtitles(video_id, output_dir, lang='en'):
    """
    下载字幕。
    回退链: yt-dlp VTT(web) → yt-dlp VTT(android) → youtube_transcript_api
    返回: (file_path, subtitle_type) 其中 type 为 'vtt' 或 'raw'
    """
    # 路径 A: yt-dlp web client
    path = download_subtitles_ytdlp(video_id, output_dir, client='web', lang=lang)
    if path:
        return path, 'vtt'

    # 路径 A2: yt-dlp android client
    path = download_subtitles_ytdlp(video_id, output_dir, client='android', lang=lang)
    if path:
        return path, 'vtt'

    # 路径 B: youtube_transcript_api
    path = download_subtitles_api(video_id, output_dir, lang=lang)
    if path:
        return path, 'raw'

    return None, None


# ── 主入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='YouTube 视频元信息与字幕获取器')
    parser.add_argument('url', help='YouTube 视频 URL')
    parser.add_argument('--output-dir', '-o', required=True, help='输出目录')
    parser.add_argument('--lang', default='en', help='字幕语言代码（默认 en）')
    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)

    # 提取视频 ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print(json.dumps({'error': '无法从 URL 提取视频 ID'}), flush=True)
        sys.exit(1)

    result = {
        'video_id': video_id,
        'title': None,
        'upload_date': None,
        'subtitle_file': None,
        'subtitle_type': None,
        'lang': args.lang,
    }

    # 步骤 1: 获取元信息
    meta = get_metadata(args.url)
    if meta:
        result['title'] = meta['title']
        result['upload_date'] = meta['upload_date']
    else:
        print(json.dumps({'error': '无法获取视频元信息，请检查视频 URL 是否有效'}), flush=True)
        sys.exit(1)

    # 步骤 2: 下载字幕
    sub_path, sub_type = get_subtitles(video_id, args.output_dir, lang=args.lang)
    if sub_path:
        result['subtitle_file'] = sub_path
        result['subtitle_type'] = sub_type
    else:
        print(json.dumps({'error': '无法获取视频字幕，视频可能无字幕或不支持', 'meta': result}), flush=True)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
