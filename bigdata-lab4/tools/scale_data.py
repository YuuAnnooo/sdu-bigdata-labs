#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成“弱扩展”实验数据：把购物篮复制 factor 份并打乱顺序。

仅用于观察数据规模对单机/Spark 耗时的影响。复制后支持度比例不变，
因此在相同 min_support 下频繁项集与关联规则完全相同，只是支持计数
按 factor 倍增长，适合做固定结果规模下的并行加速比实验。

    python tools/scale_data.py --factor 4 --out data/bench_x4.tsv
"""
import argparse
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/transactions.tsv")
    ap.add_argument("--factor", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip()]
    if not lines:
        raise SystemExit("空输入")

    out = args.out or ("data/bench_x%d.tsv" % args.factor)
    data = lines * args.factor
    random.Random(args.seed).shuffle(data)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for line in data:
            f.write(line + "\n")
    print("%s: %d 个购物篮 -> %s: %d 个购物篮"
          % (args.input, len(lines), out, len(data)))


if __name__ == "__main__":
    main()
