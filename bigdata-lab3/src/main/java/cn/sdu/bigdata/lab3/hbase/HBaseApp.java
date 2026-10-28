package cn.sdu.bigdata.lab3.hbase;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.Cell;
import org.apache.hadoop.hbase.CellUtil;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.TableName;
import org.apache.hadoop.hbase.client.Admin;
import org.apache.hadoop.hbase.client.ColumnFamilyDescriptor;
import org.apache.hadoop.hbase.client.ColumnFamilyDescriptorBuilder;
import org.apache.hadoop.hbase.client.Connection;
import org.apache.hadoop.hbase.client.ConnectionFactory;
import org.apache.hadoop.hbase.client.Delete;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.client.Table;
import org.apache.hadoop.hbase.client.TableDescriptor;
import org.apache.hadoop.hbase.client.TableDescriptorBuilder;
import org.apache.hadoop.hbase.util.Bytes;

/**
 * 实验三 第一部分：HBase 常用操作的程序实现。
 *
 * 一、与实验内容对应的 5 项通用功能：
 *     listTables()         列出所有表及其列族
 *     showTable(table)     显示指定表的全部记录
 *     addFamily / delFamily / delColumn    增加或删除列族、删除某列
 *     clearTable(table)    清空表的所有记录（truncate）
 *     countRows(table)     统计表的行数
 *
 * 二、关系型数据库表到 HBase 的转换（createTable/addRecord/scanColumn/
 *     modifyData/deleteRow），三张表的设计见 README。
 *
 * 用法：hadoop jar bigdata-lab3.jar cn.sdu.bigdata.lab3.hbase.HBaseApp <子命令> [参数...]
 */
public class HBaseApp {

    private static Connection connection;

    // ------------------------------------------------------------ 工具方法

    private static byte[] b(String s) {
        return Bytes.toBytes(s);
    }

    private static void checkTable(String tableName) throws IOException {
        try (Admin admin = connection.getAdmin()) {
            if (!admin.tableExists(TableName.valueOf(tableName))) {
                throw new IOException("表不存在: " + tableName);
            }
        }
    }

    // ------------------------------------------------------------ 一、5 项通用功能

    /** 列出所有表的名字、列族和行数 */
    public static void listTables() throws IOException {
        try (Admin admin = connection.getAdmin()) {
            TableName[] names = admin.listTableNames();
            System.out.printf("%-12s %-20s %s%n", "表名", "列族", "行数");
            for (TableName tn : names) {
                TableDescriptor td = admin.getDescriptor(tn);
                List<String> families = new ArrayList<String>();
                for (ColumnFamilyDescriptor cfd : td.getColumnFamilies()) {
                    families.add(cfd.getNameAsString());
                }
                long rows = countRows(tn.getNameAsString());
                System.out.printf("%-12s %-20s %d%n", tn.getNameAsString(),
                        String.join(",", families), rows);
            }
        }
    }

    /** 显示指定表的全部记录：行键、列族:列、值、时间戳 */
    public static void showTable(String tableName) throws IOException {
        checkTable(tableName);
        try (Table table = connection.getTable(TableName.valueOf(tableName));
             ResultScanner scanner = table.getScanner(new Scan())) {
            for (Result r : scanner) {
                System.out.println("rowkey = " + Bytes.toString(r.getRow()));
                for (Cell cell : r.rawCells()) {
                    System.out.printf("    %-22s = %-18s (ts=%d)%n",
                            Bytes.toString(CellUtil.cloneFamily(cell)) + ":"
                                    + Bytes.toString(CellUtil.cloneQualifier(cell)),
                            Bytes.toString(CellUtil.cloneValue(cell)),
                            cell.getTimestamp());
                }
            }
        }
    }

    /** 增加列族：alter 'table', NAME => 'family' */
    public static void addFamily(String tableName, String family) throws IOException {
        checkTable(tableName);
        try (Admin admin = connection.getAdmin()) {
            admin.addColumnFamily(TableName.valueOf(tableName),
                    ColumnFamilyDescriptorBuilder.of(family));
        }
        System.out.println("已为表 " + tableName + " 增加列族 " + family);
    }

    /** 删除列族：alter 'table', NAME => 'family', METHOD => 'delete' */
    public static void deleteFamily(String tableName, String family) throws IOException {
        checkTable(tableName);
        try (Admin admin = connection.getAdmin()) {
            admin.deleteColumnFamily(TableName.valueOf(tableName), b(family));
        }
        System.out.println("已删除表 " + tableName + " 的列族 " + family);
    }

    /** 删除某行的某一列（列族:列） */
    public static void deleteColumn(String tableName, String row, String column) throws IOException {
        String[] fq = splitColumn(column);
        try (Table table = connection.getTable(TableName.valueOf(tableName))) {
            Delete delete = new Delete(b(row));
            if (fq[1] == null) {
                delete.addFamily(b(fq[0]));          // 没有列限定符就是整个列族
            } else {
                delete.addColumns(b(fq[0]), b(fq[1]));
            }
            table.delete(delete);
        }
        System.out.println("已删除 " + tableName + " 中 " + row + " 的列 " + column);
    }

