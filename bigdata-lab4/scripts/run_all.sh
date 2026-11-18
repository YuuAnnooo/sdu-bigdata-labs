#!/usr/bin/env bash
# 一键复现：清洗数据（如缺失）→ 单机版 → Spark 版 → 逐字节比较
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3}

if [ ! -f data/transactions.tsv ]; then
  "$PYTHON" tools/prepare_data.py --download
fi

bash scripts/run_local.sh
bash scripts/run_spark.sh
"$PYTHON" tools/compare_results.py --local out/local --spark out/spark --out out/compare.txt
