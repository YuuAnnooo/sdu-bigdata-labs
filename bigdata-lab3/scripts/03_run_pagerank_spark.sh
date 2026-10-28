#!/usr/bin/env bash
# 实验三 第二部分：PageRank 的 Spark 实现（伪分布式，local 或 standalone 均可）
set -e

JAR=target/bigdata-lab3.jar
HDFS_IN=/user/hadoop/lab3/pagerank/input
HDFS_OUT_SPARK=/user/hadoop/lab3/pagerank/output-spark

mvn -q clean package
python3 tools/gen_dataset.py
hdfs dfs -mkdir -p $HDFS_IN
hdfs dfs -put -f data/pagerank.txt $HDFS_IN/

# 方式一：Java 版
spark-submit --class cn.sdu.bigdata.lab3.pagerank.PageRankSpark \
    --master local[2] $JAR $HDFS_IN/pagerank.txt 10

# 方式二：PySpark 版（算法与输出完全相同）
spark-submit --master local[2] spark/pagerank_spark.py $HDFS_IN/pagerank.txt 10

# 与 MapReduce 版本比对：两个文件应逐行一致
hdfs dfs -getmerge $HDFS_OUT_SPARK/part-r-00000 out/pagerank_spark_result.txt
# hdfs dfs -rm -r $HDFS_IN/pagerank.txt_pagerank_spark
