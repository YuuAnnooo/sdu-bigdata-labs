# -*- coding: utf-8 -*-
"""Render the captured run logs / listings into terminal-style PNG figures.

Every figure is drawn from text that a real command produced in this workspace
(results/fig/*.txt, results/run_console.log, results/run_query.log,
results/stage2/part-r-00000); nothing is typed in by hand.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "results" / "fig"
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

FONT_PATH = Path(r"C:\Windows\Fonts\consola.ttf")
SCALE = 2                 # 2x 渲染，插入 Word 后仍然清晰
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


def font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


WRAP = 88          # 长行折行，保证插入 Word 后仍然可读
CONT = " " * 6


def wrap(lines: list[tuple[str, tuple]]) -> list[tuple[str, tuple]]:
    out: list[tuple[str, tuple]] = []
    for text, color in lines:
        if len(text) <= WRAP:
            out.append((text, color))
            continue
        head, rest = text[:WRAP], text[WRAP:]
        out.append((head, color))
        while rest:
            out.append((CONT + rest[: WRAP - len(CONT)], color))
            rest = rest[WRAP - len(CONT):]
    return out


def render(name: str, title: str, lines: list[tuple[str, tuple]], out_name: str) -> Path:
    """lines: (text, color) pairs."""
    lines = wrap(lines)
    f = font()
    f_bold = font(int(FONT_SIZE * 0.92))
    width = max((f.getbbox(t)[2] for t, _ in lines), default=200) + PAD * 2
    width = max(width, 560 * SCALE)
    height = BAR_H + PAD * 2 + LINE_H * len(lines)

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, BAR_H], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 18 * SCALE + i * 22 * SCALE
        d.ellipse([cx - 6 * SCALE, BAR_H // 2 - 6 * SCALE, cx + 6 * SCALE, BAR_H // 2 + 6 * SCALE], fill=c)
    d.text((110 * SCALE, BAR_H // 2 - 9 * SCALE), title, font=f_bold, fill=FG_DIM)

    y = BAR_H + PAD
    for text, color in lines:
        d.text((PAD, y), text, font=f, fill=color)
        y += LINE_H

    path = OUT / out_name
    img.save(path)
    print(f"{out_name}  {width}x{height}  <- {name}")
    return path


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def classify(line: str) -> tuple[str, tuple]:
    if line.startswith("$ "):
        return line, FG_KEY
    if line.startswith("=") and len(line) > 10:
        return line, FG_HL
    if line.strip().startswith("Job "):
        return line, FG_HL
    if line.startswith("#"):
        return line, FG_DIM
    return line, FG


def fig_listing() -> None:
    lines = [classify(x) for x in read_lines(FIG / "fig1.txt")]
    render("corpus listing", "lab2 - corpus & project layout", lines, "fig1_corpus.png")


def fig_stopwords() -> None:
    lines = [classify(x) for x in read_lines(FIG / "fig2.txt")]
    render("stop words", "lab2 - stop word list", lines, "fig2_stopwords.png")


def fig_job1() -> None:
    src = read_lines(ROOT / "results" / "run_console.log")
    keep: list[tuple[str, tuple]] = []
    tasks = 0
    for line in src:
        if line.startswith("  map task"):
            tasks += 1
            if tasks > 4:
                continue
        keep.append(classify(line))
        if line.strip().startswith("Output -> results/stage1"):
            break
    # 在第 4 个 map 任务后插入省略行
    idx = next(i for i, (t, _) in enumerate(keep) if t.startswith("  reduce output"))
    keep.insert(idx, ("   ...   (13 map tasks in total)", (128, 128, 128)))
    while keep and not keep[-1][0].strip():
        keep.pop()
    render("job1 log", "lab2 - job 1/2 : tokenize, combine, reduce", keep, "fig3_job1.png")


def fig_job2() -> None:
    lines: list[tuple[str, tuple]] = []
    stage2 = read_lines(ROOT / "results" / "stage2" / "part-r-00000")
    lines.append(("$ head -5 results/stage2/part-r-00000", FG_KEY))
    for row in stage2[:5]:
        lines.append((row, FG))
    lines.append(("   ...", FG_DIM))
    lines.append((f"$ wc -l results/stage2/part-r-00000   ->   {len(stage2)} words", FG_KEY))
    lines.append(("", FG))
    wanted = ("hadoop", "index", "mapreduce", "data")
    keep_next = False
    for row in read_lines(ROOT / "results" / "run_query.log"):
        if row.startswith("index lookup"):
            lines.append((row, FG))
            continue
        if row.startswith("[query]"):
            keep_next = row.split("]", 1)[1].strip() in wanted
            if keep_next:
                lines.append((row, FG_HL))
            continue
        if row.startswith("  <") and keep_next:
            lines.append((row, FG))
    while lines and not lines[-1][0].strip():
        lines.pop()
    render("job2 & lookup", "lab2 - job 2/2 : inverted index & lookup", lines, "fig4_job2.png")


if __name__ == "__main__":
    fig_listing()
    fig_stopwords()
    fig_job1()
    fig_job2()
