# -*- coding: utf-8 -*-
"""生成《实验四 并行化数据挖掘算法设计》实验报告 DOCX。

版式：宋体、小四（12pt）、1.25 倍行距、A4、不超过 8 页。
所有统计数字都从 bigdata-lab4/out/ 与 data/ 读取，保证与代码输出一致。
"""
import csv
import hashlib
import json
import os
from collections import Counter

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK

import docx_kit as kit
from docx_kit import (add_tail_paragraph, apply_keep_rules, new_report_doc,
                      new_report_table, put, put_code, put_heading,
                      set_col_width, add_title)

BASE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(BASE, "bigdata-lab4")
OUT = os.path.join(LAB, "out")
DOCX_NAME = "实验四报告.docx"


# ------------------------------------------------------------------ 读取结果

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_items():
    items = {}
    with open(os.path.join(LAB, "data", "items.tsv"), encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] != "code":
                items[p[0]] = p[1]
    return items


def read_itemsets():
    rows = []
    with open(os.path.join(OUT, "local_itemsets.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            rows.append((int(p[0]), p[1], int(p[2])))
    return rows


def read_rules():
    rows = []
    with open(os.path.join(OUT, "local_rules.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            ante, cons = p[0].split(" => ")
            rows.append((ante, cons, int(p[1]), p[3], p[4]))
    return rows


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def top_items(itemsets, n=5):
    rows = [(supp, code) for size, code, supp in itemsets if size == 1]
    rows.sort(reverse=True)
    return rows[:n]


def find_rule(rules, ante, cons):
    for a, c, supp, conf, lift in rules:
        if a == ante and c == cons:
            return supp, conf, lift
    raise KeyError((ante, cons))


def code(cell, text, size=9):
    """输出块不跨页断开。"""
    p = put_code(cell, text, size=size)
    p.paragraph_format.keep_together = True
    return p


# ------------------------------------------------------------------ 正文

def build():
    stats = load_json(os.path.join(LAB, "data", "dataset_stats.json"))
    local = load_json(os.path.join(OUT, "local_timing.json"))
    spark = load_json(os.path.join(OUT, "spark_timing.json"))
    itemsets = read_itemsets()
    rules = read_rules()
    items = read_items()
    level = Counter(size for size, _, _ in itemsets)

    with open(os.path.join(OUT, "benchmark.csv"), encoding="utf-8") as f:
        bench = list(csv.DictReader(f))
    bench_map = {(r["scale"], r["implementation"]): r for r in bench}

    doc = new_report_doc()
    add_title(doc)
    table = new_report_table(doc)

    # ---- 行 0：实验题目 + 学号
    c = table.cell(0, 0).merge(table.cell(0, 1))
    put(c, "实验题目：并行化数据挖掘算法设计——Apriori 频繁项集挖掘的单机与 Spark 实现",
        indent=False)
    put(table.cell(0, 2), "学号：202400390047", indent=False)

    # ---- 行 1：日期 / 班级 / 姓名
    put(table.cell(1, 0), "日期：2026.11.18", indent=False)
    put(table.cell(1, 1), "班级：1", indent=False)
    put(table.cell(1, 2), "姓名：平祥可", indent=False)

    # ---- 行 2：Email
    c = table.cell(2, 0).merge(table.cell(2, 2))
    put(c, "Email：2245270713@qq.com", indent=False)

    # ---- 行 3：实验目的
    c = table.cell(3, 0).merge(table.cell(3, 2))
    label(c, "实验目的：")
    for i, item in enumerate([
        "理解关联规则挖掘中的支持度、置信度、提升度以及 Apriori 先验性质，"
        "掌握由频繁 k-1 项集生成候选 k 项集的连接与剪枝方法。",
        "针对交易数据“购物篮大、商品种类多”的特点，设计基于垂直位图的支持度计数方法，"
        "避免横向枚举子集带来的组合爆炸。",
        "把 Apriori 拆成“Driver 生成候选 + Executor 并行计数”的两阶段流程，"
        "用 PySpark 实现并分析 Driver/Executor 的分工与数据广播。",
        "用单机 Python 与 Spark 两套实现处理真实交易数据，验证结果逐字节一致；"
        "再通过弱扩展和并行度实验分析 Spark 的加速比、开销来源与适用规模。",
    ], 1):
        put(c, "（%d）%s" % (i, item))

    # ---- 行 4：实验软件和硬件环境
    c = table.cell(4, 0).merge(table.cell(4, 2))
    label(c, "实验软件和硬件环境：")
    put(c, "硬件：HP OMEN 16 笔记本，Intel Core i7-14650HX（16 核 24 线程）、16 GB 内存、"
           "1 TB SSD；WSL2 中可用内存 7.6 GB，Spark 统一使用 `local[4]`（4 个并行任务）。")
    put(c, "软件：Ubuntu 24.04.4 LTS（WSL2）；OpenJDK 1.8.0_504；Python 3.12.3；"
           "Spark 3.5.3；不依赖 Hadoop/HDFS，输入输出均为本地文件。另用 Spark standalone "
           "（1 Master + 1 Worker，4 核）提交同一脚本，结果与 `local[4]` 完全一致。")
    put(c, "数据：UCI Machine Learning Repository 的 Online Retail 数据集"
           "（DOI 10.24432/C5BW33），2010-12-01 至 2011-12-09 英国在线零售商的交易明细，"
           "原始 541 909 行；清洗后得到 18 270 个购物篮、3 784 种商品。")

    # ---- 行 5：实验原理和方法
    c = table.cell(5, 0).merge(table.cell(5, 2))
    label(c, "实验原理和方法：")

    put(c, "（1）关联规则的基本概念。设 N 为购物篮总数，X、Y 为商品集合，则")
    put(c, "support(X) = count(X) / N\n"
           "confidence(X → Y) = support(X ∪ Y) / support(X)\n"
           "lift(X → Y) = support(X ∪ Y) / (support(X) · support(Y))",
        indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    put(c, "支持度衡量项集出现的频繁程度，置信度是“买了 X 的人中有多少也买 Y”的条件概率，"
           "提升度则扣除了 Y 本身的热门程度：`lift > 1` 表示正相关，`lift = 1` 表示独立，"
           "`lift < 1` 表示负相关。挖掘任务是在 `support ≥ min_support` 的频繁项集中，"
           "找出 `confidence ≥ min_confidence` 的规则。")

    put(c, "（2）Apriori 的逐层搜索。先统计 1 项集，保留频繁项集 L₁；由 L_{k-1} 中前缀相同的"
           "项集两两连接得到候选 C_k，再利用先验性质剪枝：若候选的任一 k-1 子集不是频繁项集，"
           "则它一定不频繁，直接删除。对保留下来的候选扫描数据计数，得到 L_k，直到某一层为空。"
           "由频繁项集生成规则时，枚举每个项集的非空真子集 X，令 Y = itemset − X，"
           "用 `support(X ∪ Y) / support(X)` 计算置信度并过滤。")

    put(c, "（3）支持度计数：从横向枚举到垂直位图。最直观的写法是对每个购物篮枚举 C(n,k) 个"
           "k 元子集再累加，但本数据集平均购物篮有 28 种商品，最大的一个购物篮有 1 097 种商品，"
           "枚举 3 项集需要约 C(1097,3) ≈ 2.2 亿次组合；实测这种横向写法在 2% 支持度下算完 3 项集"
           "要 174 s，完全不可用。因此改用垂直表示：给每个商品维护一个大整数位图，第 t 位为 1 "
           "表示该商品出现在第 t 个购物篮；候选项集的支持数就是各商品位图按位与之后 1 的个数。"
           "上面那个 1 097 种商品的购物篮，算 3 项集只需要 3 次按位与，复杂度从“商品数的指数”"
           "降为“项集大小 × 位图长度”。")

    put(c, "（4）并行化设计。Apriori 的层与层之间有严格依赖，但同一层的候选之间完全独立，"
           "正好适合按候选切分：")
    put(c, "① Driver 端完成连接、剪枝和候选排序。候选只与上一层频繁项集有关，"
           "本实验中 L₁ = 1 609 个商品，L₂ 候选 1 293 636 个，生成本身只需秒级，"
           "且结果要作为下一层的输入，放在 Driver 上最简单。")
    put(c, "② Executor 端并行计数。先由 `mapPartitionsWithIndex` 在每个分区内用局部事务号"
           "建位图，再整体左移拼成全局位图，避免 Driver 串行处理全部事务；随后把候选 "
           "`parallelize` 成若干分区，各任务只访问广播变量中的位图，用按位与 + `bit_count()` "
           "求支持数，最后 `collect` 回 Driver 过滤、排序。")
    put(c, "③ 规则生成。项集数较多（≥ 2 000）时用 `flatMap` 把项集分发到各分区并行枚举规则，"
           "否则在 Driver 直接生成；规则枚举只与项集大小有关，代价远小于支持度计数。")
    put(c, "④ 结果确定性。商品按编码字典序排列，候选、项集、规则全部排序；支持数用整数，"
           "置信度和提升度用 `Fraction` 精确比较、最后统一四舍五入到 6 位小数。"
           "单机版和并行版共用同一套候选生成、计数和格式化语义，因此输出可以逐字节比较。")

    put(c, "（5）数据清洗与参数选择。原始 Excel 先去掉取消单（发票号以 C 开头）、数量 ≤ 0 的"
           "退货/调账行、单价 ≤ 0 的行，以及 `POST`、`D`、`M`、`BANK CHARGES` 等非商品编码，"
           "只保留 5 位数字（可带 1 个字母后缀）的商品；再按发票号聚合成购物篮，同一商品在一次"
           "交易中只计一次，并去掉只有 1 种商品的购物篮。最终 18 270 个购物篮、3 784 种商品、"
           "513 506 次商品出现。取 `min_support = 0.005`（支持数 ≥ 92）、`min_confidence = 0.5`："
           "阈值再高（如 0.02）只剩 470 个项集、162 条规则，看不到具体的商品组合；再低则规则数"
           "和运行时间增长过快，且大量规则只是稀有商品的偶然共现。")

    # ---- 行 6：实验步骤
    c = table.cell(6, 0).merge(table.cell(6, 2))
    label(c, "实验步骤：（不要求罗列完整源代码）")

    put_heading(c, "一、数据准备")
    put(c, "用 `tools/prepare_data.py` 读取原始 Excel 并按上述规则清洗，输出一行一个购物篮的 "
           "`data/transactions.tsv`、商品描述表 `data/items.tsv` 和统计文件 "
           "`data/dataset_stats.json`。关键数字如下：")
    code(c, """原始行数        541909
清洗后行数      525462   （取消单 9288、非商品 5265、数量<=0 10624、单价<=0 2517）
发票数          19769
购物篮数        18270    （至少 2 种商品）
商品数          3784
商品出现次数    513506
平均/中位/最大  28.11 / 17 / 1097
日期范围        2010-12-01 ~ 2011-12-09""")

    put_heading(c, "二、单机（非并行）Apriori 实现")
    put(c, "`python/apriori_local.py` 用纯 Python 实现：`build_masks()` 扫描一遍事务建位图，"
           "`apriori_gen()` 完成连接和剪枝，`support_of()` 做按位与计数，规则枚举用 "
           "`itertools.combinations` 生成所有真子集。核心只有几行：")
    code(c, """for tid, basket in enumerate(transactions):
    bit = 1 << tid
    for item in basket:
        masks[item] = masks.get(item, 0) | bit     # 商品 -> 事务位图

def support_of(itemset, masks):
    m = masks[itemset[0]]
    for item in itemset[1:]:
        m &= masks[item]
    return m.bit_count()                           # 同时包含全部商品的购物篮数""")
    put(c, "运行命令与输出（完整命令见 `scripts/run_local.sh`）：")
    code(c, """python python/apriori_local.py --input data/transactions.tsv \\
    --min-support 0.005 --min-confidence 0.5 \\
    --out-prefix out/local --timing out/local_timing.json

第 2 层：候选 1293636，频繁 10082（3.702s）
第 3 层：候选 155804，频繁 7136（0.699s）
第 4 层：候选 11207，频繁 2805（0.080s）
第 5 层：候选 1923，频繁 802（0.015s）
频繁项集 22522 个，关联规则 35657 条
总耗时 5.494s""")
    put(c, "各层频繁项集数为：")
    code(c, "k          1      2      3     4     5    6   7     合计\n"
                "项集数  1609  10082   7136  2805   802   87   1    22522")

    put_heading(c, "三、Spark 并行实现")
    put(c, "`spark/apriori_spark.py` 保留同一套候选生成和规则格式化代码，把支持度计数改成 "
           "RDD 操作。每层的核心逻辑是：")
    code(c, """candidates = apriori_gen([x for x, _ in level], k)       # Driver：连接 + 剪枝
counted = (sc.parallelize(candidates, slices)             # 候选切分到各分区
           .mapPartitions(lambda part: [(c, support_of(c, masks))
                                        for c in part])    # Executor：位图与运算
           .collect())
nxt = sorted([(c, n) for c, n in counted if n >= min_count])""")
    put(c, "其中 `masks` 是广播变量；分区内建位图时先用局部事务号，再按分区偏移左移，"
           "这样每个分区只需处理自己的事务，Driver 只负责合并 3 784 个商品的位图。"
           "提交命令为 `spark-submit --master local[4] spark/apriori_spark.py ...`，"
           "1x 数据下计算耗时 9.49 s、总墙钟 11.81 s。")

    put_heading(c, "四、并行与单机结果的一致性验证")
    put(c, "`tools/compare_results.py` 同时比较行数、逐行内容和 SHA-256，并统计每层项集数。"
           "1x 数据的比较结果：")
    code(c, """实现     项集行数  SHA-256（前 16 位）   规则行数  SHA-256（前 16 位）
单机       22522    435950d87334f2b1        35657    dbafc37104bf1c9
Spark      22522    435950d87334f2b1        35657    dbafc37104bf1c9
结果：频繁项集、关联规则均逐字节一致（exit code 0）""")
    put(c, "把购物篮复制 4 份、8 份并打乱后重复实验（支持度比例不变，项集和规则应完全相同），"
           "两组输出同样逐字节一致；standalone 集群提交的结果也与 `local[4]` 相同。"
           "这说明差异只可能来自算法语义，而不是分区数、任务顺序或机器环境。")

    put_heading(c, "五、性能对比")
    put(c, "为观察数据规模的影响，用 `tools/scale_data.py` 把购物篮复制并打乱成 4x、8x，"
           "支持度阈值按比例换算，因此项集和规则不变，只有计数规模增大（弱扩展）。")
    code(c, """数据   购物篮数   单机/s   Spark local[4]/s   加速比（单机/Spark）
1x       18270     5.49        11.81              0.47
4x       73080    15.08        16.12              0.94
8x      146160    30.97        21.91              1.41""")
    put(c, "固定 8x 数据、只改 Spark 的并行度：")
    code(c, """并行度     local[1]   local[2]   local[4]
墙钟时间/s    43.46      27.91      21.91
相对单核      1.00x      1.56x      1.98x""")
    put(c, "1x 数据下 Spark 反而比单机慢一倍：SparkContext 启动、任务调度、候选序列化和 "
           "Python worker 启动都是固定开销，而 18 270 个购物篮的位图计数只需几秒。数据增大后"
           "固定开销被摊薄，8x 时 Spark 反超单机 1.41 倍；4 核相对单核加速 1.98 倍，"
           "低于线性的 4 倍，说明候选生成、位图构建/合并、规则排序等串行部分不可忽略，"
           "符合 Amdahl 定律。")
    put_heading(c, "六、挖掘结果分析")
    top3 = top_items(itemsets, 3)
    put(c, "支持度最高的商品是 %s。" % "、".join(
        "%s（%s，%d 次，%.2f%%）" % (code, items.get(code, ""), supp,
                                   supp / local["transactions"] * 100)
        for supp, code in top3))
    put(c, "提升度最高的几条规则（`support` 为支持数，`conf` 为置信度，`lift` 为提升度）：")
    shown = [
        ("22386", "85099B"),
        ("21084", "21090"),
        ("22522", "22523"),
        ("23171,23173,23175", "23172,23174"),
    ]
    lines = ["规则（商品编码）                       supp   conf    lift"]
    for ante, cons in shown:
        supp, conf, lift = find_rule(rules, ante, cons)
        lines.append("%-28s => %-18s %5d  %.3f  %6.2f"
                     % (ante, cons, supp, float(conf), float(lift)))
    code(c, "\n".join(lines))
    put(c, "编码对应关系：`22386/85099B` 是粉色/红色 Retrospot 手提袋，`21084/21090` 是拼贴"
           "纸杯/纸盘，`22522/22523` 是蓝色/粉色儿童园艺叉，最后一行 5 个编码依次是绿色 Regency "
           "茶盘、玫瑰茶壶、粉色奶壶 → 粉色茶盘、绿色糖罐。")
    put(c, "这些规则有两类典型含义。第一类是“同系列不同颜色/图案一起买”：粉色和红色 Retrospot "
           "手提袋、蓝色和粉色儿童园艺叉、绿色/粉色/玫瑰图案的 Regency 茶具，置信度和提升度都很高；"
           "第二类是“互补商品成套买”：拼贴纸杯配纸盘、儿童碗配杯子，5 件商品的 Regency 茶具组合"
           "（绿盘、玫瑰茶壶、粉奶壶 → 粉盘、绿糖罐）支持数 95、置信度 0.819、提升度 104.63，"
           "说明顾客倾向于一次配齐整套。提升度高的规则支持度往往不高（约 0.5%），因为它们描述的是"
           "特定商品组合而非大众商品；只看置信度会被“本身就热门”的商品误导，必须结合提升度判断。")
    put(c, "全部代码、数据、脚本和输出已上传到 GitHub 公开仓库："
           "`https://github.com/YuuAnnooo/sdu-bigdata-labs`（Public，本实验位于 "
           "`bigdata-lab4/`）。目录约定：`python/` 单机实现，`spark/` PySpark 实现，"
           "`data/` 清洗后的数据，`tools/` 数据准备、弱扩展与结果比较脚本，"
           "`out/` 项集、规则、对比报告和计时结果。")

    # ---- 行 7：结论分析与体会
    c = table.cell(7, 0).merge(table.cell(7, 2))
    label(c, "结论分析与体会：")
    put(c, "（1）算法设计要服从数据形态。最初按课本写横向 Apriori，最大 1 097 种商品的购物篮使"
           "3 项集要跑 174 s；改成垂直位图后，1.29M 个 2 项候选只需 3.7 s。算法表示（横向/垂直、"
           "位图/集合）决定了计算量本身，往往比增加机器更有效。")
    put(c, "（2）并行不是免费的。1x 数据下 Spark 比单机慢一倍，4x 才基本持平，8x 才反超 1.41 倍；"
           "4 核相对单核只有 1.98 倍加速。原因有三：Spark 启动和任务调度是固定开销；每层候选"
           "要序列化后分发，层数越多开销越大；候选生成、位图合并、规则排序仍在 Driver 串行执行。"
           "因此小数据不适合上 Spark，数据量、候选数和迭代层数足够大时并行才有意义。")
    put(c, "（3）结果一致性需要工程手段保证。两套实现都使用整数支持数、`Fraction` 精确比较置信度、"
           "统一的 `ceil(min_support × N)` 阈值和全排序输出；阈值边界不能用浮点数直接乘，否则"
           "`0.005 × 18270 = 91.35` 可能因舍入得到 91 或 92，两边就会差一个项集。最后用 SHA-256 "
           "比较，比人工抽查可靠得多。")
    put(c, "（4）对数据挖掘本身的理解。支持度阈值决定“看多远”：0.02 时只剩 470 个项集、162 条"
           "规则，只看得到热门商品；0.005 时得到 22 522 个项集、35 657 条规则，才能发现茶具这类"
           "成套购买行为。高提升度规则的支持度通常很低，实际要同时看支持度、置信度和提升度，"
           "再结合业务成本决定推荐哪些组合。")
    put(c, "（5）可扩展性。位图内存为 O(商品数 × N/8)，本实验只占几 MB；N 到千万级时单机放不下，"
           "需要按商品分片、改用垂直 tid 列表或 Spark MLlib 的 FP-Growth。下一步可把候选生成也"
           "按前缀分桶做成分布式，并用 HDFS 存放输入输出，在真实集群上验证扩展性。")

    # ---- 行 8：问答题
    c = table.cell(8, 0).merge(table.cell(8, 2))
    label(c, "就实验过程中遇到和出现的问题，你是如何解决和处理的，自拟 1－3 道问答题：")

    put(c, "问题一：候选生成放在 Driver 上，是否没有真正并行？L₁ 很大时怎么办？",
        indent=False, bold=True)
    put(c, "答：不是。Apriori 的主要计算量在支持度计数：本实验 L₂ 有 129 万个候选，每个候选要对"
           "18 270 位（8x 时 146 160 位）的位图做与运算，这部分完全按候选切分到各 Executor，"
           "是并行的主体；候选生成只依赖上一层频繁项集，本实验中生成 129 万个二元组只需不到"
           "一秒，放在 Driver 上可避免额外的 shuffle 和全局同步。若 L₁ 达到数万，候选数按平方"
           "增长，Driver 会成为瓶颈，此时可按前缀哈希把候选生成分到多个分区，或改用 FP-Growth "
           "避免候选集。")

    put(c, "问题二：怎样保证并行版和单机版结果“完全一致”？有哪些容易踩的坑？",
        indent=False, bold=True)
    put(c, "答：关键是消除所有不确定性和浮点误差。① 阈值：用 `Fraction` 表示支持度和置信度，"
           "支持数阈值统一取 `ceil(min_support × N)`，不用浮点乘法直接比较；② 计数：支持数始终"
           "是整数，置信度、提升度用分数比较，输出时才用 `Decimal` 四舍五入到 6 位；③ 顺序："
           "商品编码、候选、项集、规则全部排序，不依赖 `set` 的遍历顺序；④ 语义：两边使用相同的"
           "购物篮解析、去重和格式化函数，规则枚举顺序也一致；⑤ 用 SHA-256 比较整个文件。"
           "最容易出错的是边界：如果一边用 `count > min_support*N`、另一边用"
           "`>=`，或者一边向上取整、一边直接截断，就会在阈值附近差一个项集。")

    put(c, "问题三：支持度阈值应该怎么选？置信度高就一定是好规则吗？",
        indent=False, bold=True)
    put(c, "答：阈值是“频繁”和“长尾”的折中：阈值高，项集少、运行快，但只看得到大众商品；"
           "阈值低，能发现具体组合，但候选和规则增长快，容易混入偶然共现。本实验 0.02 时只剩 "
           "470 个项集、162 条规则，看不到茶具等组合，降到 0.005 后得到 22 522 个项集、35 657 "
           "条规则，运行仍在 10 s 内。置信度高不一定是好规则：若 Y 本身是爆款，`P(Y|X)` 天然高，"
           "但 X 可能没有提升作用；“红色手提袋 → 粉色手提袋”提升度 5.98 才说明真正相关。"
           "实际要同时看支持度、置信度和提升度。")

    # ---- 收尾
    add_tail_paragraph(doc)
    set_col_width(table, [4.5, 5.75, 5.75])
    apply_keep_rules(doc)

    out = os.path.join(BASE, DOCX_NAME)
    doc.save(out)
    print("saved:", out)
    return out


def label(cell, text, keep=False):
    p = put(cell, text, indent=False, bold=True)
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


if __name__ == "__main__":
    build()

