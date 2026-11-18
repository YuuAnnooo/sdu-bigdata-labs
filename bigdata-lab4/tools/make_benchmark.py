#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把多次运行的 timing JSON 汇总成 out/benchmark.csv。

    python tools/make_benchmark.py

1x 数据是 18 270 个购物篮；x4 / x8 是用 tools/scale_data.py 复制打乱后的
弱扩展数据。所有运行使用相同的 min_support=0.005、min_confidence=0.5，
因此频繁项集和规则完全相同，只是支持计数按倍数放大。
"""
import csv
import json
import os

ROWS = [
    ("1x", 1, "单机 Python", "out/local_timing.json"),
    ("1x", 1, "Spark local[4]", "out/spark_timing.json"),
    ("1x", 1, "Spark standalone", "out/spark_standalone.json"),
    ("4x", 4, "单机 Python", "out/local_x4.json"),
    ("4x", 4, "Spark local[4]", "out/spark_x4.json"),
    ("8x", 8, "单机 Python", "out/local_x8.json"),
    ("8x", 8, "Spark local[1]", "out/spark_x8_c1.json"),
    ("8x", 8, "Spark local[2]", "out/spark_x8_c2.json"),
    ("8x", 8, "Spark local[4]", "out/spark_x8.json"),
    ("8x", 8, "Spark standalone", "out/spark_standalone_x8.json"),
]
FIELDS = ["scale", "transactions", "implementation", "load_s", "tidset_s",
          "l2_s", "l3_s", "l4_s", "l5plus_s", "rules_s", "compute_s",
          "wall_s", "itemsets", "rules", "speedup_vs_local", "speedup_vs_1core"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    data = []
    local_wall = {}
    core1_wall = None
    for scale, factor, impl, path in ROWS:
        if not os.path.exists(path):
            continue
        t = load(path)
        levels = t.get("level_seconds", {})
        wall = t.get("wall_seconds", t.get("total_seconds", 0.0))
        row = {
            "scale": scale,
            "transactions": t.get("transactions"),
            "implementation": impl,
            "load_s": t.get("load_seconds", 0.0),
            "tidset_s": t.get("tidset_seconds", 0.0),
            "l2_s": levels.get("2", 0.0),
            "l3_s": levels.get("3", 0.0),
            "l4_s": levels.get("4", 0.0),
            "l5plus_s": sum(v for k, v in levels.items() if int(k) >= 5),
            "rules_s": t.get("rules_seconds", 0.0),
            "compute_s": t.get("compute_seconds", t.get("total_seconds", 0.0)),
            "wall_s": wall,
            "itemsets": t.get("itemsets"),
            "rules": t.get("rules"),
            "speedup_vs_local": "",
            "speedup_vs_1core": "",
        }
        if impl == "单机 Python":
            local_wall[scale] = wall
        row["_scale"] = scale
        if impl == "Spark local[1]" and scale == "8x":
            core1_wall = wall
        data.append(row)

    for row in data:
        if row["implementation"].startswith("Spark") and row["_scale"] in local_wall:
            row["speedup_vs_local"] = "%.2f" % (local_wall[row["_scale"]] / row["wall_s"])
        if core1_wall and row["_scale"] == "8x" and row["implementation"].startswith("Spark"):
            row["speedup_vs_1core"] = "%.2f" % (core1_wall / row["wall_s"])

    os.makedirs("out", exist_ok=True)
    with open("out/benchmark.csv", "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in data:
            w.writerow({k: row[k] for k in FIELDS})

    print("写出 out/benchmark.csv")
    for row in data:
        print("  %-3s %-17s wall=%7.3fs compute=%7.3fs speedup_local=%-5s speedup_1core=%s"
              % (row["scale"], row["implementation"], row["wall_s"], row["compute_s"],
                 row["speedup_vs_local"], row["speedup_vs_1core"]))


if __name__ == "__main__":
    main()
