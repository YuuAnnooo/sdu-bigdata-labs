package edu.sdu.bigdata.invertedindex;

import java.io.IOException;
import java.util.Set;

import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.lib.input.FileSplit;

/**
 * 第一阶段 Mapper：把"文档"切成 "(单词, 文档名) → 1"。
 *
 * 关键点：MapReduce 的输入是"行"，map 端拿不到文档名，
 * 必须从 FileSplit（当前分片）里取出所属文件的名称。
 */
public class TokenizeMapper extends Mapper<LongWritable, Text, Text, IntWritable> {

    private static final IntWritable ONE = new IntWritable(1);

    private final Text outKey = new Text();
    private String docName;
    private Set<String> stopwords;

    @Override
    protected void setup(Context context) throws IOException {
        FileSplit split = (FileSplit) context.getInputSplit();
        // 只取文件名，避免 HDFS 绝对路径进入索引
        this.docName = split.getPath().getName();
        this.stopwords = StopwordDictionary.get(context.getConfiguration());
    }

    @Override
    protected void map(LongWritable key, Text value, Context context)
            throws IOException, InterruptedException {
        for (String word : WordNormalizer.tokenize(value.toString())) {
            if (!WordNormalizer.isIndexable(word) || stopwords.contains(word)) {
                continue;   // 过滤停词与过短的词
            }
            // 用制表符把单词和文档名拼成一个复合键，MapReduce 会按键排序、分组
            outKey.set(word + "\t" + docName);
            context.write(outKey, ONE);
        }
    }
}
