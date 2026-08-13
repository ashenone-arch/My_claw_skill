---
name: pdf-batch-extract
version: "3.0"
description: 当用户需要将文件夹内多个 PDF 统一提取原文和表格为 MD 文件时使用。即使用户说"批量提取 PDF"、"把 PDF 转成 Markdown"、"读取 PDF 原文"、"提取 PDF 表格"、"将文件夹内所有 PDF 转为 md"、"PDF 批量转 markdown"、"把 PDF 里的表格导出来"、"PDF 原文提取"、"帮我把这个文件夹的 PDF 都转成 md"也应触发。也支持指定章节/页码范围精准提取（如"只提取第X节""提取XX页到XX页"）。NOT for：单篇 PDF 的简单格式转换（用 read 工具直接读即可）；需要对话交叉分析的场景（用 cross-talk-synthesis）；PDF 合并/拆分/旋转/加密操作。
---

# PDF 批量提取（含表格）

## 你的角色

你是 pdf-batch-extract 的**操作员**。你的工作：
1. 检测环境、展示 PDF 列表、判断提取策略
2. 调度 subagent 运行 `extract_pdf_to_md.py`（**唯一提取方式**）
3. 汇总结果向用户报告

你不需要理解 pdfplumber 的 API，**不允许在 prompt 中让 subagent 编写 Python 提取逻辑**。

## 铁律

| 禁止 | 后果 |
|------|------|
| 在 subagent prompt 中写 Python 提取代码 | 绕过脚本，输出质量参差不齐 |
| 让 subagent 自行安装 pdfplumber | 重复安装，环境不一致 |
| 子任务中自行重试限流错误 | 无间隔重试触发频率限制 |

## 辅助文件

| 文件 | 角色 |
|------|------|
| `scripts/extract_pdf_to_md.py` | **核心脚本**（文本清理+表格格式化+中文编码+页码范围） |
| `EXTRACTION_STRATEGIES.md` | 按需参考：章节感知提取、subagent 模板、水印处理、港股/A股结构对照 |
| `WATERMARK.md` | 水印清理专项（按需触发） |
| `QUICKREF.md` | 快速参考表 |

## 执行步骤

### 步骤 0：环境预检

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" -c "import pdfplumber; print('ok')"
```

- `ok` → 继续
- `ModuleNotFoundError` → 安装：

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" -m pip install pdfplumber --quiet
```

### 步骤 1：确定目标与策略

扫描目标文件夹，展示 PDF 列表。根据用户意图选择策略：

| 用户意图 | 策略 | 参考文档 |
|----------|------|---------|
| 提取**特定章节/页码范围** | 章节感知提取 | `EXTRACTION_STRATEGIES.md` |
| 全量提取少量 PDF（≤2） | 主流程直接调脚本 | 步骤 2-A |
| 全量提取多个 PDF（≥3） | 分批 subagent 并行 | 步骤 2-B |
| 只读极少量页面（≤20 页，无需表格） | 直接用 `read` 工具 | 不触发本 skill |

> PDF 数量 > 20 时建议分批处理。

### 步骤 2-A：全量提取（少量 PDF）

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" "{技能目录}/scripts/extract_pdf_to_md.py" "{pdf_path}" "{output_dir}"
```

### 步骤 2-B：全量提取（多个 PDF，subagent 并行）

每批最多 3 个，同一消息中并行发出所有 task 调用。subagent prompt：

```
你负责调用通用脚本提取 PDF 为 markdown。

调用命令（直接在 bash 中执行，不要写 Python 代码）：
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" "{技能目录}/scripts/extract_pdf_to_md.py" "{pdf_path}" "{output_dir}"

执行后解析输出：
- 成功：输出格式为 "OK|<md文件路径>|<总页数>|<表格数>|<实际提取页数>"
- 失败：输出格式为 "ERROR|<错误信息>"

完成后汇报：文件名、页数、表格数、md 文件路径（或失败原因）。
```

批次间等待 5 秒。失败项统一重试（最多 2 次，间隔 30 秒）。

### 步骤 2-C：章节感知提取（指定页码范围）

当用户指定了章节名称或页码范围时，用 `--pages` 参数精准提取：

```bash
"C:\Program Files\AlphaEngine\resources\python\python\python.exe" "{技能目录}/scripts/extract_pdf_to_md.py" "{pdf_path}" "{output_dir}" --pages "146-278"
```

章节定位方法、港股/A股结构对照、subagent 模板详见 `EXTRACTION_STRATEGIES.md`。

### 步骤 3：展示汇总结果

展示成功/失败表格，标注失败原因（密码保护、扫描件无文字等）。

## 退出前自检

1. subagent prompt 中是否包含 Python 提取代码？→ 任务失败
2. 是否让 subagent 自行安装 pdfplumber？→ 任务失败
3. 限流时是否让 subagent 内部重试？→ 任务失败

## 输出格式

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
| subagent 自己写 pdfplumber 代码 | prompt 中描述了提取 API | prompt 只给命令，不给 API |
| 限流后 subagent 连续重试 | subagent 遇到 429 后立即重试 | 重试由主流程统一控制间隔 |
| 中文文件名乱码 | subagent 用 `python` 而非安装时的路径 | 始终使用完整的 Python 绝对路径 |

## 注意事项

- **不重复安装**：步骤 0 已检查环境
- **不猜测路径**：用户未指定文件夹时先询问
- **不覆盖已有文件**：同名 .md 存在时询问
- **不合并**：每个 PDF 独立输出
- **不分析**：纯原文提取，不做摘要/话题识别
- **扫描件 PDF**：无文字层标记为失败