    /** 清空表：先 disable 再 truncate，保留表结构 */
    public static void clearTable(String tableName) throws IOException {
        checkTable(tableName);
        TableName tn = TableName.valueOf(tableName);
        try (Admin admin = connection.getAdmin()) {
            if (admin.isTableEnabled(tn)) {
                admin.disableTable(tn);
            }
            admin.truncateTable(tn, true);
        }
        System.out.println("已清空表 " + tableName + "，剩余行数 = " + countRows(tableName));
    }

    /** 统计行数：MapReduce 的 RowCounter，或直接遍历 Region 计数 */
    public static long countRows(String tableName) throws IOException {
        try (Table table = connection.getTable(TableName.valueOf(tableName));
             ResultScanner scanner = table.getScanner(new Scan())) {
            long n = 0;
            for (Result ignored : scanner) {
                n++;
            }
            return n;
        }
    }

    // ------------------------------------------------------------ 二、关系表转换

    /**
     * 创建表：若已存在同名表先删除，再按 fields 建立列族。
     */
    public static void createTable(String tableName, String[] fields) throws IOException {
        TableName tn = TableName.valueOf(tableName);
        try (Admin admin = connection.getAdmin()) {
            if (admin.tableExists(tn)) {
                System.out.println("表 " + tableName + " 已存在，先删除原有表");
                if (admin.isTableEnabled(tn)) {
                    admin.disableTable(tn);
                }
                admin.deleteTable(tn);
            }
            TableDescriptorBuilder builder = TableDescriptorBuilder.newBuilder(tn);
            for (String field : fields) {
                builder.setColumnFamily(ColumnFamilyDescriptorBuilder.of(field));
            }
            admin.createTable(builder.build());
        }
        System.out.println("已创建表 " + tableName + "，列族 = " + String.join(",", fields));
    }

    /**
     * 向表 tableName 的 row 行写入 fields/values 指定的单元格。
     * fields 元素形如 "Info:name" 或 "Score:Math"（列族:列）。
     */
    public static void addRecord(String tableName, String row, String[] fields,
                                 String[] values) throws IOException {
        if (fields.length != values.length) {
            throw new IllegalArgumentException("fields 与 values 长度不一致");
        }
        try (Table table = connection.getTable(TableName.valueOf(tableName))) {
            Put put = new Put(b(row));
            for (int i = 0; i < fields.length; i++) {
                String[] fq = splitColumn(fields[i]);
                if (fq[1] == null) {
                    throw new IllegalArgumentException(
                            "fields 需要写成 列族:列 的形式: " + fields[i]);
                }
                put.addColumn(b(fq[0]), b(fq[1]), b(values[i]));
            }
            table.put(put);
        }
        System.out.println("已向 " + tableName + " 的 " + row + " 写入 " + fields.length + " 个单元格");
    }

    /**
     * 浏览某一列的数据。
     *  - column 是列族名：列出该列族下每一个列限定符及其值；
     *  - column 是 "列族:列"：只列出该列的值，该行没有此列时输出 null。
     */
    public static void scanColumn(String tableName, String column) throws IOException {
        checkTable(tableName);
        String[] fq = splitColumn(column);
        System.out.printf("--- %s 的列 %s ---%n", tableName, column);
        try (Table table = connection.getTable(TableName.valueOf(tableName));
             ResultScanner scanner = table.getScanner(new Scan().addFamily(b(fq[0])))) {
            for (Result r : scanner) {
                String row = Bytes.toString(r.getRow());
                if (fq[1] != null) {
                    // 具体某一列：不存在时输出 null
                    byte[] v = r.getValue(b(fq[0]), b(fq[1]));
                    System.out.printf("%-12s %s%n", row, v == null ? "null" : Bytes.toString(v));
                    continue;
                }
                // 整个列族：逐个列限定符输出
                for (Cell cell : r.rawCells()) {
                    System.out.printf("%-12s %-22s = %s%n", row,
                            Bytes.toString(CellUtil.cloneQualifier(cell)),
                            Bytes.toString(CellUtil.cloneValue(cell)));
                }
                if (r.rawCells().length == 0) {
                    System.out.printf("%-12s %s%n", row, "null");
                }
            }
        }
    }

    /** 修改某行某列的值：HBase 的 put 本身就是“覆盖写”，不需要先读再写 */
    public static void modifyData(String tableName, String row, String column,
                                  String value) throws IOException {
        String[] fq = splitColumn(column);
        if (fq[1] == null) {
            throw new IllegalArgumentException("column 需要写成 列族:列 的形式: " + column);
        }
        try (Table table = connection.getTable(TableName.valueOf(tableName))) {
            byte[] old = table.get(new Get(b(row))).getValue(b(fq[0]), b(fq[1]));
            table.put(new Put(b(row)).addColumn(b(fq[0]), b(fq[1]), b(value)));
            System.out.printf("已修改 %s 的 %s：%s -> %s%n", row, column,
                    old == null ? "null" : Bytes.toString(old), value);
        }
    }

