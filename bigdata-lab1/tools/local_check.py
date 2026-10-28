#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地校验脚本：在未启动 Hadoop 时，用纯 Python 复现三个 MapReduce 程序的
map -> shuffle/sort -> reduce 语义，用于提前确认输出结果是否正确。
运行： python3 tools/local_check.py
"""
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(BASE, "input")


def read(name):
    with open(os.path.join(IN, name), encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f if ln.strip()]


# ---------------------------------------------------------------- 1. 合并去重
def merge_dedup(files):
    pairs = []
    for name in files:
        for line in read(name):
            key = " ".join(line.split())          # 归一化空白，避免 A/B 空格数不同导致漏去重
            pairs.append((key, None))
    grouped = defaultdict(list)                    # shuffle + sort
    for k, v in pairs:
        grouped[k].append(v)
    return sorted(grouped.keys())                  # reduce：每个 key 只输出一次


# ---------------------------------------------------------------- 2. 排序
def sort_ints(files):
    nums = []
    for name in files:
        for line in read(name):
            nums.append(int(line.strip()))
    grouped = defaultdict(list)                    # shuffle：按 key 排序并分组
    for n in nums:
        grouped[n].append(None)
    out, rank = [], 0
    for key in sorted(grouped.keys()):
        rank += 1
        out.append(f"{rank}\t{key}")
    return out


# ---------------------------------------------------------------- 3. 祖孙关系
def grand_child(files):
    pairs = []
    for name in files:
        for line in read(name):
            parts = line.split()
            if len(parts) != 2:
                continue
            child, parent = parts[0], parts[1]
            pairs.append((parent, "1:" + child))   # 该结点作为父辈
            pairs.append((child, "2:" + parent))   # 该结点作为子辈
    grouped = defaultdict(list)
    for k, v in pairs:
        grouped[k].append(v)
    out = []
    for key in sorted(grouped.keys()):
        vals = sorted(grouped[key])
        kids = [v[2:] for v in vals if v.startswith("1:")]
        parents = [v[2:] for v in vals if v.startswith("2:")]
        for c in kids:
            for p in parents:
                out.append(f"{c}\t{p}")
    return out


def show(title, lines):
    print("=" * 60)
    print(title)
    print("=" * 60)
    for ln in lines:
        print(ln)
    print()


if __name__ == "__main__":
    c = merge_dedup(["A.txt", "B.txt"])
    s = sort_ints(["int1.txt", "int2.txt", "int3.txt"])
    g = grand_child(["child_parent.txt"])

    show("C = MergeDedup(A, B)", c)
    show("Sorted = Sort(int1, int2, int3)", s)
    show("grandchild/grandparent = GrandChild(child_parent)", g)

    # 同时把结果写入 out/，与 Hadoop 实际输出（part-r-00000）格式保持一致
    if "--write" in sys.argv:
        outdir = os.path.join(BASE, "out")
        os.makedirs(outdir, exist_ok=True)
        for name, lines in (("C.txt", c), ("sorted.txt", s), ("grandchild.txt", g)):
            with open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines) + "\n")
            print("written out/" + name)
