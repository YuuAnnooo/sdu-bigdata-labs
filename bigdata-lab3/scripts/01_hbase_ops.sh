#!/usr/bin/env bash
# 实验三 第一部分：HBase 常用操作（Shell 版）
# 说明：本脚本只做演示记录，逐段执行；每段前面注释写的是"实验内容"中的对应任务。
set -e

# ============================================================ 0. 启动 HBase
start-hbase.sh
jps                       # 应看到 HMaster 与 HRegionServer
hbase shell <<'EOF'
status                    # 集群状态、版本
EOF

# ============================================================ 1. 列出所有表
hbase shell <<'EOF'
list
EOF

# ============================================================ 2. 创建大作业用到的三张表
#    student : 列族 Info（姓名/性别/年龄）、Score（各门课成绩）
#    course  : 列族 Info（课程名/学分）
#    sc      : 列族 Score（成绩）
hbase shell <<'EOF'
create 'student', 'Info', 'Score'
create 'course',  'Info'
create 'sc', 'Score'
list
EOF

# ============================================================ 3. 插入数据
hbase shell <<'EOF'
put 'student', '2015001', 'Info:name', 'Zhangsan'
put 'student', '2015001', 'Info:sex',  'male'
put 'student', '2015001', 'Info:age',  '23'
put 'student', '2015002', 'Info:name', 'Mary'
put 'student', '2015002', 'Info:sex',  'female'
put 'student', '2015002', 'Info:age',  '22'
put 'student', '2015003', 'Info:name', 'Lisi'
put 'student', '2015003', 'Info:sex',  'male'
put 'student', '2015003', 'Info:age',  '24'

put 'student', '2015001', 'Score:Math', '86'
put 'student', '2015001', 'Score:English', '69'
put 'student', '2015002', 'Score:Computer Science', '77'
put 'student', '2015002', 'Score:English', '99'
put 'student', '2015003', 'Score:Math', '98'
put 'student', '2015003', 'Score:Computer Science', '95'

put 'course', '123001', 'Info:name', 'Math'
put 'course', '123001', 'Info:credit', '2.0'
put 'course', '123002', 'Info:name', 'Computer Science'
put 'course', '123002', 'Info:credit', '5.0'
put 'course', '123003', 'Info:name', 'English'
put 'course', '123003', 'Info:credit', '3.0'

put 'sc', '2015001_123001', 'Score:score', '86'
put 'sc', '2015001_123003', 'Score:score', '69'
put 'sc', '2015002_123002', 'Score:score', '77'
put 'sc', '2015002_123003', 'Score:score', '99'
put 'sc', '2015003_123001', 'Score:score', '98'
put 'sc', '2015003_123002', 'Score:score', '95'
EOF

# ============================================================ 4. 显示指定表的全部记录
hbase shell <<'EOF'
scan 'student'
EOF
# 也可以只看某一行的某几列
hbase shell <<'EOF'
get 'student', '2015001', {COLUMNS => ['Info', 'Score']}
EOF

# ============================================================ 5. 增加/删除列族或列
hbase shell <<'EOF'
# 增加列族 Email
alter 'student', NAME => 'Email'
describe 'student'
# 在新增的列族里写数据（列不需要事先定义，put 时自动出现）
put 'student', '2015001', 'Email:school', 'zhangsan@sdu.edu.cn'

# 删除某个单元格（某行某列）
delete 'student', '2015002', 'Score:English'
get 'student', '2015002'

# 删除整个列族
alter 'student', NAME => 'Email', METHOD => 'delete'
describe 'student'
EOF

# ============================================================ 6. 统计表的行数
hbase shell <<'EOF'
count 'student'
count 'student', INTERVAL => 1
EOF

# ============================================================ 7. 清空表
hbase shell <<'EOF'
truncate 'sc'
count 'sc'
EOF

# ============================================================ 8. 删除表
hbase shell <<'EOF'
disable 'sc'
drop 'sc'
list
EOF

# 全部任务结束后可以关闭 HBase
# stop-hbase.sh
