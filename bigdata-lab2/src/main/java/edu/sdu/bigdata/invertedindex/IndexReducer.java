package edu.sdu.bigdata.invertedindex;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

/**
 * 第二阶段 Reducer：一个单词的所有 "文档:次数" 都在这里汇聚，
 * 按次数降序、文档名升序排列，并追加总词频 total。
 *
 * 输出形如：
 * data &lt;document01.txt,6&gt;;&lt;document02.txt,3&gt;;&lt;document05.txt,2&gt;;&lt;total,11&gt;.
 */
public class IndexReducer extends Reducer<Text, Text, Text, Text> {

    private final Text outValue = new Text();

    @Override
    protected void reduce(Text key, Iterable<Text> values, Context context)
            throws IOException, InterruptedException {
        Map<String, Integer> postings = new LinkedHashMap<>();
        int total = 0;

        for (Text value : values) {
            String[] pair = value.toString().split(":");
            if (pair.length != 2) {
                continue;
            }
            int count;
            try {
                count = Integer.parseInt(pair[1]);
            } catch (NumberFormatException e) {
                continue;
            }
            // 同一文档可能因 Combiner/分片被多次投递，这里做一次合并
            postings.merge(pair[0], count, Integer::sum);
            total += count;
        }
        if (postings.isEmpty()) {
            return;
        }

        List<Map.Entry<String, Integer>> list = new ArrayList<>(postings.entrySet());
        list.sort((a, b) -> {
            int byCount = Integer.compare(b.getValue(), a.getValue());
            return byCount != 0 ? byCount : a.getKey().compareTo(b.getKey());
        });

        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, Integer> entry : list) {
            sb.append('<').append(entry.getKey()).append(',').append(entry.getValue()).append(">;");
        }
        sb.append("<total,").append(total).append(">.");

        outValue.set(sb.toString());
        context.write(key, outValue);
    }
}
