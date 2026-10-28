#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成实验数据集 data/pagerank.txt。

数据集是围绕“大数据 / 搜索引擎”主题人工构建的网页链接图，共 25 个页面，
其中 hadoop_tutorial_pdf 是一个只有入链、没有出链的“悬挂页面”（dangling node），
用来检验算法对漏出概率的处理。

文件格式（与实验要求一致）：
    网页 \t 该网页链接到的网页集合（英文逗号分隔）
悬挂页面写成“网页 + 制表符 + 空”的形式。

运行： python3 tools/gen_dataset.py
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "pagerank.txt")

# 主题 → 出链
GRAPH = [
    ("Big_data", ["Apache_Hadoop", "MapReduce", "Apache_Spark", "NoSQL",
                  "Machine_learning", "Data_mining", "Cloud_computing", "Database"]),
    ("Apache_Hadoop", ["HDFS", "MapReduce", "YARN", "HBase", "Hive",
                       "Apache_ZooKeeper", "hadoop_tutorial_pdf"]),
    ("MapReduce", ["Apache_Hadoop", "Distributed_computing", "Apache_Spark"]),
    ("Apache_Spark", ["MapReduce", "Apache_Hadoop", "Machine_learning",
                      "Python_(programming_language)"]),
    ("HBase", ["NoSQL", "Apache_Hadoop", "HDFS"]),
    ("HDFS", ["Apache_Hadoop", "Distributed_computing", "Computer_cluster"]),
    ("Hive", ["Data_warehouse", "Apache_Hadoop", "MapReduce"]),
    ("NoSQL", ["Database", "Big_data", "HBase"]),
    ("Distributed_computing", ["Computer_cluster", "Cloud_computing", "MapReduce"]),
    ("Cloud_computing", ["Distributed_computing", "Big_data", "Apache_Hadoop"]),
    ("Machine_learning", ["Data_mining", "Statistics", "Python_(programming_language)",
                          "Big_data"]),
    ("Data_mining", ["Machine_learning", "Statistics", "Database", "Big_data"]),
    ("Database", ["Data_warehouse", "NoSQL"]),
    ("Google", ["Search_engine", "PageRank", "Big_data", "MapReduce"]),
    ("PageRank", ["Search_engine", "Inverted_index", "Google", "Information_retrieval"]),
    ("Search_engine", ["Inverted_index", "Information_retrieval", "PageRank", "Google"]),
    ("Inverted_index", ["Information_retrieval", "Search_engine", "Database"]),
    ("Information_retrieval", ["Search_engine", "Inverted_index", "Machine_learning"]),
    ("YARN", ["Apache_Hadoop", "Computer_cluster", "Distributed_computing"]),
    ("Apache_ZooKeeper", ["Distributed_computing", "Apache_Hadoop"]),
    ("Data_warehouse", ["Database", "Hive", "Data_mining"]),
    ("Computer_cluster", ["Distributed_computing", "Cloud_computing"]),
    ("Statistics", ["Data_mining", "Machine_learning"]),
    ("Python_(programming_language)", ["Machine_learning", "Apache_Spark", "Data_mining"]),
    ("hadoop_tutorial_pdf", []),          # 悬挂页面（无出链）
]


def main():
    nodes = {n for n, _ in GRAPH}
    # 校验：每个出链都必须是数据集里出现过的页面，否则 PR 会“流出”图外
    for n, links in GRAPH:
        for t in links:
            assert t in nodes, "未定义的链接目标: %s -> %s" % (n, t)
            assert t != n, "不允许自环: %s" % n
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for n, links in GRAPH:
            f.write("%s\t%s\n" % (n, ",".join(links)))
    edges = sum(len(l) for _, l in GRAPH)
    print("written %s: %d 个页面, %d 条链接, %d 个悬挂页面"
          % (os.path.relpath(OUT, BASE), len(GRAPH), edges,
             sum(1 for _, l in GRAPH if not l)))


if __name__ == "__main__":
    main()
