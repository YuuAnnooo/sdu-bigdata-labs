package edu.sdu.bigdata.invertedindex;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * 文本规范化与分词。
 *
 * 英文文本不需要中文分词器：先统一转小写，再把所有非字母字符替换成空格，
 * 最后按空格切分即可得到候选单词。数字、标点、URL 中的符号都会被自然丢弃。
 */
public final class WordNormalizer {

    /** 匹配一个或多个非小写字母字符。 */
    private static final Pattern NON_LETTER = Pattern.compile("[^a-z]+");

    /** 最短有效单词长度，过滤 a、i 这类单字母噪声（停词表之外的兜底）。 */
    public static final int MIN_WORD_LENGTH = 2;

    private WordNormalizer() {
    }

    /**
     * 将一行文本切分为小写单词数组。
     *
     * @param line 原始行
     * @return 规范化后的单词数组，已去掉空串
     */
    public static List<String> tokenize(String line) {
        List<String> words = new ArrayList<>();
        if (line == null || line.isEmpty()) {
            return words;
        }
        String cleaned = NON_LETTER.matcher(line.toLowerCase(Locale.ROOT)).replaceAll(" ");
        for (String token : cleaned.trim().split(" ")) {
            if (!token.isEmpty()) {
                words.add(token);
            }
        }
        return words;
    }

    /** 单词是否满足索引条件（长度足够）。 */
    public static boolean isIndexable(String word) {
        return word != null && word.length() >= MIN_WORD_LENGTH;
    }
}
