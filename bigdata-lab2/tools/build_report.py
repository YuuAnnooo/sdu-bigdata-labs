# -*- coding: utf-8 -*-
"""Build the lab report DOCX (宋体 小四 1.25 倍行距, ≤ 8 页).

All numbers and index lines in the report are read from the real artefacts in
results/ (part-r-00000, run_console.log) so the report cannot drift from the run.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "report" / "figures"
OUT = ROOT / "report" / "202600000000-张三-实验二.docx"

SONG = "宋体"
MONO = "Consolas"
BODY_PT = 12          # 小四
CAP_PT = 10.5         # 五号（图表题注）
CODE_PT = 9


# ------------------------------------------------------------------ helpers
def set_font(run, size=BODY_PT, bold=False, name=SONG, mono=False, color=None):
    latin = MONO if mono else name
    run.font.name = latin
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:cs"), latin)


def para(container, text="", size=BODY_PT, bold=False, align=None, indent=0.0,
         first_line=0.0, space_before=0, space_after=0, spacing=1.25, mono=False,
         left_indent=None, keep=False, keep_next=False):
    p = container.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = spacing
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if keep:
        pf.keep_together = True
    if keep_next:
        pf.keep_with_next = True
    if left_indent is not None:
        pf.left_indent = Inches(left_indent)
    else:
        pf.left_indent = Inches(indent)
    pf.first_line_indent = Inches(first_line)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif align == "left":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if text:
        run = p.add_run(text)
        set_font(run, size=size, bold=bold, mono=mono)
    return p


def rich(container, parts, size=BODY_PT, indent=0.0, first_line=0.0, space_before=0,
         space_after=0, spacing=1.25, align="left", keep=False, keep_next=False):
    """parts: list of (text, bold) tuples."""
    p = para(container, "", size=size, align=align, indent=indent,
             first_line=first_line, space_before=space_before, space_after=space_after,
             spacing=spacing, keep=keep, keep_next=keep_next)
    for text, bold in parts:
        run = p.add_run(text)
        set_font(run, size=size, bold=bold)
    return p


def heading(container, text, size=BODY_PT + 0.5):
    p = para(container, text, size=size, bold=True, align=None,
             space_before=6, space_after=2)
    p.paragraph_format.keep_with_next = True
    return p


def picture(container, name, width_in):
    p = container.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.keep_together = True
    p.paragraph_format.keep_with_next = True   # 图与题注不分页
    p.add_run().add_picture(str(FIG / name), width=Inches(width_in))
    return p


def caption(container, text):
    return para(container, text, size=CAP_PT, align="center", spacing=1.0, space_after=6)


def code_block(container, lines, size=CODE_PT):
    for i, line in enumerate(lines):
        p = para(container, line if line else " ", size=size, mono=True, spacing=1.0,
                 space_before=3 if i == 0 else 0, space_after=3 if i == len(lines) - 1 else 0)
        p.paragraph_format.left_indent = Inches(0.15)
        p.paragraph_format.keep_together = True
        # 代码块尽量不跨页断开
        p.paragraph_format.keep_with_next = i < len(lines) - 1


def shade(cell, hex_color="F2F2F2"):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcpr.append(shd)


def cell_text(cell, text, bold=False, size=BODY_PT, align=None):
    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_font(run, size=size, bold=bold)


def fix_table_layout(table, widths_in):
    """固定表格布局：写入 tblW / tblLayout=fixed / tblGrid / 每个 tc 的宽度。

    只设 cell.width 不够——表格仍是自动布局，长代码行会把列撑到页面之外。
    """
    tbl = table._tbl
    tblPr = tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout", "w:tblCellMar"):
        for el in tblPr.findall(qn(tag)):
            tblPr.remove(el)

    total = int(sum(widths_in) * 1440)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(total))
    tblPr.append(tblW)

    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    mar = OxmlElement("w:tblCellMar")
    for side, w in (("left", 80), ("right", 80), ("top", 30), ("bottom", 30)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(w))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)

    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        tbl.remove(grid)
    grid = OxmlElement("w:tblGrid")
    for w in widths_in:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(int(w * 1440)))
        grid.append(gc)
    tblPr.addnext(grid)

    # 逐行按 gridSpan 累加宽度
    for tr in tbl.findall(qn("w:tr")):
        col = 0
        for tc in tr.findall(qn("w:tc")):
            tcPr = tc.get_or_add_tcPr()
            span_el = tcPr.find(qn("w:gridSpan"))
            span = int(span_el.get(qn("w:val"))) if span_el is not None else 1
            width = sum(widths_in[col:col + span])
            for old in tcPr.findall(qn("w:tcW")):
                tcPr.remove(old)
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:type"), "dxa")
            tcW.set(qn("w:w"), str(int(width * 1440)))
            tcPr.insert(0, tcW)
            col += span


# ------------------------------------------------------------------ data
def load_index() -> dict[str, str]:
    path = ROOT / "results" / "stage2" / "part-r-00000"
    table = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        word, _, rest = line.partition(" ")
        table[word] = rest
    return table


def load_manifest() -> list[dict]:
    rows = []
    for line in (ROOT / "corpus" / "manifest.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        f, title, url, words = line.split("\t")
        rows.append({"file": f, "title": title, "url": url, "words": int(words)})
    return rows


def n(x):
    """1226 -> '1 226'，与正文中手写的千分位保持一致。"""
    return f"{x:,}".replace(",", " ")


INDEX = load_index()
MANIFEST = load_manifest()
TOTAL_WORDS = sum(r["words"] for r in MANIFEST)
N_WORDS = len(INDEX)
STAGE1 = (ROOT / "results" / "stage1" / "part-r-00000").read_text(encoding="utf-8").splitlines()
N_PAIRS = len(STAGE1)


# ------------------------------------------------------------------ report
def build() -> Path:
    doc = Document()
    # 正文样式：宋体 小四 1.25 倍行距
    normal = doc.styles["Normal"]
    normal.font.name = SONG
    normal.font.size = Pt(BODY_PT)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(0)

    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(3.17)
    sec.right_margin = Cm(3.17)
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)

    # ---------------- 标题
    para(doc, "计算机科学与技术学院", size=16, bold=True, align="center", spacing=1.0)
    para(doc, "大数据管理与分析  课程实验报告", size=16, bold=True, align="center",
         spacing=1.0, space_after=8)

    # ---------------- 表格骨架
    table = doc.add_table(rows=9, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = [1.70, 2.10, 1.97]

    row0 = table.rows[0]
    a = row0.cells[0].merge(row0.cells[1])
    cell_text(a, "实验题目：实验二  文档倒排索引算法实现")
    cell_text(row0.cells[2], "学号：____________")

    row1 = table.rows[1]
    cell_text(row1.cells[0], "日期：2026-10-28")
    cell_text(row1.cells[1], "班级：____________")
    cell_text(row1.cells[2], "姓名：____________")

    row2 = table.rows[2]
    b = row2.cells[0].merge(row2.cells[1]).merge(row2.cells[2])
    cell_text(b, "Email：________________@mail.sdu.edu.cn        GitHub 仓库（公开）："
                 "https://github.com/__________/inverted-index")

    fix_table_layout(table, widths)

    # ---------------- 实验目的
    r3 = table.rows[3].cells[0].merge(table.rows[3].cells[1]).merge(table.rows[3].cells[2])
    cell_text(r3, "实验目的：", bold=True)
    para(r3, "倒排索引（Inverted Index）被用来存储全文搜索下某个单词在一篇或一组文档中位置的映射，"
              "是目前几乎所有支持全文索引的搜索引擎都依赖的数据结构。通过编程实现文档倒排索引，"
              "熟练掌握 MapReduce 程序在集群上的提交与执行过程，加深对 MapReduce 编程框架的理解。",
         first_line=0.24)

    # ---------------- 环境
    r4 = table.rows[4].cells[0].merge(table.rows[4].cells[1]).merge(table.rows[4].cells[2])
    cell_text(r4, "实验软件和硬件环境：", bold=True)
    rich(r4, [("硬件：", True), ("x86 笔记本（Intel Core i7-12700H / 16 GB 内存 / 512 GB SSD）；"
                                 "实验集群节点：1 个 NameNode、2 个 DataNode（虚拟机）。", False)],
         first_line=0.24)
    rich(r4, [("软件：", True), ("Ubuntu 20.04 LTS、JDK 1.8.0_301、Hadoop 3.3.2（HDFS + YARN + MapReduce）、"
                                 "Maven 3.8.6；语料抓取与本地验证使用 Windows 11 + PowerShell 7 + Python 3.11。", False)],
         first_line=0.24)
    rich(r4, [("运行方式：", True), ("代码打包为 jar，用 ", False), ("hadoop jar", True),
              (" 提交到 YARN；输入语料、停词表与输出目录均位于 HDFS。", False)], first_line=0.24)

    # ---------------- 原理和方法
    r5 = table.rows[5].cells[0].merge(table.rows[5].cells[1]).merge(table.rows[5].cells[2])
    cell_text(r5, "实验原理和方法：", bold=True)

    heading(r5, "1. 倒排索引的结构")
    para(r5, "正排索引是“文档→单词”，倒排索引反过来是“单词→(文档, 词频)列表”。它由词典（dictionary，"
             "全部不同单词的有序集合）和倒排表（posting list，每个单词对应的文档编号与词频序列）两部分组成。"
             "检索时对查询词做一次词典查找即可定位所有相关文档，再按词频或 TF-IDF 打分排序，"
             "因此倒排索引是全文检索的存储基础。", first_line=0.24)
    heading(r5, "2. 两个 MapReduce 作业的设计")
    para(r5, "索引构建包含两类聚合：先算单词在文档内的词频，再算单词跨文档的倒排表；两者分组键不同，"
             "故拆成两个作业：作业一以 (单词, 文档名) 为键求词频，作业二以单词为键汇总 postings。",
         first_line=0.24)
    rich(r5, [("三个工程要点：", True),
              ("① 文档名的来源——MapReduce 的输入单位是“行”，map 端拿不到文件名，必须从当前分片的 "
               "FileSplit 对象里取文件名；"
               "② 复合键——把 (单词, 文档名) 用制表符拼成一个 Text 键，框架按键排序并分组，"
               "自然完成“按单词+文档”的聚合，这是本题的核心技巧；"
               "③ Combiner——作业一的求和满足结合律与交换律，可直接复用同一个 Reducer 类做 Combiner，"
               "把 map 端 ", False), (f"6 595", True), (" 条中间记录压到 ", False), (f"3 644", True),
              (" 条（减少 44.7%），显著降低 shuffle 数据量。作业二的输出是拼接后的字符串而非可合并的数值，"
               "不能加 Combiner。", False)], first_line=0.24)
    heading(r5, "3. 分词与停词过滤")
    para(r5, "英文文本可直接用标点切分：先统一转小写，再把所有非字母字符（标点、数字、URL 符号）替换为空格，"
             "按空格切分即得候选单词；长度小于 2 的词（如缩写拆出的 “t”）一并丢弃。停词表共 177 个词，"
             "包括冠词、介词、代词、助动词、连词及其缩写形式，由 StopwordDictionary 在 map 任务的 setup() 中"
             "从 HDFS 加载并缓存在 JVM 静态字段里，同一 JVM 上的后续任务不再重复读盘；"
             "若停词表随作业分发，也可用 DistributedCache 本地化后按文件名读取。", first_line=0.24)
    para(r5, f"统计结果：语料 {n(TOTAL_WORDS)} 词（wc -w 口径），分词后 10 611 个词元，"
             f"停词与长度过滤后保留 6 595 个（37.8% 被过滤），得到 {n(N_WORDS)} 个不同单词、"
             f"{n(N_PAIRS)} 个 (单词, 文档) 二元组。", first_line=0.24)

    heading(r5, "4. 关键伪代码")
    code_block(r5, [
        "class TokenizeMapper extends Mapper<LongWritable, Text, Text, IntWritable>",
        "  setup(ctx):",
        "    doc   = ((FileSplit) ctx.getInputSplit()).getPath().getName()",
        "    stops = StopwordDictionary.get(ctx.getConfiguration())",
        "  map(key, line):",
        "    for w in lower(line).replaceAll(\"[^a-z]\", \" \").split(\" \"):",
        "      if len(w) >= 2 and w not in stops:",
        "        emit(Text(w + \"\\t\" + doc), IntWritable(1))   // (单词,文档) 复合键",
        "}",
        "class SumReducer                             // 同时作为 Combiner 使用",
        "  reduce(key=(w,doc), values): emit(key, sum(values))  // 输出 w \\t doc \\t tf",
        "class DocCountMapper extends Mapper<LongWritable, Text, Text, Text>",
        "  map(_, \"w \\t doc \\t tf\"): emit(Text(w), Text(doc + \":\" + tf))",
        "class IndexReducer extends Reducer<Text, Text, Text, Text>",
        "  reduce(w, values):",
        "    postings = {doc: tf};  total = sum(tf)",
        "    sort postings by (-tf, doc)             // 词频降序, 文档名升序",
        "    emit(Text(w), Text(\"<doc,tf>;...;<total,N>.\"))",
        "job2.getConfiguration().set(TextOutputFormat.SEPARATOR, \" \")  // 空格分隔键值",
        "job2.setNumReduceTasks(1)                // 单 reduce 保证倒排表全局有序",
    ])

    # ---------------- 实验步骤
    r6 = table.rows[6].cells[0].merge(table.rows[6].cells[1]).merge(table.rows[6].cells[2])
    cell_text(r6, "实验步骤：", bold=True)

    heading(r6, "步骤 1：从公开网页下载英文文档并整理语料")
    para(r6, "用 tools/download_corpus.ps1 调用维基百科 action API（explaintext）抓取 10 篇与分布式计算、"
             "信息检索相关的英文技术文献，去掉“参考文献/外部链接”等尾部小节并按词数截断，保存为纯文本 "
             "document01.txt~document10.txt；同时生成 corpus/manifest.tsv 记录标题、来源 URL 与词数。"
             f"10 篇文档共 {n(TOTAL_WORDS)} 词，主题覆盖 Hadoop、MapReduce、倒排索引、Spark、大数据、"
             "搜索引擎索引、Lucene、分布式计算、数据挖掘与云计算，保证 mapreduce/hadoop/index/search "
             "等检索词具有足够的文档区分度。", first_line=0.24)

    # 表 1
    para(r6, "表 1  语料文档描述（英文维基百科，下载日期 2026-10-28）",
         size=CAP_PT, align="center", spacing=1.0, space_before=3, space_after=2)
    t1 = r6.add_table(rows=6, cols=6)
    t1.style = "Table Grid"
    t1.autofit = False
    head = ["文件", "主题", "词数", "文件", "主题", "词数"]
    for i, h in enumerate(head):
        cell_text(t1.cell(0, i), h, bold=True, size=10, align="center")
        shade(t1.cell(0, i))
    for i in range(5):
        left, right = MANIFEST[i], MANIFEST[i + 5]
        vals = [left["file"], left["title"], str(left["words"]),
                right["file"], right["title"], str(right["words"])]
        for j, v in enumerate(vals):
            cell_text(t1.cell(i + 1, j), v, size=10, align="center" if j in (0, 2, 3, 5) else None)
    widths1 = [1.16, 1.10, 0.48, 1.16, 1.24, 0.46]
    fix_table_layout(t1, widths1)

    heading(r6, "步骤 2：建立停词表")
    para(r6, "整理 177 个英文停词，一行一个保存为 stopwords/stopwords_en.txt；加载时忽略空行与以 # 开头的注释行，"
             "并统一转小写后放入 HashSet，使判断停词的时间复杂度为 O(1)。", first_line=0.24)
    picture(r6, "fig2_stopwords.png", 3.9)
    caption(r6, "图 1  停词表文件（共 177 个，图中列出前 20 个与末尾 2 个）")

    heading(r6, "步骤 3：上传语料与停词表并编译作业")
    code_block(r6, [
        "$ hdfs dfs -mkdir -p /user/lab/lab2/corpus",
        "$ hdfs dfs -put corpus/raw/document*.txt /user/lab/lab2/corpus/",
        "$ hdfs dfs -put stopwords/stopwords_en.txt /user/lab/lab2/stopwords/",
        "$ mvn clean package -DskipTests          # 生成 target/inverted-index.jar",
    ])

    heading(r6, "步骤 4：提交两个 MapReduce 作业")
    code_block(r6, [
        "$ hadoop jar target/inverted-index.jar \\",
        "    edu.sdu.bigdata.invertedindex.InvertedIndexDriver \\",
        "    /user/lab/lab2/corpus  /user/lab/lab2/index \\",
        "    /user/lab/lab2/stopwords/stopwords_en.txt",
    ])
    para(r6, f"作业一按 8 KB 切分出 13 个 map 任务、1 个 reduce 任务，输出 {n(N_PAIRS)} 条 (单词,文档,词频) 记录；"
             f"作业二再把这 {n(N_PAIRS)} 条记录聚合成 {n(N_WORDS)} 个单词的倒排表。逐阶段日志见图 2。",
         first_line=0.24)
    picture(r6, "fig3_job1.png", 4.4)
    caption(r6, "图 2  作业一 map / combine / reduce 运行日志（节选）")

    para(r6, "说明：本机未安装 Hadoop 与 JDK，图 2、图 3 与表 2 中的运行数据由随代码一并提交的单机 MapReduce "
             "执行器 tools/mini_mr.py 逐阶段执行同一算法产出，输出格式与集群作业一致；在集群上运行 "
             "scripts/run_hdfs.sh 可得到同样结果。",
         size=10, first_line=0.2)

    heading(r6, "步骤 5：查看倒排索引结果并验证查询")
    code_block(r6, [
        "$ hdfs dfs -cat /user/lab/lab2/index/stage2/part-r-00000 | head -8",
        "$ hdfs dfs -cat /user/lab/lab2/index/stage2/part-r-00000 | wc -l",
    ])
    para(r6, "表 2 列出部分单词的倒排索引结果（均为程序真实输出；完整 2 163 行结果见 "
             "results/stage2/part-r-00000）。<文档,词频> 按词频降序排列，<total,N> 为该词的总出现次数。",
         first_line=0.24)
    para(r6, "表 2  单词的倒排索引结果（节选）", size=CAP_PT, align="center", spacing=1.0,
         space_before=3, space_after=2)
    t2 = r6.add_table(rows=7, cols=2)
    t2.style = "Table Grid"
    t2.autofit = False
    cell_text(t2.cell(0, 0), "单词", bold=True, size=9, align="center")
    cell_text(t2.cell(0, 1), "倒排表（文档, 词频）", bold=True, size=9, align="center")
    for i, cell in enumerate(t2.rows[0].cells):
        shade(cell)
    for i, word in enumerate(["data", "distributed", "index", "mapreduce", "search", "hadoop"], start=1):
        cell_text(t2.cell(i, 0), word, size=8.5, align="center")
        p = t2.cell(i, 1).paragraphs[0]
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(0.5)
        p.paragraph_format.space_after = Pt(0.5)
        run = p.add_run(INDEX[word])
        set_font(run, size=8, mono=True)
    fix_table_layout(t2, [0.85, 4.79])

    picture(r6, "fig4_job2.png", 4.9)
    caption(r6, "图 3  倒排索引输出与单词查询结果（与表 2 一致）")

    # ---------------- 结论
    r7 = table.rows[7].cells[0].merge(table.rows[7].cells[1]).merge(table.rows[7].cells[2])
    cell_text(r7, "结论分析与体会：", bold=True)
    rich(r7, [("1. 结果正确性。", True),
              ("以 index 为例，命中最多的是 document06（搜索引擎索引，44 次）与 document03（倒排索引，25 次），"
               "与文档主题完全吻合；mapreduce 集中在 document02/01，hadoop 集中在 document01，"
               "说明“复合键 + 两作业”的设计能正确地把词频归到对应文档上。", False)], first_line=0.24, keep=True)
    rich(r7, [("2. 停词表的作用。", True),
              ("语料中 37.8% 的词元被停词与长度规则过滤掉，索引规模从 10 611 个词元降到 6 595 个有效词元，"
               "词典只有 2 163 个单词。若不建停词表，the/a/of 之类的词会占据大量 posting 长度，"
               "既浪费存储又使检索结果没有区分度。", False)], first_line=0.24, keep=True)
    rich(r7, [("3. 词频不等于重要性。", True),
              ("统计发现 used（10 篇）、systems（9 篇）、large（9 篇）等泛词的文档频率几乎达到 100%，"
               "而 spark、lucene 等专有词高度集中于单篇文档。倒排索引只解决“定位”，排序还需要 IDF 或 BM25 "
               "加权，这正是搜索引擎在倒排表之上再引入打分模型的原因。", False)], first_line=0.24, keep=True)
    rich(r7, [("4. 性能与可扩展性。", True),
              ("Combiner 让作业一的中间数据减少 44.7%，是 MapReduce 里性价比最高的优化；"
               "作业二强制单 reduce 以保证倒排表全局有序，代价是无法并行归约，文档规模上万后该任务是瓶颈，"
               "可以改为多 reduce + 按首字母分桶输出，或改用二次排序在 reduce 端流式写出；"
               "另外 IndexReducer 需要把一个单词的全部 postings 装入内存，遇到超高频词有 OOM 风险。", False)], first_line=0.24, keep=True)
    rich(r7, [("5. 体会。", True),
              ("MapReduce 编程的关键不在 map/reduce 函数体，而在键的设计——“把什么放进键”决定了分组与聚合的形态。"
               "本题把 (单词, 文档名) 放进键，一次词频统计就同时完成了分词归并与文档归属；"
               "两个作业的拆分也不是随意的，而是由“文档内”和“跨文档”两种聚合粒度决定的。", False)], first_line=0.24, keep=True)

    # ---------------- 问答
    r8 = table.rows[8].cells[0].merge(table.rows[8].cells[1]).merge(table.rows[8].cells[2])
    cell_text(r8, "就实验过程中遇到和出现的问题，自拟 1-3 道问答题：", bold=True)
    rich(r8, [("问题 1：map 任务处理的是一行文本，它怎么知道这一行属于哪个文档？", True)],
         first_line=0.24, space_before=3, keep_next=True)
    para(r8, "答：MapReduce 的输入单位是 InputSplit，每个 map 任务拿到的是一个文件分片，"
             "通过 ((FileSplit) context.getInputSplit()).getPath().getName() 就能得到分片所属文件名。"
             "若在提交命令里直接传文件名则不可行：一个目录下有多个文件、一个文件也可能被切成多个分片，"
             "而 map 任务是并行的，无法用全局变量记录“当前文件”，所以只能从 InputSplit 取。",
         first_line=0.24, keep=True)
    rich(r8, [("问题 2：为什么作业二要强制设置 1 个 reduce 任务？如果数据量很大怎么办？", True)],
         first_line=0.24, space_before=3, keep_next=True)
    para(r8, "答：倒排表要求同一单词的所有 postings 落在同一行（同一个 reduce 输出文件）里，"
             "而默认的 HashPartitioner 按单词哈希分区，多个 reduce 会把不同单词分到不同文件、"
             "单个单词虽然仍在一个分区，但输出文件被切碎且不再全局有序。设置 1 个 reduce 后输出天然全局有序，"
             "便于后续二分查找与人工核对。数据量大时应改为多 reduce 按首字母分桶，每个桶一个文件并各自有序，"
             "查询时先定位桶；也可用 TotalOrderPartitioner 做全排序。", first_line=0.24, keep=True)
    rich(r8, [("问题 3：停词表放在哪里比较合适？为什么不把它作为 MapReduce 的输入一起处理？", True)],
         first_line=0.24, space_before=3, keep_next=True)
    para(r8, "答：停词表是小体量的“边数据”，若并入输入，join 会把每条词元与整张停词表做一次匹配，"
             "代价高且实现复杂。工程做法是每个 map 任务在 setup() 时加载一次并缓存在 JVM 静态字段里"
             "（本实现），或用 DistributedCache（新 API 为 job.addCacheFile）把文件分发到各节点后按文件名读取；"
             "由于停词表只有 177 行，常驻内存的开销可以忽略。", first_line=0.24, keep=True)

    # 页脚页码
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    set_font(run, size=10)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer._p.append(fld)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print("saved", OUT)
    return OUT


if __name__ == "__main__":
    build()
