#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PageRank 的 PySpark 实现（与 Java 版本算法、输出完全一致）。

用法：
    spark-submit spark/pagerank_spark.py <输入路径> [迭代次数]

输入每行： 网页 \t 出链1,出链2,...      （出链为空表示悬挂页面）
输出每行： (网页,PR值)   PR 保留 10 位小数，按 PR 从大到小排列
"""
import sys

from pyspark import SparkConf, SparkContext

DAMPING = 0.85


def parse(line):
    """网页 \t 出链集合  ->  (网页, [出链...])"""
    s = line.strip()
    if not s:
        return None
    if "\t" in s:
        name, rhs = s.split("\t", 1)
        links = [t.strip() for t in rhs.split(",") if t.strip()]
    else:
        name, links = s, []
    return name, links


def main():
    if len(sys.argv) < 2:
        print("用法: spark-submit spark/pagerank_spark.py <输入路径> [迭代次数]")
        sys.exit(2)
    path = sys.argv[1]
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    sc = SparkContext(conf=SparkConf().setAppName("PageRank-PySpark"))
    links = (sc.textFile(path)
             .map(parse)
             .filter(lambda x: x is not None)
             .cache())
    n = links.count()
    teleport = (1.0 - DAMPING) / n

    ranks = links.mapValues(lambda _: 1.0 / n)

    for i in range(1, iterations + 1):
        # (1) 每个页面把自己的 PR 平均分给它的出链
        contrib = links.join(ranks).values().flatMap(
            lambda kv: [(t, kv[1] / len(kv[0])) for t in kv[0]])
        # (2) 悬挂页面没有出链，其 PR 均分给所有页面
        dangling = links.join(ranks).filter(lambda kv: not kv[1][0]).values() \
                       .map(lambda kv: kv[1]).sum()
        # (3) 没有入链的页面补 0，保证结果中每个页面都在
        sums = (links.keys().map(lambda k: (k, 0.0))
                .union(contrib)
                .reduceByKey(lambda a, b: a + b))
        ranks = sums.mapValues(
            lambda s: teleport + DAMPING * dangling / n + DAMPING * s).cache()
        tips = ranks.count()
        print("[PageRank] 第 %d 轮完成, 页面数 = %d, 悬挂页面质量 = %.10f"
              % (i, tips, dangling))

    # 排序输出 (网页,PR值)
    out = (ranks.map(lambda kv: (kv[1], kv[0]))
                .sortByKey(ascending=False)
                .map(lambda kv: "(%s,%.10f)" % (kv[1], kv[0]))
                .collect())

    text = "\n".join(out)
    print(text)
    sc.parallelize(out).coalesce(1).saveAsTextFile(path + "_pagerank_spark")
    sc.stop()


if __name__ == "__main__":
    main()
