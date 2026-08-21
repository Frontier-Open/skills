#!/usr/bin/env python3
"""Render a validated Frontier Signals record as WeChat HTML and Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

from validate_signal import validate_record


PUBLIC_SOURCE_LIMIT = 3


def _e(value: Any) -> str:
    return escape(str(value), quote=True)


def _md(value: Any) -> str:
    text = str(value).replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "<", ">"):
        text = text.replace(character, f"\\{character}")
    return text


def _bold_spans(section: dict[str, Any], paragraph_number: int) -> list[str]:
    spans = section.get("bold_spans", [])
    if not isinstance(spans, list):
        return []
    return [
        span["text"]
        for span in spans
        if isinstance(span, dict)
        and span.get("paragraph") == paragraph_number
        and isinstance(span.get("text"), str)
    ]


def _html_text(text: str, bold_texts: list[str]) -> str:
    if not bold_texts:
        return _e(text)
    parts: list[str] = []
    cursor = 0
    ranges = sorted(
        (
            (text.find(bold_text), bold_text)
            for bold_text in bold_texts
            if text.find(bold_text) >= 0
        ),
        key=lambda item: item[0],
    )
    for start, bold_text in ranges:
        if start < cursor:
            continue
        parts.append(_e(text[cursor:start]))
        parts.append(
            '<strong style="color:#101114;font-weight:700;">'
            f'{_e(bold_text)}</strong>'
        )
        cursor = start + len(bold_text)
    parts.append(_e(text[cursor:]))
    return "".join(parts)


def _markdown_text(text: str, bold_texts: list[str]) -> str:
    if not bold_texts:
        return _md(text)
    parts: list[str] = []
    cursor = 0
    ranges = sorted(
        (
            (text.find(bold_text), bold_text)
            for bold_text in bold_texts
            if text.find(bold_text) >= 0
        ),
        key=lambda item: item[0],
    )
    for start, bold_text in ranges:
        if start < cursor:
            continue
        parts.append(_md(text[cursor:start]))
        parts.append(f'**{_md(bold_text)}**')
        cursor = start + len(bold_text)
    parts.append(_md(text[cursor:]))
    return "".join(parts)


def _html_media(media: dict[str, Any], *, cover: bool = False) -> str:
    margin = "22px 0 28px" if cover else "24px 0"
    parts = [
        f'<figure style="margin:{margin};padding:0;">'
        f'<img src="{_e(media["path"])}" alt="{_e(media["alt"])}" '
        'style="display:block;width:100%;max-width:100%;height:auto;margin:0;border-radius:4px;" />'
    ]
    if not cover and media.get("show_caption") is True:
        parts.append(
            '<p style="margin:9px 4px 0;color:#5D626D;font-size:12px;line-height:1.65;text-align:left;">'
            f'{_e(media["caption"])}</p>'
        )
    parts.append('</figure>')
    return "".join(parts)


def _public_sources(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the small reader-facing subset while preserving the full evidence ledger."""
    if record.get("show_public_sources") is not True:
        return []
    sources = record["sources"]
    selected_ids = record.get("public_source_ids")
    if isinstance(selected_ids, list):
        sources_by_id = {source["id"]: source for source in sources}
        selected = [sources_by_id[source_id] for source_id in selected_ids if source_id in sources_by_id]
        return selected[:PUBLIC_SOURCE_LIMIT]
    return []


