package edu.sdu.bigdata.invertedindex;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * 倒排索引驱动程序：串联两个 MapReduce 作业。
 *
 * <pre>
 *   usages: hadoop jar inverted-index.jar &lt;input&gt; &lt;output&gt; [stopwords]
 *
 *   stage1: (行) --map--> ((word,doc),1) --combine/reduce--> (word\tdoc, count)
 *   stage2: (word\tdoc\tcount) --map--> (word, doc:count) --reduce--> 词 → 倒排表
 * </pre>
 */
public class InvertedIndexDriver extends Configured implements Tool {

    private static final String USAGE =
            "usages: hadoop jar inverted-index.jar <input-dir> <output-dir> [stopword-file]";

    @Override
    public int run(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println(USAGE);
            return 2;
        }
        Path input = new Path(args[0]);
        Path output = new Path(args[1]);
        Path stage1Output = new Path(output, "stage1");
        Path stage2Output = new Path(output, "stage2");

        Configuration conf = getConf();
        if (args.length >= 3) {
            conf.set(StopwordDictionary.STOPWORDS_CONF, args[2]);
        }

        FileSystem fs = output.getFileSystem(conf);
        if (fs.exists(output)) {
            // 输出目录必须预先不存在，这里主动清理，避免反复调试时手动删除
            fs.delete(output, true);
        }

        // ---------- 作业一：分词 + 停词过滤 + 词频统计 ----------
        Job stage1 = Job.getInstance(conf, "inverted-index stage1: tokenize & count");
        stage1.setJarByClass(InvertedIndexDriver.class);
        stage1.setMapperClass(TokenizeMapper.class);
        stage1.setCombinerClass(SumReducer.class);
        stage1.setReducerClass(SumReducer.class);
        stage1.setMapOutputKeyClass(Text.class);
        stage1.setMapOutputValueClass(IntWritable.class);
        stage1.setOutputKeyClass(Text.class);
        stage1.setOutputValueClass(IntWritable.class);
        stage1.setOutputFormatClass(TextOutputFormat.class);
        FileInputFormat.addInputPath(stage1, input);
        FileOutputFormat.setOutputPath(stage1, stage1Output);

        long start = System.currentTimeMillis();
        if (!stage1.waitForCompletion(true)) {
            System.err.println("stage1 failed");
            return 1;
        }

        // ---------- 作业二：按单词聚合倒排表 ----------
        Job stage2 = Job.getInstance(conf, "inverted-index stage2: build postings");
        stage2.setJarByClass(InvertedIndexDriver.class);
        stage2.setMapperClass(DocCountMapper.class);
        stage2.setReducerClass(IndexReducer.class);
        stage2.setMapOutputKeyClass(Text.class);
        stage2.setMapOutputValueClass(Text.class);
        stage2.setOutputKeyClass(Text.class);
        stage2.setOutputValueClass(Text.class);
        stage2.setOutputFormatClass(TextOutputFormat.class);
        // 默认 key/value 之间是制表符，改成空格以匹配实验要求的输出格式
        stage2.getConfiguration().set(TextOutputFormat.SEPARATOR, " ");
        FileInputFormat.addInputPath(stage2, stage1Output);
        FileOutputFormat.setOutputPath(stage2, stage2Output);
        // 倒排表需要全局有序，强制使用一个 reduce 任务
        stage2.setNumReduceTasks(1);

        if (!stage2.waitForCompletion(true)) {
            System.err.println("stage2 failed");
            return 1;
        }

        long cost = System.currentTimeMillis() - start;
        System.out.println("==================================================");
        System.out.println("inverted index built in " + cost + " ms");
        System.out.println("stage1 (word/doc counts): " + stage1Output);
        System.out.println("stage2 (inverted index  ): " + stage2Output);
        System.out.println("index words: " + stage2.getCounters()
                .findCounter("org.apache.hadoop.mapreduce.TaskCounter.REDUCE_OUTPUT_RECORDS").getValue());
        System.out.println("==================================================");
        return 0;
    }

    public static void main(String[] args) throws Exception {
        int code = ToolRunner.run(new Configuration(), new InvertedIndexDriver(), args);
        System.exit(code);
    }
}
