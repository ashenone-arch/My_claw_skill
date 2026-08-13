"""
PDF 批量原文提取通用脚本
用法: python extract_pdf_to_md.py <pdf_path> [output_dir] [--pages "1-15"]
"""
import argparse, pdfplumber, re, sys, os

PYTHON_BIN = r"C:\Program Files\AlphaEngine\resources\python\python\python.exe"


def clean_text(text):
    """清理页眉/页脚/页码"""
    if not text:
        return ""
    lines = text.split('\n')
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+$', line):
            continue
        result.append(line)
    return '\n'.join(result)


def extract_tables(page, page_num):
    """提取表格，转换为 Markdown 格式"""
    tables = page.extract_tables()
    out = []
    for idx, table in enumerate(tables):
        if not table:
            continue
        rows = [r for r in table if any(c for c in r)]
        if len(rows) < 2:
            continue
        out.append(f"\n**表 {page_num}-{idx + 1}:**\n")
        out.append("| " + " | ".join(str(c or "").strip() for c in rows[0]) + " |\n")
        out.append("| " + " | ".join(["---"] * len(rows[0])) + " |\n")
        for row in rows[1:]:
            out.append("| " + " | ".join(str(c or "").strip() for c in row) + " |\n")
    return '\n'.join(out)


def parse_page_range(arg):
    """解析页码范围，如 '1-15' -> (1, 15), '146' -> (146, 146)"""
    if not arg:
        return None
    parts = arg.split('-')
    if len(parts) == 1:
        p = int(parts[0])
        return (p, p)
    return (int(parts[0]), int(parts[1]))


def process_single_pdf(pdf_path, output_dir, page_range=None):
    """处理单个 PDF，输出同名 .md 文件。page_range 为 (start, end) 元组。"""
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(output_dir, f"{filename}.md")

    total_tables = 0
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"---\n# {filename}\n\n> 来源：{os.path.basename(pdf_path)}\n\n---\n\n")

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            if page_range:
                start, end = page_range
                start = max(1, start)
                end = min(end, total_pages)
                pages = pdf.pages[start - 1:end]            # pdfplumber 0-indexed
                page_offset = start - 1                     # 页码偏移
            else:
                pages = pdf.pages
                page_offset = 0

            for idx, page in enumerate(pages):
                real_page = page_offset + idx + 1
                text = clean_text(page.extract_text() or "")
                tables_md = extract_tables(page, real_page)

                if tables_md.strip():
                    table_count = tables_md.count("**表 ")
                    total_tables += table_count

                f.write(f"--- 第 {real_page} 页 ---\n{text}\n{tables_md}\n\n")

    extracted_pages = len(pages)
    return out_path, total_pages, total_tables, extracted_pages


def main():
    parser = argparse.ArgumentParser(description="PDF 批量原文提取脚本")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("output_dir", nargs="?", default=None,
                        help="输出目录，默认与 PDF 同目录")
    parser.add_argument("--pages", default=None,
                        help="页码范围，如 '1-15' 或 '146-278'，不指定则提取全部")
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.dirname(args.pdf_path)
    page_range = parse_page_range(args.pages)

    try:
        out_path, total_pages, tables, extracted_pages = process_single_pdf(
            args.pdf_path, output_dir, page_range
        )
        print(f"OK|{out_path}|{total_pages}|{tables}|{extracted_pages}")
    except Exception as e:
        print(f"ERROR|{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
