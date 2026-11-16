# bigdata-lab1：大数据系统基本实验

山东大学 计算机科学与技术学院《大数据管理与分析》课程 **实验一** 代码仓库。

内容包括三部分：

| 目录 / 文件 | 对应实验内容 |
| --- | --- |
| `scripts/01_linux_ops.sh` | 1.1 常用 Linux 命令（cd、ls、mkdir、rmdir、cp、mv、rm、cat、tac、more、head、tail、touch、chown、find、tar、grep） |
| `scripts/02_hdfs_basic.sh` | 1.2 启动 Hadoop、创建 `/user/hadoop` 目录、上传/下载 `test` 目录 |
| `src/main/java/.../hdfs/HDFSApp.java` | 2. HDFS 常用 Java API 编程（10 项功能） |
| `scripts/04_hdfs_shell.sh` | 2. 与 Java API 等价的 HDFS Shell 命令 |
| `src/main/java/.../mr/MergeDedup.java` | 3.1 文件合并与去重 |
| `src/main/java/.../mr/Sort.java` | 3.2 整数排序（输出 "名次 整数"） |
| `src/main/java/.../mr/GrandChild.java` | 3.3 child-parent 表挖掘祖孙关系 |
| `scripts/03_run_mapreduce.sh` | 编译、上传输入、运行三个 MapReduce 作业 |
| `input/` | 实验指导书中的样例输入文件 |
| `out/` | 三个作业的输出结果（与样例完全一致） |
| `tools/local_check.py` | 本地校验脚本：不启动 Hadoop，用 Python 复现 map/shuffle/reduce 语义核对输出 |

> 实验报告（DOCX / PDF）按课程要求单独提交，不放在本仓库内。

## 环境

- Ubuntu 20.04 LTS（VMware 虚拟机），JDK 1.8，Hadoop 3.3.4 伪分布式
- Maven 3.8（或直接使用 `hadoop classpath` + `javac`）

## 编译与运行

```bash
# 编译打包
mvn -q clean package            # 生成 target/bigdata-lab1.jar

# 第 1 部分：Linux 与 HDFS 基础操作
bash scripts/01_linux_ops.sh
bash scripts/02_hdfs_basic.sh

# 第 2 部分：HDFS Java API（10 项功能）
JAR=target/bigdata-lab1.jar
hadoop jar $JAR cn.sdu.bigdata.lab1.hdfs.HDFSApp mkdir /user/hadoop/lab1/hdfsdemo
hadoop jar $JAR cn.sdu.bigdata.lab1.hdfs.HDFSApp upload ~/.bashrc /user/hadoop/lab1/hdfsdemo/.bashrc overwrite
hadoop jar $JAR cn.sdu.bigdata.lab1.hdfs.HDFSApp stat   /user/hadoop/lab1/hdfsdemo/.bashrc
hadoop jar $JAR cn.sdu.bigdata.lab1.hdfs.HDFSApp lsr    /user/hadoop/lab1/hdfsdemo
hadoop jar $JAR cn.sdu.bigdata.lab1.hdfs.HDFSApp append /user/hadoop/lab1/hdfsdemo/.bashrc "hello" tail
hadoop jar $JAR cn.sdu.bigdata.lab1.hdfs.HDFSApp download /user/hadoop/lab1/hdfsdemo/.bashrc /tmp/download

# 第 3 部分：MapReduce
bash scripts/03_run_mapreduce.sh
```

## 未启动 Hadoop 时的本地校验

```bash
python3 tools/local_check.py
```

该脚本按 MapReduce 语义（map → 按 key 排序分组 → reduce）复现三个作业，输出与
`input/` 中样例的期望结果逐行一致，可用于在提交前确认逻辑正确。

## 三个作业的输出结果

`out/C.txt`（A 与 B 合并去重）：

```
20170101 x
20170101 y
20170102 y
20170103 x
20170104 y
20170104 z
20170105 y
20170105 z
20170106 x
```

`out/sorted.txt`（三个文件中的整数升序 + 名次）：

```
1	1
2	4
3	5
4	12
5	16
6	25
7	33
8	37
9	39
10	40
11	45
```

`out/grandchild.txt`（祖孙关系）：

```
Mark	Alice
Mark	Jesse
Philip	Alice
Philip	Jesse
Jone	Alice
Jone	Jesse
Steven	Alice
Steven	Jesse
Jone	Frank
Jone	Mary
Steven	Frank
Steven	Mary
```
