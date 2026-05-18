# PDF 读取说明

当输入文件为 PDF 时，按以下步骤处理。

## 第一步：检查 Python 环境

在命令行执行：

```bash
python -c "import pdfplumber; print('ok')"
```

如果报错 `ModuleNotFoundError`，先安装：

```bash
python -m pip install pdfplumber --quiet
```

## 第二步：读取 PDF 内容

使用 pdfplumber，**避免使用 pymupdf**（在该环境下静默失败，难以排查）。

```python
import pdfplumber

files = [  # 所有 PDF 绝对路径列表
]
with pdfplumber.open(file_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text and text.strip():
            # 追加到输出
```

**中文路径处理**：Python 3.13+ 原生支持中文路径，直接传入绝对路径字符串即可。

## 第三步：提取后立即结构化

不要将 PDF 文本直接追加到纯文本文件——每读完一个 PDF，立即提取结构化摘要并追加到 JSON 文件中，避免大量文本堆积在内存中。

## 第四步：文件过大的分页处理

如果单个 PDF 超过 20 页，按每 10 页为单位分段读取，避免单次提取超时。
