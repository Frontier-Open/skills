#!/usr/bin/env python3
"""Create a deterministic 900×383 Frontier Signals cover from signal JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_signal import validate_record

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFont
except ImportError:  # The rest of the pipeline remains stdlib-only.
    Image = ImageChops = ImageDraw = ImageFont = None  # type: ignore[assignment]


WIDTH = 900
HEIGHT = 383
PASSAGE_BLUE = "#155EEF"
INK = "#101114"
CANVAS = "#FAFAF7"
REGULAR_FONTS = (
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
)
BOLD_FONTS = (
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
)
BRAND_FONTS = (
    ("/System/Library/Fonts/HelveticaNeue.ttc", 10),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
)


def _font(size: int, *, bold: bool = False):
    if ImageFont is None:
        raise RuntimeError("pillow_not_installed")
    for candidate, index in BOLD_FONTS if bold else REGULAR_FONTS:
        try:
            return ImageFont.truetype(candidate, size=size, index=index)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _brand_font(size: int):
    if ImageFont is None:
        raise RuntimeError("pillow_not_installed")
    for candidate, index in BRAND_FONTS:
        try:
            return ImageFont.truetype(candidate, size=size, index=index)
        except OSError:
            continue
    return _font(size, bold=True)


def _text_width(draw, text: str, font) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for hard_line in text.strip().splitlines():
        current = ""
        for character in hard_line:
            candidate = current + character
            if current and _text_width(draw, candidate, font) > max_width:
                lines.append(current.rstrip())
                current = character.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


def _truncate(draw, text: str, font, max_width: int) -> str:
    suffix = "…"
    current = text
    while current and _text_width(draw, current + suffix, font) > max_width:
        current = current[:-1]
    return current.rstrip() + suffix


def _fit_title(draw, title: str, max_width: int) -> tuple[Any, list[str], int]:
    for size in range(48, 29, -2):
        font = _font(size, bold=True)
        lines = _wrap(draw, title, font, max_width)
        line_height = int(size * 1.34)
        if len(lines) <= 2 and len(lines) * line_height <= 130:
            return font, lines, line_height
    font = _font(30, bold=True)
    lines = _wrap(draw, title, font, max_width)
    if len(lines) > 2:
        lines = [lines[0], _truncate(draw, "".join(lines[1:]), font, max_width)]
    return font, lines, 41


def _add_concept_background(image, background_path: Path) -> None:
    if Image is None or ImageChops is None or ImageDraw is None:
        raise RuntimeError("pillow_not_installed")
    with Image.open(background_path) as source:
        background = source.convert("RGB")

    max_width = 720
    max_height = 306
    scale = min(max_width / background.width, max_height / background.height)
    resampling = getattr(Image, "Resampling", Image)
    resized = background.resize(
        (round(background.width * scale), round(background.height * scale)),
        resampling.LANCZOS,
    )
    x = WIDTH - resized.width
    y = (HEIGHT - resized.height) // 2

    horizontal = Image.new("L", resized.size, 255)
    horizontal_draw = ImageDraw.Draw(horizontal)
    left_fade = min(320, resized.width)
    for offset in range(left_fade):
        alpha = round(255 * offset / max(1, left_fade - 1))
        horizontal_draw.line((offset, 0, offset, resized.height), fill=alpha)

    vertical = Image.new("L", resized.size, 255)
    vertical_draw = ImageDraw.Draw(vertical)
    edge_fade = min(28, resized.height // 2)
    for offset in range(edge_fade):
        alpha = round(255 * offset / max(1, edge_fade - 1))
        vertical_draw.line((0, offset, resized.width, offset), fill=alpha)
        vertical_draw.line(
            (0, resized.height - 1 - offset, resized.width, resized.height - 1 - offset),
            fill=alpha,
        )

    mask = ImageChops.multiply(horizontal, vertical)
    image.paste(resized, (x, y), mask)


def _add_subject_image(image, subject_path: Path) -> None:
    if Image is None:
        raise RuntimeError("pillow_not_installed")
    with Image.open(subject_path) as source:
        subject = source.convert("RGBA")

    alpha_bounds = subject.getchannel("A").getbbox()
    if alpha_bounds is None:
        raise ValueError("subject_has_no_visible_pixels")
    subject = subject.crop(alpha_bounds)
    max_width = 128
    max_height = 128
    scale = min(max_width / subject.width, max_height / subject.height, 1.0)
    resampling = getattr(Image, "Resampling", Image)
    resized = subject.resize(
        (round(subject.width * scale), round(subject.height * scale)),
        resampling.LANCZOS,
    )
    x = 764 - resized.width // 2
    y = 154 - resized.height // 2
    image.paste(resized, (x, y), resized)


def render_cover(
    record: dict[str, Any],
    *,
    background_path: Path | None = None,
    subject_path: Path | None = None,
):
    if Image is None or ImageDraw is None:
        raise RuntimeError("pillow_not_installed")
    if background_path is not None and subject_path is not None:
        raise ValueError("background_and_subject_mutually_exclusive")
    image = Image.new("RGB", (WIDTH, HEIGHT), CANVAS)
    if background_path is not None:
        _add_concept_background(image, background_path)
    if subject_path is not None:
        _add_subject_image(image, subject_path)
    draw = ImageDraw.Draw(image)

    draw.text((68, 29), "FRONTIER SIGNALS", font=_brand_font(24), fill=PASSAGE_BLUE)

    cover_title = record["headlines"]["cover"].replace("：", "：\n", 1)
    title_font, title_lines, line_height = _fit_title(
        draw,
        cover_title,
        max_width=430 if background_path is not None else 610 if subject_path is not None else 590,
    )
    title_y = 104
    for line_index, line in enumerate(title_lines):
        draw.text((68, title_y + line_index * line_height), line, font=title_font, fill=INK)

    footer = "FRONTIER WORLD"
    footer_font = _brand_font(18)
    footer_x = WIDTH - 68 - _text_width(draw, footer, footer_font)
    draw.text((footer_x, 331), footer, font=footer_font, fill=PASSAGE_BLUE)

    return image


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 900×383 Frontier Signals 公众号封面")
    parser.add_argument("input", type=Path, help="文章 JSON 文件")
    parser.add_argument("--output", type=Path, help="PNG 输出路径，默认与输入同目录")
    parser.add_argument("--background", type=Path, help="可选的无文字原创概念底图")
    parser.add_argument("--subject", type=Path, help="可选的透明 PNG 报道主体标志")
    parser.add_argument("--strict", action="store_true", help="存在任何校验警告时停止")
    parser.add_argument("--require-ready", action="store_true", help="只为发布就绪记录生成封面")
    args = parser.parse_args(argv)

    if Image is None:
        json.dump(
            {"ok": False, "error": "pillow_not_installed", "hint": "python -m pip install Pillow"},
            sys.stderr,
            ensure_ascii=False,
        )
        sys.stderr.write("\n")
        return 2

    try:
        with args.input.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return 1

    validation = validate_record(record, strict=args.strict)
    if not validation["renderable"] or (args.require_ready and not validation["publication_ready"]):
        json.dump(
            {"ok": False, "error": "record_not_renderable", "validation": validation},
            sys.stderr,
            ensure_ascii=False,
            indent=2,
        )
        sys.stderr.write("\n")
        return 1

    output_path = args.output or args.input.with_suffix(".cover.png")
    if output_path.resolve() == args.input.resolve():
        json.dump({"ok": False, "error": "output_must_not_overwrite_input"}, sys.stderr)
        sys.stderr.write("\n")
        return 1
    if args.background is not None and args.subject is not None:
        json.dump(
            {"ok": False, "error": "background_and_subject_mutually_exclusive"},
            sys.stderr,
        )
        sys.stderr.write("\n")
        return 1
    if args.background is not None and not args.background.is_file():
        json.dump(
            {"ok": False, "error": "background_not_found", "background": str(args.background)},
            sys.stderr,
            ensure_ascii=False,
        )
        sys.stderr.write("\n")
        return 1
    if args.background is not None and output_path.resolve() == args.background.resolve():
        json.dump(
            {"ok": False, "error": "output_must_not_overwrite_background"},
            sys.stderr,
        )
        sys.stderr.write("\n")
        return 1
    if args.subject is not None and not args.subject.is_file():
        json.dump(
            {"ok": False, "error": "subject_not_found", "subject": str(args.subject)},
            sys.stderr,
            ensure_ascii=False,
        )
        sys.stderr.write("\n")
        return 1
    if args.subject is not None and output_path.resolve() == args.subject.resolve():
        json.dump(
            {"ok": False, "error": "output_must_not_overwrite_subject"},
            sys.stderr,
        )
        sys.stderr.write("\n")
        return 1

    try:
        cover = render_cover(record, background_path=args.background, subject_path=args.subject)
    except (OSError, ValueError) as error:
        json.dump(
            {
                "ok": False,
                "error": (
                    "background_read_failed"
                    if args.background is not None
                    else "subject_read_failed"
                    if args.subject is not None
                    else "render_failed"
                ),
                "message": str(error),
            },
            sys.stderr,
            ensure_ascii=False,
        )
        sys.stderr.write("\n")
        return 1

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cover.save(output_path, format="PNG", optimize=False)
    except OSError as error:
        json.dump(
            {"ok": False, "error": "output_write_failed", "message": str(error)},
            sys.stderr,
            ensure_ascii=False,
        )
        sys.stderr.write("\n")
        return 1
    json.dump(
        {
            "ok": True,
            "input": str(args.input),
            "output": str(output_path),
            "background": str(args.background) if args.background is not None else None,
            "subject": str(args.subject) if args.subject is not None else None,
            "width": WIDTH,
            "height": HEIGHT,
            "publication_ready": validation["publication_ready"],
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
