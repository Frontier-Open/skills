#!/usr/bin/env python3
"""Deterministic editorial validator for a Frontier Signals article record."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


FORMATS = {"bulletin", "report", "profile"}
SECTION_KINDS = {"facts", "context", "analysis", "impact", "profile", "timeline", "outlook"}
SOURCE_KINDS = {"primary", "filing", "research", "secondary", "social"}
CLAIM_KINDS = {"fact", "quote", "analysis", "forecast"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
MEDIA_KINDS = {"image", "chart", "screenshot", "portrait"}
MEDIA_ROLES = {"cover", "inline"}
MEDIA_RIGHTS = {"owned", "licensed", "official", "fair_use_reviewed", "pending"}
PUBLICATION_STATES = {
    "local_draft",
    "editor_reviewed",
    "owner_approved",
    "remote_draft",
    "published",
    "sent",
    "failed",
}
CHECK_STATES = {"pending", "passed", "failed"}
APPROVED_STATES = {"owner_approved", "remote_draft", "published", "sent"}
REMOTE_STATES = {"remote_draft", "published", "sent"}
FORMAT_RULES = {
    "bulletin": {"body_min": 900, "body_max": 1500, "sources": 3, "inline": 2},
    "report": {"body_min": 1600, "body_max": 2800, "sources": 4, "inline": 3},
    "profile": {"body_min": 2400, "body_max": 4200, "sources": 6, "inline": 4},
}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_ID_PATTERN = re.compile(r"^S[1-9][0-9]*$")
CLAIM_ID_PATTERN = re.compile(r"^C[1-9][0-9]*$")
MEDIA_ID_PATTERN = re.compile(r"^M[1-9][0-9]*$")
TEST_RUN_ID_PATTERN = re.compile(r"^T[1-9][0-9]*$")
RELATIVE_MEDIA_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
MAX_BOLD_SPANS = 6


Issue = dict[str, str]


def _add(issues: list[Issue], level: str, code: str, path: str, message: str) -> None:
    issues.append({"level": level, "code": code, "path": path, "message": message})


def _object(
    parent: dict[str, Any], key: str, path: str, issues: list[Issue]
) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        _add(issues, "error", "schema.type", f"{path}.{key}", "必须是对象")
        return {}
    return value


def _text(
    parent: dict[str, Any],
    key: str,
    path: str,
    issues: list[Issue],
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> str:
    value = parent.get(key)
    field_path = f"{path}.{key}"
    if not isinstance(value, str):
        _add(issues, "error", "schema.type", field_path, "必须是字符串")
        return ""
    value = value.strip()
    if len(value) < minimum:
        _add(issues, "error", "editorial.too_short", field_path, f"至少需要 {minimum} 个字符")
    if maximum is not None and len(value) > maximum:
        _add(issues, "error", "editorial.too_long", field_path, f"最多允许 {maximum} 个字符")
    return value


def _string_list(
    parent: dict[str, Any],
    key: str,
    path: str,
    issues: list[Issue],
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> list[str]:
    value = parent.get(key)
    field_path = f"{path}.{key}"
    if not isinstance(value, list):
        _add(issues, "error", "schema.type", field_path, "必须是字符串数组")
        return []
    if len(value) < minimum:
        _add(issues, "error", "schema.list_too_short", field_path, f"至少需要 {minimum} 项")
    if maximum is not None and len(value) > maximum:
        _add(issues, "error", "schema.list_too_long", field_path, f"最多允许 {maximum} 项")
    output: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            _add(issues, "error", "schema.type", f"{field_path}[{index}]", "必须是非空字符串")
        else:
            output.append(item.strip())
    if len(output) != len(set(output)):
        _add(issues, "error", "schema.duplicate", field_path, "不得包含重复项")
    return output


def _enum(
    value: str,
    allowed: set[str],
    path: str,
    issues: list[Issue],
    code: str = "schema.enum",
) -> None:
    if value and value not in allowed:
        _add(issues, "error", code, path, f"只允许：{', '.join(sorted(allowed))}")


def _boolean(
    parent: dict[str, Any], key: str, path: str, issues: list[Issue]
) -> bool:
    value = parent.get(key)
    field_path = f"{path}.{key}"
    if not isinstance(value, bool):
        _add(issues, "error", "schema.type", field_path, "必须是布尔值")
        return False
    return value


def _parse_temporal(value: str, path: str, issues: list[Issue]) -> date | None:
    if not value:
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            _add(issues, "warning", "date.timezone_missing", path, "日期时间建议包含时区")
        return parsed.date()
    except ValueError:
        _add(issues, "error", "date.invalid", path, "必须是 ISO 8601 日期或日期时间")
        return None


def _valid_url(value: str) -> bool:
    if not value or any(character.isspace() for character in value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _check_url(value: str, path: str, issues: list[Issue], *, https_required: bool = False) -> None:
    if not _valid_url(value):
        _add(issues, "error", "url.invalid", path, "必须是完整的 http(s) URL")
        return
    if https_required and urlsplit(value).scheme != "https":
        _add(issues, "error", "url.https_required", path, "发布态资源必须使用 HTTPS")
    elif urlsplit(value).scheme == "http":
        _add(issues, "warning", "url.insecure", path, "建议改用 HTTPS")


def _body_character_count(record: dict[str, Any]) -> int:
    """Count non-whitespace characters in section paragraphs only."""
    total = 0
    sections = record.get("sections")
    if not isinstance(sections, list):
        return total
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("paragraphs"), list):
            continue
        for paragraph in section["paragraphs"]:
            if isinstance(paragraph, str):
                total += len(re.sub(r"\s+", "", paragraph))
    return total


def _publication(record: dict[str, Any], issues: list[Issue]) -> tuple[str, dict[str, str]]:
    publication = _object(record, "publication", "$", issues)
    state = _text(publication, "state", "$.publication", issues)
    _enum(state, PUBLICATION_STATES, "$.publication.state", issues, "publication.state_invalid")

    checks_raw = _object(publication, "checks", "$.publication", issues)
    checks: dict[str, str] = {}
    for name in ("facts", "media_rights", "editorial"):
        value = _text(checks_raw, name, "$.publication.checks", issues)
        _enum(value, CHECK_STATES, f"$.publication.checks.{name}", issues, "publication.check_invalid")
        checks[name] = value
        if value == "failed" and state != "failed":
            _add(
                issues,
                "error",
                "publication.check_failed",
                f"$.publication.checks.{name}",
                "检查失败，必须处理后才能继续",
            )
        elif state in APPROVED_STATES and value != "passed":
            _add(
                issues,
                "error",
                "publication.check_not_passed",
                f"$.publication.checks.{name}",
                f"{state} 状态要求所有检查为 passed",
            )

    remote_id = publication.get("remote_id")
    published_at = publication.get("published_at")
    published_url = publication.get("url")
    sent_at = publication.get("sent_at")
    failure = publication.get("error")

    if state == "remote_draft" and (not isinstance(remote_id, str) or not remote_id.strip()):
        _add(
            issues,
            "error",
            "publication.remote_id_missing",
            "$.publication.remote_id",
            "remote_draft 状态必须保存远端草稿标识",
        )
    elif remote_id is not None and not isinstance(remote_id, str):
        _add(issues, "error", "schema.type", "$.publication.remote_id", "必须是字符串或 null")

    if state in {"published", "sent"}:
        if not isinstance(published_at, str):
            _add(
                issues,
                "error",
                "publication.published_at_missing",
                "$.publication.published_at",
                "published 状态必须提供发布时间",
            )
        if not isinstance(published_url, str):
            _add(
                issues,
                "error",
                "publication.url_missing",
                "$.publication.url",
                "published 状态必须提供文章 URL",
            )

    if state == "sent" and not isinstance(sent_at, str):
        _add(
            issues,
            "error",
            "publication.sent_at_missing",
            "$.publication.sent_at",
            "sent 状态必须提供群发时间",
        )
    if sent_at is not None:
        if not isinstance(sent_at, str):
            _add(issues, "error", "schema.type", "$.publication.sent_at", "必须是字符串或 null")
        else:
            _parse_temporal(sent_at, "$.publication.sent_at", issues)

    if state == "failed" and (not isinstance(failure, str) or not failure.strip()):
        _add(
            issues,
            "error",
            "publication.error_missing",
            "$.publication.error",
            "failed 状态必须记录失败原因",
        )
    elif failure is not None and not isinstance(failure, str):
        _add(issues, "error", "schema.type", "$.publication.error", "必须是字符串或 null")

    if published_at is not None:
        if not isinstance(published_at, str):
            _add(issues, "error", "schema.type", "$.publication.published_at", "必须是字符串或 null")
        else:
            _parse_temporal(published_at, "$.publication.published_at", issues)
    if published_url is not None:
        if not isinstance(published_url, str):
            _add(issues, "error", "schema.type", "$.publication.url", "必须是字符串或 null")
        else:
            _check_url(published_url, "$.publication.url", issues, https_required=state in {"published", "sent"})

    return state, checks


def validate_record(
    record: Any,
    *,
    strict: bool = False,
    require_media: bool = False,
    media_base: Path | None = None,
) -> dict[str, Any]:
    """Validate a decoded JSON value and return a machine-readable report."""
    issues: list[Issue] = []
    if not isinstance(record, dict):
        _add(issues, "error", "schema.root", "$", "根节点必须是对象")
        return _build_result(issues, strict=strict)

    version = _text(record, "schema_version", "$", issues)
    if version and version != "1.0":
        _add(issues, "error", "schema.version", "$.schema_version", "当前仅支持 1.0")

    brand = _object(record, "brand", "$", issues)
    company = _text(brand, "company", "$.brand", issues)
    column = _text(brand, "column", "$.brand", issues)
    language = _text(brand, "language", "$.brand", issues)
    if company and company != "Frontier World":
        _add(issues, "error", "brand.company", "$.brand.company", "必须为 Frontier World")
    if column and column != "Frontier Signals":
        _add(issues, "error", "brand.column", "$.brand.column", "必须为 Frontier Signals")
    if language and language != "zh-CN":
        _add(issues, "error", "brand.language", "$.brand.language", "公众号稿件语言必须为 zh-CN")

    meta = _object(record, "meta", "$", issues)
    record_id = _text(meta, "id", "$.meta", issues, minimum=3, maximum=96)
    if record_id and not ID_PATTERN.fullmatch(record_id):
        _add(issues, "error", "meta.id_invalid", "$.meta.id", "只允许小写字母、数字和单连字符")
    article_format = _text(meta, "format", "$.meta", issues)
    _enum(article_format, FORMATS, "$.meta.format", issues, "meta.format_invalid")
    event_at = _text(meta, "event_at", "$.meta", issues)
    updated_at = _text(meta, "updated_at", "$.meta", issues)
    event_date = _parse_temporal(event_at, "$.meta.event_at", issues)
    updated_date = _parse_temporal(updated_at, "$.meta.updated_at", issues)
    if event_date and updated_date and updated_date < event_date:
        _add(issues, "error", "meta.time_order", "$.meta.updated_at", "更新时间不得早于事件时间")
    authors = _string_list(meta, "authors", "$.meta", issues, minimum=1, maximum=3)
    for index, author in enumerate(authors):
        if len(author) > 40:
            _add(issues, "error", "meta.author_too_long", f"$.meta.authors[{index}]", "作者名最多 40 字符")

    wechat = _object(record, "wechat", "$", issues)
    author = _text(wechat, "author", "$.wechat", issues, minimum=0)
    digest = _text(wechat, "digest", "$.wechat", issues, minimum=0)
    content_source_url = _text(
        wechat,
        "content_source_url",
        "$.wechat",
        issues,
        minimum=0,
    )
    for field, normalized, maximum in (
        ("author", author, 16),
        ("digest", digest, 120),
    ):
        raw_value = wechat.get(field)
        field_path = f"$.wechat.{field}"
        if isinstance(raw_value, str) and raw_value != normalized:
            _add(
                issues,
                "error",
                "wechat.text_not_normalized",
                field_path,
                "不得包含首尾空白",
            )
        if "\n" in normalized or "\r" in normalized:
            _add(
                issues,
                "error",
                "wechat.text_not_single_line",
                field_path,
                "必须是单行文本",
            )
        if len(normalized) > maximum:
            _add(
                issues,
                "error",
                f"wechat.{field}_too_long",
                field_path,
                f"最多允许 {maximum} 个字符",
            )
    raw_source_url = wechat.get("content_source_url")
    if isinstance(raw_source_url, str) and raw_source_url != content_source_url:
        _add(
            issues,
            "error",
            "wechat.text_not_normalized",
            "$.wechat.content_source_url",
            "不得包含首尾空白",
        )
    if content_source_url:
        _check_url(content_source_url, "$.wechat.content_source_url", issues)
        if len(content_source_url.encode("utf-8")) >= 1024:
            _add(
                issues,
                "error",
                "wechat.content_source_url_too_long",
                "$.wechat.content_source_url",
                "原文链接的 UTF-8 字节长度必须小于 1024",
            )
    comments = _object(wechat, "comments", "$.wechat", issues)
    comments_enabled = _boolean(comments, "enabled", "$.wechat.comments", issues)
    comments_fans_only = _boolean(comments, "fans_only", "$.wechat.comments", issues)
    if comments_fans_only and not comments_enabled:
        _add(
            issues,
            "error",
            "wechat.comments_fans_only_requires_enabled",
            "$.wechat.comments.fans_only",
            "仅粉丝可评论时必须同时开启评论",
        )
    topics_value = wechat.get("topics")
    topics = (
        _string_list(wechat, "topics", "$.wechat", issues, maximum=3)
        if topics_value is not None
        else []
    )
    for index, topic in enumerate(topics):
        topic_path = f"$.wechat.topics[{index}]"
        if not 2 <= len(topic) <= 20:
            _add(
                issues,
                "error",
                "wechat.topic_length",
                topic_path,
                "每个微信话题应为 2–20 个字符",
            )
        if topic.startswith("#") or "\n" in topic or "\r" in topic:
            _add(
                issues,
                "error",
                "wechat.topic_format",
                topic_path,
                "只记录话题名称，不添加 # 或换行",
            )

    state, checks = _publication(record, issues)
    approved_like = state in APPROVED_STATES
    remote_like = state in REMOTE_STATES

    headlines = _object(record, "headlines", "$", issues)
    primary_headline = _text(headlines, "primary", "$.headlines", issues, minimum=8, maximum=64)
    cover_headline = _text(headlines, "cover", "$.headlines", issues, minimum=4, maximum=32)
    candidates = _string_list(headlines, "candidates", "$.headlines", issues, minimum=3, maximum=6)
    for index, candidate in enumerate(candidates):
        if not 8 <= len(candidate) <= 64:
            _add(
                issues,
                "error",
                "headline.length",
                f"$.headlines.candidates[{index}]",
                "候选标题应为 8–64 个字符",
            )
    if primary_headline and primary_headline not in candidates:
        _add(
            issues,
            "error",
            "headline.primary_not_candidate",
            "$.headlines.primary",
            "主标题必须来自候选标题列表",
        )
    brief_value = record.get("brief_30s")
    brief = (
        _string_list(record, "brief_30s", "$", issues, minimum=2, maximum=4)
        if brief_value is not None
        else []
    )
    for index, item in enumerate(brief):
        if not 12 <= len(item) <= 140:
            _add(
                issues,
                "error",
                "brief.item_length",
                f"$.brief_30s[{index}]",
                "每条速读应为 12–140 个字符",
            )
    brief_length = sum(len(item) for item in brief)
    if brief and not 50 <= brief_length <= 420:
        _add(issues, "error", "brief.total_length", "$.brief_30s", "速读总长应为 50–420 个字符")

    show_thesis = record.get("show_thesis")
    if show_thesis is not None and not isinstance(show_thesis, bool):
        _add(issues, "error", "schema.type", "$.show_thesis", "必须是布尔值")

    thesis = _object(record, "thesis", "$", issues)
    _text(thesis, "core", "$.thesis", issues, minimum=20, maximum=240)
    boundary = _text(thesis, "boundary", "$.thesis", issues, minimum=12, maximum=200)
    boundary_words = ("但", "不等于", "并非", "不能", "尚未", "仍需", "取决于", "未知", "仅限")
    if boundary and not any(word in boundary for word in boundary_words):
        _add(
            issues,
            "warning",
            "thesis.boundary_weak",
            "$.thesis.boundary",
            "建议明确写出反例、限制条件或尚未证实之处",
        )

    sections_raw = record.get("sections")
    if not isinstance(sections_raw, list):
        _add(issues, "error", "schema.type", "$.sections", "必须是数组")
        sections_raw = []
    section_minimum = {"bulletin": 2, "report": 3, "profile": 3}.get(article_format, 2)
    if len(sections_raw) < section_minimum:
        _add(
            issues,
            "error",
            "section.count",
            "$.sections",
            f"{article_format or '文章'} 至少需要 {section_minimum} 个正文段落",
        )
    if len(sections_raw) > 12:
        _add(issues, "error", "section.count", "$.sections", "正文段落最多 12 个")

    section_ids: set[str] = set()
    section_claims: dict[str, list[str]] = {}
    section_media: dict[str, list[str]] = {}
    section_kinds: list[str] = []
    total_bold_spans = 0
    for index, section_value in enumerate(sections_raw):
        path = f"$.sections[{index}]"
        if not isinstance(section_value, dict):
            _add(issues, "error", "schema.type", path, "必须是对象")
            continue
        section_id = _text(section_value, "id", path, issues)
        if section_id and not ID_PATTERN.fullmatch(section_id):
            _add(issues, "error", "section.id_invalid", f"{path}.id", "只允许小写字母、数字和单连字符")
        if section_id in section_ids:
            _add(issues, "error", "section.id_duplicate", f"{path}.id", "段落 ID 不得重复")
        section_ids.add(section_id)
        _text(section_value, "heading", path, issues, minimum=2, maximum=40)
        show_heading = section_value.get("show_heading")
        if show_heading is not None and not isinstance(show_heading, bool):
            _add(issues, "error", "schema.type", f"{path}.show_heading", "必须是布尔值")
        kind = _text(section_value, "kind", path, issues)
        _enum(kind, SECTION_KINDS, f"{path}.kind", issues, "section.kind_invalid")
        section_kinds.append(kind)
        paragraphs = _string_list(section_value, "paragraphs", path, issues, minimum=1, maximum=6)
        for paragraph_index, paragraph in enumerate(paragraphs):
            if not 18 <= len(paragraph) <= 800:
                _add(
                    issues,
                    "error",
                    "section.paragraph_length",
                    f"{path}.paragraphs[{paragraph_index}]",
                    "正文段落应为 18–800 个字符",
                )
        bold_spans_raw = section_value.get("bold_spans", [])
        if not isinstance(bold_spans_raw, list):
            _add(issues, "error", "schema.type", f"{path}.bold_spans", "必须是数组")
        else:
            total_bold_spans += len(bold_spans_raw)
            emphasized_paragraphs: set[int] = set()
            for bold_index, bold_value in enumerate(bold_spans_raw):
                bold_path = f"{path}.bold_spans[{bold_index}]"
                if not isinstance(bold_value, dict):
                    _add(issues, "error", "schema.type", bold_path, "必须是对象")
                    continue
                paragraph_number = bold_value.get("paragraph")
                if (
                    not isinstance(paragraph_number, int)
                    or isinstance(paragraph_number, bool)
                    or not 1 <= paragraph_number <= len(paragraphs)
                ):
                    _add(
                        issues,
                        "error",
                        "section.bold_span_position",
                        f"{bold_path}.paragraph",
                        f"必须是 1–{len(paragraphs)} 的整数",
                    )
                elif paragraph_number in emphasized_paragraphs:
                    _add(
                        issues,
                        "error",
                        "section.bold_span_paragraph_limit",
                        f"{bold_path}.paragraph",
                        "每个正文段落最多加粗一处",
                    )
                else:
                    emphasized_paragraphs.add(paragraph_number)

                bold_text_raw = bold_value.get("text")
                if not isinstance(bold_text_raw, str):
                    _add(issues, "error", "schema.type", f"{bold_path}.text", "必须是字符串")
                    continue
                bold_text = bold_text_raw.strip()
                if bold_text != bold_text_raw or "\n" in bold_text or "\r" in bold_text:
                    _add(
                        issues,
                        "error",
                        "section.bold_span_not_normalized",
                        f"{bold_path}.text",
                        "加粗文本必须是无首尾空白的单行原文",
                    )
                if not 4 <= len(bold_text) <= 40:
                    _add(
                        issues,
                        "error",
                        "section.bold_span_length",
                        f"{bold_path}.text",
                        "单处加粗应为 4–40 个字符",
                    )
                if (
                    isinstance(paragraph_number, int)
                    and not isinstance(paragraph_number, bool)
                    and 1 <= paragraph_number <= len(paragraphs)
                    and bold_text
                ):
                    paragraph = paragraphs[paragraph_number - 1]
                    occurrence_count = paragraph.count(bold_text)
                    if occurrence_count == 0:
                        _add(
                            issues,
                            "error",
                            "section.bold_span_missing",
                            f"{bold_path}.text",
                            "加粗文本必须完整出现在指定段落中",
                        )
                    elif occurrence_count > 1:
                        _add(
                            issues,
                            "error",
                            "section.bold_span_ambiguous",
                            f"{bold_path}.text",
                            "加粗文本在指定段落中必须只出现一次",
                        )
                    if bold_text == paragraph or len(bold_text) * 2 > len(paragraph):
                        _add(
                            issues,
                            "error",
                            "section.bold_span_too_broad",
                            f"{bold_path}.text",
                            "局部加粗不得覆盖整段或超过段落一半",
                        )
        claim_ids = _string_list(section_value, "claim_ids", path, issues, minimum=1)
        media_ids = _string_list(section_value, "media_ids", path, issues)
        placements_value = section_value.get("media_placements")
        if placements_value is not None:
            if not isinstance(placements_value, list):
                _add(issues, "error", "schema.type", f"{path}.media_placements", "必须是数组")
            else:
                placed_media_ids: list[str] = []
                for placement_index, placement in enumerate(placements_value):
                    placement_path = f"{path}.media_placements[{placement_index}]"
                    if not isinstance(placement, dict):
                        _add(issues, "error", "schema.type", placement_path, "必须是对象")
                        continue
                    placed_media_id = _text(placement, "media_id", placement_path, issues)
                    if placed_media_id not in media_ids:
                        _add(
                            issues,
                            "error",
                            "section.media_placement_unlisted",
                            f"{placement_path}.media_id",
                            "段落级图片位置只能引用本节 media_ids",
                        )
                    placed_media_ids.append(placed_media_id)
                    after_paragraph = placement.get("after_paragraph")
                    if (
                        not isinstance(after_paragraph, int)
                        or isinstance(after_paragraph, bool)
                        or not 0 <= after_paragraph <= len(paragraphs)
                    ):
                        _add(
                            issues,
                            "error",
                            "section.media_placement_position",
                            f"{placement_path}.after_paragraph",
                            f"必须是 0–{len(paragraphs)} 的整数",
                        )
                if len(placed_media_ids) != len(set(placed_media_ids)):
                    _add(
                        issues,
                        "error",
                        "section.media_placement_duplicate",
                        f"{path}.media_placements",
                        "同一张图片只能安排一次",
                    )
                if set(placed_media_ids) != set(media_ids):
                    _add(
                        issues,
                        "error",
                        "section.media_placement_incomplete",
                        f"{path}.media_placements",
                        "启用段落级图片位置后必须安排本节全部 media_ids",
                    )
        section_claims[section_id] = claim_ids
        section_media[section_id] = media_ids

    if total_bold_spans > MAX_BOLD_SPANS:
        _add(
            issues,
            "error",
            "section.bold_span_article_limit",
            "$.sections",
            f"每篇文章最多允许 {MAX_BOLD_SPANS} 处局部加粗",
        )

    if not any(kind in {"analysis", "impact", "outlook"} for kind in section_kinds):
        _add(issues, "error", "section.analysis_required", "$.sections", "至少需要一个分析、影响或展望段落")
    if article_format == "profile" and "timeline" not in section_kinds:
        _add(issues, "error", "profile.timeline_required", "$.sections", "人物稿必须包含 timeline 段落")

    format_rule = FORMAT_RULES.get(article_format)
    body_characters = _body_character_count(record)
    if format_rule and not format_rule["body_min"] <= body_characters <= format_rule["body_max"]:
        _add(
            issues,
            "error",
            "format.body_length",
            "$.sections",
            f"{article_format} 正文需为 {format_rule['body_min']}–{format_rule['body_max']} 个非空白字符，当前为 {body_characters}",
        )

    sources_raw = record.get("sources")
    if not isinstance(sources_raw, list):
        _add(issues, "error", "schema.type", "$.sources", "必须是数组")
        sources_raw = []
    source_minimum = FORMAT_RULES.get(article_format, {}).get("sources", 2)
    if len(sources_raw) < source_minimum:
        _add(
            issues,
            "error",
            "source.count",
            "$.sources",
            f"{article_format or '文章'} 至少需要 {source_minimum} 个来源",
        )

    source_ids: set[str] = set()
    source_urls: set[str] = set()
    for index, source_value in enumerate(sources_raw):
        path = f"$.sources[{index}]"
        if not isinstance(source_value, dict):
            _add(issues, "error", "schema.type", path, "必须是对象")
            continue
        source_id = _text(source_value, "id", path, issues)
        if source_id and not SOURCE_ID_PATTERN.fullmatch(source_id):
            _add(issues, "error", "source.id_invalid", f"{path}.id", "来源 ID 应使用 S1、S2 格式")
        if source_id in source_ids:
            _add(issues, "error", "source.id_duplicate", f"{path}.id", "来源 ID 不得重复")
        source_ids.add(source_id)
        kind = _text(source_value, "kind", path, issues)
        _enum(kind, SOURCE_KINDS, f"{path}.kind", issues, "source.kind_invalid")
        _text(source_value, "title", path, issues, minimum=3, maximum=180)
        _text(source_value, "publisher", path, issues, minimum=2, maximum=80)
        url = _text(source_value, "url", path, issues)
        _check_url(url, f"{path}.url", issues)
        normalized_url = url.rstrip("/").lower()
        if normalized_url in source_urls:
            _add(issues, "error", "source.url_duplicate", f"{path}.url", "来源 URL 不得重复")
        source_urls.add(normalized_url)
        published_at_value = source_value.get("published_at")
        if "published_at" not in source_value:
            published_at = ""
            _add(issues, "error", "schema.required", f"{path}.published_at", "必须显式提供日期或 null")
        elif published_at_value is None:
            published_at = ""
        elif isinstance(published_at_value, str):
            published_at = published_at_value.strip()
            if not published_at:
                _add(
                    issues,
                    "error",
                    "source.published_at_empty",
                    f"{path}.published_at",
                    "未知发布日期请使用 null，不要使用空字符串",
                )
        else:
            published_at = ""
            _add(issues, "error", "schema.type", f"{path}.published_at", "必须是 ISO 8601 字符串或 null")
        accessed_at = _text(source_value, "accessed_at", path, issues)
        published_date = _parse_temporal(published_at, f"{path}.published_at", issues) if published_at else None
        accessed_date = _parse_temporal(accessed_at, f"{path}.accessed_at", issues)
        if published_date and accessed_date and accessed_date < published_date:
            _add(issues, "error", "source.time_order", f"{path}.accessed_at", "访问日期不得早于发布日期")

    show_public_sources = record.get("show_public_sources", False)
    if not isinstance(show_public_sources, bool):
        _add(issues, "error", "schema.type", "$.show_public_sources", "必须是布尔值")

    public_source_ids_raw = record.get("public_source_ids")
    if public_source_ids_raw is not None:
        if not isinstance(public_source_ids_raw, list):
            _add(issues, "error", "schema.type", "$.public_source_ids", "必须是 1–3 个来源 ID 的数组")
        else:
            if show_public_sources and not 1 <= len(public_source_ids_raw) <= 3:
                _add(
                    issues,
                    "error",
                    "source.public_count",
                    "$.public_source_ids",
                    "显示延伸阅读时只保留 1–3 条关键来源",
                )
            seen_public_source_ids: set[str] = set()
            seen_public_labels: set[str] = set()
            sources_by_id = {
                source.get("id"): source
                for source in sources_raw
                if isinstance(source, dict) and isinstance(source.get("id"), str)
            }
            for index, source_id in enumerate(public_source_ids_raw):
                path = f"$.public_source_ids[{index}]"
                if not isinstance(source_id, str):
                    _add(issues, "error", "schema.type", path, "必须是来源 ID 字符串")
                    continue
                if source_id in seen_public_source_ids:
                    _add(issues, "error", "source.public_duplicate", path, f"公开来源 {source_id} 不得重复")
                seen_public_source_ids.add(source_id)
                if source_id not in source_ids:
                    _add(issues, "error", "source.public_missing", path, f"公开来源 {source_id} 不存在")
                    continue
                source = sources_by_id[source_id]
                public_label_raw = source.get("public_label")
                if public_label_raw is not None and not isinstance(public_label_raw, str):
                    _add(
                        issues,
                        "error",
                        "schema.type",
                        f"$.sources[{sources_raw.index(source)}].public_label",
                        "必须是字符串",
                    )
                    continue
                public_label = (
                    public_label_raw.strip()
                    if isinstance(public_label_raw, str)
                    else str(source.get("title", "")).strip()
                )
                if isinstance(public_label_raw, str) and (
                    public_label_raw != public_label or "\n" in public_label or "\r" in public_label
                ):
                    _add(
                        issues,
                        "error",
                        "source.public_label_not_normalized",
                        f"$.sources[{sources_raw.index(source)}].public_label",
                        "公开短标签必须是无首尾空白的单行文本",
                    )
                if not 2 <= len(public_label) <= 36:
                    _add(
                        issues,
                        "error",
                        "source.public_label_length",
                        f"$.sources[{sources_raw.index(source)}].public_label",
                        "公开来源的展示文字应为 2–36 个字符；标题较长时请提供 public_label",
                    )
                if public_label in seen_public_labels:
                    _add(
                        issues,
                        "error",
                        "source.public_label_duplicate",
                        path,
                        "公开来源的展示文字不得重复",
                    )
                seen_public_labels.add(public_label)
    if show_public_sources and public_source_ids_raw is None:
        _add(
            issues,
            "error",
            "source.public_required",
            "$.public_source_ids",
            "显示延伸阅读时必须明确选择公开来源",
        )

    test_runs_raw = record.get("test_runs", [])
    if not isinstance(test_runs_raw, list):
        _add(issues, "error", "schema.type", "$.test_runs", "必须是数组")
        test_runs_raw = []
    test_run_ids: set[str] = set()
    for index, test_run_value in enumerate(test_runs_raw):
        path = f"$.test_runs[{index}]"
        if not isinstance(test_run_value, dict):
            _add(issues, "error", "schema.type", path, "必须是对象")
            continue
        test_run_id = _text(test_run_value, "id", path, issues)
        if test_run_id and not TEST_RUN_ID_PATTERN.fullmatch(test_run_id):
            _add(issues, "error", "test.id_invalid", f"{path}.id", "实测记录 ID 应使用 T1、T2 格式")
        if test_run_id in test_run_ids:
            _add(issues, "error", "test.id_duplicate", f"{path}.id", "实测记录 ID 不得重复")
        test_run_ids.add(test_run_id)

        tested_at = _text(test_run_value, "tested_at", path, issues)
        _parse_temporal(tested_at, f"{path}.tested_at", issues)
        for field in (
            "access_scope",
            "region",
            "account_tier",
            "product_version",
            "model_version",
            "application_or_harness",
            "task",
            "prompt_or_input",
            "acceptance_criteria",
            "tools",
            "permissions",
            "reasoning_mode",
            "relevant_settings",
            "duration",
            "tokens",
            "cost",
            "result",
            "failures",
            "manual_intervention",
            "comparison_conditions",
            "limitations",
        ):
            _text(test_run_value, field, path, issues)

        for field, minimum in (("run_count", 1), ("retries", 0)):
            value = test_run_value.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                _add(
                    issues,
                    "error",
                    "test.count_invalid",
                    f"{path}.{field}",
                    f"必须是大于等于 {minimum} 的整数",
                )

        artifact_paths = _string_list(
            test_run_value,
            "artifact_paths",
            path,
            issues,
            minimum=1,
        )
        for artifact_index, artifact_path in enumerate(artifact_paths):
            artifact_field_path = f"{path}.artifact_paths[{artifact_index}]"
            is_relative = bool(RELATIVE_MEDIA_PATTERN.fullmatch(artifact_path))
            if not is_relative or ".." in Path(artifact_path).parts:
                _add(
                    issues,
                    "error",
                    "test.artifact_path_invalid",
                    artifact_field_path,
                    "实测产物必须使用稿件目录内的安全相对路径",
                )
            elif require_media:
                if media_base is None:
                    _add(
                        issues,
                        "error",
                        "test.artifact_base_missing",
                        artifact_field_path,
                        "检查实测产物时必须提供 JSON 所在目录",
                    )
                elif not (media_base / artifact_path).is_file():
                    _add(
                        issues,
                        "error",
                        "test.artifact_missing",
                        artifact_field_path,
                        f"实测产物不存在：{media_base / artifact_path}",
                    )

    claims_raw = record.get("claims")
    if not isinstance(claims_raw, list):
        _add(issues, "error", "schema.type", "$.claims", "必须是数组")
        claims_raw = []
    claim_minimum = {"bulletin": 3, "report": 6, "profile": 6}.get(article_format, 3)
    if len(claims_raw) < claim_minimum:
        _add(
            issues,
            "error",
            "claim.count",
            "$.claims",
            f"{article_format or '文章'} 的主张台账至少需要 {claim_minimum} 项",
        )

    claim_ids: set[str] = set()
    claim_statements: set[str] = set()
    used_source_ids: set[str] = set()
    used_test_run_ids: set[str] = set()
    factual_claim_count = 0
    analysis_claim_count = 0
    for index, claim_value in enumerate(claims_raw):
        path = f"$.claims[{index}]"
        if not isinstance(claim_value, dict):
            _add(issues, "error", "schema.type", path, "必须是对象")
            continue
        claim_id = _text(claim_value, "id", path, issues)
        if claim_id and not CLAIM_ID_PATTERN.fullmatch(claim_id):
            _add(issues, "error", "claim.id_invalid", f"{path}.id", "主张 ID 应使用 C1、C2 格式")
        if claim_id in claim_ids:
            _add(issues, "error", "claim.id_duplicate", f"{path}.id", "主张 ID 不得重复")
        claim_ids.add(claim_id)
        kind = _text(claim_value, "kind", path, issues)
        _enum(kind, CLAIM_KINDS, f"{path}.kind", issues, "claim.kind_invalid")
        if kind in {"fact", "quote"}:
            factual_claim_count += 1
        if kind in {"analysis", "forecast"}:
            analysis_claim_count += 1
        statement = _text(claim_value, "statement", path, issues, minimum=12, maximum=260)
        normalized_statement = re.sub(r"\s+", "", statement)
        if normalized_statement in claim_statements:
            _add(issues, "error", "claim.statement_duplicate", f"{path}.statement", "主张内容不得重复")
        claim_statements.add(normalized_statement)
        section_id = _text(claim_value, "section_id", path, issues)
        if section_id not in section_ids:
            _add(issues, "error", "claim.section_missing", f"{path}.section_id", "引用了不存在的正文段落")
        elif claim_id not in section_claims.get(section_id, []):
            _add(
                issues,
                "error",
                "claim.section_link_missing",
                f"{path}.section_id",
                "主张必须同时出现在对应段落的 claim_ids 中",
            )
        linked_sources = _string_list(claim_value, "source_ids", path, issues)
        linked_test_runs = (
            _string_list(claim_value, "test_run_ids", path, issues)
            if "test_run_ids" in claim_value
            else []
        )
        if kind == "fact" and not linked_sources and not linked_test_runs:
            _add(
                issues,
                "error",
                "claim.evidence_required",
                path,
                "事实必须关联公开来源或编辑部实测记录",
            )
        if kind == "quote" and not linked_sources:
            _add(issues, "error", "claim.source_required", f"{path}.source_ids", "引语必须关联公开来源")
        if kind == "forecast" and not linked_sources and not linked_test_runs:
            _add(issues, "warning", "claim.forecast_unanchored", path, "预测最好关联事实依据")
        for source_id in linked_sources:
            used_source_ids.add(source_id)
            if source_id not in source_ids:
                _add(issues, "error", "claim.source_missing", f"{path}.source_ids", f"来源 {source_id} 不存在")
        for test_run_id in linked_test_runs:
            used_test_run_ids.add(test_run_id)
            if test_run_id not in test_run_ids:
                _add(
                    issues,
                    "error",
                    "claim.test_run_missing",
                    f"{path}.test_run_ids",
                    f"实测记录 {test_run_id} 不存在",
                )
        confidence = _text(claim_value, "confidence", path, issues)
        _enum(confidence, CONFIDENCE_LEVELS, f"{path}.confidence", issues, "claim.confidence_invalid")

    minimum_facts = 2 if article_format == "bulletin" else 4
    if factual_claim_count < minimum_facts:
        _add(
            issues,
            "error",
            "claim.factual_count",
            "$.claims",
            f"至少需要 {minimum_facts} 条事实或引语主张",
        )
    if analysis_claim_count < 1:
        _add(issues, "error", "claim.analysis_required", "$.claims", "至少需要一条分析或预测主张")

    listed_claim_locations: dict[str, list[str]] = {}
    for section_id, listed_ids in section_claims.items():
        for listed_id in listed_ids:
            listed_claim_locations.setdefault(listed_id, []).append(section_id)
            if listed_id not in claim_ids:
                _add(
                    issues,
                    "error",
                    "section.claim_missing",
                    f"$.sections[{section_id}].claim_ids",
                    f"主张 {listed_id} 不存在",
                )
    for claim_id, locations in listed_claim_locations.items():
        if len(locations) > 1:
            _add(
                issues,
                "error",
                "section.claim_reused",
                "$.sections",
                f"主张 {claim_id} 被多个段落重复认领",
            )

    for source_id in source_ids - used_source_ids:
        _add(issues, "warning", "source.unused", "$.sources", f"来源 {source_id} 未被任何主张引用")
    for test_run_id in test_run_ids - used_test_run_ids:
        _add(issues, "warning", "test.unused", "$.test_runs", f"实测记录 {test_run_id} 未被任何主张引用")

    media_raw = record.get("media")
    if not isinstance(media_raw, list):
        _add(issues, "error", "schema.type", "$.media", "必须是数组")
        media_raw = []
    media_ids: set[str] = set()
    cover_count = 0
    inline_count = 0
    ai_generated_inline_count = 0
    for index, media_value in enumerate(media_raw):
        path = f"$.media[{index}]"
        if not isinstance(media_value, dict):
            _add(issues, "error", "schema.type", path, "必须是对象")
            continue
        media_id = _text(media_value, "id", path, issues)
        if media_id and not MEDIA_ID_PATTERN.fullmatch(media_id):
            _add(issues, "error", "media.id_invalid", f"{path}.id", "媒体 ID 应使用 M1、M2 格式")
        if media_id in media_ids:
            _add(issues, "error", "media.id_duplicate", f"{path}.id", "媒体 ID 不得重复")
        media_ids.add(media_id)
        kind = _text(media_value, "kind", path, issues)
        _enum(kind, MEDIA_KINDS, f"{path}.kind", issues, "media.kind_invalid")
        role = _text(media_value, "role", path, issues)
        _enum(role, MEDIA_ROLES, f"{path}.role", issues, "media.role_invalid")
        if role == "cover":
            cover_count += 1
        elif role == "inline":
            inline_count += 1
        asset_path = _text(media_value, "path", path, issues)
        is_remote = _valid_url(asset_path)
        is_relative = bool(RELATIVE_MEDIA_PATTERN.fullmatch(asset_path)) and ".." not in Path(asset_path).parts
        if not is_remote and not is_relative:
            _add(issues, "error", "media.path_invalid", f"{path}.path", "必须是 http(s) URL 或安全的相对路径")
        elif remote_like and (not is_remote or urlsplit(asset_path).scheme != "https"):
            _add(issues, "error", "media.path_not_remote", f"{path}.path", "远端草稿、发布和群发状态只能使用 HTTPS 图片")
        if require_media and is_relative:
            if media_base is None:
                _add(issues, "error", "media.base_missing", f"{path}.path", "检查相对媒体时必须提供 JSON 所在目录")
            elif not (media_base / asset_path).is_file():
                _add(
                    issues,
                    "error",
                    "media.file_missing",
                    f"{path}.path",
                    f"相对媒体文件不存在：{media_base / asset_path}",
                )
        _text(media_value, "purpose", path, issues, minimum=4, maximum=120)
        _text(media_value, "alt", path, issues, minimum=4, maximum=120)
        _text(media_value, "caption", path, issues, minimum=6, maximum=180)
        show_caption = media_value.get("show_caption", False)
        if not isinstance(show_caption, bool):
            _add(issues, "error", "schema.type", f"{path}.show_caption", "必须是布尔值")
        elif role == "cover" and show_caption:
            _add(issues, "error", "media.cover_caption_forbidden", f"{path}.show_caption", "封面图不显示正文图注")
        _text(media_value, "credit", path, issues, minimum=2, maximum=120)
        source_url = _text(media_value, "source_url", path, issues)
        _check_url(source_url, f"{path}.source_url", issues, https_required=remote_like)
        rights = _text(media_value, "rights", path, issues)
        _enum(rights, MEDIA_RIGHTS, f"{path}.rights", issues, "media.rights_invalid")
        if rights == "pending":
            _add(
                issues,
                "error" if approved_like else "warning",
                "media.rights_pending",
                f"{path}.rights",
                "版权状态尚未确认",
            )
        _text(media_value, "crop_note", path, issues, minimum=2, maximum=120)
        generated = media_value.get("generated")
        if not isinstance(generated, bool):
            _add(issues, "error", "schema.type", f"{path}.generated", "必须是布尔值")
        elif generated:
            if role == "inline":
                ai_generated_inline_count += 1
            if kind == "screenshot":
                _add(
                    issues,
                    "error",
                    "media.ai_screenshot_forbidden",
                    f"{path}.generated",
                    "网页截图不得标记为生成式 AI 图片",
                )
        section_id = media_value.get("section_id")
        if section_id is not None and not isinstance(section_id, str):
            _add(issues, "error", "schema.type", f"{path}.section_id", "必须是字符串或 null")
        elif isinstance(section_id, str):
            if section_id not in section_ids:
                _add(issues, "error", "media.section_missing", f"{path}.section_id", "引用了不存在的正文段落")
            elif media_id not in section_media.get(section_id, []):
                _add(
                    issues,
                    "error",
                    "media.section_link_missing",
                    f"{path}.section_id",
                    "媒体必须同时出现在对应段落的 media_ids 中",
                )
        if role == "inline" and not isinstance(section_id, str):
            _add(issues, "error", "media.inline_section_required", f"{path}.section_id", "正文媒体必须绑定段落")
        if role == "cover" and section_id is not None:
            _add(issues, "warning", "media.cover_section_ignored", f"{path}.section_id", "封面图无需绑定正文段落")

    if approved_like and cover_count != 1:
        _add(issues, "error", "media.cover_count", "$.media", "批准及后续状态必须且只能有一张封面图")
    inline_minimum = FORMAT_RULES.get(article_format, {}).get("inline", 0)
    if inline_count < inline_minimum:
        _add(
            issues,
            "error",
            "media.inline_count",
            "$.media",
            f"{article_format or '文章'} 至少需要 {inline_minimum} 张正文图，封面不计入，当前为 {inline_count}",
        )
    if ai_generated_inline_count > 1:
        _add(
            issues,
            "error",
            "media.ai_inline_limit",
            "$.media",
            "正文最多允许一张生成式 AI 概念图",
        )
    for section_id, listed_ids in section_media.items():
        for listed_id in listed_ids:
            if listed_id not in media_ids:
                _add(
                    issues,
                    "error",
                    "section.media_missing",
                    f"$.sections[{section_id}].media_ids",
                    f"媒体 {listed_id} 不存在",
                )

    question_value = record.get("discussion_question")
    if question_value is not None:
        question = _text(record, "discussion_question", "$", issues, minimum=12, maximum=160)
        if question and not question.endswith(("？", "?")):
            _add(issues, "error", "discussion.not_question", "$.discussion_question", "讨论题必须以问号结尾")

    return _build_result(issues, strict=strict, state=state, checks=checks, record=record)


def _build_result(
    issues: list[Issue],
    *,
    strict: bool,
    state: str = "unknown",
    checks: dict[str, str] | None = None,
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = checks or {}
    error_count = sum(issue["level"] == "error" for issue in issues)
    warning_count = sum(issue["level"] == "warning" for issue in issues)

    def gate(prefixes: tuple[str, ...]) -> bool:
        return not any(
            issue["level"] == "error" and issue["code"].startswith(prefixes)
            for issue in issues
        )

    gates = {
        "record": gate(("schema.", "brand.", "meta.", "date.", "url.", "wechat.")),
        "editorial": gate(
            ("editorial.", "headline.", "brief.", "thesis.", "section.", "profile.", "format.", "discussion.")
        ),
        "sources": gate(("source.", "test.", "claim.")),
        "media": gate(("media.",)),
        "status": gate(("publication.",)),
    }
    ready_checks = all(checks.get(name) == "passed" for name in ("facts", "media_rights", "editorial"))
    valid = error_count == 0 and (not strict or warning_count == 0)
    publication_ready = (
        state in APPROVED_STATES
        and ready_checks
        and valid
        and all(gates.values())
    )
    renderable = valid and state != "failed"
    media_items = record.get("media", []) if record and isinstance(record.get("media"), list) else []
    summary = {
        "errors": error_count,
        "warnings": warning_count,
        "body_characters": _body_character_count(record) if record else 0,
        "sections": len(record.get("sections", [])) if record and isinstance(record.get("sections"), list) else 0,
        "sources": len(record.get("sources", [])) if record and isinstance(record.get("sources"), list) else 0,
        "test_runs": len(record.get("test_runs", [])) if record and isinstance(record.get("test_runs"), list) else 0,
        "claims": len(record.get("claims", [])) if record and isinstance(record.get("claims"), list) else 0,
        "media": len(media_items),
        "inline_media": sum(
            isinstance(item, dict) and item.get("role") == "inline" for item in media_items
        ),
    }
    return {
        "ok": valid,
        "strict": strict,
        "publication_state": state,
        "publication_ready": publication_ready,
        "renderable": renderable,
        "gates": gates,
        "summary": summary,
        "issues": issues,
    }


def validate_file(path: Path, *, strict: bool = False, require_media: bool = False) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
    except OSError as error:
        result = _build_result(
            [{"level": "error", "code": "io.read", "path": "$", "message": str(error)}],
            strict=strict,
        )
    except json.JSONDecodeError as error:
        result = _build_result(
            [
                {
                    "level": "error",
                    "code": "json.invalid",
                    "path": f"line {error.lineno}, column {error.colno}",
                    "message": error.msg,
                }
            ],
            strict=strict,
        )
    else:
        result = validate_record(
            record,
            strict=strict,
            require_media=require_media,
            media_base=path.parent if require_media else None,
        )
    result["file"] = str(path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验 Frontier Signals 文章 JSON")
    parser.add_argument("input", type=Path, help="文章 JSON 文件")
    parser.add_argument("--strict", action="store_true", help="将警告也视为失败")
    parser.add_argument("--require-media", action="store_true", help="确认相对媒体文件存在于 JSON 相对路径")
    parser.add_argument("--compact", action="store_true", help="输出单行 JSON")
    args = parser.parse_args(argv)

    result = validate_file(args.input, strict=args.strict, require_media=args.require_media)
    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        separators=(",", ":") if args.compact else None,
    )
    sys.stdout.write("\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
