#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 UCI Online Retail 原始 Excel 清洗成“一行一个购物篮”的事务文件。

数据来源
    Daqing Chen, Sai Liang Sain, Kun Guo. Online Retail.
    UCI Machine Learning Repository, 2015. DOI: 10.24432/C5BW33
    https://archive.ics.uci.edu/dataset/352/online+retail

清洗规则
    1. 去掉取消单（InvoiceNo 以 C 开头）、退货与调账（Quantity <= 0）；
    2. 去掉非商品行（StockCode 不是 5 位数字 + 可选字母，如 POST、D、M、
       BANK CHARGES、AMAZONFEE 等），去掉单价 <= 0 的行；
    3. 按 InvoiceNo 聚合成购物篮，同一商品在一次交易中只计一次；
    4. 只保留至少包含 2 种商品的购物篮（单商品交易对频繁项集没有贡献）。

输出
    data/transactions.tsv   每行一个购物篮，商品编码按字典序排列，制表符分隔
    data/items.tsv          code <TAB> description <TAB> 出现该商品的购物篮数
    data/dataset_stats.json 清洗前后的统计量，供报告引用

用法
    python tools/prepare_data.py                    # 读取 data/raw/Online Retail.xlsx
    python tools/prepare_data.py --download         # 先下载再清洗
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "raw")
XLSX = os.path.join(RAW_DIR, "Online Retail.xlsx")
ZIP = os.path.join(RAW_DIR, "online_retail.zip")
DATA_DIR = os.path.join(BASE, "data")
URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
PRODUCT_CODE = re.compile(r"^\d{5}[A-Z]?$")


def download():
    os.makedirs(RAW_DIR, exist_ok=True)
    if not os.path.exists(ZIP):
        print("downloading", URL)
        urllib.request.urlretrieve(URL, ZIP)
    if not os.path.exists(XLSX):
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(RAW_DIR)
    if not os.path.exists(XLSX):
        sys.exit("未找到 data/raw/Online Retail.xlsx")


def normalize_code(value):
    """StockCode 统一成字符串；Excel 偶尔把纯数字编码读成浮点数。"""
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return " ".join(str(value).split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="原始文件不存在时先下载")
    ap.add_argument("--top", type=int, default=20, help="预览出现次数最多的商品数")
    args = ap.parse_args()

    if args.download:
        download()
    if not os.path.exists(XLSX):
        sys.exit("缺少 %s，请加 --download 或手动放到 data/raw/" % XLSX)

    print("reading", XLSX)
    raw = pd.read_excel(XLSX)
    raw_rows = len(raw)

    df = raw.copy()
    df["StockCode"] = df["StockCode"].map(normalize_code)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()

    cancel = df["InvoiceNo"].str.startswith("C")
    non_product = ~df["StockCode"].str.match(PRODUCT_CODE)
    bad_qty = df["Quantity"] <= 0
    bad_price = df["UnitPrice"] <= 0

    stats = {
        "source": "UCI Online Retail (DOI 10.24432/C5BW33)",
        "raw_rows": int(raw_rows),
        "removed_cancelled": int(cancel.sum()),
        "removed_non_product": int(non_product.sum()),
        "removed_quantity_le_0": int(bad_qty.sum()),
        "removed_price_le_0": int(bad_price.sum()),
    }

    df = df[~cancel & ~non_product & ~bad_qty & ~bad_price].copy()
    stats["clean_rows"] = int(len(df))

    # 每个商品保留出现次数最多的描述，用于报告里的可读名称
    desc_counter = defaultdict(Counter)
    for code, desc in zip(df["StockCode"], df["Description"]):
        text = clean_text(desc)
        if text:
            desc_counter[code][text] += 1
    descriptions = {c: cnt.most_common(1)[0][0] for c, cnt in desc_counter.items()}

    # 按发票聚合成购物篮（集合去重）
    baskets = []
    for invoice, group in df.groupby("InvoiceNo", sort=True):
        items = tuple(sorted(set(group["StockCode"])))
        if len(items) >= 2:
            baskets.append((invoice, items))
    baskets.sort(key=lambda kv: kv[0])

    item_freq = Counter()
    for _, items in baskets:
        item_freq.update(items)

    total_items = sum(len(items) for _, items in baskets)
    sizes = [len(items) for _, items in baskets]
    stats.update({
        "invoices": int(df["InvoiceNo"].nunique()),
        "baskets": len(baskets),
        "items": len(item_freq),
        "item_occurrences": int(total_items),
        "avg_basket": round(total_items / len(baskets), 2),
        "median_basket": int(pd.Series(sizes).median()),
        "max_basket": int(max(sizes)),
        "date_start": str(df["InvoiceDate"].min().date()),
        "date_end": str(df["InvoiceDate"].max().date()),
        "countries": int(df["Country"].nunique()),
        "min_support_note": "支持度阈值按购物篮数 baskets 计算",
    })

    os.makedirs(DATA_DIR, exist_ok=True)
    tx_path = os.path.join(DATA_DIR, "transactions.tsv")
    with open(tx_path, "w", encoding="utf-8", newline="\n") as f:
        for _, items in baskets:
            f.write("\t".join(items) + "\n")

    items_path = os.path.join(DATA_DIR, "items.tsv")
    with open(items_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("code\tdescription\tbaskets\n")
        for code in sorted(item_freq):
            f.write("%s\t%s\t%d\n" % (code, descriptions.get(code, ""), item_freq[code]))

    stats_path = os.path.join(DATA_DIR, "dataset_stats.json")
    with open(stats_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("\n出现最多的 %d 种商品：" % args.top)
    for code, n in item_freq.most_common(args.top):
        print("  %s  %-45s %d" % (code, descriptions.get(code, ""), n))
    print("\n写出：%s\n      %s\n      %s" % (tx_path, items_path, stats_path))


if __name__ == "__main__":
    main()
