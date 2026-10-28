#!/bin/bash
# =============================================================================
# 实验一 第 1 部分（下半）：启动 Hadoop 并完成 HDFS 基础操作
# 用法：bash scripts/02_hdfs_basic.sh
# 前提：已配置好 Hadoop 伪分布式（core-site.xml 中 fs.defaultFS=hdfs://localhost:9000）
#      并以 hadoop 用户登录
# =============================================================================
set -e

echo "================ 1. 启动 Hadoop（HDFS + YARN） ================"
start-dfs.sh
start-yarn.sh
jps                       # 应看到 NameNode、DataNode、SecondaryNameNode、ResourceManager、NodeManager

echo "================ 2. 为 hadoop 用户创建 HDFS 用户目录 ================"
hdfs dfs -mkdir -p /user/hadoop
hdfs dfs -ls /user

echo "================ 3. 在 /user/hadoop 下创建 test 文件夹并查看 ================"
hdfs dfs -mkdir /user/hadoop/test
hdfs dfs -ls /user/hadoop

echo "================ 4. 上传本地 ~/.bashrc 到 HDFS 的 test 目录 ================"
hdfs dfs -put ~/.bashrc /user/hadoop/test
hdfs dfs -ls /user/hadoop/test

echo "================ 5. 把 HDFS 的 test 目录复制回本机 /usr/local/hadoop ================"
sudo rm -rf /usr/local/hadoop/test          # 若已存在先清理，避免覆盖提示
sudo hdfs dfs -get /user/hadoop/test /usr/local/hadoop/
ls -l /usr/local/hadoop/test

echo "================ 完成 ================"
echo "Web UI: http://localhost:9870 （NameNode）  http://localhost:8088 （YARN）"