    /** 删除整行 */
    public static void deleteRow(String tableName, String row) throws IOException {
        try (Table table = connection.getTable(TableName.valueOf(tableName))) {
            table.delete(new Delete(b(row)));
        }
        System.out.println("已删除 " + tableName + " 中行 " + row);
    }

    /** 把 "列族:列" 或 "列族" 拆成两段，第二段为 null 表示没有列限定符 */
    private static String[] splitColumn(String column) {
        int colon = column.indexOf(':');
        if (colon < 0) {
            return new String[]{column.trim(), null};
        }
        return new String[]{column.substring(0, colon).trim(),
                            column.substring(colon + 1).trim()};
    }

    // ------------------------------------------------------------ 建表并导入实验数据

    /** 创建学生表/课程表/选课表并写入指导书中的全部数据 */
    public static void initDemo() throws IOException {
        createTable("student", new String[]{"Info", "Score"});
        createTable("course", new String[]{"Info"});
        createTable("sc", new String[]{"Score"});

        // 学生表：rowkey = 学号，Info 列族存基本情况，Score 列族存成绩
        addRecord("student", "2015001", new String[]{"Info:name", "Info:sex", "Info:age"},
                new String[]{"Zhangsan", "male", "23"});
        addRecord("student", "2015002", new String[]{"Info:name", "Info:sex", "Info:age"},
                new String[]{"Mary", "female", "22"});
        addRecord("student", "2015003", new String[]{"Info:name", "Info:sex", "Info:age"},
                new String[]{"Lisi", "male", "24"});
        addRecord("student", "2015001",
                new String[]{"Score:Math", "Score:Computer Science", "Score:English"},
                new String[]{"86", "0", "69"});
        addRecord("student", "2015002", new String[]{"Score:Computer Science", "Score:English"},
                new String[]{"77", "99"});
        addRecord("student", "2015003", new String[]{"Score:Math", "Score:Computer Science"},
                new String[]{"98", "95"});

        // 课程表：rowkey = 课程号
        addRecord("course", "123001", new String[]{"Info:name", "Info:credit"},
                new String[]{"Math", "2.0"});
        addRecord("course", "123002", new String[]{"Info:name", "Info:credit"},
                new String[]{"Computer Science", "5.0"});
        addRecord("course", "123003", new String[]{"Info:name", "Info:credit"},
                new String[]{"English", "3.0"});

        // 选课表：rowkey = 学号+课程号，列族 Score 的列 score 存成绩
        String[][] sc = {
                {"2015001", "123001", "86"}, {"2015001", "123003", "69"},
                {"2015002", "123002", "77"}, {"2015002", "123003", "99"},
                {"2015003", "123001", "98"}, {"2015003", "123002", "95"},
        };
        for (String[] rec : sc) {
            addRecord("sc", rec[0] + "_" + rec[1], new String[]{"Score:score"},
                    new String[]{rec[2]});
        }
        System.out.println("三张表初始化完成");
    }

    // ------------------------------------------------------------ main

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("用法: HBaseApp <子命令> [参数...]\n"
                    + "  init                                    建表并导入实验数据\n"
                    + "  list                                    列出所有表\n"
                    + "  scan <表>                               显示表的所有记录\n"
                    + "  count <表>                              统计行数\n"
                    + "  addFamily <表> <列族>                   增加列族\n"
                    + "  delFamily <表> <列族>                   删除列族\n"
                    + "  delColumn <表> <行> <列族:列>           删除某列\n"
                    + "  truncate <表>                           清空表\n"
                    + "  create <表> <列族,列族>                 创建表（存在则先删除）\n"
                    + "  put <表> <行> <列1:列,列2:列> <值1,值2>  写入记录\n"
                    + "  showcol <表> <列族|列族:列>             浏览某一列\n"
                    + "  modify <表> <行> <列族:列> <新值>       修改单元格\n"
                    + "  delRow <表> <行>                        删除行");
            System.exit(2);
        }

        Configuration conf = HBaseConfiguration.create();
        connection = ConnectionFactory.createConnection(conf);
        String cmd = args[0];
        try {
            switch (cmd) {
                case "init":
                    initDemo();
                    break;
                case "list":
                    listTables();
                    break;
                case "scan":
                    showTable(args[1]);
                    break;
                case "count":
                    System.out.println(args[1] + " 的行数 = " + countRows(args[1]));
                    break;
                case "addFamily":
                    addFamily(args[1], args[2]);
                    break;
                case "delFamily":
                    deleteFamily(args[1], args[2]);
                    break;
                case "delColumn":
                    deleteColumn(args[1], args[2], args[3]);
                    break;
                case "truncate":
                    clearTable(args[1]);
                    break;
                case "create":
                    createTable(args[1], args[2].split(","));
                    break;
                case "put":
                    addRecord(args[1], args[2], args[3].split(","), args[4].split(","));
                    break;
                case "showcol":
                    scanColumn(args[1], args[2]);
                    break;
                case "modify":
                    modifyData(args[1], args[2], args[3], args[4]);
                    break;
                case "delRow":
                    deleteRow(args[1], args[2]);
                    break;
                default:
                    System.err.println("未知子命令: " + cmd);
                    System.exit(2);
            }
        } finally {
            connection.close();
        }
    }
}
