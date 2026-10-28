package edu.sdu.bigdata.invertedindex;

import java.io.IOException;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

/**
 * 第二阶段 Mapper：把第一阶段的 "单词 &lt;TAB&gt; 文档名 &lt;TAB&gt; 次数"
 * 重新整理成 "单词 → 文档名:次数"，为按单词聚合做准备。
 */
public class DocCountMapper extends Mapper<LongWritable, Text, Text, Text> {

    private final Text outKey = new Text();
    private final Text outValue = new Text();

    @Override
    protected void map(LongWritable key, Text value, Context context)
            throws IOException, InterruptedException {
        String[] parts = value.toString().split("\t");
        if (parts.length != 3) {
            return;   // 兜底：忽略格式异常的行
        }
        outKey.set(parts[0]);
        outValue.set(parts[1] + ":" + parts[2]);
        context.write(outKey, outValue);
    }
}
