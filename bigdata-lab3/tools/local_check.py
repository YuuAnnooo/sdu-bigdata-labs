#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地校验脚本：不启动 Hadoop / Spark，用纯 Python 分别复现
PageRank 的 MapReduce 语义和 Spark 语义，确认两套实现的输出逐字节一致，
并把结果写到 out/ 目录。

    MR 版本：map 发贡献 -> 按 key 排序分组（shuffle）-> reduce 累加套公式
    Spark 版本：links join ranks -> reduceByKey -> mapValues 套公式

运行： python3 tools/local_check.py [--write]
"""
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "pagerank.txt")
OUT = os.path.join(BASE, "out")

DAMPING = 0.85
ITERATIONS = 10


def read_graph(path=DATA):
    """返回 (nodes, links)：nodes 为页面列表，links 为 页面 -> 出链列表"""
    nodes, links = [], {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if "\t" in line:
                name, rhs = line.split("\t", 1)
                targets = [t.strip() for t in rhs.split(",") if t.strip()]
            else:
                name, targets = line, []
            nodes.append(name.strip())
            links[name.strip()] = targets
    return nodes, links


# ------------------------------------------------------------------ 语义一：MapReduce
def pagerank_mapreduce(nodes, links, iterations=ITERATIONS):
    n = len(nodes)
    state = {p: 1.0 / n for p in nodes}
    trace = []
    for _ in range(iterations):
        # map 端：每个页面自留一个 0 贡献 + 把自己的 PR 按出链数分出去
        emitted = []
        for page in nodes:
            pr = state[page]
            targets = links[page]
            emitted.append((page, 0.0))
            if not targets:                       # 悬挂页面：PR 均分给所有页面
                share = pr / n
                for p in nodes:
                    emitted.append((p, share))
            else:
                share = pr / len(targets)
                for t in targets:
                    emitted.append((t, share))
        # shuffle：按 key 排序并分组
        grouped = defaultdict(list)
        for k, v in emitted:
            grouped[k].append(v)
        # reduce 端：累加贡献后套公式
        state = {}
        for k in sorted(grouped.keys()):
            total = sum(grouped[k])
            state[k] = (1 - DAMPING) / n + DAMPING * total
        trace.append(dict(state))
    return state, trace


# ------------------------------------------------------------------ 语义二：Spark
def pagerank_spark(nodes, links, iterations=ITERATIONS):
    n = len(nodes)
    ranks = {p: 1.0 / n for p in nodes}
    for _ in range(iterations):
        # links.join(ranks).values().flatMap(...)
        contrib = defaultdict(float)
        for page in nodes:
            targets = links[page]
            pr = ranks[page]
            if not targets:
                continue
            share = pr / len(targets)
            for t in targets:
                contrib[t] += share            # 这里相当于 reduceByKey
        # links.join(ranks).filter(悬挂).values().map(_._2).sum()
        dangling = sum(ranks[p] for p in nodes if not links[p])
        teleport = (1 - DAMPING) / n
        dangling_share = DAMPING * dangling / n
        # links.keys().map(0.0).union(contrib).reduceByKey(...) -> mapValues(公式)
        ranks = {p: teleport + dangling_share + DAMPING * contrib.get(p, 0.0) for p in nodes}
    return ranks


def format_result(ranks):
    """按 PR 降序（同值按页面名升序）输出 (网页,PR值)，PR 保留 10 位小数"""
    items = sorted(ranks.items(), key=lambda kv: (-kv[1], kv[0]))
    return ["(%s,%.10f)" % (name, pr) for name, pr in items]


def main():
    nodes, links = read_graph()
    print("数据集: %d 个页面, %d 条链接, %d 个悬挂页面"
          % (len(nodes), sum(len(v) for v in links.values()),
             sum(1 for v in links.values() if not v)))

    mr_ranks, trace = pagerank_mapreduce(nodes, links)
    sp_ranks = pagerank_spark(nodes, links)

    # 两种实现必须完全一致
    diff = max(abs(mr_ranks[p] - sp_ranks[p]) for p in nodes)
    print("MapReduce 与 Spark 两套实现的最大差异: %.3e" % diff)
    assert diff < 1e-12, "两套实现结果不一致"

    print("第 0 轮 PR 总和 = %.10f" % 1.0)
    for i, st in enumerate(trace, 1):
        print("第 %2d 轮 PR 总和 = %.10f  最大值 = %.10f (%s)"
              % (i, sum(st.values()), max(st.values()),
                 max(st, key=lambda k: st[k])))

    lines = format_result(mr_ranks)
    print("\n".join(lines))

    if "--write" in sys.argv:
        os.makedirs(OUT, exist_ok=True)
        lines = format_result(mr_ranks)
        lines_sp = format_result(sp_ranks)
        assert lines == lines_sp, "MR 与 Spark 的格式化输出不一致"
        with open(os.path.join(OUT, "pagerank_result.txt"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        # 两套语义各自的输出，内容相同，分别对应 Hadoop 与 Spark 作业的结果文件
        for name in ("pagerank_mr_result.txt", "pagerank_spark_result.txt"):
            with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines) + "\n")
        with open(os.path.join(OUT, "top10.txt"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines[:10]) + "\n")
        # 收敛过程：每轮每个页面的 PR，便于在报告中分析迭代效果
        with open(os.path.join(OUT, "pr_trace.csv"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("iteration," + ",".join(nodes) + "\n")
            for i, st in enumerate(trace, 1):
                f.write("%d," % i + ",".join("%.10f" % st[p] for p in nodes) + "\n")
        print("\n已写入 out/pagerank_result.txt、out/top10.txt、out/pr_trace.csv")


if __name__ == "__main__":
    main()
