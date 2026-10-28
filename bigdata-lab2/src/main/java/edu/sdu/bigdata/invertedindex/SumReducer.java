package edu.sdu.bigdata.invertedindex;

import java.io.IOException;

import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

/**
 * 第一阶段 Reducer（同时用作 Combiner）：把复合键 "(单词,文档名)" 的出现次数求和。
 *
 * 输出记录形如：hadoop &lt;TAB&gt; document01.txt &lt;TAB&gt; 10
 */
public class SumReducer extends Reducer<Text, IntWritable, Text, IntWritable> {

    private final IntWritable outValue = new IntWritable();

    @Override
    protected void reduce(Text key, Iterable<IntWritable> values, Context context)
            throws IOException, InterruptedException {
        int sum = 0;
        for (IntWritable value : values) {
            sum += value.get();
        }
        outValue.set(sum);
        context.write(key, outValue);
    }
}
