#!/bin/bash
# =============================================================================
# 实验一 第 1 部分：常用 Linux 命令演示脚本
# 用法：bash scripts/01_linux_ops.sh
# 说明：
#   1) 建议以 hadoop 用户运行；涉及 /usr、/ 目录写入和 chown 的命令需要 sudo 权限；
#   2) 每条命令前都会打印 "===" 分隔的说明，便于对照实验内容逐条检查。
# =============================================================================
set -u

show() { echo; echo "================ $* ================"; }

# ------------------------------------------------------------------ cd 命令
show "cd：(1) 切换到 /usr/local"
cd /usr/local && pwd

show "cd：(2) 切换到当前目录的上一级目录"
cd .. && pwd

show "cd：(3) 切换到当前登录用户的主文件夹"
cd ~ && pwd            # 等价于 cd 或 cd $HOME

# ---------------------------------------------------------------- ls 命令
show "ls：查看 /usr 下的所有文件和目录"
ls -l /usr

# -------------------------------------------------------------- mkdir 命令
show "mkdir：(1) 进入 /tmp，创建目录 a，并查看 /tmp 下已有目录"
cd /tmp && mkdir a && ls -l /tmp

show "mkdir：(2) 进入 /tmp，创建目录 a1/a2/a3/a4"
cd /tmp && mkdir -p a1/a2/a3/a4 && ls -R /tmp/a1

# ------------------------------------------------------------- rmdir 命令
show "rmdir：(1) 删除 /tmp 下的目录 a"
cd /tmp && rmdir a && ls /tmp

show "rmdir：(2) 删除 a1/a2/a3/a4（-p 逐级删除空目录），并查看 /tmp"
cd /tmp && rmdir -p a1/a2/a3/a4 && ls -l /tmp

# ---------------------------------------------------------------- cp 命令
show "cp：(1) 把 ~/.bashrc 复制到 /usr 下并重命名为 bashrc1"
sudo cp ~/.bashrc /usr/bashrc1 && ls -l /usr/bashrc1

show "cp：(2) 在 /tmp 下新建目录 test，并复制到 /usr 下"
mkdir -p /tmp/test && sudo cp -r /tmp/test /usr/ && ls -ld /usr/test

# ---------------------------------------------------------------- mv 命令
show "mv：(1) 把 /usr/bashrc1 移动到 /usr/test 目录下"
sudo mv /usr/bashrc1 /usr/test/ && ls -l /usr/test

show "mv：(2) 把 /usr/test 重命名为 test2"
sudo mv /usr/test /usr/test2 && ls -ld /usr/test2

# ---------------------------------------------------------------- rm 命令
show "rm：(1) 删除 /usr/test2 下的 bashrc1 文件"
sudo rm /usr/test2/bashrc1 && ls -l /usr/test2

show "rm：(2) 删除 /usr/test2 目录（目录需递归删除）"
sudo rm -r /usr/test2 && ls -ld /usr/test2 2>/dev/null || echo "test2 已删除"

# --------------------------------------------------------------- cat 命令
show "cat：查看 ~/.bashrc 的内容"
cat ~/.bashrc

# --------------------------------------------------------------- tac 命令
show "tac：反向查看 ~/.bashrc 的内容"
tac ~/.bashrc

# -------------------------------------------------------------- more 命令
show "more：一页一页翻动查看 ~/.bashrc（用空格翻页，q 退出）"
more ~/.bashrc

# -------------------------------------------------------------- head 命令
show "head：(1) 查看 ~/.bashrc 前 20 行"
head -n 20 ~/.bashrc

show "head：(2) 后面 50 行不显示，只显示前面部分"
head -n -50 ~/.bashrc

# -------------------------------------------------------------- tail 命令
show "tail：(1) 查看 ~/.bashrc 最后 20 行"
tail -n 20 ~/.bashrc

show "tail：(2) 只列出 50 行以后的数据"
tail -n +51 ~/.bashrc

# ------------------------------------------------------------- touch 命令
show "touch：(1) 在 /tmp 下创建空文件 hello，并查看文件时间"
touch /tmp/hello && ls -l --time=atime --time-style=long-iso /tmp/hello

show "touch：(2) 把 hello 的文件时间改为 5 天前"
touch -d "5 days ago" /tmp/hello && ls -l --time-style=long-iso /tmp/hello

# ------------------------------------------------------------- chown 命令
show "chown：把 hello 文件的所有者改为 root，并查看属性"
sudo chown root /tmp/hello && ls -l /tmp/hello

# -------------------------------------------------------------- find 命令
show "find：找出主文件夹下文件名为 .bashrc 的文件"
find ~ -name ".bashrc"

# --------------------------------------------------------------- tar 命令
show "tar：(1) 在 / 下新建文件夹 test，并在 / 下打包成 test.tar.gz"
sudo mkdir -p /test && sudo touch /test/demo.txt
sudo tar -zcvf /test.tar.gz /test && ls -l /test.tar.gz

show "tar：(2) 把 test.tar.gz 解压缩到 /tmp 目录"
sudo tar -zxvf /test.tar.gz -C /tmp && ls -l /tmp/test

# -------------------------------------------------------------- grep 命令
show "grep：从 ~/.bashrc 中查找字符串 examples"
grep -n "examples" ~/.bashrc

show "全部演示命令执行完毕"
