#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apriori 频繁项集与关联规则的 PySpark 并行实现。

并行策略
    1. Driver 端完成“连接 + 剪枝”的候选生成：候选只与上一层频繁项集有关，
       数量远小于事务数，且层与层之间有严格依赖，放在 Driver 上最简单；
    2. 真正耗时的是支持度计数：把每个商品映射成“事务位图”，广播到各 Executor，
       候选项集按分区下发，各任务用按位与 + bit_count 求支持数；
    3. 规则生成同样用 flatMap 分发到各分区，最后在 Driver 端排序输出。

    位图计数避免了“每个购物篮枚举 C(n,k) 个子集”的爆炸问题：本数据集中
    最大的购物篮有 1097 种商品，横向枚举 3 项集需要两亿次组合，而位图
    只需要 3 次按位与。单机版使用完全相同的计数方式，保证结果逐字节一致。

用法
    spark-submit --master local[4] spark/apriori_spark.py \
        --input data/transactions.tsv \
        --min-support 0.02 --min-confidence 0.4 \
        --out-prefix out/spark --timing out/spark_timing.json
"""
import argparse
import itertools
import json
import operator
import os
import sys
import time
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from math import ceil

from pyspark import SparkConf, SparkContext

D6 = Decimal("0.000001")


def parse_line(line):
    line = line.strip()
    if not line:
        return None
    items = tuple(sorted(set(x for x in line.split("\t") if x)))
    if len(items) < 2:
        return None
    return items


def build_partition_masks(index, part, offsets):
    """分区内先用局部事务号建位图，再整体左移 base 位，避免 Driver 串行处理全部事务。"""
    base = offsets[index]
    masks = {}
    for local_tid, items in enumerate(part):
        bit = 1 << local_tid
        for item in items:
            masks[item] = masks.get(item, 0) | bit
    return [(item, mask << base) for item, mask in masks.items()]


def support_of(itemset, masks):
    m = masks[itemset[0]]
    for item in itemset[1:]:
        m &= masks[item]
        if not m:
            return 0
    return m.bit_count()


def apriori_gen(prev, k):
    groups = defaultdict(list)
    for itemset in prev:
        groups[itemset[:-1]].append(itemset)
    prev_set = set(prev)
    candidates = []
    for prefix in sorted(groups):
        group = sorted(groups[prefix])
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                cand = group[i] + (group[j][-1],)
                if all(cand[:m] + cand[m + 1:] in prev_set for m in range(k)):
                    candidates.append(cand)
    candidates.sort()
    return candidates


def fmt_ratio(num, den):
    return str((Decimal(num) / Decimal(den)).quantize(D6, rounding=ROUND_HALF_UP))


def fmt_fraction(value):
    return str((Decimal(value.numerator) / Decimal(value.denominator))
               .quantize(D6, rounding=ROUND_HALF_UP))


def count_partition(candidates, masks):
    return [(cand, support_of(cand, masks)) for cand in candidates]


def rules_for_itemset(itemset, supp, support_map, n, min_conf):
    out = []
    if len(itemset) < 2:
        return out
    for r in range(1, len(itemset)):
        for ante in itertools.combinations(itemset, r):
            cons = tuple(x for x in itemset if x not in ante)
            conf = Fraction(supp, support_map[ante])
            if conf < min_conf:
                continue
            lift = Fraction(supp * n, support_map[ante] * support_map[cons])
            out.append((ante, cons, supp, conf, lift))
    return out


def rules_partition(part, support_map, n, min_conf):
    out = []
    for itemset, supp in part:
        out.extend(rules_for_itemset(itemset, supp, support_map, n, min_conf))
    return out


def write_itemsets(path, n, min_support, min_confidence, min_count, itemsets):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Apriori frequent itemsets\n")
        f.write("# transactions=%d min_support=%.6f min_support_count=%d min_confidence=%.6f\n"
                % (n, min_support, min_count, min_confidence))
        f.write("# size\titems\tsupport_count\tsupport_ratio\n")
        for itemset, supp in itemsets:
            f.write("%d\t%s\t%d\t%s\n"
                    % (len(itemset), ",".join(itemset), supp, fmt_ratio(supp, n)))


def write_rules(path, n, rules):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Apriori association rules\n")
        f.write("# antecedent => consequent\tsupport_count\tsupport_ratio\tconfidence\tlift\n")
        for ante, cons, supp, conf, lift in rules:
            f.write("%s => %s\t%d\t%s\t%s\t%s\n" % (
                ",".join(ante), ",".join(cons), supp, fmt_ratio(supp, n),
                fmt_fraction(conf), fmt_fraction(lift)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/transactions.tsv")
    ap.add_argument("--min-support", type=float, default=0.02)
    ap.add_argument("--min-confidence", default="0.4")
    ap.add_argument("--out-prefix", default="out/spark")
    ap.add_argument("--timing", default="out/spark_timing.json")
    ap.add_argument("--master", default=None, help="如 local[4]；不填则用 spark-submit 的参数")
    ap.add_argument("--slices", type=int, default=0, help="支持度计数的分区数，0 表示默认并行度")
    ap.add_argument("--rule-mode", choices=("auto", "spark", "driver"), default="auto",
                    help="规则生成方式；auto 表示项集多时并行、少时在 Driver 端生成")
    args = ap.parse_args()

    wall_start = time.perf_counter()
    min_support = Fraction(str(args.min_support))
    min_confidence = Fraction(str(args.min_confidence))

    conf = SparkConf().setAppName("Apriori-PySpark")
    if args.master:
        conf = conf.setMaster(args.master)
    sc = SparkContext(conf=conf)
    sc.setLogLevel("WARN")
    slices = args.slices or max(2, sc.defaultParallelism)

    try:
        t0 = time.perf_counter()
        transactions = (sc.textFile(args.input)
                        .map(parse_line)
                        .filter(lambda x: x is not None)
                        .repartition(slices)
                        .cache())
        n = transactions.count()
        load_seconds = time.perf_counter() - t0
        if n == 0:
            sys.exit("空输入：%s" % args.input)
        print("购物篮 %d 个，分区 %d，并行度 %d" % (n, transactions.getNumPartitions(), slices))

        # 每个分区并行构造局部位图，再按分区偏移拼成全局位图
        t0 = time.perf_counter()
        sizes = transactions.mapPartitions(lambda it: [sum(1 for _ in it)]).collect()
        offsets = [0]
        for size in sizes:
            offsets.append(offsets[-1] + size)
        masks = (transactions.mapPartitionsWithIndex(
                     lambda i, it: build_partition_masks(i, it, offsets))
                 .reduceByKey(operator.or_)
                 .collectAsMap())
        tidset_seconds = time.perf_counter() - t0
        print("商品 %d 种，位图构造 %.3fs" % (len(masks), tidset_seconds))

        min_count = ceil(min_support * n)
        b_masks = sc.broadcast(masks)

        itemsets = []
        support_map = {}
        level = []
        for item in sorted(masks):
            cnt = masks[item].bit_count()
            if cnt >= min_count:
                level.append(((item,), cnt))
        itemsets.extend(level)
        support_map.update(level)
        level_sizes = {1: len(level)}

        level_seconds = {}
        k = 2
        while level:
            t0 = time.perf_counter()
            candidates = apriori_gen([items for items, _ in level], k)
            if not candidates:
                level_seconds[str(k)] = round(time.perf_counter() - t0, 4)
                level_sizes[k] = 0
                print("  第 %d 层：候选 0，频繁 0" % k)
                break
            counted = (sc.parallelize(candidates, slices)
                       .mapPartitions(lambda part: count_partition(part, b_masks.value))
                       .collect())
            nxt = sorted([(cand, cnt) for cand, cnt in counted if cnt >= min_count])
            level_seconds[str(k)] = round(time.perf_counter() - t0, 4)
            itemsets.extend(nxt)
            support_map.update(nxt)
            level_sizes[k] = len(nxt)
            print("  第 %d 层：候选 %d，频繁 %d（%.3fs）"
                  % (k, len(candidates), len(nxt), level_seconds[str(k)]))
            level = nxt
            k += 1

        t0 = time.perf_counter()
        use_spark_rules = (args.rule_mode == "spark"
                           or (args.rule_mode == "auto" and len(itemsets) >= 2000))
        if use_spark_rules:
            b_support = sc.broadcast(support_map)
            b_conf = sc.broadcast(min_confidence)
            rules = (sc.parallelize(itemsets, slices)
                     .mapPartitions(lambda part: rules_partition(
                         part, b_support.value, n, b_conf.value))
                     .collect())
        else:
            rules = []
            for itemset, supp in itemsets:
                rules.extend(rules_for_itemset(itemset, supp, support_map, n, min_confidence))
        rules.sort(key=lambda x: (x[0], x[1]))
        rules_seconds = time.perf_counter() - t0
        print("  规则：%d 条（%.3fs，%s）"
              % (len(rules), rules_seconds, "Spark" if use_spark_rules else "Driver"))

        os.makedirs(os.path.dirname(os.path.abspath(args.out_prefix)), exist_ok=True)
        write_itemsets(args.out_prefix + "_itemsets.tsv", n, float(min_support),
                       float(min_confidence), min_count, itemsets)
        write_rules(args.out_prefix + "_rules.tsv", n, rules)

        timing = {
            "implementation": "spark",
            "master": sc.master,
            "transactions": n,
            "items": len(masks),
            "partitions": transactions.getNumPartitions(),
            "slices": slices,
            "rule_mode": "spark" if use_spark_rules else "driver",
            "min_support": float(min_support),
            "min_support_count": min_count,
            "min_confidence": float(min_confidence),
            "load_seconds": round(load_seconds, 4),
            "tidset_seconds": round(tidset_seconds, 4),
            "level_seconds": level_seconds,
            "rules_seconds": round(rules_seconds, 4),
            "compute_seconds": round(load_seconds + tidset_seconds
                                     + sum(level_seconds.values()) + rules_seconds, 4),
            "wall_seconds": round(time.perf_counter() - wall_start, 4),
            "itemsets": len(itemsets),
            "rules": len(rules),
            "level_itemsets": {str(k): v for k, v in level_sizes.items()},
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.timing)), exist_ok=True)
        with open(args.timing, "w", encoding="utf-8", newline="\n") as f:
            json.dump(timing, f, ensure_ascii=False, indent=2)
            f.write("\n")

        print("频繁项集 %d 个，关联规则 %d 条" % (len(itemsets), len(rules)))
        print("计算 %.3fs，总墙钟 %.3fs" % (timing["compute_seconds"], timing["wall_seconds"]))
    finally:
        sc.stop()


if __name__ == "__main__":
    main()
