# bigdata-lab4：并行化频繁项集挖掘（Apriori）

山东大学 计算机科学与技术学院《大数据管理与分析》课程 **实验四** 代码仓库。

以 UCI **Online Retail** 交易数据为输入，用 **Apriori** 挖掘频繁项集和关联规则，
分别给出**单机（非并行）Python 实现**与 **PySpark 并行实现**，两者输出逐字节一致。

| 目录 / 文件 | 说明 |
| --- | --- |
| `data/transactions.tsv` | 清洗后的购物篮数据，一行一个交易，制表符分隔 |
| `data/items.tsv` | 商品编码、描述、出现购物篮数 |
| `data/dataset_stats.json` | 原始/清洗后行数、购物篮数、商品数等统计 |
| `python/apriori_local.py` | 单机 Apriori：逐层候选生成 + 位图支持度计数 |
| `spark/apriori_spark.py` | PySpark 并行 Apriori：Driver 生成候选，Executor 并行计数 |
| `tools/prepare_data.py` | 下载并清洗 UCI Excel，生成上述三个数据文件 |
| `tools/scale_data.py` | 复制并打乱购物篮，生成弱扩展实验数据 |
| `tools/compare_results.py` | 对两份输出做 SHA-256 / 行数 / 分层统计比较 |
| `tools/make_benchmark.py` | 汇总多次运行的 timing JSON，生成 `out/benchmark.csv` |
| `scripts/run_local.sh`、`run_spark.sh`、`run_all.sh` | 一键运行与复现 |
| `out/` | 频繁项集、关联规则、对比报告、计时结果 |

## 数据集

