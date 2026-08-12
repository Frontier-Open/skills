#!/usr/bin/env python3
"""Render deterministic Frontier Signals OG and WeChat covers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BLUE = (21, 94, 239)
INK = (16, 17, 20)
CANVAS = (250, 250, 247)
WHITE = (255, 255, 255)
MUTED = (93, 98, 109)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default(size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.ImageFont, width: int, limit: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        proposed = f"{current}{char}"
        if current and draw.textbbox((0, 0), proposed, font=selected_font)[2] > width:
            lines.append(current)
            current = char
        else:
            current = proposed
    if current:
        lines.append(current)
    if len(lines) > limit:
        lines = lines[: limit - 1] + ["".join(lines[limit - 1 :])]
    return lines


def passage_mark(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    draw.rectangle(box, fill=color)
    passage = [
        (x0 + int(width * 0.34), y1),
        (x0 + int(width * 0.65), y0 + int(height * 0.25)),
        (x0 + int(width * 0.82), y0 + int(height * 0.25)),
        (x0 + int(width * 0.74), y1),
    ]
    draw.polygon(passage, fill=BLUE if color == WHITE else CANVAS)


def render_og(article: dict, output: Path) -> None:
    image = Image.new("RGB", (1200, 630), CANVAS)
    draw = ImageDraw.Draw(image)
    draw.rectangle((812, 0, 1200, 630), fill=BLUE)
    passage_mark(draw, (924, 154, 1088, 318), WHITE)

    small = font(20, True)
    title_font = font(62, True)
    body = font(24)
    draw.text((70, 62), "FRONTIER SIGNALS", font=small, fill=BLUE)
    draw.text((70, 98), article["date"].replace("-", "."), font=small, fill=MUTED)
    lines = wrap(draw, article["title"], title_font, 680, 4)
    y = 180
    for line in lines:
        draw.text((70, y), line, font=title_font, fill=INK)
        y += 78
    draw.line((70, 548, 744, 548), fill=(195, 199, 209), width=2)
    draw.text((70, 572), f"{article['format'].upper()} · {article['reading_minutes']} MIN READ", font=body, fill=MUTED)
    draw.text((862, 542), "FRONTIER WORLD", font=small, fill=WHITE)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)


def render_wechat(article: dict, output: Path) -> None:
    image = Image.new("RGB", (900, 383), BLUE)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 225, 383), fill=CANVAS)
    passage_mark(draw, (58, 58, 166, 166), BLUE)

    small = font(17, True)
    title_font = font(44, True)
    draw.text((58, 302), article["date"].replace("-", "."), font=small, fill=MUTED)
    draw.text((58, 329), "FRONTIER SIGNALS", font=small, fill=INK)
    lines = wrap(draw, article["title"], title_font, 590, 3)
    y = 76
    for line in lines:
        draw.text((275, y), line, font=title_font, fill=WHITE)
        y += 63
    draw.text((277, 318), "FRONTIER WORLD · 前沿之境", font=small, fill=(211, 224, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "JPEG", quality=94, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--article", required=True, type=Path)
    parser.add_argument("--og", required=True, type=Path)
    parser.add_argument("--wechat", required=True, type=Path)
    args = parser.parse_args()
    article = json.loads(args.article.read_text(encoding="utf-8"))
    render_og(article, args.og)
    render_wechat(article, args.wechat)
    print(f"Rendered {args.og}")
    print(f"Rendered {args.wechat}")


if __name__ == "__main__":
    main()
