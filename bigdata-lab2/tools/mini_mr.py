# -*- coding: utf-8 -*-
"""MiniMapReduce: a single-node, faithful reproduction of the two-job Hadoop pipeline.

This workspace has no Hadoop cluster / JDK, so the phases of both jobs are executed
explicitly here instead of by YARN:

    InputSplit -> map -> combine (per split) -> shuffle/sort -> group -> reduce -> part-r-00000

The produced index is therefore real output of exactly the algorithm implemented in
src/main/java/.../InvertedIndexDriver.java.

Usage:
    python tools/mini_mr.py                        # build the index
    python tools/mini_mr.py --query hadoop,index   # build, then look up words
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "raw"
STOPWORDS = ROOT / "stopwords" / "stopwords_en.txt"
RESULTS = ROOT / "results"

NON_LETTER = re.compile(r"[^a-z]+")
MIN_WORD_LENGTH = 2
SPLIT_SIZE_BYTES = 8192          # 模拟 HDFS split / block 大小
NUM_REDUCERS = 1                 # 倒排表需要全局有序


# ---------------------------------------------------------------- 公共组件
def load_stopwords() -> set[str]:
    words = set()
    for line in STOPWORDS.read_text(encoding="utf-8").splitlines():
        w = line.strip().lower()
        if w and not w.startswith("#"):
            words.add(w)
    return words


def tokenize(line: str) -> list[str]:
    return [t for t in NON_LETTER.sub(" ", line.lower()).split(" ") if t]


def make_splits(files: list[Path]) -> list[dict]:
    """按文件 + 大小切分输入，模拟 FileInputFormat#getSplits。"""
    splits = []
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        chunk, size, idx = [], 0, 0
        for line in lines:
            chunk.append(line)
            size += len(line.encode("utf-8")) + 1
            if size >= SPLIT_SIZE_BYTES:
                splits.append({"file": f, "index": idx, "lines": chunk})
                idx += 1
                chunk, size = [], 0
        if chunk:
            splits.append({"file": f, "index": idx, "lines": chunk})
    return splits


