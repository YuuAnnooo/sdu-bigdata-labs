#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单机（非并行）Apriori 频繁项集与关联规则挖掘。

算法要点
    * 逐层搜索：由 k-1 频繁项集连接、剪枝得到 k 候选项集；
    * 支持度计数用“垂直”位图：第 i 位为 1 表示该商品出现在第 i 个购物篮，
      候选项集的支持数 = 各商品位图按位与之后 1 的个数；
    * 全部用整数计数，规则置信度用分数比较，输出按字典序排序，
      因此结果与 Spark 并行版逐字节一致。

用法
    python python/apriori_local.py \
        --input data/transactions.tsv \
        --min-support 0.02 --min-confidence 0.4 \
        --out-prefix out/local --timing out/local_timing.json
"""
import argparse
import itertools
import json
import os
import sys
import time
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from math import ceil

D6 = Decimal("0.000001")


def load_transactions(path):
    """每行一个购物篮，返回 tuple 列表（去重、排序）。"""
    transactions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            items = tuple(sorted(set(x for x in line.split("\t") if x)))
            if len(items) >= 2:
                transactions.append(items)
    return transactions


def build_masks(transactions):
    """item -> Python 大整数位图，第 tid 位表示该购物篮包含此商品。"""
    masks = {}
    for tid, items in enumerate(transactions):
        bit = 1 << tid
        for item in items:
            masks[item] = masks.get(item, 0) | bit
    return masks


def support_of(itemset, masks):
    m = masks[itemset[0]]
    for item in itemset[1:]:
        m &= masks[item]
        if not m:
            return 0
    return m.bit_count()


def apriori_gen(prev, k):
    """由 k-1 频繁项集生成 k 候选项集（连接 + 剪枝）。

    prev 为按字典序排好的 tuple 列表，每个 tuple 内部也有序。
    两条前缀相同的项集连接后，检查全部 k-1 子集是否频繁。
    """
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


def mine(transactions, min_support, min_confidence):
    n = len(transactions)
    min_count = ceil(min_support * n)
    t0 = time.perf_counter()
    masks = build_masks(transactions)
    tidset_seconds = time.perf_counter() - t0

    itemsets = []                       # [(tuple, support_count), ...]
    support_map = {}
    level_sizes = {}
    level_seconds = {}

    # L1
    level = []
    for item in sorted(masks):
        cnt = masks[item].bit_count()
        if cnt >= min_count:
            level.append(((item,), cnt))
    itemsets.extend(level)
    support_map.update(level)
    level_sizes[1] = len(level)

    k = 2
    while level:
        t0 = time.perf_counter()
        candidates = apriori_gen([items for items, _ in level], k)
        nxt = []
        for cand in candidates:
            cnt = support_of(cand, masks)
            if cnt >= min_count:
                nxt.append((cand, cnt))
        itemsets.extend(nxt)
        support_map.update(nxt)
        level_sizes[k] = len(nxt)
        level_seconds[str(k)] = round(time.perf_counter() - t0, 4)
        print("  第 %d 层：候选 %d，频繁 %d（%.3fs）"
              % (k, len(candidates), len(nxt), level_seconds[str(k)]))
        level = nxt
        k += 1

    # 关联规则：X -> Y，conf = supp(XY) / supp(X)，lift = supp(XY)*N/(supp(X)*supp(Y))
    t0 = time.perf_counter()
    rules = []
    for itemset, supp in itemsets:
        if len(itemset) < 2:
            continue
        for r in range(1, len(itemset)):
            for ante in itertools.combinations(itemset, r):
                cons = tuple(x for x in itemset if x not in ante)
                conf = Fraction(supp, support_map[ante])
                if conf < min_confidence:
                    continue
                lift = Fraction(supp * n, support_map[ante] * support_map[cons])
                rules.append((ante, cons, supp, conf, lift))
    rules.sort(key=lambda x: (x[0], x[1]))
    rules_seconds = time.perf_counter() - t0
    print("  规则：%d 条（%.3fs）" % (len(rules), rules_seconds))

    return {
        "n": n,
        "min_count": min_count,
        "itemsets": itemsets,
        "rules": rules,
        "level_sizes": level_sizes,
        "level_seconds": level_seconds,
        "tidset_seconds": tidset_seconds,
        "rules_seconds": rules_seconds,
    }


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
    ap.add_argument("--min-support", type=float, default=0.02, help="最小支持度（0~1）")
    ap.add_argument("--min-confidence", default="0.4", help="最小置信度（0~1）")
    ap.add_argument("--out-prefix", default="out/local", help="输出文件前缀")
    ap.add_argument("--timing", default="out/local_timing.json")
    args = ap.parse_args()

    min_support = Fraction(str(args.min_support))
    min_confidence = Fraction(str(args.min_confidence))
    started = time.perf_counter()

    t0 = time.perf_counter()
    transactions = load_transactions(args.input)
    load_seconds = time.perf_counter() - t0
    if not transactions:
        sys.exit("空输入：%s" % args.input)
    print("购物篮 %d 个，商品 %d 种" % (len(transactions), len({x for t in transactions for x in t})))

    t0 = time.perf_counter()
    result = mine(transactions, min_support, min_confidence)
    mine_seconds = time.perf_counter() - t0

    os.makedirs(os.path.dirname(os.path.abspath(args.out_prefix)), exist_ok=True)
    write_itemsets(args.out_prefix + "_itemsets.tsv", result["n"], float(min_support),
                   float(min_confidence), result["min_count"], result["itemsets"])
    write_rules(args.out_prefix + "_rules.tsv", result["n"], result["rules"])

    timing = {
        "implementation": "local",
        "transactions": result["n"],
        "items": len({x for t in transactions for x in t}),
        "min_support": float(min_support),
        "min_support_count": result["min_count"],
        "min_confidence": float(min_confidence),
        "load_seconds": round(load_seconds, 4),
        "tidset_seconds": round(result["tidset_seconds"], 4),
        "level_seconds": result["level_seconds"],
        "rules_seconds": round(result["rules_seconds"], 4),
        "mine_seconds": round(mine_seconds, 4),
        "compute_seconds": round(load_seconds + mine_seconds, 4),
        "total_seconds": round(time.perf_counter() - started, 4),
        "itemsets": len(result["itemsets"]),
        "rules": len(result["rules"]),
        "level_itemsets": {str(k): v for k, v in result["level_sizes"].items()},
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.timing)), exist_ok=True)
    with open(args.timing, "w", encoding="utf-8", newline="\n") as f:
        json.dump(timing, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("频繁项集 %d 个，关联规则 %d 条" % (timing["itemsets"], timing["rules"]))
    print("总耗时 %.3fs，写出 %s_itemsets.tsv / %s_rules.tsv"
          % (timing["total_seconds"], args.out_prefix, args.out_prefix))


if __name__ == "__main__":
    main()
