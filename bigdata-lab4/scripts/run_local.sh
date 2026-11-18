#!/usr/bin/env bash
# 运行单机（非并行）Apriori
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3}
MIN_SUPPORT=${MIN_SUPPORT:-0.005}
MIN_CONFIDENCE=${MIN_CONFIDENCE:-0.5}

"$PYTHON" python/apriori_local.py \
  --input data/transactions.tsv \
  --min-support "$MIN_SUPPORT" \
  --min-confidence "$MIN_CONFIDENCE" \
  --out-prefix out/local \
  --timing out/local_timing.json
