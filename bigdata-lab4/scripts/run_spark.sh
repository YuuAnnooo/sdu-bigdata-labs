#!/usr/bin/env bash
# 运行 PySpark 并行版 Apriori
#   SPARK_MASTER 默认 local[4]；也可用 spark://127.0.0.1:7077（standalone 伪分布式）
set -euo pipefail
cd "$(dirname "$0")/.."

MIN_SUPPORT=${MIN_SUPPORT:-0.005}
MIN_CONFIDENCE=${MIN_CONFIDENCE:-0.5}
SPARK_MASTER=${SPARK_MASTER:-local[4]}

spark-submit \
  --master "$SPARK_MASTER" \
  --conf spark.ui.showConsoleProgress=false \
  spark/apriori_spark.py \
  --input data/transactions.tsv \
  --min-support "$MIN_SUPPORT" \
  --min-confidence "$MIN_CONFIDENCE" \
  --out-prefix out/spark \
  --timing out/spark_timing.json
