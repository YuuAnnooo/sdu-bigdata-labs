#!/bin/bash
# =============================================================================
# 实验一 第 2 部分：用 HDFS Shell 命令完成与 Java API 程序相同的 10 项任务
# 用法：bash scripts/04_hdfs_shell.sh
# =============================================================================
set -e

LOCAL=~/.bashrc
DIR=/user/hadoop/lab1/hdfsdemo

echo "================ 0. 准备目录 ================"
hdfs dfs -mkdir -p $DIR
hdfs dfs -ls -R $DIR

echo "================ 1. 上传（已存在时覆盖 / 追加） ================"
# 覆盖：-put -f
hdfs dfs -put -f $LOCAL $DIR/.bashrc
hdfs dfs -ls $DIR
# 追加到末尾：-appendToFile
echo "append by shell" > /tmp/append.txt
hdfs dfs -appendToFile /tmp/append.txt $DIR/.bashrc
hdfs dfs -tail $DIR/.bashrc

echo "================ 2. 下载（同名自动重命名） ================"
mkdir -p /tmp/download
f=$(basename $DIR/.bashrc)
if [ -e /tmp/download/$f ]; then
    i=1
    while [ -e /tmp/download/${f}_$i ]; do i=$((i+1)); done
    echo "本地已存在同名文件，自动重命名为 ${f}_$i"
    hdfs dfs -get $DIR/.bashrc /tmp/download/${f}_$i
else
    hdfs dfs -get $DIR/.bashrc /tmp/download/
fi
ls -l /tmp/download

echo "================ 3. 输出文件内容到终端 ================"
hdfs dfs -cat $DIR/.bashrc | head -n 5

echo "================ 4. 显示单个文件的详细信息 ================"
hdfs dfs -ls $DIR/.bashrc
hdfs dfs -stat "权限:%A  大小:%b  修改时间:%y  路径:%n" $DIR/.bashrc

echo "================ 5. 递归显示目录下所有文件信息 ================"
hdfs dfs -ls -R $DIR

echo "================ 6. 创建 / 删除文件（父目录不存在则自动创建） ================"
hdfs dfs -mkdir -p $DIR/sub
hdfs dfs -touchz $DIR/sub/new.txt          # touchz 创建 0 字节文件
hdfs dfs -ls $DIR/sub
hdfs dfs -rm $DIR/sub/new.txt
hdfs dfs -ls $DIR/sub

echo "================ 7. 创建 / 删除目录 ================"
hdfs dfs -mkdir -p $DIR/a/b/c              # -p 自动创建缺失的父目录
hdfs dfs -ls -R $DIR/a
hdfs dfs -rmdir $DIR/a/b/c                 # rmdir 只删除空目录，非空会报错
hdfs dfs -rmdir $DIR/a/b
hdfs dfs -rmdir $DIR/a
hdfs dfs -ls $DIR

echo "================ 8. 在文件开头 / 结尾追加内容 ================"
# 结尾：-appendToFile
echo "tail-line" > /tmp/tail.txt
hdfs dfs -appendToFile /tmp/tail.txt $DIR/.bashrc
# 开头：HDFS 不支持随机写，只能 下载 -> 拼接 -> 覆盖上传
echo "head-line" > /tmp/head.txt
hdfs dfs -get -f $DIR/.bashrc /tmp/base.tmp
cat /tmp/head.txt /tmp/base.tmp > /tmp/merged.tmp
hdfs dfs -put -f /tmp/merged.tmp $DIR/.bashrc
hdfs dfs -cat $DIR/.bashrc | head -n 2

echo "================ 9. 删除指定文件 ================"
hdfs dfs -rm $DIR/.bashrc
hdfs dfs -ls $DIR

echo "================ 10. 移动文件（改名） ================"
hdfs dfs -touchz $DIR/src.txt
hdfs dfs -mv $DIR/src.txt $DIR/dst.txt
hdfs dfs -ls $DIR
hdfs dfs -rm $DIR/dst.txt

echo "================ Shell 演示结束 ================"
