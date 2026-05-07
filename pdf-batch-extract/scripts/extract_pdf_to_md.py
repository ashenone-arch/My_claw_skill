import re, os, json, pdfplumber
from collections import Counter
from pathlib import Path

def detect_headers_footers(pdf_path, sample_pages=5):
    """统计所有页面首行/末行，出现次数>=阈值则识别为页眉/页脚"""
    header_candidates = Counter()
    footer_candidates = Counter()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_check = pdf.pages[:sample_pages] if len(pdf.pages) > sample_pages else pdf.pages

        for page in pages_to_check:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            if lines:
                first = lines[0].strip()
                last = lines[-1].strip()
                if len(first) <= 200 and first:
                    header_candidates[first] += 1
                if len(last) <= 200 and last:
                    footer_candidates[last] += 1

    threshold = max(2, len(pdf.pages) // 10)
    headers = {k for k, v in header_candidates.items() if v >= threshold}
    footers = {k for k, v in footer_candidates.items() if v >= threshold}
    return headers, footers

def clean_text_block(text, headers, footers, wm_chars=None):
    """清理页眉/页脚/页码，可选水印清理"""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        s = line.strip()
        # 跳过页眉
        if s in headers:
            continue
        # 跳过页脚
        if s in footers:
            continue
        # 跳过页码行
        if re.match(r'^\d+$', s):
            continue
        # 水印清理：水印字符混入行间时移除（前后都是中文的水印字）
        if wm_chars:
            result = []
            i = 0
            while i < len(s):
                c = s[i]
                if c in wm_chars:
                    prev = result[-1] if result else ''
                    nxt = s[i+1] if i+1 < len(s) else ''
                    if prev and '\u4e00' <= prev <= '\u9fff' and nxt and '\u4e00' <= nxt <= '\u9fff':
                        i += 1
                        continue
                result.append(c)
                i += 1
            line = ''.join(result)
        cleaned.append(line)
    return '\n'.join(cleaned)

def extract_tables_markdown(tables, page_num):
    """将 pdfplumber 表格转为 Markdown"""
    md_parts = []
    for idx, table in enumerate(tables, 1):
        if not table:
            continue
        # 跳过全空表格
        non_empty = [r for r in table if any(c for c in r)]
        if len(non_empty) < 2:
            continue
        md_parts.append(f"\n**表 {page_num}-{idx}:**\n")
        # 逐行输出
        for row_idx, row in enumerate(non_empty):
            cells = [str(c).strip().replace('\n', ' ') if c else '' for c in row]
            if all(c == '' for c in cells):
                continue
            if row_idx == 0:
                md_parts.append('| ' + ' | '.join(cells) + ' |\n')
                md_parts.append('| ' + ' | '.join(['---'] * len(cells)) + ' |\n')
            else:
                md_parts.append('| ' + ' | '.join(cells) + ' |\n')
    return ''.join(md_parts)

def extract_pdf(pdf_path, output_dir, wm_chars=None):
    """提取单个 PDF，返回 (md_path, page_count, table_count)"""
    filename = os.path.basename(pdf_path)
    basename = os.path.splitext(filename)[0]
    out_path = os.path.join(output_dir, basename + '.md')

    headers, footers = detect_headers_footers(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        all_content = []

        # 批量处理，每批10页
        batch_size = 10
        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            for page_num in range(batch_start + 1, batch_end + 1):
                page = pdf.pages[page_num - 1]

                text = page.extract_text()
                if text:
                    cleaned = clean_text_block(text, headers, footers, wm_chars)
                    if cleaned.strip():
                        all_content.append(f"\n--- 第 {page_num} 页 ---\n{cleaned}")

                tables = page.extract_tables()
                if tables:
                    table_md = extract_tables_markdown(tables, page_num)
                    if table_md.strip():
                        all_content.append(table_md)

        output = f"""---
# {basename}

> 来源：{filename}  |  共 {total_pages} 页

---

""" + '\n'.join(all_content)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(output)

    table_count = sum(len(page.extract_tables() or []) for page in pdf.pages)
    return out_path, total_pages, table_count

def batch_extract(pdf_dir, wm_chars=None):
    """批量提取目录下所有 PDF"""
    pdf_dir = Path(pdf_dir)
    pdf_files = sorted(pdf_dir.glob('*.pdf')) + sorted(pdf_dir.glob('*.PDF'))

    results = []
    for pdf_path in pdf_files:
        try:
            out_path, page_count, table_count = extract_pdf(str(pdf_path), str(pdf_dir), wm_chars)
            results.append({
                'pdf': pdf_path.name,
                'status': 'success',
                'pages': page_count,
                'tables': table_count,
                'md': Path(out_path).name
            })
        except Exception as e:
            results.append({
                'pdf': pdf_path.name,
                'status': 'failed',
                'error': str(e)
            })

    summary_path = pdf_dir / '_pdf_extract_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        print("Usage: python extract_pdf_to_md.py <pdf_dir>")
    elif len(sys.argv) == 2:
        pdf_dir = sys.argv[1]
        results = batch_extract(pdf_dir)
        for r in results:
            status = f"✓ {r['pdf']} ({r.get('pages','?')}页, {r.get('tables',0)}表)" if r['status']=='success' else f"✗ {r['pdf']}: {r.get('error','')}"
            print(status)
    else:
        print("不支持的参数，请参考 SKILL.md")