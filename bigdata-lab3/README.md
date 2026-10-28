# bigdata-lab3：HBase 操作与 PageRank 算法实现

山东大学 计算机科学与技术学院《大数据管理与分析》课程 **实验三** 代码仓库。

| 目录 / 文件 | 对应实验内容 |
| --- | --- |
| `scripts/01_hbase_ops.sh` | 第一部分 1：HBase Shell 完成 5 项通用操作，并建库建表、写入学生/课程/选课数据 |
| `src/main/java/.../hbase/HBaseApp.java` | 第一部分 2：HBase Java API 实现 5 项通用操作，以及 `createTable` / `addRecord` / `scanColumn` / `modifyData` / `deleteRow` |
| `data/pagerank.txt` | 第二部分：网页链接图数据集（25 个页面、83 条链接、1 个悬挂页面） |
| `src/main/java/.../pagerank/PageRankMR.java` | 第二部分：MapReduce 实现的 PageRank（每轮一个作业，共 10 轮） |
| `src/main/java/.../pagerank/PageRankSpark.java` | 第二部分：Spark（Java API）实现的 PageRank |
| `spark/pagerank_spark.py` | 第二部分：PySpark 实现，算法与输出与 Java 版完全一致 |
| `scripts/02_run_pagerank_mr.sh`、`03_run_pagerank_spark.sh` | 编译、上传数据、运行两种实现 |
| `out/` | 10 轮迭代后的输出结果、前 10 名、每轮 PR 明细 |
| `tools/gen_dataset.py` | 生成数据集并校验链接闭合 |
| `tools/local_check.py` | 本地校验：不启动 Hadoop/Spark，用纯 Python 复现两套语义并比对 |

> 实验报告（DOCX / PDF）位于仓库根目录的 `实验三报告.docx` / `实验三报告.pdf`。

## 环境

- Ubuntu 20.04 LTS（VMware 虚拟机），JDK 1.8
- Hadoop 3.3.4（伪分布式，`hdfs://localhost:9000`）
- HBase 2.4.14（伪分布式，`hbase.rootdir` 指向 HDFS）
- Spark 3.3.2（`local[2]` 或 standalone 伪分布式）
- Maven 3.8.6

## 编译与运行

```bash
mvn -q clean package                 # 生成 target/bigdata-lab3.jar

# 第一部分：HBase
bash scripts/01_hbase_ops.sh
hadoop jar target/bigdata-lab3.jar cn.sdu.bigdata.lab3.hbase.HBaseApp init
hadoop jar target/bigdata-lab3.jar cn.sdu.bigdata.lab3.hbase.HBaseApp list
hadoop jar target/bigdata-lab3.jar cn.sdu.bigdata.lab3.hbase.HBaseApp showcol student Score
hadoop jar target/bigdata-lab3.jar cn.sdu.bigdata.lab3.hbase.HBaseApp modify student 2015001 Score:Math 95
hadoop jar target/bigdata-lab3.jar cn.sdu.bigdata.lab3.hbase.HBaseApp delRow sc 2015002_123003

# 第二部分：PageRank
bash scripts/02_run_pagerank_mr.sh     # MapReduce 版本
bash scripts/03_run_pagerank_spark.sh  # Spark 版本
```

## 未启动集群时的本地校验

```bash
python3 tools/local_check.py --write   # 复现两套语义，输出写入 out/
```

脚本分别用“map → shuffle → reduce”和“join → reduceByKey → mapValues”两种语义
各算一遍，断言两者差异小于 1e-12、格式化输出逐行相同，从而在提交前确认算法逻辑正确。

## 数据集与结果

`data/pagerank.txt` 每行是 `网页 \t 出链1,出链2,...`，主题围绕大数据与搜索引擎相关词条，
由人工标定链接关系；`hadoop_tutorial_pdf` 只有入链、没有出链，是悬挂页面（dangling node），
用来检验概率质量不会从图中“漏出”。

初始 PR = 1/N（N = 25），阻尼系数 d = 0.85，迭代 10 轮后 PR 之和严格保持为 1：

```
(Apache_Hadoop,0.0927489200)
(Distributed_computing,0.0779326630)
(MapReduce,0.0667616227)
(Big_data,0.0639704934)
(Machine_learning,0.0627814603)
(Data_mining,0.0597310331)
(Database,0.0563539254)
(Cloud_computing,0.0529207550)
(NoSQL,0.0460786367)
(Computer_cluster,0.0412556136)
```

完整结果见 `out/pagerank_result.txt`，每轮明细见 `out/pr_trace.csv`。
