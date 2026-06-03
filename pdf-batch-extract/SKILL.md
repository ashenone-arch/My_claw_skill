---
name: pdf-batch-extract
version: "2.0"
description: 当用户需要将文件夹内多个 PDF 统一提取原文和表格为 MD 文件时使用。即使用户说"批量提取 PDF"、"把 PDF 转成 Markdown"、"读取 PDF 原文"、"提取 PDF 表格"、"将文件夹内所有 PDF 转为 md"、"PDF 批量转 markdown"、"把 PDF 里的表格导出来"、"PDF 原文提取"、"帮我把这个文件夹的 PDF 都转成 md"也应触发。NOT for：单篇 PDF 的简单格式转换（用 read 工具直接读即可）；需要对话交叉分析的场景（用 cross-talk-synthesis）；PDF 合并/拆分/旋转/加密操作。
---

# PDF 批量原文提取（含表格）

## 你的角色

你是 pdf-batch-extract 的**操作员**，不是 PDF 提取库的开发者。

你的工作只有三件事：
1. 确定目标文件夹、检测环境、展示 PDF 列表
2. 调度 subagent 运行 `extract_pdf_to_md.py`（本文档指定的唯一提取方式）
3. 汇总结果向用户报告

你不需要理解 pdfplumber 的 API，**不允许在 prompt 中让 subagent 编写 Python 提取逻辑**。

## 最高优先级铁律

**违反即任务失败。以下行为绝对禁止：**

| 禁止行为 | 曾导致的事故 |
|---------|------------|
| 在 subagent prompt 中写"用 pdfplumber 提取 PDF"之类的 Python 代码指令 | subagent 会自己写一套提取逻辑，忽略 `extract_pdf_to_md.py` 中的页眉/页脚/水印清理、表格格式化、中文编码处理，导致输出质量参差不齐 |
| 让 subagent 自己安装 pdfplumber | 重复安装浪费时间，且 subagent 环境可能与主环境不一致 |
| 子任务中自行重试限流错误 | 无间隔重试触发频率限制，正确做法是由主流程统一控制重试间隔 |

**允许的操作：**
- 环境预检（`python -c "import pdfplumber"`）
- 运行 `extract_pdf_to_md.py`（唯一提取方式）
- 调度 subagent 并行执行脚本
- 汇总展示结果

## 概述

将指定文件夹内的所有 PDF 文件逐一读取，同时提取全文文本和表格，保存为同名 .md 文件。提取逻辑统一由 `scripts/extract_pdf_to_md.py` 完成（内置文本清理、表格格式化、中文路径支持），不进行话题分析或摘要。

> **辅助文件**：
> - `scripts/extract_pdf_to_md.py` — 通用提取脚本（所有 PDF 共用）
> - `WATERMARK.md` — 水印检测与清理专项指引
> - `QUICKREF.md` — 快速参考表

## 执行步骤

### 步骤 0：环境预检

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" -c "import pdfplumber; print('ok')"
```

- 输出 `ok` → 环境完备，跳到步骤 1
- 报错 `ModuleNotFoundError` → 执行安装：

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" -m pip install pdfplumber --quiet
```

### 步骤 1：确定目标文件夹

扫描目标文件夹，获取所有 `.pdf` 文件列表，按文件名排序。向用户展示扫描结果。PDF 数量 > 20 时建议分批。

### 步骤 1.5：水印检测

读取每个 PDF 前 3 页检查水印特征。检测到水印时询问用户提供水印文字用于精准清理，用户说"跳过"则不清理继续。

> 清理策略详见 `WATERMARK.md`。

### 步骤 2：执行提取

**唯一提取方式**：运行 `scripts/extract_pdf_to_md.py`。Python 路径：`C:\Program Files\AlphaEngine\resources\python\python\python.exe`

#### PDF 数量 ≤ 2：直接执行

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" "{技能目录}/scripts/extract_pdf_to_md.py" "{pdf_path}" "{output_dir}"
```

#### PDF 数量 ≥ 3：分批 subagent 并行

每批最多 3 个，**同一消息中并行发出所有 task 调用**。每个 subagent 的 prompt：

```
你负责调用通用脚本提取 PDF 为 markdown。

调用命令（直接在 bash 中执行，不要写 Python 代码）：
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" "{技能目录}/scripts/extract_pdf_to_md.py" "{pdf_path}" "{output_dir}"

执行后解析输出：
- 成功：输出格式为 "OK|<md文件路径>|<页数>|<表格数>"
- 失败：输出格式为 "ERROR|<错误信息>"

完成后汇报：文件名、页数、表格数、md 文件路径（或失败原因）。
```

> **关键**：subagent prompt 中只给命令，不给提取逻辑。脚本内部已处理页眉/页脚/水印清理、表格格式化、中文编码。

批次间等待 5 秒。失败项统一重试（最多 2 次，间隔 30 秒）。

### 步骤 3：展示汇总结果

展示成功/失败表格，标注失败原因（密码保护、扫描件无文字等）。

## 退出前自检

在向用户报告结果之前，必须完成：

1. 任何 subagent 的 prompt 中是否包含了 Python 提取代码（如 `pdfplumber.open`、`extract_text` 等）？→ 是则**任务失败**。所有 subagent 必须且只能调用 `extract_pdf_to_md.py`。
2. 是否让 subagent 自行安装了 pdfplumber？→ 是则**任务失败**。环境预检只在步骤 0 执行一次。
3. 是否在遇到限流时让 subagent 内部重试？→ 是则**任务失败**。重试由主流程统一控制。

全部通过后，正常报告结果。

## 输出格式

每个 .md 文件由脚本自动生成，格式为：

```markdown
# {文件名}

> 来源：{原文件名}  |  共 {N} 页

--- 第 1 页 ---
{清理后的文本}

**表 1-1：**
| 列A | 列B |
| --- | --- |
| ... |
```

## 踩坑日志

| 事故 | 原因 | 教训 |
|------|------|------|
| subagent 自己写 pdfplumber 代码 | prompt 中描述了提取 API，subagent 绕过脚本自行实现 | prompt 中只给命令，不给 API 细节 |
| 限流后 subagent 连续重试 | subagent 遇到 429 后立即重试 3 次，全部被拒 | 重试由主流程统一控制间隔 |
| 中文文件名乱码 | subagent 用 `python` 而非安装时的 Python 路径 | 始终使用完整的 Python 绝对路径 |

## 注意事项

- **不重复安装**：步骤 0 已检查环境
- **不猜测路径**：用户未指定文件夹时先询问
- **不覆盖已有文件**：同名 .md 存在时询问
- **不合并**：每个 PDF 独立输出
- **不分析**：纯原文提取，不做摘要/话题识别
- **扫描件 PDF**：无文字层标记为失败
