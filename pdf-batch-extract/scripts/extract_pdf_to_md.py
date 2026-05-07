#!/usr/bin/env python3
"""
PDF 批量原文 + 表格提取工具
用法：
  python extract_pdf_to_md.py <pdf_dir> [output_dir]    批量处理目录下所有 PDF
  python extract_pdf_to_md.py --single <pdf_path> <output_dir>  处理单个 PDF
"""

import pdfplumber
import os
import json
import re
import sys
from collections import Counter


# ============================================================================
# 页眉 / 页脚 / 页码清理
# ============================================================================

SKIP_PATTERNS = [
    re.compile(r'^\s*\d+\s*$'),                               # 纯页码
    re.compile(r'^\s*\d+\s*/\s*\d+\s*$'),                     # X / Y
    re.compile(r'^\s*Page\s+\d+\s+of\s+\d+\s*$', re.IGNORECASE),
    re.compile(r'^\s*第\s*\d+\s*页\s*$'),                     # 第 X 页
    re.compile(r'^\s*页码[:：]?\s*\d+\s*$', re.IGNORECASE),
    re.compile(r'^\s*私有[保秘]?定[密]?[文件资料]?\s*$'),
    re.compile(r'^\s*[Cc]onfidential\s*$'),
    re.compile(r'^\s*[Ii]nternal\s+[Uu]se\s+[Oo]nly\s*$'),
    re.compile(r'^\s*内部文件\s*$'),
    re.compile(r'^\s*免责声明\s*$'),
    re.compile(r'^\s*请务必阅读正文之后的信息披露和法律声明\s*$'),
]


def detect_headers_footers(pdf):
    """
    统计多页首行/末行，识别反复出现的页眉和页脚。
    返回 (header_candidates, footer_candidates)。
    """
    first_lines = []
    last_lines = []
    for page in pdf.pages:
        t = page.extract_text()
        if not t:
            continue
        lines = [l.strip() for l in t.split('\n') if l.strip()]
        if len(lines) >= 2:
            first_lines.append(lines[0])
            last_lines.append(lines[-1])
        elif len(lines) == 1:
            first_lines.append(lines[0])

    header_candidates = {l for l, c in Counter(first_lines).items() if c >= 2}
    footer_candidates = {l for l, c in Counter(last_lines).items() if c >= 2}
    return header_candidates, footer_candidates


def clean_page_text(text, header_candidates=None, footer_candidates=None):
    """清理单页文本：去除页码、页眉、页脚。"""
    lines = text.split('\n')
    cleaned = []
    header_set = set(h.strip() for h in header_candidates) if header_candidates else set()
    footer_set = set(f.strip() for f in footer_candidates) if footer_candidates else set()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(p.match(stripped) for p in SKIP_PATTERNS):
            continue
        if stripped in header_set:
            continue
        if stripped in footer_set:
            continue
        cleaned.append(line)

    return '\n'.join(cleaned)


# ============================================================================
# 表格提取 & Markdown 格式化
# ============================================================================

def format_table_as_markdown(table):
    """将 pdfplumber 提取的表格（list of lists）转为 Markdown 表格。"""
    if not table or len(table) < 1:
        return ""

    # 清洗单元格内容：去除首尾空白、将换行替换为空格
    rows = []
    for row in table:
        cleaned_row = [str(cell).strip().replace('\n', ' ') if cell else '' for cell in row]
        # 跳过全空行
        if any(c for c in cleaned_row):
            rows.append(cleaned_row)

    if not rows:
        return ""

    max_cols = max(len(row) for row in rows)
    for row in rows:
        while len(row) < max_cols:
            row.append('')

    lines = []
    lines.append('| ' + ' | '.join(rows[0]) + ' |')
    lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    for row in rows[1:]:
        lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(lines)


# ============================================================================
# 单页内容提取（文本 + 表格）
# ============================================================================

