package cn.sdu.bigdata.lab1.hdfs;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FSDataInputStream;
import org.apache.hadoop.fs.FSDataOutputStream;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IOUtils;

/**
 * 实验一 第 2 部分：HDFS 常用 Java API 编程实现（与 Shell 命令等价）。
 *
 * 编译： mvn -q clean package
 * 运行： hadoop jar target/bigdata-lab1.jar cn.sdu.bigdata.lab1.hdfs.HDFSApp <子命令> ...
 *
 * 子命令一览（对应实验内容中的 10 项要求）：
 *   1  upload   <本地路径> <HDFS路径> <append|overwrite>   上传，已存在时由用户选择追加或覆盖
 *   2  download <HDFS路径> <本地目录>                      下载，同名文件自动重命名
 *   3  cat      <HDFS文件>                                 输出到终端
 *   4  stat     <HDFS路径>                                 显示权限/大小/创建时间/路径
 *   5  lsr      <HDFS目录>                                 递归显示目录下所有文件的信息
 *   6  touch    <HDFS文件>                                 创建文件（父目录不存在则自动创建）
 *   6  rm       <HDFS文件>                                 删除文件
 *   7  mkdir    <HDFS目录>                                 创建目录（父目录不存在则自动创建）
 *   7  rmdir    <HDFS目录>                                 仅在目录为空时删除
 *   8  append   <HDFS文件> <内容> <head|tail>              在文件开头或结尾追加内容
 *   9  del      <HDFS文件>                                 删除指定文件
 *  10  mv       <源路径> <目的路径>                        移动文件
 */
public class HDFSApp {

    /** 伪分布式/集群的 NameNode 地址，与 core-site.xml 中 fs.defaultFS 保持一致 */
    private static final String DEFAULT_FS = "hdfs://localhost:9000";
    private static final String USER = "hadoop";

    private static FileSystem fs;

    public static void main(String[] args) {
        if (args.length == 0) {
            usage();
            System.exit(1);
        }
        Configuration conf = new Configuration();
        conf.set("fs.defaultFS", DEFAULT_FS);
        try {
            fs = FileSystem.get(URI.create(DEFAULT_FS), conf, USER);
            String cmd = args[0].toLowerCase();
            switch (cmd) {
                case "upload":   upload(args[1], new Path(args[2]), args[3]); break;
                case "download": download(new Path(args[1]), new Path(args[2])); break;
                case "cat":      cat(new Path(args[1])); break;
                case "stat":     stat(new Path(args[1])); break;
                case "lsr":      listRecursive(new Path(args[1])); break;
                case "touch":    touch(new Path(args[1])); break;
                case "rm":
                case "del":      deleteFile(new Path(args[1])); break;
                case "mkdir":    makeDir(new Path(args[1])); break;
                case "rmdir":    removeEmptyDir(new Path(args[1])); break;
                case "append":   append(args[1], args[2], args[3]); break;
                case "mv":       move(new Path(args[1]), new Path(args[2])); break;
                default:         usage(); System.exit(1);
            }
        } catch (Exception e) {
            System.err.println("执行失败：" + e.getMessage());
            e.printStackTrace();
        } finally {
            IOUtils.closeStream(fs);
        }
    }

    private static void usage() {
        System.out.println("用法: HDFSApp <upload|download|cat|stat|lsr|touch|rm|mkdir|rmdir|append|mv> ...");
        System.out.println("  upload   <本地路径> <HDFS路径> <append|overwrite>");
        System.out.println("  download <HDFS路径> <本地目录>");
    }

    // ---------------------------------------------------------- 1. 上传
    private static void upload(String local, Path dst, String mode) throws IOException {
        Path src = new Path(local);
        if (!(new java.io.File(local)).exists()) {
            System.err.println("本地文件不存在：" + local);
            return;
        }
        if ("append".equalsIgnoreCase(mode)) {
            if (!fs.exists(dst)) {
                // 目标不存在时直接上传即可
                fs.copyFromLocalFile(false, false, src, dst);
                System.out.println("目标文件不存在，已直接上传：" + dst);
            } else {
                // 追加：把本地文件内容写入目标文件末尾
                try (OutputStream out = fs.append(dst)) {
                    copyLocalTo(src, out);
                }
                System.out.println("已追加到原有文件末尾：" + dst);
            }
        } else if ("overwrite".equalsIgnoreCase(mode)) {
            fs.copyFromLocalFile(false, true, src, dst);
            System.out.println("已覆盖原有文件：" + dst);
        } else {
            System.err.println("mode 只能是 append 或 overwrite");
            return;
        }
        stat(dst);
    }

