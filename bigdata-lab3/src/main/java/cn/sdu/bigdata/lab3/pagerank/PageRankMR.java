package cn.sdu.bigdata.lab3.pagerank;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.DoubleWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

/**
 * 实验三 第二部分：PageRank 的 MapReduce 实现。
 *
 * 迭代公式（归一化形式，所有页面的 PR 之和恒为 1）：
 *     PR(p) = (1 - d) / N + d * ( Σ_{q -> p} PR(q) / outDegree(q) + PR_dangling / N )
 * 其中 d 为阻尼系数（0.85），N 为页面总数，PR_dangling 为所有悬挂页面
 * （没有出链）的 PR 之和。悬挂页面的 PR 平均分给所有页面，避免概率漏出。
 *
 * 用法：
 *   hadoop jar bigdata-lab3.jar cn.sdu.bigdata.lab3.pagerank.PageRankMR \
 *       <输入目录或文件> <输出目录> [迭代次数，默认 10]
 *
 * 每轮迭代都是一个完整的 MapReduce 作业：
 *   map    ：读入一行"网页 + 出链集合"，从缓存中取出该网页当前的 PR，
 *            把 PR / 出链数 作为贡献发给每个出链；
 *   shuffle：框架按 key（网页）分组，同一个网页的所有入链贡献进入同一次 reduce；
 *   reduce ：累加贡献，套用上面的公式算出新 PR，写成一列"网页 \t 新PR"。
 */
public class PageRankMR {

    /** 阻尼系数 */
    public static final double DAMPING = 0.85;
    /** 页面总数，由 Driver 读取图数据后写入 Configuration */
    public static final String CONF_N = "pagerank.nPages";
    /** 缓存文件的本地化名字 */
    public static final String CACHE_NAME = "pagerank_state.txt";

    // ------------------------------------------------------------ 迭代作业

    /** map：分发当前 PR 值 */
    public static class DistributeMapper extends Mapper<LongWritable, Text, Text, DoubleWritable> {

        private final Map<String, Double> prValues = new HashMap<String, Double>();
        private final List<String> allPages = new ArrayList<String>();
        private final Text outKey = new Text();
        private final DoubleWritable outValue = new DoubleWritable();
        private int nPages = 1;

