# 大数据管理与分析 · 课程实验

山东大学计算机科学与技术学院《大数据管理与分析》课程四次实验的代码与实验说明。
运行环境：Linux（Ubuntu 20.04 / 24.04）+ JDK 1.8 + Hadoop 3.3.x（部分实验含 Spark / HBase）。

## 目录

| 目录 | 实验 | 主要内容 |
| --- | --- | --- |
| `bigdata-lab1/` | 实验一 HDFS 与 MapReduce 基础 | Linux/HDFS 常用操作、HDFS Java API、MapReduce 去重与排序、多级父子关系挖掘 |
| `bigdata-lab2/` | 实验二 文档倒排索引 | 两个 MapReduce 作业构建倒排索引、停词表、10 篇英文语料 |
| `bigdata-lab3/` | 实验三 PageRank | MapReduce / Spark 两种实现、HBase 存储与 top-10 输出 |
| `bigdata-lab4/` | 实验四 并行化数据挖掘 | Apriori 频繁项集 / 关联规则、单机 Python 与 PySpark、逐字节一致性验证、弱扩展加速比 |

实验报告（docx / pdf）按课程要求单独提交，不纳入本仓库；仓库中只保留代码、数据与运行输出。

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

`bigdata-lab2/tools/mini_mr.py` 是同一套 map/combine/shuffle/reduce 逻辑的单机版本，
用于不启动集群时快速校验算法与输出格式。
## 实验四：并行化数据挖掘

以 UCI Online Retail 的 18 270 个购物篮为输入，用 Apriori 挖掘频繁项集和关联规则。
支持度计数采用垂直位图（商品 -> 事务位图，按位与后 `bit_count`），避免大购物篮
横向枚举子集的组合爆炸；单机 Python 与 PySpark 两套实现共用同一套候选生成、
整数计数和排序规则，输出逐字节一致。

```
bigdata-lab4/
├── data/transactions.tsv       18 270 个购物篮、3 784 种商品
├── python/apriori_local.py     单机实现（位图计数）
├── spark/apriori_spark.py      PySpark 实现（Driver 生成候选 + Executor 并行计数）
├── tools/prepare_data.py       UCI Excel 清洗
├── tools/compare_results.py    SHA-256 / 行数 / 分层统计比较
├── tools/scale_data.py         4x / 8x 弱扩展数据
├── scripts/run_all.sh          一键复现
└── out/                        项集、规则、对比报告、benchmark.csv
```

`min_support=0.005`、`min_confidence=0.5` 时得到 22 522 个频繁项集、35 657 条规则；
1x 数据单机 5.49 s、Spark `local[4]` 11.81 s，8x 数据分别为 30.97 s 和 21.91 s
（加速比 1.41）；8x 下 Spark 从 1 核到 4 核加速 1.98 倍。详见
[`bigdata-lab4/README.md`](bigdata-lab4/README.md)。