def render_html(record: dict[str, Any]) -> str:
    """Return a WeChat-safe fragment with inline styles only."""
    sources = _public_sources(record)
    media_by_id = {item["id"]: item for item in record["media"]}
    cover = next((item for item in record["media"] if item["role"] == "cover"), None)
    title = record["headlines"]["primary"]

    parts = [
        "<!doctype html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{_e(title)}</title>',
        "</head>",
        '<body style="margin:0;padding:0;background:#FAFAF7;color:#101114;">',
        '<section id="frontier-signals-body" style="box-sizing:border-box;max-width:677px;margin:0 auto;padding:8px 18px 42px;'
        'background:#FAFAF7;color:#101114;font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\','
        '\'Hiragino Sans GB\',\'Microsoft YaHei\',sans-serif;letter-spacing:0.02em;">',
        '<header style="margin:0 0 24px;padding:0;">',
        '<p style="margin:0;color:#155EEF;font-size:12px;font-weight:700;letter-spacing:0.18em;">FRONTIER SIGNALS</p>',
        '</header>',
    ]
    if cover:
        parts.append(_html_media(cover, cover=True))

    brief = record.get("brief_30s")
    if isinstance(brief, list) and brief:
        parts.extend(
            [
                '<section style="margin:28px 0;padding:20px 20px 18px;background:#E8EEFF;border-left:4px solid #155EEF;">',
                '<p style="margin:0 0 12px;color:#155EEF;font-size:13px;font-weight:750;letter-spacing:0.08em;">30 秒速读</p>',
            ]
        )
        for item in brief:
            parts.append(
                '<p style="margin:8px 0;color:#101114;font-size:15px;line-height:1.8;">'
                f'<span style="color:#155EEF;font-weight:700;margin-right:8px;">•</span>{_e(item)}</p>'
            )
        parts.append('</section>')

    if record.get("show_thesis", True):
        parts.extend(
            [
                '<section style="margin:30px 0;padding:0 0 0 16px;border-left:1px solid #155EEF;">',
                '<p style="margin:0 0 9px;color:#155EEF;font-size:12px;font-weight:750;letter-spacing:0.16em;">THE SIGNAL</p>',
                f'<p style="margin:0;color:#101114;font-size:18px;font-weight:650;line-height:1.75;">{_e(record["thesis"]["core"])}</p>',
                '</section>',
            ]
        )

    for section in record["sections"]:
        show_heading = section.get("show_heading", True)
        section_margin = "36px" if show_heading else "20px"
        parts.append(f'<section style="margin:{section_margin} 0 0;padding:0;">')
        if show_heading:
            parts.append(
                f'<h2 style="margin:0 0 16px;padding:0 0 0 12px;border-left:3px solid #155EEF;color:#101114;font-size:22px;line-height:1.45;font-weight:730;text-wrap:balance;word-break:keep-all;overflow-wrap:normal;">{_e(section["heading"])}</h2>'
            )
        placements = section.get("media_placements")
        placements_by_position: dict[int, list[str]] = {}
        if isinstance(placements, list):
            for placement in placements:
                placements_by_position.setdefault(placement["after_paragraph"], []).append(
                    placement["media_id"]
                )
        for media_id in placements_by_position.get(0, []):
            parts.append(_html_media(media_by_id[media_id]))
        for paragraph_index, paragraph in enumerate(section["paragraphs"], start=1):
            parts.append(
                '<p style="margin:0 0 20px;color:#101114;font-size:16px;line-height:1.92;text-align:justify;">'
                f'{_html_text(paragraph, _bold_spans(section, paragraph_index))}</p>'
            )
            for media_id in placements_by_position.get(paragraph_index, []):
                parts.append(_html_media(media_by_id[media_id]))
        if not isinstance(placements, list):
            for media_id in section["media_ids"]:
                parts.append(_html_media(media_by_id[media_id]))
        parts.append('</section>')

    if sources:
        parts.extend(
            [
                '<section style="margin:38px 0 0;padding:24px 0 0;border-top:1px solid #E8EEFF;">',
                '<h2 style="margin:0 0 15px;color:#101114;font-size:16px;font-weight:700;">延伸阅读</h2>',
            ]
        )
        for source in sources:
            public_label = source.get("public_label") or source["title"]
            parts.append(
                f'<p id="source-{_e(source["id"])}" style="margin:0 0 11px;color:#5D626D;font-size:12px;line-height:1.7;">'
                f'<a href="{_e(source["url"])}" style="color:#155EEF;text-decoration:underline;">{_e(public_label)}</a></p>'
            )
        parts.append('</section>')
    parts.extend(
        [
            '<footer style="margin:34px 0 0;padding:18px 0 0;border-top:1px solid #E8EEFF;text-align:center;">',
            '<p style="margin:0;color:#155EEF;font-size:12px;font-weight:750;letter-spacing:0.16em;">FRONTIER WORLD</p>',
            '</footer>',
            '</section>',
            '</body>',
            '</html>',
        ]
    )
    return "\n".join(parts) + "\n"