        @Override
        protected void setup(Context context) throws IOException {
            nPages = context.getConfiguration().getInt(CONF_N, 1);
            // 从分布式缓存读出上一轮的 PR 结果：每行 "网页 \t PR值"
            URI[] cacheFiles = context.getCacheFiles();
            if (cacheFiles == null || cacheFiles.length == 0) {
                throw new IOException("缺少上一轮 PR 结果，请在 Driver 中调用 addCacheFile");
            }
            FileSystem fs = FileSystem.get(cacheFiles[0], context.getConfiguration());
            Path path = new Path(cacheFiles[0].getPath());
            BufferedReader reader = new BufferedReader(new InputStreamReader(fs.open(path), "UTF-8"));
            try {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty()) {
                        continue;
                    }
                    int tab = line.indexOf('\t');
                    if (tab < 0) {
                        continue;
                    }
                    String page = line.substring(0, tab);
                    prValues.put(page, Double.parseDouble(line.substring(tab + 1).trim()));
                    allPages.add(page);
                }
            } finally {
                reader.close();
            }
        }

        @Override
        protected void map(LongWritable key, Text value, Context context)
                throws IOException, InterruptedException {
            String line = value.toString().trim();
            if (line.isEmpty()) {
                return;
            }
            int tab = line.indexOf('\t');
            String page = (tab < 0) ? line : line.substring(0, tab);
            List<String> links = new ArrayList<String>();
            if (tab >= 0) {
                for (String s : line.substring(tab + 1).split(",")) {
                    s = s.trim();
                    if (!s.isEmpty()) {
                        links.add(s);
                    }
                }
            }
            Double pr = prValues.get(page);
            if (pr == null) {                 // 图里出现、上一轮结果里没有（理论上不会发生）
                pr = 1.0 / nPages;
            }
            // 自留一个 0 贡献：保证没有任何入链的页面也能出现在本轮结果中，不会“消失”
            outKey.set(page);
            outValue.set(0.0);
            context.write(outKey, outValue);

            if (links.isEmpty()) {
                // 悬挂页面：把它自己的 PR 平均分给所有页面
                double share = pr / nPages;
                outValue.set(share);
                for (String p : allPages) {
                    outKey.set(p);
                    context.write(outKey, outValue);
                }
            } else {
                outValue.set(pr / links.size());
                for (String link : links) {
                    outKey.set(link);
                    context.write(outKey, outValue);
                }
            }
        }
    }

    /** reduce：累加贡献并套用 PageRank 公式 */
    public static class RankReducer extends Reducer<Text, DoubleWritable, Text, DoubleWritable> {

        private int nPages = 1;
        private final DoubleWritable outValue = new DoubleWritable();

        @Override
        protected void setup(Context context) {
            nPages = context.getConfiguration().getInt(CONF_N, 1);
        }

        @Override
        protected void reduce(Text key, Iterable<DoubleWritable> values, Context context)
                throws IOException, InterruptedException {
            double sum = 0.0;
            for (DoubleWritable v : values) {
                sum += v.get();
            }
            // 注意：悬挂页面的份额已经在 map 端平摊到每个页面，这里的 sum 已包含它
            double newPr = (1 - DAMPING) / nPages + DAMPING * sum;
            outValue.set(newPr);
            context.write(key, outValue);
        }
    }

    // ------------------------------------------------------------ 初始化作业

    /** 初始化：每行"网页 \t 出链"→ "网页 \t 1/N"（map-only，不需要 reduce） */
    public static class InitMapper extends Mapper<LongWritable, Text, Text, DoubleWritable> {

        private int nPages = 1;
        private final Text outKey = new Text();
        private final DoubleWritable outValue = new DoubleWritable();

        @Override
        protected void setup(Context context) {
            nPages = context.getConfiguration().getInt(CONF_N, 1);
            outValue.set(1.0 / nPages);
        }

        @Override
        protected void map(LongWritable key, Text value, Context context)
                throws IOException, InterruptedException {
            String line = value.toString().trim();
            if (line.isEmpty()) {
                return;
            }
            int tab = line.indexOf('\t');
            outKey.set(tab < 0 ? line : line.substring(0, tab));
            context.write(outKey, outValue);
        }
    }

    // ------------------------------------------------------------ 输出格式作业

    /**
     * 排序输出：最后一轮的结果 "网页 \t PR值" 直接作为输入，所有记录进入同一个
     * Reducer，按 PR 从大到小排序后输出实验要求的 "(网页,PR值)" 格式，PR 保留 10 位小数。
     */
    public static class FormatReducer extends Reducer<NullWritable, Text, Text, NullWritable> {

        private final List<Map.Entry<String, Double>> ranks = new ArrayList<Map.Entry<String, Double>>();

        @Override
        protected void reduce(NullWritable key, Iterable<Text> values, Context context) {
            for (Text v : values) {
                String s = v.toString();
                int tab = s.indexOf('\t');
                if (tab < 0) {
                    continue;
                }
                ranks.add(new java.util.AbstractMap.SimpleEntry<String, Double>(
                        s.substring(0, tab), Double.parseDouble(s.substring(tab + 1).trim())));
            }
        }

        @Override
        protected void cleanup(Context context) throws IOException, InterruptedException {
            Collections.sort(ranks, new Comparator<Map.Entry<String, Double>>() {
                @Override
                public int compare(Map.Entry<String, Double> a, Map.Entry<String, Double> b) {
                    int c = Double.compare(b.getValue(), a.getValue());   // PR 降序
                    return c != 0 ? c : a.getKey().compareTo(b.getKey()); // PR 相同按页面名升序
                }
            });
            for (Map.Entry<String, Double> e : ranks) {
                context.write(new Text(String.format("(%s,%.10f)", e.getKey(), e.getValue())),
                        NullWritable.get());
            }
        }
    }

    // ------------------------------------------------------------ Driver

    /** 统计图里有多少个页面：小规模数据集直接读文件，页面上亿时改用计数作业 */
    static int countPages(Configuration conf, Path input) throws IOException {
        FileSystem fs = FileSystem.get(conf);
        List<Path> files = new ArrayList<Path>();
        if (fs.isDirectory(input)) {
            for (org.apache.hadoop.fs.FileStatus st : fs.listStatus(input)) {
                String name = st.getPath().getName();
                // 跳过 _SUCCESS 之类的隐藏文件
                if (!name.startsWith("_") && !name.startsWith(".")) {
                    files.add(st.getPath());
                }
            }
        } else {
            files.add(input);
        }
        int n = 0;
        for (Path f : files) {
            BufferedReader reader = new BufferedReader(new InputStreamReader(fs.open(f), "UTF-8"));
            try {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (!line.trim().isEmpty()) {
                        n++;
                    }
                }
            } finally {
                reader.close();
            }
        }
        return n;
    }

    /** 把上一轮输出目录中的结果文件路径取出来，用于分布式缓存 */
    static Path resultFile(Configuration conf, Path dir) throws IOException {
        FileSystem fs = FileSystem.get(conf);
        for (org.apache.hadoop.fs.FileStatus st : fs.listStatus(dir)) {
            if (st.getPath().getName().startsWith("part-")) {
                return st.getPath();
            }
        }
        throw new IOException("目录中没有 result 文件: " + dir);
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("用法: PageRankMR <输入路径> <输出目录> [迭代次数]");
            System.exit(2);
        }
        Path input = new Path(args[0]);
        Path output = new Path(args[1]);
        int iterations = args.length > 2 ? Integer.parseInt(args[2]) : 10;

        Configuration conf = new Configuration();
        FileSystem fs = FileSystem.get(conf);
        int nPages = countPages(conf, input);
        conf.setInt(CONF_N, nPages);
        System.out.println("[PageRank] 页面数 N = " + nPages + "，迭代次数 = " + iterations
                + "，阻尼系数 d = " + DAMPING);

        if (fs.exists(output)) {
            fs.delete(output, true);
        }
        Path state = new Path(output, "iter0");

        // 第 0 轮：初始化 PR = 1/N
        Job init = Job.getInstance(conf, "pagerank-init");
        init.setJarByClass(PageRankMR.class);
        init.setMapperClass(InitMapper.class);
        init.setNumReduceTasks(0);
        init.setOutputKeyClass(Text.class);
        init.setOutputValueClass(DoubleWritable.class);
        FileInputFormat.addInputPath(init, input);
        FileOutputFormat.setOutputPath(init, state);
        if (!init.waitForCompletion(true)) {
            System.exit(1);
        }

        // 第 1..k 轮：一次迭代一个作业
        for (int i = 1; i <= iterations; i++) {
            Path next = new Path(output, "iter" + i);
            Job job = Job.getInstance(conf, "pagerank-" + i);
            job.setJarByClass(PageRankMR.class);
            job.setMapperClass(DistributeMapper.class);
            job.setReducerClass(RankReducer.class);
            job.setOutputKeyClass(Text.class);
            job.setOutputValueClass(DoubleWritable.class);
            job.addCacheFile(resultFile(conf, state).toUri());
            FileInputFormat.addInputPath(job, input);
            FileOutputFormat.setOutputPath(job, next);
            long start = System.currentTimeMillis();
            if (!job.waitForCompletion(true)) {
                System.err.println("[PageRank] 第 " + i + " 轮失败");
                System.exit(1);
            }
            System.out.printf("[PageRank] 第 %d 轮完成，用时 %d ms%n",
                    i, System.currentTimeMillis() - start);
            state = next;
        }

        // 收尾：以最后一轮的结果为输入，排序 + 格式化输出 (网页,PR值)
        Path result = new Path(output, "result");
        Job format = Job.getInstance(conf, "pagerank-format");
        format.setJarByClass(PageRankMR.class);
        format.setMapperClass(FormatMapper.class);
        format.setReducerClass(FormatReducer.class);
        format.setNumReduceTasks(1);          // 全局排序，必须只有一个 Reducer
        format.setMapOutputKeyClass(NullWritable.class);
        format.setMapOutputValueClass(Text.class);
        format.setOutputKeyClass(Text.class);
        format.setOutputValueClass(NullWritable.class);
        FileInputFormat.addInputPath(format, state);
        FileOutputFormat.setOutputPath(format, result);
        if (!format.waitForCompletion(true)) {
            System.exit(1);
        }
        System.out.println("[PageRank] 结果目录: " + result);
    }

    /** 格式化作业的 map 端：把 "网页 \t PR值" 原样交给唯一的 Reducer 排序 */
    public static class FormatMapper extends Mapper<LongWritable, Text, NullWritable, Text> {

        private final Text outValue = new Text();

        @Override
        protected void map(LongWritable key, Text value, Context context)
                throws IOException, InterruptedException {
            String line = value.toString().trim();
            if (line.isEmpty()) {
                return;
            }
            outValue.set(line);
            context.write(NullWritable.get(), outValue);
        }
    }
}
