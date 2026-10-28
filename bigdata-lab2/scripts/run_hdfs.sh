#!/usr/bin/env bash
# 在 Linux + Hadoop 集群（或伪分布式）上提交倒排索引作业。
#
#   1) 上传语料到 HDFS
#   2) 上传停词表到 HDFS
#   3) 编译打包
#   4) 运行两个 MapReduce 作业
#   5) 查看结果
set -euo pipefail

INPUT=${INPUT:-/user/$(whoami)/lab2/corpus}
OUTPUT=${OUTPUT:-/user/$(whoami)/lab2/index}
STOPWORDS=${STOPWORDS:-/user/$(whoami)/lab2/stopwords/stopwords_en.txt}

echo "==> [1/5] upload corpus to HDFS"
hdfs dfs -mkdir -p "${INPUT}"
hdfs dfs -put -f corpus/raw/document*.txt "${INPUT}/"
hdfs dfs -ls "${INPUT}"

echo "==> [2/5] upload stop word list to HDFS"
hdfs dfs -mkdir -p "$(dirname "${STOPWORDS}")"
hdfs dfs -put -f stopwords/stopwords_en.txt "${STOPWORDS}"

echo "==> [3/5] build the jar with Maven"
mvn -q clean package -DskipTests
JAR=$(ls target/inverted-index.jar)

echo "==> [4/5] run the two MapReduce jobs"
hdfs dfs -rm -r -f "${OUTPUT}" || true
hadoop jar "${JAR}" \
  edu.sdu.bigdata.invertedindex.InvertedIndexDriver \
  "${INPUT}" "${OUTPUT}" "${STOPWORDS}"

echo "==> [5/5] show the inverted index"
hdfs dfs -cat "${OUTPUT}/stage2/part-r-00000" | head -n 20
echo "..."
echo "total index words: $(hdfs dfs -cat "${OUTPUT}/stage2/part-r-00000" | wc -l)"