    // ---------------------------------------------------------- 2. 下载（同名自动重命名）
    private static void download(Path src, Path localDir) throws IOException {
        if (!fs.exists(src)) {
            System.err.println("HDFS 文件不存在：" + src);
            return;
        }
        java.io.File dir = new java.io.File(localDir.toUri().getPath());
        if (!dir.exists() && !dir.mkdirs()) {
            System.err.println("无法创建本地目录：" + dir);
            return;
        }
        java.io.File target = new java.io.File(dir, src.getName());
        // 本地已存在同名文件时自动重命名：a.txt -> a_1.txt -> a_2.txt ...
        int i = 0;
        while (target.exists()) {
            i++;
            String name = src.getName();
            int dot = name.lastIndexOf('.');
            String renamed = (dot > 0)
                    ? name.substring(0, dot) + "_" + i + name.substring(dot)
                    : name + "_" + i;
            target = new java.io.File(dir, renamed);
        }
        fs.copyToLocalFile(false, src, new Path(target.getAbsolutePath()), true);
        System.out.println("已下载到本地：" + target.getAbsolutePath());
    }

    // ---------------------------------------------------------- 3. 输出到终端
    private static void cat(Path path) throws IOException {
        if (!fs.exists(path)) {
            System.err.println("文件不存在：" + path);
            return;
        }
        try (FSDataInputStream in = fs.open(path);
             BufferedReader reader = new BufferedReader(
                     new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }
        }
    }

    // ---------------------------------------------------------- 4. 文件详细信息
    private static void stat(Path path) throws IOException {
        if (!fs.exists(path)) {
            System.err.println("路径不存在：" + path);
            return;
        }
        FileStatus st = fs.getFileStatus(path);
        System.out.printf("%-10s %-8s %-12s %-20s %s%n",
                "权限", "大小(字节)", "副本数", "修改时间", "路径");
        System.out.println(describe(st));
    }

    private static String describe(FileStatus st) {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String perm = st.getPermission().toString();
        String size = st.isDirectory() ? "-" : String.valueOf(st.getLen());
        String rep = st.isDirectory() ? "-" : String.valueOf(st.getReplication());
        String time = sdf.format(new Date(st.getModificationTime()));
        return String.format("%-10s %-8s %-12s %-20s %s", perm, size, rep, time, st.getPath());
    }

    // ---------------------------------------------------------- 5. 递归列出目录
    private static void listRecursive(Path dir) throws IOException {
        if (!fs.exists(dir)) {
            System.err.println("目录不存在：" + dir);
            return;
        }
        if (!fs.getFileStatus(dir).isDirectory()) {
            System.err.println("不是目录：" + dir);
            return;
        }
        FileStatus[] list = fs.listStatus(dir);
        for (FileStatus st : list) {
            if (st.isDirectory()) {
                listRecursive(st.getPath());
            } else {
                System.out.println(describe(st));
            }
        }
    }

    // ---------------------------------------------------------- 6. 创建文件（父目录自动创建）
    private static void touch(Path file) throws IOException {
        Path parent = file.getParent();
        if (parent != null && !fs.exists(parent)) {
            fs.mkdirs(parent);
            System.out.println("父目录不存在，已自动创建：" + parent);
        }
        if (fs.exists(file)) {
            System.out.println("文件已存在，内容保持不变：" + file);
        } else {
            // create 不带 overwrite 参数时，文件已存在会抛异常，这里先判断
            try (OutputStream out = fs.create(file)) {
                out.write("hello hdfs\n".getBytes(StandardCharsets.UTF_8));
            }
            System.out.println("文件已创建：" + file);
        }
        stat(file);
    }

