---
name: deepread
description: "按固定流程深度阅读论文，依次完成关键章节翻译、逐 RQ 讲解、吸收总结。触发词：DeepRead、深度读论文、论文精读、逐段读论文、paper deep read。"
---

# DeepRead — 论文深度阅读流程

## 目标

把一篇论文按固定流程结构化读完，形成你自己的理解，而不是只看 AI 总结。

## PDF 读取协议（强制）

输入是 PDF 时，**必须**使用本 skill 自带提取器。不要改用本地通用 PDF skill，也不要临时编写 Python / pdfplumber / pypdf 解析代码。通用 PDF skill 的默认抽取会把 ACM 双栏论文抽成无空格粘连文本。

以下命令中的 `<skill-dir>` 指当前 `SKILL.md` 所在目录。

1. 如果缺少 PDF 依赖，先安装：

   ```bash
   python -m pip install -r "<skill-dir>/requirements.txt"
   ```

2. 运行固定入口：

   ```bash
   python "<skill-dir>/scripts/extract_pdf.py" "<PDF 路径>" --output "<输出目录>/<PDF 文件名>.extracted.md"
   ```

3. 等待命令成功并出现 `[DeepRead_PDF_READY]`，然后读取生成的提取文件。
4. 用 Python 打开提取文件时指定 `encoding="utf-8"`。不要把提取正文或中文 print 到终端来判断编码。
5. 后续填写论文信息、翻译和逐 RQ 讲解都必须基于该提取文件；引用原文时保留其中的页码标记。
6. 如果提取器报告 PDF 无可提取文字，停止并告诉用户该文件可能是扫描件、需要 OCR。不要自行改写成另一段临时解析代码。
7. 如果 stderr 出现 `[DeepRead_PDF_SPACING_WARN]`，继续基于该提取文件工作，并在收尾时注明英文词距可能仍偏紧。不要为此再写解析代码。

如果输入已经是 Markdown、纯文本或用户直接粘贴的正文，则跳过本节。

## 执行约束（强制，防卡住）

这些规则就是为了避免在“写文件 / 终端乱码”上空转。

1. 报告只写一个 UTF-8 文件：`outputs/<安全论文英文名>_DeepRead.md`。安全名只保留字母、数字、空格、点、下划线和连字符；把 `'`、`’`、`‘` 等撇号去掉。需要时运行：

   ```bash
   python "<skill-dir>/scripts/check_report.py" --suggest-name "<论文英文名>"
   ```

2. 不要把报告正文嵌进 `python -c`、PowerShell here-string 套 Python、或终端一次性粘贴。用文件写入工具直接写目标 `.md`，或先把内容落到磁盘再复制到目标路径。
3. 写完后只运行：

   ```bash
   python "<skill-dir>/scripts/check_report.py" "<报告路径>"
   ```

   只看脚本打印的 `OK` / `MISSING` / `[DeepRead_REPORT_READY]`。不要把报告正文 print 到终端。Windows 终端用系统代码页显示 UTF-8 中文时会看起来像乱码，那不是文件损坏。
4. 出现 `[DeepRead_REPORT_READY]` 后立即收尾：给出文件路径，提醒用户读摘要 / 引言 / 结论。不要再抽 PDF，不要再为编码循环检查。
5. 若打印 `[DeepRead_REPORT_INCOMPLETE]`，只补缺失标题对应的内容，再跑一次检查，然后停止。

## 输入

- 论文 PDF 路径或论文文本内容
- 输出目录，默认 `./outputs`
- 是否保留英文对照：默认保留

## 输出

- 输出目录：`outputs/<安全论文英文名>_DeepRead.md`
- 输出模板：`templates/DeepRead.md`

## 边界

- 本 skill 只负责阅读、讲解、总结吸收
- 禁止生成新的研究 idea
- 不替代用户亲自阅读原文

## 第一步：初始化

1. 确认论文文件可访问。
2. 创建输出目录。
3. 先填写论文基本信息，包括：
   - 英文原名
   - 中文名
   - 发表日期
   - 期刊 / 会议 / arXiv
   - 作者
   - 作者单位
   - DOI

## 第二步：阶段一 — 关键章节翻译

只处理以下部分：
- Abstract
- Introduction
- Conclusion / Summary

规则：
先给出英文原文，再进行翻译

## 第三步：阶段二 — 逐 RQ 讲解

1. 从论文中拆出研究问题 `RQ1`、`RQ2` ...
2. 若论文没有明确列出 RQ，先和用户确认拟定的 RQ。
3. 对每个 RQ：
   - 先讲解原文中对应的方法
   - 再讲解原文中对应的实验 / 结果
   - 最后再给出 AI 总结
4. 每个 RQ 都要单独成节，节的标题要包含 RQ 原文，且要与原文英文翻译保持一致。

## 第四步：阶段三 — 翻译并总结 related work

1. 不需要 related work 的英文原文
2. 直接给出 related work 的中文翻译
3. AI 总结 related work

## 第五步：阶段四 — 吸收总结，不生成 idea

回答以下 3 个问题：
1. 论文解决了什么问题，没有解决什么问题
2. 论文有效依赖什么关键前提
3. 论文原文中是怎么展望未来工作的

规则：
- 只总结，不生成 idea，尤其是第三个问题，只可以引用原文中对未来工作的展望，不能生成新的研究 idea
- 每个问题都要引用论文具体证据

## 第六步：收尾

运行 `scripts/check_report.py`。看到 `[DeepRead_REPORT_READY]` 后，输出最终文件清单：

- `<安全论文英文名>_DeepRead.md`

提醒用户：
- 本 Skill 以人为中心，建议人工阅读引言、摘要、结论部分

然后停止。

## 触发方式

- 用户说：`DeepRead`、论文精读、逐 RQ 读论文、论文阅读流程
- 用户上传论文 PDF 并希望按固定阅读流程进行

## 禁止行为

- 不在阶段四主动生成研究 idea
- 不跳过任何阶段
- 不改用通用 PDF skill 抽取论文
- 不把报告或提取正文打印到终端做编码检查
- 不在 `[DeepRead_REPORT_READY]` 之后继续抽取或循环验证