def extract_page_content(page, header_candidates, footer_candidates, page_num):
    """
    从单页同时提取文本和表格。
    文本先行，表格追加，保持同页上下文关联。
    """
    parts = []
    page_header = f"--- 第 {page_num} 页 ---"

    # 提取文本
    text = page.extract_text()
    has_text = text and text.strip()

    # 提取表格
    tables = page.extract_tables()
    has_tables = tables and any(t for t in tables)

    if not has_text and not has_tables:
        return ""

    parts.append(page_header)

    # 文本部分
    if has_text:
        cleaned = clean_page_text(text, header_candidates, footer_candidates)
        if cleaned.strip():
            parts.append(cleaned)

    # 表格部分
    if has_tables:
        table_count = 0
        for t in tables:
            if not t:
                continue
            md_table = format_table_as_markdown(t)
            if md_table:
                table_count += 1
                parts.append(f"\n**表 {page_num}-{table_count}：**\n\n{md_table}")

    return '\n\n'.join(parts)


# ============================================================================
# 单 PDF 处理
# ============================================================================

def process_pdf(pdf_path, output_dir):
    """处理单个 PDF：提取文本 + 表格，输出同名 .md 文件。"""
    pdf_name = os.path.basename(pdf_path)
    md_name = os.path.splitext(pdf_name)[0] + '.md'
    md_path = os.path.join(output_dir, md_name)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        # 全局页眉页脚识别
        header_candidates, footer_candidates = detect_headers_footers(pdf)

        all_content = []

        if total_pages > 20:
            batch_size = 10
            for batch_start in range(0, total_pages, batch_size):
                batch_end = min(batch_start + batch_size, total_pages)
                batch_parts = []
                for i in range(batch_start, batch_end):
                    content = extract_page_content(
                        pdf.pages[i], header_candidates, footer_candidates, i + 1
                    )
                    if content:
                        batch_parts.append(content)
                if batch_parts:
                    all_content.append('\n\n'.join(batch_parts))
        else:
            for i, page in enumerate(pdf.pages):
                content = extract_page_content(
                    page, header_candidates, footer_candidates, i + 1
                )
                if content:
                    all_content.append(content)

    full_text = '\n\n'.join(all_content)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {os.path.splitext(pdf_name)[0]}\n\n")
        f.write(f"> 来源：{pdf_name}  |  共 {total_pages} 页\n\n")
        f.write("---\n\n")
        f.write(full_text)

    return {
        "file": pdf_name,
        "status": "成功",
        "pages": total_pages,
        "md": md_name,
        "md_path": md_path,
    }


# ============================================================================
# 入口
# ============================================================================

def main():
    single_mode = False
    pdf_path = None
    pdf_dir = None
    output_dir = None

    args = sys.argv[1:]

    if '--single' in args or '-s' in args:
        single_mode = True
        idx = args.index('--single') if '--single' in args else args.index('-s')
        args.pop(idx)
        if len(args) < 2:
            print("用法: python extract_pdf_to_md.py --single <pdf_path> <output_dir>")
            sys.exit(1)
        pdf_path = args[0]
        output_dir = args[1]
    else:
        if len(args) < 1:
            print("用法: python extract_pdf_to_md.py <pdf_dir> [output_dir]")
            sys.exit(1)
        pdf_dir = args[0]
        output_dir = args[1] if len(args) > 1 else pdf_dir

    if single_mode:
        # 单文件模式
        pdf_name = os.path.basename(pdf_path)
        print(f"处理：{pdf_name}")
        try:
            result = process_pdf(pdf_path, output_dir)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({
                "file": pdf_name, "status": f"失败: {e}", "pages": 0, "md": None, "error": str(e)
            }, ensure_ascii=False))
            sys.exit(1)
    else:
        # 批量模式
        pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')])

        # 先扫描页数
        print(f"找到 {len(pdf_files)} 个 PDF 文件：")
        file_info = []
        for f in pdf_files:
            fp = os.path.join(pdf_dir, f)
            with pdfplumber.open(fp) as pdf:
                pages = len(pdf.pages)
                file_info.append((f, pages))
                print(f"  {len(file_info)}. {f}（{pages} 页）")

        results = []
        for pdf_name, _ in file_info:
            fp = os.path.join(pdf_dir, pdf_name)
            try:
                result = process_pdf(fp, output_dir)
                results.append(result)
                print(f"✓ {pdf_name} → {result['md']}")
            except Exception as e:
                results.append({
                    "file": pdf_name, "status": f"失败: {e}", "pages": 0, "md": None, "error": str(e)
                })
                print(f"✗ {pdf_name} 失败: {e}")

        # 保存汇总
        summary_path = os.path.join(output_dir, '_pdf_extract_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n汇总已保存至：{summary_path}")


if __name__ == '__main__':
    main()