    // ---------------------------------------------------------- 6/9. 删除文件
    private static void deleteFile(Path file) throws IOException {
        if (!fs.exists(file)) {
            System.err.println("文件不存在：" + file);
            return;
        }
        if (fs.getFileStatus(file).isDirectory()) {
            System.err.println("这是目录，请用 rmdir：" + file);
            return;
        }
        if (fs.delete(file, false)) {
            System.out.println("已删除文件：" + file);
        } else {
            System.err.println("删除失败：" + file);
        }
    }

    // ---------------------------------------------------------- 7. 创建目录（父目录自动创建）
    private static void makeDir(Path dir) throws IOException {
        if (fs.exists(dir)) {
            System.out.println("目录已存在：" + dir);
            return;
        }
        if (fs.mkdirs(dir)) {          // mkdirs 会自动创建所有不存在的父目录
            System.out.println("目录已创建（缺失的父目录已一并创建）：" + dir);
        } else {
            System.err.println("创建失败：" + dir);
        }
    }

    // ---------------------------------------------------------- 7. 删除空目录
    private static void removeEmptyDir(Path dir) throws IOException {
        if (!fs.exists(dir)) {
            System.err.println("目录不存在：" + dir);
            return;
        }
        if (!fs.getFileStatus(dir).isDirectory()) {
            System.err.println("不是目录：" + dir);
            return;
        }
        // 目录非空时 listStatus 长度不为 0，直接拒绝删除
        if (fs.listStatus(dir).length > 0) {
            System.err.println("目录非空，不予删除：" + dir);
            return;
        }
        if (fs.delete(dir, false)) {   // recursive=false，非空会抛异常，这里已提前判断
            System.out.println("已删除空目录：" + dir);
        } else {
            System.err.println("删除失败：" + dir);
        }
    }

    // ---------------------------------------------------------- 8. 追加内容到开头或结尾
    private static void append(String pathStr, String content, String position) throws IOException {
        Path path = new Path(pathStr);
        if (!fs.exists(path)) {
            System.err.println("文件不存在：" + path);
            return;
        }
        if ("tail".equalsIgnoreCase(position)) {
            // 末尾追加：HDFS 原生支持 append
            try (OutputStream out = fs.append(path)) {
                out.write((content + "\n").getBytes(StandardCharsets.UTF_8));
            }
            System.out.println("已在文件末尾追加内容");
        } else if ("head".equalsIgnoreCase(position)) {
            // 开头追加：HDFS 不支持随机写，只能读出全文 -> 重写
            List<String> lines = new ArrayList<>();
            try (FSDataInputStream in = fs.open(path);
                 BufferedReader reader = new BufferedReader(
                         new InputStreamReader(in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    lines.add(line);
                }
            }
            try (FSDataOutputStream out = fs.create(path, true)) {
                out.write((content + "\n").getBytes(StandardCharsets.UTF_8));
                for (String line : lines) {
                    out.write((line + "\n").getBytes(StandardCharsets.UTF_8));
                }
            }
            System.out.println("已在文件开头追加内容（读取全文后重写）");
        } else {
            System.err.println("position 只能是 head 或 tail");
            return;
        }
        cat(path);
    }

    // ---------------------------------------------------------- 10. 移动
    private static void move(Path src, Path dst) throws IOException {
        if (!fs.exists(src)) {
            System.err.println("源路径不存在：" + src);
            return;
        }
        if (fs.rename(src, dst)) {
            System.out.println("已移动：" + src + " -> " + dst);
        } else {
            System.err.println("移动失败（目标可能已存在）");
        }
    }

    // ---------------------------------------------------------- 工具方法
    private static void copyLocalTo(Path src, OutputStream out) throws IOException {
        java.io.File file = new java.io.File(src.toUri().getPath());
        java.io.InputStream in = new java.io.FileInputStream(file);
        try {
            IOUtils.copyBytes(in, out, 4096, false);
        } finally {
            IOUtils.closeStream(in);
        }
    }
}
