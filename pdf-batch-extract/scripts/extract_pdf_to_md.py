"""
PDF 批量原文提取通用脚本
用法: python extract_pdf_to_md.py <pdf_path> <output_dir>
"""
import pdfplumber, re, sys, os

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
        # 过滤纯数字页码行
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
        # 表头
        out.append("| " + " | ".join(str(c or "").strip() for c in rows[0]) + " |\n")
        # 分隔线
        out.append("| " + " | ".join(["---"] * len(rows[0])) + " |\n")
        # 数据行
        for row in rows[1:]:
            out.append("| " + " | ".join(str(c or "").strip() for c in row) + " |\n")
    return '\n'.join(out)

def process_single_pdf(pdf_path, output_dir):
    """处理单个 PDF，输出同名 .md 文件"""
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(output_dir, f"{filename}.md")

    total_tables = 0
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"---\n# {filename}\n\n> 来源：{os.path.basename(pdf_path)}\n\n---\n\n")

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                text = clean_text(page.extract_text() or "")
                tables_md = extract_tables(page, i)

                # 统计表格数
                if tables_md.strip():
                    table_count = tables_md.count("**表 ")
                    total_tables += table_count

                f.write(f"--- 第 {i} 页 ---\n{text}\n{tables_md}\n\n")

    return out_path, total_pages, total_tables

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_pdf_to_md.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(pdf_path)

    try:
        out_path, pages, tables = process_single_pdf(pdf_path, output_dir)
        print(f"OK|{out_path}|{pages}|{tables}")
    except Exception as e:
        print(f"ERROR|{str(e)}")
        sys.exit(1)