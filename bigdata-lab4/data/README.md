# 数据集说明

## 来源

UCI Machine Learning Repository：**Online Retail**。

> Daqing Chen, Sai Liang Sain, Kun Guo. Online Retail.
> UCI Machine Learning Repository, 2015. DOI: [10.24432/C5BW33](https://doi.org/10.24432/C5BW33)

原始文件是 2010-12-01 至 2011-12-09 一家英国在线零售商的交易明细，共
541 909 行、8 列（发票号、商品编码、商品描述、数量、单价、客户号、国家等）。
原始 Excel 体积约 23 MB，不纳入仓库；运行
`python tools/prepare_data.py --download` 可自动下载。

## 清洗与转换

`tools/prepare_data.py` 依次执行：

1. 去掉取消单（`InvoiceNo` 以 `C` 开头）、数量 ≤ 0 的退货/调账行；
2. 只保留 5 位数字（可带 1 个字母后缀）的商品编码，去掉 `POST`、`D`、`M`、
   `BANK CHARGES`、`AMAZONFEE` 等非商品行；去掉单价 ≤ 0 的行；
3. 按发票号聚合，同一商品在一次交易中只计一次；
4. 只保留至少 2 种商品的购物篮。

清洗结果：

| 指标 | 数值 |
| --- | --- |
| 原始行数 | 541 909 |
| 清洗后行数 | 525 462 |
| 发票数 | 19 769 |
| 购物篮数（≥ 2 种商品） | 18 270 |
| 不同商品数 | 3 784 |
| 商品出现总次数 | 513 506 |
| 平均/中位/最大购物篮 | 28.11 / 17 / 1 097 |
| 国家数 | 38 |
| 日期范围 | 2010-12-01 ~ 2011-12-09 |

## 文件

- `transactions.tsv`：一行一个购物篮，商品编码按字典序排列、制表符分隔；
- `items.tsv`：`code`、`description`、`baskets` 三列，描述取该编码出现最多的文本；
- `dataset_stats.json`：上述统计量，供报告和脚本直接读取。

## 许可

数据版权归原发布者所有，仅用于课程实验与学习。使用时请引用上述 UCI 数据集。
