#!/bin/bash
# =============================================================================
# 实验一 第 3 部分：编译并运行三个 MapReduce 程序
# 用法：bash scripts/03_run_mapreduce.sh
# 说明：在项目根目录（bigdata-lab1）下执行；需要已 start-dfs.sh && start-yarn.sh
# =============================================================================
set -e

JAR=target/bigdata-lab1.jar
BASE=/user/hadoop/lab1

echo "================ 0. 编译打包 ================"
mvn -q clean package
ls -l $JAR

echo "================ 1. 准备 HDFS 输入目录 ================"
hdfs dfs -mkdir -p $BASE/input/dedup $BASE/input/sort $BASE/input/grandchild
hdfs dfs -put -f input/A.txt input/B.txt            $BASE/input/dedup/
hdfs dfs -put -f input/int1.txt input/int2.txt input/int3.txt $BASE/input/sort/
hdfs dfs -put -f input/child_parent.txt             $BASE/input/grandchild/
hdfs dfs -ls -R $BASE/input

echo "================ 2. 文件合并与去重 ================"
hdfs dfs -rm -r -f $BASE/output/dedup
hadoop jar $JAR cn.sdu.bigdata.lab1.mr.MergeDedup $BASE/input/dedup $BASE/output/dedup
echo "---- 输出文件 C ----"
hdfs dfs -cat $BASE/output/dedup/part-r-00000
hdfs dfs -get -f $BASE/output/dedup/part-r-00000 out/C.txt

echo "================ 3. 整数排序 ================"
hdfs dfs -rm -r -f $BASE/output/sort
hadoop jar $JAR cn.sdu.bigdata.lab1.mr.Sort $BASE/input/sort $BASE/output/sort
echo "---- 输出文件（名次 整数）----"
hdfs dfs -cat $BASE/output/sort/part-r-00000
hdfs dfs -get -f $BASE/output/sort/part-r-00000 out/sorted.txt

echo "================ 4. 祖孙关系挖掘 ================"
hdfs dfs -rm -r -f $BASE/output/grandchild
hadoop jar $JAR cn.sdu.bigdata.lab1.mr.GrandChild $BASE/input/grandchild $BASE/output/grandchild
echo "---- 输出文件（grandchild  grandparent）----"
hdfs dfs -cat $BASE/output/grandchild/part-r-00000
hdfs dfs -get -f $BASE/output/grandchild/part-r-00000 out/grandchild.txt

echo "================ 全部作业运行完成，结果已下载到 ./out ================"
ls -l out
