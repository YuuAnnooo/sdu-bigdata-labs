package cn.sdu.bigdata.lab1.mr;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

/**
 * 实验一 第 3 部分（3）：从 child-parent 表挖掘祖孙（grandchild-grandparent）关系。
 *
 * 基本思路：把同一张表看成一个关系和它自身的连接（自连接），连接条件是
 * “记录1的父辈 == 记录2的子辈”。为在 reduce 端区分两类记录，map 输出时打上标记：
 *   标记 1：<父辈, "1:子辈">  —— 这条记录的父辈正好是 join key，它的子辈是“可能的孙辈”
 *   标记 2：<子辈, "2:父辈">  —— 这条记录的子辈正好是 join key，它的父辈是“可能的祖辈”
 * reduce 端拿到同一个 key 下的这两个列表后做笛卡尔积，即得到祖孙关系。
 */
public class GrandChild {

    private static final String TAG_CHILD = "1:";    // 该结点是父辈
    private static final String TAG_PARENT = "2:";   // 该结点是子辈

    public static class ChildParentMapper extends Mapper<Object, Text, Text, Text> {

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {
            String line = value.toString().trim();
            if (line.isEmpty() || line.startsWith("child")) {   // 跳过表头
                return;
            }
            String[] parts = line.split("\\s+");
            if (parts.length != 2) {
                return;
            }
            String child = parts[0];
            String parent = parts[1];
            // 同一个结点既可能作为父辈出现，也可能作为子辈出现，因此每次输出两条记录
            context.write(new Text(parent), new Text(TAG_CHILD + child));
            context.write(new Text(child), new Text(TAG_PARENT + parent));
        }
    }

    public static class JoinReducer extends Reducer<Text, Text, Text, Text> {
        @Override
        protected void reduce(Text key, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {
            List<String> grandChildren = new ArrayList<>();
            List<String> grandParents = new ArrayList<>();
            for (Text v : values) {
                String s = v.toString();
                if (s.startsWith(TAG_CHILD)) {
                    grandChildren.add(s.substring(TAG_CHILD.length()));
                } else if (s.startsWith(TAG_PARENT)) {
                    grandParents.add(s.substring(TAG_PARENT.length()));
                }
            }
            // 笛卡尔积：每个孙辈 对应 每个祖辈
            for (String gc : grandChildren) {
                for (String gp : grandParents) {
                    context.write(new Text(gc), new Text(gp));
                }
            }
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("用法: GrandChild <输入路径> <输出路径>");
            System.exit(2);
        }
        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "grandchild-grandparent");
        job.setJarByClass(GrandChild.class);

        job.setMapperClass(ChildParentMapper.class);
        job.setReducerClass(JoinReducer.class);

        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(Text.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