def _markdown_media(media: dict[str, Any], *, cover: bool = False) -> str:
    output = f'![{_md(media["alt"])}]({media["path"]})'
    if not cover and media.get("show_caption") is True:
        output += f'\n\n*{_md(media["caption"])}*'
    return output


def render_markdown(record: dict[str, Any]) -> str:
    sources = _public_sources(record)
    media_by_id = {item["id"]: item for item in record["media"]}
    cover = next((item for item in record["media"] if item["role"] == "cover"), None)
    parts = [
        'FRONTIER SIGNALS',
        "",
        f'# {_md(record["headlines"]["primary"])}',
    ]
    if cover:
        parts.extend(["", _markdown_media(cover, cover=True)])

    brief = record.get("brief_30s")
    if isinstance(brief, list) and brief:
        parts.extend(["", "## 30 秒速读", ""])
        parts.extend(f'- {_md(item)}' for item in brief)
    if record.get("show_thesis", True):
        parts.extend(
            [
                "",
                "## The Signal",
                "",
                '> **核心判断**',
                '>',
                f'> {_md(record["thesis"]["core"])}',
            ]
        )

    for section in record["sections"]:
        if section.get("show_heading", True):
            parts.extend(["", f'## {_md(section["heading"])}', ""])
        else:
            parts.append("")
        placements = section.get("media_placements")
        placements_by_position: dict[int, list[str]] = {}
        if isinstance(placements, list):
            for placement in placements:
                placements_by_position.setdefault(placement["after_paragraph"], []).append(
                    placement["media_id"]
                )
        for media_id in placements_by_position.get(0, []):
            parts.extend([_markdown_media(media_by_id[media_id]), ""])
        for paragraph_index, paragraph in enumerate(section["paragraphs"], start=1):
            parts.extend([_markdown_text(paragraph, _bold_spans(section, paragraph_index)), ""])
            for media_id in placements_by_position.get(paragraph_index, []):
                parts.extend([_markdown_media(media_by_id[media_id]), ""])
        if not isinstance(placements, list):
            for media_id in section["media_ids"]:
                parts.extend([_markdown_media(media_by_id[media_id]), ""])

    if sources:
        parts.extend(["", "## 延伸阅读", ""])
        for source in sources:
            public_label = source.get("public_label") or source["title"]
            parts.append(f'- [{_md(public_label)}]({source["url"]})')
    parts.extend(["", "---", "", "**FRONTIER WORLD**", ""])
    return "\n".join(parts)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成公众号 HTML 与 Markdown")
    parser.add_argument("input", type=Path, help="已完成的文章 JSON")
    parser.add_argument("--html", type=Path, help="HTML 输出路径，默认与输入同目录")
    parser.add_argument("--markdown", type=Path, help="Markdown 输出路径，默认与输入同目录")
    parser.add_argument("--strict", action="store_true", help="存在任何校验警告时停止")
    parser.add_argument("--require-ready", action="store_true", help="仅渲染 ready、scheduled 或 published 记录")
    args = parser.parse_args(argv)

    try:
        record = _read_json(args.input)
    except (OSError, json.JSONDecodeError) as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1

    validation = validate_record(record, strict=args.strict)
    if not validation["renderable"] or (args.require_ready and not validation["publication_ready"]):
        output = {"ok": False, "error": "record_not_renderable", "validation": validation}
        json.dump(output, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1

    html_path = args.html or args.input.with_suffix(".wechat.html")
    markdown_path = args.markdown or args.input.with_suffix(".wechat.md")
    if html_path == args.input or markdown_path == args.input or html_path == markdown_path:
        json.dump({"ok": False, "error": "output_paths_must_be_distinct"}, sys.stderr)
        sys.stderr.write("\n")
        return 1

    html_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_html(record), encoding="utf-8")
    markdown_path.write_text(render_markdown(record), encoding="utf-8")
    json.dump(
        {
            "ok": True,
            "input": str(args.input),
            "html": str(html_path),
            "markdown": str(markdown_path),
            "renderable": validation["renderable"],
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
