package edu.sdu.bigdata.invertedindex;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;

/**
 * 停词表（stop word list）。
 *
 * 停词表不在 MapReduce 数据流里，而是一份"边数据"（side data）：
 * 每个 map 任务启动时加载一次并缓存在 JVM 静态字段中，
 * 同一个 JVM 上后续的任务不会再重复读取 HDFS。
 */
public final class StopwordDictionary {

    /** 停词表位置：可以是 HDFS 路径，也可以是本地路径。 */
    public static final String STOPWORDS_CONF = "invertedindex.stopwords.path";

    /** 默认停词表位置（相对作业提交目录）。 */
    public static final String DEFAULT_PATH = "stopwords/stopwords_en.txt";

    private static volatile Set<String> cached;

    private StopwordDictionary() {
    }

    /** 获取（必要时加载）停词表。 */
    public static Set<String> get(Configuration conf) throws IOException {
        Set<String> local = cached;
        if (local == null) {
            synchronized (StopwordDictionary.class) {
                local = cached;
                if (local == null) {
                    local = load(conf);
                    cached = local;
                }
            }
        }
        return local;
    }

    private static Set<String> load(Configuration conf) throws IOException {
        String location = conf.get(STOPWORDS_CONF, DEFAULT_PATH);
        Set<String> words = new HashSet<>();

        try (InputStream in = open(conf, location);
             BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String word = line.trim().toLowerCase(Locale.ROOT);
                // 支持 # 开头的注释行与空行
                if (word.isEmpty() || word.charAt(0) == '#') {
                    continue;
                }
                words.add(word);
            }
        }
        if (words.isEmpty()) {
            throw new IOException("stop word list is empty: " + location);
        }
        return Collections.unmodifiableSet(words);
    }

    /**
     * 依次尝试：HDFS/本地文件系统路径 → DistributedCache 本地化副本。
     * 这样同一份代码在伪分布式（HDFS 路径）和 LocalJobRunner（本地路径）下都能跑。
     */
    private static InputStream open(Configuration conf, String location) throws IOException {
        Path path = new Path(location);
        FileSystem fs = path.getFileSystem(conf);
        if (fs.exists(path)) {
            return fs.open(path);
        }
        // DistributedCache 会把文件软链接到任务的工作目录，文件名即 path.getName()
        File localized = new File(path.getName());
        if (localized.exists()) {
            return new FileInputStream(localized);
        }
        throw new IOException("stop word list not found: " + location);
    }

    /** 清空缓存，仅供单元测试使用。 */
    static void reset() {
        cached = null;
    }
}
