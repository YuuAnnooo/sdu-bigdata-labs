package cn.sdu.bigdata.lab1.mr;

import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

/**
 * 实验一 第 3 部分（1）：文件合并与去重。
 *
 * 基本思路：把“一整行”作为 map 输出的 key，value 置空。
 * MapReduce 在 shuffle 阶段会把相同 key 的记录合并成一条迭代序列，
 * 因此 reduce 阶段对每个 key 只输出一次，就同时完成了合并与去重。
 */
public class MergeDedup {

    public static class DedupMapper extends Mapper<Object, Text, Text, NullWritable> {
        private final Text outKey = new Text();

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {
            String line = value.toString().trim();
            if (line.isEmpty()) {
                return;
            }
            // 把连续空白归一化为单个空格：文件 A、B 中字段间空格个数不同，
            // 不归一化会把 "20170101     x" 和 "20170101      x" 当成两行而漏掉去重
            outKey.set(line.replaceAll("\\s+", " "));
            context.write(outKey, NullWritable.get());
        }
    }

    public static class DedupReducer extends Reducer<Text, NullWritable, Text, NullWritable> {
        @Override
        protected void reduce(Text key, Iterable<NullWritable> values, Context context)
                throws IOException, InterruptedException {
            // 相同 key 只输出一次
            context.write(key, NullWritable.get());
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("用法: MergeDedup <输入路径> <输出路径>");
            System.exit(2);
        }
        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "merge and dedup");
        job.setJarByClass(MergeDedup.class);

        job.setMapperClass(DedupMapper.class);
        job.setReducerClass(DedupReducer.class);

        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(NullWritable.class);

        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
