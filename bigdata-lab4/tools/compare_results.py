#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比较单机版与 Spark 版的输出，确认逐字节一致。

    python tools/compare_results.py --local out/local --spark out/spark --out out/compare.txt

除了 SHA-256 与行数，还会统计每一层的频繁项集数、规则数，并读取两边的
timing JSON 生成对比表。退出码 0 表示完全一致，1 表示有差异。
"""
import argparse
import hashlib
import json
import os
import sys
from collections import Counter


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f if not ln.startswith("#")]


def first_diff(a_path, b_path):
    with open(a_path, encoding="utf-8") as fa, open(b_path, encoding="utf-8") as fb:
        for i, (a, b) in enumerate(zip(fa, fb), 1):
            if a != b:
                return i, a.rstrip("\n"), b.rstrip("\n")
    return None


def level_counts(rows):
    c = Counter()
    for row in rows:
        c[int(row.split("\t", 1)[0])] += 1
    return dict(sorted(c.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", default="out/local")
    ap.add_argument("--spark", default="out/spark")
    ap.add_argument("--out", default="out/compare.txt")
    args = ap.parse_args()

    itemset_a = args.local + "_itemsets.tsv"
    itemset_b = args.spark + "_itemsets.tsv"
    rule_a = args.local + "_rules.tsv"
    rule_b = args.spark + "_rules.tsv"

    timing = {}
    for name, path in (("local", args.local + "_timing.json"),
                       ("spark", args.spark + "_timing.json")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                timing[name] = json.load(f)

    report = []
    ok = True

    for title, pa, pb in (("频繁项集", itemset_a, itemset_b), ("关联规则", rule_a, rule_b)):
        ha, hb = sha256(pa), sha256(pb)
        ra, rb = read_rows(pa), read_rows(pb)
        same = ha == hb and len(ra) == len(rb)
        ok = ok and same
        report.append("[%s] %s" % (title, "一致" if same else "不一致"))
        report.append("  单机: %6d 行  sha256=%s" % (len(ra), ha))
        report.append("  Spark: %6d 行  sha256=%s" % (len(rb), hb))
        if not same:
            diff = first_diff(pa, pb)
            if diff:
                report.append("  首个差异行 %d:\n    单机: %s\n    Spark: %s" % diff)
        if title == "频繁项集":
            report.append("  各层项集数: %s" % level_counts(ra))

    if timing:
        report.append("")
        report.append("耗时（秒）")
        report.append("  实现      装载    位图    L2      L3      L4      L5+    规则    合计")
        for name in ("local", "spark"):
            if name not in timing:
                continue
            t = timing[name]
            levels = t.get("level_seconds", {})
            l2 = levels.get("2", 0.0)
            l3 = levels.get("3", 0.0)
            l4 = levels.get("4", 0.0)
            l5 = sum(v for k, v in levels.items() if int(k) >= 5)
            total = t.get("compute_seconds", t.get("total_seconds", 0.0))
            report.append("  %-9s %6.2f  %6.2f  %6.2f  %6.2f  %6.2f  %6.2f  %6.2f  %6.2f"
                          % (name, t.get("load_seconds", 0.0), t.get("tidset_seconds", 0.0),
                             l2, l3, l4, l5, t.get("rules_seconds", 0.0), total))
        if "local" in timing and "spark" in timing:
            lt = timing["local"].get("total_seconds", 0.0)
            st = timing["spark"].get("compute_seconds", 0.0)
            if lt:
                report.append("  加速比（单机/Spark 计算）= %.2fx" % (lt / st))

    text = "\n".join(report)
    print(text)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
