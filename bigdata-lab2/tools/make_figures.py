# -*- coding: utf-8 -*-
"""把真实运行产生的内容渲染成终端风格 PNG 插图。

数据来源全部是实跑产物，不含手写内容：
  results/fig/fig_stopwords.txt   在 WSL(Ubuntu) 里执行 wc/head/tail 的真实输出
  results/run_hadoop.log          hadoop jar 提交两个作业的真实日志
  results/fig/fig_output.txt      hdfs dfs -cat | head / wc -l 的真实输出
  results/fig/fig_query.txt       hdfs dfs -cat | grep 的查询结果
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = RES / "fig"
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

FONT_PATH = Path(r"C:\Windows\Fonts\consola.ttf")
SCALE = 2                 # 2x 渲染，插入 Word 后仍清晰
FONT_SIZE = 13 * SCALE
LINE_H = int(FONT_SIZE * 1.55)
PAD = 16 * SCALE
BAR_H = 30 * SCALE

BG = (30, 30, 30)
BAR = (58, 58, 58)
FG = (214, 214, 214)
FG_DIM = (128, 128, 128)
FG_KEY = (86, 182, 255)
FG_HL = (106, 190, 96)

WRAP = 88                 # 长行折行，保证插入 Word 后仍可读
CONT = " " * 6

JAR_CMD = [
    "$ hadoop jar inverted-index.jar \\",
    "    edu.sdu.bigdata.invertedindex.InvertedIndexDriver \\",
    "    /user/hadoop/lab2/corpus /user/hadoop/lab2/index \\",
    "    /user/hadoop/lab2/stopwords/stopwords_en.txt",
]


def font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def wrap(lines: list[tuple[str, tuple]]) -> list[tuple[str, tuple]]:
    out: list[tuple[str, tuple]] = []
    for text, color in lines:
        if len(text) <= WRAP:
            out.append((text, color))
            continue
        out.append((text[:WRAP], color))
        rest = text[WRAP:]
        while rest:
            out.append((CONT + rest[: WRAP - len(CONT)], color))
            rest = rest[WRAP - len(CONT):]
    return out


def render(title: str, lines: list[tuple[str, tuple]], out_name: str) -> Path:
    lines = wrap(lines)
    f = font()
    f_title = font(int(FONT_SIZE * 0.92))
    width = max((f.getbbox(t)[2] for t, _ in lines), default=200) + PAD * 2
    width = max(width, 560 * SCALE)
    height = BAR_H + PAD * 2 + LINE_H * len(lines)

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, BAR_H], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 18 * SCALE + i * 22 * SCALE
        d.ellipse([cx - 6 * SCALE, BAR_H // 2 - 6 * SCALE,
                   cx + 6 * SCALE, BAR_H // 2 + 6 * SCALE], fill=c)
    d.text((110 * SCALE, BAR_H // 2 - 9 * SCALE), title, font=f_title, fill=FG_DIM)

    y = BAR_H + PAD
    for text, color in lines:
        d.text((PAD, y), text, font=f, fill=color)
        y += LINE_H

    path = OUT / out_name
    img.save(path)
    print(f"{out_name}  {width}x{height}")
    return path


def read_lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").splitlines()


def classify(line: str) -> tuple[str, tuple]:
    if line.startswith("$ "):
        return line, FG_KEY
    if line.startswith("#"):
        return line, FG_DIM
    return line, FG


# --------------------------------------------------------------- 图 1
def fig_stopwords() -> None:
    lines = [classify(x) for x in read_lines(FIG / "fig_stopwords.txt")]
    while lines and not lines[-1][0].strip():
        lines.pop()
    render("bash - stop word list (WSL Ubuntu)", lines, "fig2_stopwords.png")


# --------------------------------------------------------------- 图 2
def fig_job1() -> None:
    """作业一在 YARN 上的真实日志：提交 -> 进度 -> 完成 -> 关键计数器。"""
    log = read_lines(RES / "run_hadoop.log")
    keep: list[tuple[str, tuple]] = [(c, FG_KEY) for c in JAR_CMD]

    wanted = [
        "number of splits:",
        "Running job:",
        "map 0% reduce 0%",
        "map 50% reduce 0%",
        "map 100% reduce 0%",
        "map 100% reduce 100%",
        "completed successfully",
        "Launched map tasks=",
        "Launched reduce tasks=",
        "Map input records=",
        "Map output records=",
        "Combine output records=",
        "Reduce output records=",
    ]
    for line in log:
        if not wanted:
            break
        body = line.split(" INFO ", 1)[-1]
        if wanted[0] in body:
            txt = body.split(": ", 1)[-1].replace("\t", "  ").strip()
            keep.append((txt, FG_HL if "completed" in txt else FG))
            wanted.pop(0)
    render("hadoop jar - job 1/2 on YARN", keep, "fig3_job1.png")


# --------------------------------------------------------------- 图 3
def fig_job2() -> None:
    lines: list[tuple[str, tuple]] = []
    for row in read_lines(FIG / "fig_output.txt"):
        lines.append(classify(row))
    lines.append(("", FG))
    for row in read_lines(FIG / "fig_query.txt"):
        lines.append(classify(row))
    while lines and not lines[-1][0].strip():
        lines.pop()
    render("bash - hdfs dfs -cat / grep on the index", lines, "fig4_job2.png")


if __name__ == "__main__":
    fig_stopwords()
    fig_job1()
    fig_job2()
