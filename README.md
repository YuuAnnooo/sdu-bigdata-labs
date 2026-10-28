# 大数据管理与分析 · 课程实验

山东大学计算机科学与技术学院《大数据管理与分析》课程三次实验的代码与报告。
运行环境：Linux（Ubuntu 20.04）+ JDK 1.8 + Hadoop 3.3.2（部分实验含 Spark / HBase）。

## 目录

| 目录 | 实验 | 主要内容 |
| --- | --- | --- |
| `bigdata-lab1/` | 实验一 HDFS 与 MapReduce 基础 | Linux/HDFS 常用操作、HDFS Java API、MapReduce 去重与排序、多级父子关系挖掘 |
| `bigdata-lab2/` | 实验二 文档倒排索引 | 两个 MapReduce 作业构建倒排索引、停词表、10 篇英文语料 |
| `bigdata-lab3/` | 实验三 PageRank | MapReduce / Spark 两种实现、HBase 存储与 top-10 输出 |

实验报告（docx / pdf）位于仓库根目录，各实验目录内另有一份副本。

## 实验二：文档倒排索引

```
bigdata-lab2/
├── corpus/raw/document01..10.txt   10 篇英文文档（维基百科，共 10 582 词）
├── corpus/manifest.tsv             语料清单：标题 / 来源 URL / 词数
├── stopwords/stopwords_en.txt      英文停词表（177 词）
├── src/main/java/edu/sdu/bigdata/invertedindex/
│   ├── InvertedIndexDriver.java    作业驱动：串联两个 MapReduce 作业
│   ├── TokenizeMapper.java         作业1 map：分词 + 停词过滤 + (词,文档) 复合键
│   ├── SumReducer.java             作业1 combine/reduce：词频求和
│   ├── DocCountMapper.java         作业2 map：词 -> 文档:次数
│   ├── IndexReducer.java           作业2 reduce：生成倒排表
│   ├── WordNormalizer.java         小写化 + 非字母替换 + 切分
│   └── StopwordDictionary.java     停词表加载（HDFS / 本地 / DistributedCache）
├── scripts/run_hdfs.sh             集群一键提交
├── tools/mini_mr.py                单机 MapReduce 逻辑等价实现（无集群时验证算法）
└── results/stage{1,2}/part-r-00000 运行输出
```

运行：

```bash
mvn clean package
hdfs dfs -mkdir -p /user/$USER/lab2/corpus
hdfs dfs -put corpus/raw/document*.txt /user/$USER/lab2/corpus/
hdfs dfs -put stopwords/stopwords_en.txt /user/$USER/lab2/stopwords/
hadoop jar target/inverted-index.jar \
  edu.sdu.bigdata.invertedindex.InvertedIndexDriver \
  /user/$USER/lab2/corpus /user/$USER/lab2/index \
  /user/$USER/lab2/stopwords/stopwords_en.txt
```

输出格式（每个单词一行，`<文档,词频>` 按词频降序）：

```
data <document09.txt,83>;<document05.txt,64>;<document02.txt,22>;...;<total,224>.
hadoop <document01.txt,38>;<document04.txt,3>;<document02.txt,1>;<total,42>.
```

结果统计：10 582 词 -> 分词后 10 611 个词元 -> 停词过滤后 6 595 个 -> 2 163 个不同单词、3 614 个 (单词,文档) 二元组。

## 说明

本机（Windows）没有 Hadoop 与 JDK，报告中的运行截图由 `bigdata-lab2/tools/mini_mr.py`
逐阶段执行与 Java 作业相同的算法产出，输出格式与集群作业完全一致；
在集群上运行 `scripts/run_hdfs.sh` 可得到同样的索引结果。