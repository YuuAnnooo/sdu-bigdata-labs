# 实验二：文档倒排索引算法实现（Hadoop MapReduce）

大数据管理与分析课程实验。用两个 MapReduce 作业对 10 篇英文文档建立倒排索引：
`单词 -> (文档, 词频) 列表`，并统计每个单词的总词频。

## 目录结构

```
.
├── corpus/
│   ├── manifest.tsv          # 语料清单：文件名 / 标题 / 来源 URL / 词数
│   └── raw/document01..10.txt# 10 篇英文文档（公开网页下载，纯文本）
├── stopwords/stopwords_en.txt# 英文停词表（177 词）
├── src/main/java/edu/sdu/bigdata/invertedindex/
│   ├── InvertedIndexDriver.java  # 驱动：串联两个作业
│   ├── TokenizeMapper.java       # 作业1 map：分词 + 停词过滤 + (词,文档) 复合键
│   ├── SumReducer.java           # 作业1 combine/reduce：词频求和
│   ├── DocCountMapper.java       # 作业2 map：词 -> 文档:次数
│   ├── IndexReducer.java         # 作业2 reduce：生成倒排表
│   ├── WordNormalizer.java       # 小写化 + 非字母替换 + 切分
│   └── StopwordDictionary.java   # 停词表加载（HDFS / 本地 / 分布式缓存）
├── scripts/run_hdfs.sh       # 集群上一键提交脚本
├── tools/
│   ├── download_corpus.ps1   # 语料下载脚本
│   ├── mini_mr.py            # 单机 MapReduce 逻辑等价实现（无集群时验证用）
│   └── make_figures.py       # 生成报告插图
├── results/                  # 运行输出
├── pom.xml
└── README.md
```

## 环境

| 项目 | 版本 |
| --- | --- |
| Linux | Ubuntu 24.04 LTS |
| JDK | 1.8.0_504 |
| Hadoop | 3.3.6（伪分布式；pom 按 3.3.2 编译） |
| Maven | 3.8+ |
| Python（仅单机验证用） | 3.11 |

## 算法

**作业一**：`(行) --map--> ((word, doc), 1) --combine/reduce--> (word, doc, count)`

- map 端从 `FileSplit` 取文档名（MapReduce 的输入是行，拿不到文件名）；
- `WordNormalizer` 统一小写并把 `[^a-z]` 替换为空格完成英文分词；
- 停词表与长度 < 2 的单词被过滤；
- Combiner 提前聚合，减少 shuffle 数据量。

**作业二**：`(word, doc, count) --map--> (word, doc:count) --reduce--> word <doc,n>;...;<total,N>.`

- 按单词分组，postings 按词频降序、文档名升序排列；
- 单 reduce 任务保证输出全局有序。

## 编译与运行

```bash
# 本地（单机）验证：不需要 Hadoop
python3 tools/mini_mr.py
python3 tools/mini_mr.py --query hadoop,index,mapreduce

# 集群 / 伪分布式
mvn clean package
hdfs dfs -mkdir -p /user/$USER/lab2/corpus
hdfs dfs -put corpus/raw/document*.txt /user/$USER/lab2/corpus/
hdfs dfs -put stopwords/stopwords_en.txt /user/$USER/lab2/stopwords/
hadoop jar target/inverted-index.jar \
  edu.sdu.bigdata.invertedindex.InvertedIndexDriver \
  /user/$USER/lab2/corpus /user/$USER/lab2/index \
  /user/$USER/lab2/stopwords/stopwords_en.txt

# 或直接执行脚本
bash scripts/run_hdfs.sh
```

## 输出格式

`results/stage2/part-r-00000`，每行一个单词：

```
data <document09.txt,83>;<document05.txt,64>;<document02.txt,22>;...;<total,224>.
hadoop <document01.txt,38>;<document04.txt,3>;<document02.txt,1>;<total,42>.
index <document06.txt,44>;<document03.txt,25>;<document01.txt,1>;<total,70>.
```

`<文档,词频>` 按词频降序排列，`<total,N>` 为该词在语料中的总出现次数。

## 实验数据

10 篇文档共 10 582 词（wc -w），分词后 10 611 个词元，停词过滤后保留 6 595 个，不同单词 2 163 个，
`(单词,文档)` 二元组 3 614 个。
