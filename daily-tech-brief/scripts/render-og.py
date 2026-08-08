#!/usr/bin/env python3
"""Render a deterministic 1.9:1 social preview from an issue JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1731
HEIGHT = 909
PAPER = (248, 247, 244)
INK = (12, 12, 12)
MUTED = (99, 96, 91)
ACCENT = (215, 66, 25)
LINE = (213, 209, 203)


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = f"{current}{char}"
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render(issue_path: Path, output_path: Path) -> None:
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    date = issue["date"]
    day = date[-2:]

    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image, "RGBA")

    # Quiet editorial glow on the right, built from concentric translucent circles.
    center_x, center_y = 1475, 265
    for radius in range(520, 20, -10):
        alpha = max(0, int(12 * (1 - radius / 520)))
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            fill=(255, 99, 61, alpha),
        )

    mono = load_font("/System/Library/Fonts/Menlo.ttc", 28)
    mono_small = load_font("/System/Library/Fonts/Menlo.ttc", 22)
    headline_font = load_font("/System/Library/Fonts/STHeiti Medium.ttc", 91)
    day_font = load_font("/System/Library/Fonts/Helvetica.ttc", 500)

    draw.ellipse((90, 108, 114, 132), fill=ACCENT)
    draw.ellipse((80, 98, 124, 142), outline=(255, 98, 61, 36), width=10)
    draw.text((146, 103), issue["brand"], font=mono, fill=INK)
    display_date = date.replace("-", ".")
    date_width = draw.textbbox((0, 0), display_date, font=mono_small)[2]
    draw.text((WIDTH - 92 - date_width, 108), display_date, font=mono_small, fill=MUTED)
    draw.line((90, 168, WIDTH - 90, 168), fill=LINE, width=2)

    draw.text((1100, 180), day, font=day_font, fill=(249, 224, 216))

    lines = wrap_text(draw, issue["headline"], headline_font, 1260)
    if len(lines) > 3:
        lines = lines[:2] + ["".join(lines[2:])]

    y = 295
    line_height = 128
    for index, line in enumerate(lines):
        color = ACCENT if index == len(lines) - 1 else INK
        draw.text((90, y + index * line_height), line, font=headline_font, fill=color)

    footer_y = 827
    draw.line((90, footer_y - 28, WIDTH - 90, footer_y - 28), fill=LINE, width=2)
    draw.text((90, footer_y), "CURATED DAILY · 10 MINUTES", font=mono_small, fill=MUTED)
    footer = "TECH · BUSINESS · OPEN SOURCE · PRODUCTS"
    footer_width = draw.textbbox((0, 0), footer, font=mono_small)[2]
    draw.text((WIDTH - 90 - footer_width, footer_y), footer, font=mono_small, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    render(args.issue, args.out)
    print(f"Rendered {args.out}")


if __name__ == "__main__":
    main()
