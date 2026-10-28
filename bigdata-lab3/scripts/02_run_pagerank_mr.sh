#!/usr/bin/env bash
# 实验三 第二部分：PageRank 的 MapReduce 实现（伪分布式）
set -e

JAR=target/bigdata-lab3.jar
HDFS_IN=/user/hadoop/lab3/pagerank/input
HDFS_OUT_MR=/user/hadoop/lab3/pagerank/output-mr

# 1. 编译打包
mvn -q clean package

# 2. 生成数据集并上传到 HDFS
python3 tools/gen_dataset.py
hdfs dfs -mkdir -p $HDFS_IN
hdfs dfs -put -f data/pagerank.txt $HDFS_IN/

# 3. 运行：10 轮迭代 + 排序格式化
hadoop jar $JAR cn.sdu.bigdata.lab3.pagerank.PageRankMR \
    $HDFS_IN $HDFS_OUT_MR 10

# 4. 查看结果：每行形如 (网页,0.xxxxxxxxxx)
hdfs dfs -cat $HDFS_OUT_MR/result/part-r-00000
hdfs dfs -cat $HDFS_OUT_MR/result/part-r-00000 | head -10

# 5. 取回本地
hdfs dfs -getmerge $HDFS_OUT_MR/result/part-r-00000 out/pagerank_mr_result.txt