UCI Online Retail（DOI [10.24432/C5BW33](https://doi.org/10.24432/C5BW33)）：
2010-12-01 ~ 2011-12-09 英国在线零售商的 541 909 条交易明细。

清洗规则与统计见 [`data/README.md`](data/README.md)。结果：**18 270 个购物篮、
3 784 种商品、513 506 次商品出现**，平均购物篮 28.11 种商品，最大 1 097 种。
原始 Excel 不纳入仓库，`python tools/prepare_data.py --download` 可重新下载。

## 算法与并行设计

支持度、置信度、提升度：

```
support(X)        = count(X) / N
confidence(X -> Y) = support(X ∪ Y) / support(X)
lift(X -> Y)      = support(X ∪ Y) / (support(X) * support(Y))
```

Apriori 逐层搜索：由 k-1 频繁项集连接、剪枝得到 k 候选项集，扫描数据计数后
保留支持度 ≥ 阈值的项集；再由频繁项集枚举非空真子集生成规则。

**支持度计数用“垂直位图”而不是横向枚举。** 第 i 个商品对应一个大整数，
第 t 位为 1 表示该商品出现在第 t 个购物篮；候选项集的支持数等于各商品位图
按位与之后 1 的个数（`int.bit_count()`）。本数据集中最大的购物篮有 1 097 种
商品，横向枚举 3 项集需要约 2.2 亿次组合（实测单机需要 174 s），而位图只需
3 次按位与。单机版和并行版使用同一种计数语义，因此结果完全可比。

并行版的分工：

1. **Driver**：连接 + 剪枝生成候选。候选只依赖上一层频繁项集，层间有严格
   依赖，且数量远小于事务数，放在 Driver 上最简单；
2. **Executor**：`sc.parallelize(candidates)` 后各分区并行做位图与运算；
   `mapPartitionsWithIndex` 先在每个分区内用局部事务号建位图，再整体左移
   拼成全局位图，避免 Driver 串行处理全部事务；
3. **规则生成**：项集数 ≥ 2 000 时用 `flatMap` 分发到各分区，否则在 Driver
   生成（规则枚举本身很便宜）；
4. **确定性**：候选、项集、规则全部按字典序排序；支持数、置信度、提升度
   都用整数/分数计算，最后统一四舍五入到 6 位小数。

## 运行

```bash
# 0) 数据（仓库已带清洗后的数据，可跳过）
python tools/prepare_data.py --download

# 1) 单机版
python python/apriori_local.py \
  --input data/transactions.tsv \
  --min-support 0.005 --min-confidence 0.5 \
  --out-prefix out/local --timing out/local_timing.json

# 2) Spark 版（local[4] 或 standalone 伪分布式）
spark-submit --master local[4] spark/apriori_spark.py \
  --input data/transactions.tsv \
  --min-support 0.005 --min-confidence 0.5 \
  --out-prefix out/spark --timing out/spark_timing.json

# 3) 逐字节比较
python tools/compare_results.py --local out/local --spark out/spark --out out/compare.txt
```

或直接 `bash scripts/run_all.sh`。

## 结果

`min_support = 0.005`（支持数 ≥ 92 / 18 270）、`min_confidence = 0.5`：

| 项集大小 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 合计 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 频繁项集数 | 1 609 | 10 082 | 7 136 | 2 805 | 802 | 87 | 1 | **22 522** |

关联规则 **35 657** 条。单机与 Spark 输出逐字节一致：

```
频繁项集 22 522 行  sha256=435950d87334f2b1a83fac4fccfe4a12036755c39a36ccaa6c6c7cded33aa520
关联规则 35 657 行  sha256=dbafc37104bf1c93a928274e0737cb95ae88ecf4259088a72c59003c59088d67
```

典型规则（支持数 / 置信度 / 提升度）：

| 规则 | support | confidence | lift |
| --- | --- | --- | --- |
| `JUMBO BAG PINK POLKADOT` → `JUMBO BAG RED RETROSPOT` | 825 | 0.678 | 5.98 |
| `SET/6 COLLAGE PAPER CUPS` → `SET/6 COLLAGE PAPER PLATES` | 161 | 0.890 | 74.89 |
| `CHILDS GARDEN FORK BLUE` → `CHILDS GARDEN FORK PINK` | 93 | 0.727 | 99.06 |
| `{REGENCY TEA PLATE GREEN, REGENCY TEAPOT ROSES, REGENCY MILK JUG PINK}` → `{REGENCY TEA PLATE PINK, REGENCY SUGAR BOWL GREEN}` | 95 | 0.819 | 104.63 |

前三条说明同系列不同颜色/图案的商品会被一起购买；最后一条是 5 件商品的
“整套茶具”组合，提升度超过 100，说明它远不是独立购买行为。

## 性能（弱扩展）

把购物篮复制 4 / 8 份并打乱（支持度比例不变，项集和规则完全相同），
用于观察数据规模对并行效率的影响。计时单位为秒，取实际墙钟时间：

| 数据 | 购物篮 | 单机 | Spark local[4] | 加速比 |
| --- | --- | --- | --- | --- |
| 1x | 18 270 | 5.49 | 11.81 | 0.47 |
| 4x | 73 080 | 15.08 | 16.12 | 0.94 |
| 8x | 146 160 | 30.97 | 21.91 | **1.41** |

小数据下 Spark 的启动、任务调度和序列化开销占主导，单机反而更快；数据量
增大后并行的收益才显现。8x 数据下固定 4 个 Executor 核、只改并行度：

| 并行度 | local[1] | local[2] | local[4] |
| --- | --- | --- | --- |
| 墙钟时间 / s | 43.46 | 27.91 | 21.91 |
| 相对单核加速比 | 1.00 | 1.56 | **1.98** |

完整计时见 `out/benchmark.csv`，逐层耗时见 `out/compare.txt`。

## 环境

- Ubuntu 24.04 LTS（WSL2），4 个 vCPU、8 GB 内存
- OpenJDK 8、Python 3.12
- Spark 3.5.3（`local[4]`；另用 standalone 1 Master + 1 Worker 验证过同一脚本）
- 不依赖 Hadoop/HDFS，输入输出均为本地文件；把路径换成 `hdfs://...` 也可直接提交

> 实验报告（DOCX / PDF）按课程要求单独提交，不放在本仓库内。