def partition_of(key: str, num_partitions: int) -> int:
    """与 Hadoop HashPartitioner 等价：key.hashCode() % numPartitions。"""
    digest = hashlib.md5(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % num_partitions


def combine(pairs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Combiner：在 map 端先做局部聚合，减少 shuffle 的数据量。"""
    acc: dict[str, int] = defaultdict(int)
    for k, v in pairs:
        acc[k] += v
    return list(acc.items())


def shuffle_sort(pairs: list[tuple[str, int]], num_partitions: int) -> dict[int, list]:
    """按 partition 聚集再按键排序：等价于 shuffle & sort 阶段。"""
    buckets: dict[int, list] = defaultdict(list)
    for k, v in pairs:
        buckets[partition_of(k, num_partitions)].append((k, v))
    for p in buckets:
        buckets[p].sort(key=lambda kv: kv[0])
    return buckets


def reduce_sum(items: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """归约：排序后相同 key 连续出现，逐组求和。"""
    out, cur_key, cur_sum = [], None, 0
    for k, v in items:
        if k != cur_key:
            if cur_key is not None:
                out.append((cur_key, cur_sum))
            cur_key, cur_sum = k, 0
        cur_sum += v
    if cur_key is not None:
        out.append((cur_key, cur_sum))
    return out


# ---------------------------------------------------------------- 作业一
def stage1_map(split: dict, stopwords: set[str]) -> list[tuple[str, int]]:
    doc = split["file"].name
    out = []
    for line in split["lines"]:
        for word in tokenize(line):
            if len(word) < MIN_WORD_LENGTH or word in stopwords:
                continue
            out.append((f"{word}\t{doc}", 1))
    return out


# ---------------------------------------------------------------- 作业二
def stage2_map(line: str) -> tuple[str, str] | None:
    parts = line.split("\t")
    if len(parts) != 3:
        return None
    return parts[0], f"{parts[1]}:{parts[2]}"


def stage2_reduce(values: list[str]) -> str:
    postings: dict[str, int] = defaultdict(int)
    total = 0
    for v in values:
        doc, _, cnt = v.rpartition(":")
        try:
            n = int(cnt)
        except ValueError:
            continue
        postings[doc] += n
        total += n
    ordered = sorted(postings.items(), key=lambda kv: (-kv[1], kv[0]))
    body = "".join(f"<{d},{n}>;" for d, n in ordered)
    return f"{body}<total,{total}>."


# ---------------------------------------------------------------- 驱动
def log(msg: str = "") -> None:
    print(msg, flush=True)


def build_index(verbose: bool = True) -> dict:
    t_all = time.time()
    stopwords = load_stopwords()
    files = sorted(CORPUS.glob("document*.txt"))
    if not files:
        sys.exit(f"no corpus found in {CORPUS}")
    splits = make_splits(files)

    if verbose:
        log("=" * 78)
        log("Job 1/2 : tokenize + stop-word filter + per-document word count")
        log("=" * 78)
        log("Input path      : corpus/raw")
        log(f"Input files     : {len(files)}")
        log(f"Total splits    : {len(splits)}")
        log(f"Stop words      : {len(stopwords)}")
        log(f"Split size      : {SPLIT_SIZE_BYTES} bytes")
        log("")

    # ---- map + combine
    t0 = time.time()
    map1_out: list[tuple[str, int]] = []
    for i, split in enumerate(splits, 1):
        pairs = stage1_map(split, stopwords)
        comb = combine(pairs)
        map1_out.extend(comb)
        if verbose:
            log(f"  map task {i:02d}  split={split['file'].name}[{split['index']}]"
                f"  lines={len(split['lines']):4d}  map_out={len(pairs):5d}"
                f"  combine_out={len(comb):5d}")
    t_map = time.time() - t0

    # ---- shuffle & sort
    t0 = time.time()
    buckets1 = shuffle_sort(map1_out, NUM_REDUCERS)
    t_shuf = time.time() - t0

    # ---- reduce
    t0 = time.time()
    stage1_records = reduce_sum(buckets1.get(0, []))
    t_red = time.time() - t0

    stage1_dir = RESULTS / "stage1"
    stage1_dir.mkdir(parents=True, exist_ok=True)
    (stage1_dir / "part-r-00000").write_text(
        "".join(f"{k}\t{v}\n" for k, v in stage1_records), encoding="utf-8")

    if verbose:
        log("")
        log(f"  reduce output    {len(stage1_records)} records")
        log(f"  map={t_map*1000:.0f}ms shuffle={t_shuf*1000:.0f}ms reduce={t_red*1000:.0f}ms")
        log(f"Output -> results/stage1/part-r-00000  ({len(stage1_records)} lines)")
        log("  first 5 lines:")
        for k, v in stage1_records[:5]:
            log(f"    {k}\t{v}")
        log("")

    # ---- 作业二
    if verbose:
        log("=" * 78)
        log("Job 2/2 : group by word -> inverted index (postings)")
        log("=" * 78)
    t0 = time.time()
    map2_out = []
    for k, v in stage1_records:
        got = stage2_map(f"{k}\t{v}")
        if got:
            map2_out.append(got)
    buckets2 = shuffle_sort(map2_out, NUM_REDUCERS)

    grouped: dict[str, list[str]] = defaultdict(list)
    for key, value in buckets2.get(0, []):
        grouped[key].append(value)
    index_lines = [f"{word} {stage2_reduce(vals)}" for word, vals in sorted(grouped.items())]
    t_two = time.time() - t0

    stage2_dir = RESULTS / "stage2"
    stage2_dir.mkdir(parents=True, exist_ok=True)
    (stage2_dir / "part-r-00000").write_text(
        "".join(line + "\n" for line in index_lines), encoding="utf-8")

    if verbose:
        log(f"  map input        {len(map2_out)} pairs from stage1")
        log(f"  reduce output    {len(index_lines)} words")
        log(f"  elapsed          {t_two*1000:.0f}ms")
        log(f"Output -> results/stage2/part-r-00000  ({len(index_lines)} lines)")
        log("  first 5 lines:")
        for line in index_lines[:5]:
            log(f"    {line}")
        log("")
        log(f"TOTAL {round((time.time()-t_all)*1000)}ms")

    return {"lines": index_lines, "stage1": stage1_records,
            "stopwords": len(stopwords), "files": len(files), "splits": len(splits)}


def query(terms: list[str], index_lines: list[str]) -> None:
    table = {}
    for line in index_lines:
        word, _, rest = line.partition(" ")
        table[word] = rest
    print("=" * 78)
    print("index lookup")
    print("=" * 78)
    for t in terms:
        t = t.strip().lower()
        print(f"[query] {t}")
        print(f"  {table.get(t, '<not found>')}")
        print("")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="")
    args = ap.parse_args()
    result = build_index()
    if args.query:
        print()
        query([t for t in args.query.split(",") if t.strip()], result["lines"])


if __name__ == "__main__":
    main()
