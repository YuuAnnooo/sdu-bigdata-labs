package cn.sdu.bigdata.lab1.mr;

import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

/**
 * 实验一 第 3 部分（2）：对多个输入文件中的整数做升序排序，
 * 输出格式为 “名次 整数”。
 *
 * 基本思路：MapReduce 在 shuffle 阶段会按 key 排序，所以把整数本身作为 key，
 * 利用框架的排序能力完成排序；再用一个全局计数器在 reduce 阶段生成名次。
 * 注意必须把 Reduce 个数设为 1，否则只能得到“每个分区内部有序”的结果。
 */
public class Sort {

    public static class IntMapper extends Mapper<Object, Text, IntWritable, NullWritable> {
        private final IntWritable outKey = new IntWritable();

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {
            String line = value.toString().trim();
            if (line.isEmpty()) {
                return;
            }
            outKey.set(Integer.parseInt(line));
            context.write(outKey, NullWritable.get());
        }
    }

    public static class RankReducer extends Reducer<IntWritable, NullWritable, IntWritable, IntWritable> {
        private int rank = 0;      // 全局名次，key 已由框架排好序

        @Override
        protected void reduce(IntWritable key, Iterable<NullWritable> values, Context context)
                throws IOException, InterruptedException {
            rank++;
            context.write(new IntWritable(rank), new IntWritable(key.get()));
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("用法: Sort <输入路径> <输出路径>");
            System.exit(2);
        }
        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "sort integers");
        job.setJarByClass(Sort.class);

        job.setMapperClass(IntMapper.class);
        job.setReducerClass(RankReducer.class);

        job.setMapOutputKeyClass(IntWritable.class);
        job.setMapOutputValueClass(NullWritable.class);
        job.setOutputKeyClass(IntWritable.class);
        job.setOutputValueClass(IntWritable.class);

        // 全局有序必须只有一个 Reducer
        job.setNumReduceTasks(1);

        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
