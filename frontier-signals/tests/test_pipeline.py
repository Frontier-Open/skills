from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ASSETS = ROOT / "assets"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from render_wechat import render_html, render_markdown  # noqa: E402
from validate_signal import validate_record  # noqa: E402

try:
    from PIL import Image, ImageDraw
    from render_cover import HEIGHT, WIDTH, _font, _wrap, render_cover

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_run_fixture() -> dict:
    return {
        "id": "T1",
        "tested_at": "2026-08-14T12:00:00+08:00",
        "access_scope": "公开预览版",
        "region": "中国大陆",
        "account_tier": "开发者测试账号",
        "product_version": "0.1.0-rc.6",
        "model_version": "示例模型 1.0",
        "application_or_harness": "示例 Harness",
        "task": "在干净仓库中修复一个带回归测试的解析错误",
        "prompt_or_input": "tests/artifacts/T1/prompt.txt",
        "acceptance_criteria": "原有测试和新增回归测试全部通过",
        "tools": "文件读取、补丁写入与测试命令",
        "permissions": "仅允许修改临时仓库，不允许联网",
        "reasoning_mode": "默认",
        "relevant_settings": "温度与并发沿用产品默认值",
        "run_count": 3,
        "duration": "分别为 8、9、8 分钟",
        "tokens": "产品未提供",
        "cost": "测试期未计费",
        "result": "三次运行均通过验收测试",
        "failures": "未观察到失败",
        "retries": 0,
        "manual_intervention": "每次仅确认文件写入权限",
        "artifact_paths": ["tests/artifacts/T1/run-summary.json"],
        "comparison_conditions": "非横向对比测试",
        "limitations": "只覆盖一个仓库与一种任务",
    }


class ValidationTests(unittest.TestCase):
    def test_example_passes_all_gates_in_strict_mode(self) -> None:
        result = validate_record(load_json(ASSETS / "signal.example.json"), strict=True)

        self.assertTrue(result["ok"])
        self.assertTrue(result["publication_ready"])
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["summary"]["warnings"], 0)
        self.assertGreaterEqual(result["summary"]["body_characters"], 900)
        self.assertLessEqual(result["summary"]["body_characters"], 1500)
        self.assertEqual(result["summary"]["inline_media"], 2)
        self.assertTrue(all(result["gates"].values()))

    def test_invalid_fixture_exposes_editorial_source_media_and_status_failures(self) -> None:
        result = validate_record(load_json(FIXTURES / "signal.invalid.json"))
        codes = {issue["code"] for issue in result["issues"]}

        self.assertFalse(result["ok"])
        self.assertFalse(result["publication_ready"])
        self.assertIn("headline.primary_not_candidate", codes)
        self.assertIn("claim.source_missing", codes)
        self.assertIn("format.body_length", codes)
        self.assertIn("media.inline_count", codes)
        self.assertIn("media.rights_pending", codes)
        self.assertIn("publication.check_not_passed", codes)
        self.assertFalse(result["gates"]["editorial"])
        self.assertFalse(result["gates"]["sources"])
        self.assertFalse(result["gates"]["media"])
        self.assertFalse(result["gates"]["status"])

    def test_emotional_headline_is_allowed_when_it_is_a_valid_candidate(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        hype_title = "刚刚，OpenAI 彻底颠覆所有 AI 产品"
        record["headlines"]["primary"] = hype_title
        record["headlines"]["candidates"][0] = hype_title

        result = validate_record(record)

        self.assertTrue(result["ok"])
        self.assertNotIn("headline.hype_blacklist", {issue["code"] for issue in result["issues"]})

    def test_cover_headline_allows_complete_bilingual_title_up_to_32_characters(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        title = "超 70 亿美元，Stripe 被曝收购 OpenRouter"
        record["headlines"]["cover"] = title + "！"

        accepted = validate_record(record)

        self.assertEqual(len(record["headlines"]["cover"]), 32)
        self.assertTrue(accepted["ok"])

        record["headlines"]["cover"] += "！"
        rejected = validate_record(record)

        self.assertFalse(rejected["ok"])
        self.assertIn("editorial.too_long", {issue["code"] for issue in rejected["issues"]})

    def test_public_source_selection_is_small_unique_and_resolvable(self) -> None:
        cases = (
            (["S1"], None),
            (["S1", "S2", "S3"], None),
            ([], "source.public_count"),
            (["S1", "S2", "S3", "S404"], "source.public_count"),
            (["S1", "S1", "S2"], "source.public_duplicate"),
            (["S1", "S2", "S404"], "source.public_missing"),
            ("S1", "schema.type"),
        )
        for value, expected_code in cases:
            with self.subTest(value=value):
                record = deepcopy(load_json(ASSETS / "signal.example.json"))
                record["show_public_sources"] = True
                record["public_source_ids"] = value
                result = validate_record(record)
                codes = {issue["code"] for issue in result["issues"]}
                if expected_code is None:
                    self.assertNotIn("source.public_count", codes)
                    self.assertNotIn("source.public_missing", codes)
                else:
                    self.assertIn(expected_code, codes)

    def test_showing_public_sources_requires_explicit_selection(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["show_public_sources"] = True
        record.pop("public_source_ids")

        result = validate_record(record)

        self.assertIn("source.public_required", {issue["code"] for issue in result["issues"]})

    def test_selected_public_source_uses_a_short_reader_facing_label(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["show_public_sources"] = True
        record["public_source_ids"] = ["S3"]
        record["sources"][2].pop("public_label")

        too_long = validate_record(record)
        self.assertIn("source.public_label_length", {issue["code"] for issue in too_long["issues"]})

        record["sources"][2]["public_label"] = "Azure 上线说明"
        valid = validate_record(record, strict=True)
        self.assertTrue(valid["ok"])

    def test_bold_spans_are_exact_sparse_paragraph_anchors(self) -> None:
        same_paragraph = deepcopy(load_json(ASSETS / "signal.example.json"))
        same_paragraph["sections"][1]["bold_spans"].append(
            {"paragraph": 3, "text": "会话状态、工具权限"}
        )
        same_codes = {issue["code"] for issue in validate_record(same_paragraph)["issues"]}
        self.assertIn("section.bold_span_paragraph_limit", same_codes)

        missing = deepcopy(load_json(ASSETS / "signal.example.json"))
        missing["sections"][1]["bold_spans"][0]["text"] = "正文中不存在的重点"
        missing_codes = {issue["code"] for issue in validate_record(missing)["issues"]}
        self.assertIn("section.bold_span_missing", missing_codes)

        ambiguous = deepcopy(load_json(ASSETS / "signal.example.json"))
        ambiguous["sections"][1]["bold_spans"][0]["text"] = "统一模型"
        ambiguous["sections"][1]["paragraphs"][2] += "统一模型仍需应用配合。"
        ambiguous_codes = {issue["code"] for issue in validate_record(ambiguous)["issues"]}
        self.assertIn("section.bold_span_ambiguous", ambiguous_codes)

    def test_article_allows_at_most_six_bold_spans(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["sections"][0]["bold_spans"] = [
            {"paragraph": 1, "text": "2024 年 5 月 13 日"},
            {"paragraph": 2, "text": "最容易被感知的变化是速度"},
            {"paragraph": 3, "text": "发布并非当天开放所有能力"},
            {"paragraph": 4, "text": "开发者侧的变化更直接"},
            {"paragraph": 5, "text": "模型发布与云平台上架几乎同步"},
        ]
        record["sections"][2]["bold_spans"] = [
            {"paragraph": 1, "text": "原生多模态也扩大了风险面"}
        ]

        result = validate_record(record)

        self.assertIn("section.bold_span_article_limit", {issue["code"] for issue in result["issues"]})

    def test_wechat_metadata_accepts_optional_empty_fields(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["wechat"] = {
            "author": "",
            "digest": "",
            "content_source_url": "",
            "comments": {
                "enabled": False,
                "fans_only": False,
            },
        }

        result = validate_record(record, strict=True)

        self.assertTrue(result["ok"])
        self.assertTrue(result["publication_ready"])

    def test_wechat_metadata_is_required_and_platform_bounded(self) -> None:
        cases = (
            (
                "missing",
                lambda record: record.pop("wechat"),
                ("schema.type", "$.wechat"),
            ),
            (
                "author_too_long",
                lambda record: record["wechat"].update(author="A" * 17),
                ("wechat.author_too_long", "$.wechat.author"),
            ),
            (
                "digest_too_long",
                lambda record: record["wechat"].update(digest="A" * 121),
                ("wechat.digest_too_long", "$.wechat.digest"),
            ),
            (
                "author_not_normalized",
                lambda record: record["wechat"].update(author=" Frontier World "),
                ("wechat.text_not_normalized", "$.wechat.author"),
            ),
            (
                "digest_not_single_line",
                lambda record: record["wechat"].update(digest="第一行\n第二行"),
                ("wechat.text_not_single_line", "$.wechat.digest"),
            ),
            (
                "relative_source_url",
                lambda record: record["wechat"].update(content_source_url="news/article"),
                ("url.invalid", "$.wechat.content_source_url"),
            ),
            (
                "source_url_too_long",
                lambda record: record["wechat"].update(
                    content_source_url="https://example.com/" + "a" * 1024
                ),
                ("wechat.content_source_url_too_long", "$.wechat.content_source_url"),
            ),
            (
                "comment_flag_not_boolean",
                lambda record: record["wechat"]["comments"].update(enabled=1),
                ("schema.type", "$.wechat.comments.enabled"),
            ),
            (
                "fans_only_without_comments",
                lambda record: record["wechat"]["comments"].update(
                    enabled=False,
                    fans_only=True,
                ),
                (
                    "wechat.comments_fans_only_requires_enabled",
                    "$.wechat.comments.fans_only",
                ),
            ),
        )
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                record = deepcopy(load_json(ASSETS / "signal.example.json"))
                mutate(record)

                result = validate_record(record)
                issue_keys = {(issue["code"], issue["path"]) for issue in result["issues"]}

                self.assertFalse(result["ok"])
                self.assertIn(expected, issue_keys)

    def test_wechat_fans_only_comments_are_valid_when_comments_are_enabled(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["wechat"]["comments"] = {
            "enabled": True,
            "fans_only": True,
        }

        result = validate_record(record, strict=True)

        self.assertTrue(result["ok"])
        self.assertTrue(result["publication_ready"])

    def test_wechat_topics_are_optional_and_platform_bounded(self) -> None:
        cases = (
            (["AI安全", "Anthropic"], None),
            (["#AI安全"], "wechat.topic_format"),
            (["A"], "wechat.topic_length"),
            (["话题一", "话题二", "话题三", "话题四"], "schema.list_too_long"),
            (["AI安全", "AI安全"], "schema.duplicate"),
        )
        for topics, expected_code in cases:
            with self.subTest(topics=topics):
                record = deepcopy(load_json(ASSETS / "signal.example.json"))
                record["wechat"]["topics"] = topics
                result = validate_record(record)
                codes = {issue["code"] for issue in result["issues"]}
                if expected_code is None:
                    self.assertTrue(result["ok"])
                else:
                    self.assertFalse(result["ok"])
                    self.assertIn(expected_code, codes)

    def test_profile_requires_its_length_sources_timeline_and_inline_media(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["meta"]["format"] = "profile"

        result = validate_record(record)
        codes = {issue["code"] for issue in result["issues"]}

        self.assertIn("format.body_length", codes)
        self.assertIn("source.count", codes)
        self.assertIn("profile.timeline_required", codes)
        self.assertIn("media.inline_count", codes)

    def test_require_media_resolves_relative_paths_from_json_directory(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["media"][1]["path"] = "images/chatgpt.svg"
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            image_dir = base / "images"
            image_dir.mkdir()
            (image_dir / "chatgpt.svg").write_text("<svg/>", encoding="utf-8")

            present = validate_record(record, strict=True, require_media=True, media_base=base)
            self.assertTrue(present["ok"])

            record["media"][1]["path"] = "images/missing.svg"
            missing = validate_record(record, require_media=True, media_base=base)
            self.assertIn("media.file_missing", {issue["code"] for issue in missing["issues"]})

    def test_only_owner_approval_or_later_is_publication_ready(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["publication"]["state"] = "editor_reviewed"

        result = validate_record(record, strict=True)

        self.assertTrue(result["ok"])
        self.assertTrue(result["renderable"])
        self.assertFalse(result["publication_ready"])

    def test_ai_generated_media_is_limited_and_never_a_screenshot(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["media"][1]["generated"] = True
        record["media"][1]["kind"] = "screenshot"
        record["media"][2]["generated"] = True

        result = validate_record(record)
        codes = {issue["code"] for issue in result["issues"]}

        self.assertIn("media.ai_screenshot_forbidden", codes)
        self.assertIn("media.ai_inline_limit", codes)

    def test_public_caption_flag_is_boolean_and_never_allowed_on_cover(self) -> None:
        invalid_type = deepcopy(load_json(ASSETS / "signal.example.json"))
        invalid_type["media"][1]["show_caption"] = "yes"
        type_codes = {issue["code"] for issue in validate_record(invalid_type)["issues"]}
        self.assertIn("schema.type", type_codes)

        cover_caption = deepcopy(load_json(ASSETS / "signal.example.json"))
        cover_caption["media"][0]["show_caption"] = True
        cover_codes = {issue["code"] for issue in validate_record(cover_caption)["issues"]}
        self.assertIn("media.cover_caption_forbidden", cover_codes)

    def test_media_placements_must_be_complete_unique_and_in_range(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        section = record["sections"][0]
        section["media_placements"] = [
            {"media_id": "M2", "after_paragraph": 99},
            {"media_id": "M2", "after_paragraph": 1},
        ]
        codes = {issue["code"] for issue in validate_record(record)["issues"]}
        self.assertIn("section.media_placement_position", codes)
        self.assertIn("section.media_placement_duplicate", codes)

        unlisted = deepcopy(load_json(ASSETS / "signal.example.json"))
        unlisted["sections"][0]["media_placements"] = [
            {"media_id": "M404", "after_paragraph": 1}
        ]
        unlisted_codes = {issue["code"] for issue in validate_record(unlisted)["issues"]}
        self.assertIn("section.media_placement_unlisted", unlisted_codes)
        self.assertIn("section.media_placement_incomplete", unlisted_codes)

    def test_first_party_test_fact_uses_test_run_without_inventing_a_url(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["test_runs"] = [test_run_fixture()]
        tested_claim = record["claims"][0]
        tested_claim["source_ids"] = []
        tested_claim["test_run_ids"] = ["T1"]

        result = validate_record(record, strict=True)

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["test_runs"], 1)

    def test_test_run_links_and_artifact_paths_fail_closed(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        invalid_test_run = test_run_fixture()
        invalid_test_run["artifact_paths"] = ["../outside.log"]
        record["test_runs"] = [invalid_test_run]
        record["claims"][0]["test_run_ids"] = ["T404"]

        result = validate_record(record)
        codes = {issue["code"] for issue in result["issues"]}

        self.assertIn("test.artifact_path_invalid", codes)
        self.assertIn("claim.test_run_missing", codes)
        self.assertFalse(result["gates"]["sources"])

    def test_quotes_still_require_a_public_source(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["test_runs"] = [test_run_fixture()]
        quoted_claim = record["claims"][0]
        quoted_claim["kind"] = "quote"
        quoted_claim["source_ids"] = []
        quoted_claim["test_run_ids"] = ["T1"]

        codes = {issue["code"] for issue in validate_record(record)["issues"]}

        self.assertIn("claim.source_required", codes)

    def test_undated_living_source_uses_null_without_inventing_a_date(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        record["sources"][1]["published_at"] = None

        result = validate_record(record, strict=True)

        self.assertTrue(result["ok"])
        self.assertNotIn("发布日期未标注", render_html(record))
        self.assertNotIn("发布日期未标注", render_markdown(record))

    def test_validator_cli_always_returns_json(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_signal.py"), str(FIXTURES / "signal.invalid.json")],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertFalse(result["ok"])
        self.assertEqual(result["file"], str(FIXTURES / "signal.invalid.json"))


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = load_json(ASSETS / "signal.example.json")

    def test_html_is_inline_only_and_contains_editorial_structure(self) -> None:
        record = deepcopy(self.record)
        record["media"][1]["show_caption"] = True
        output = render_html(record)

        self.assertTrue(output.startswith("<!doctype html>\n"))
        self.assertIn('<html lang="zh-CN">', output)
        self.assertIn("<head>", output)
        self.assertIn('<meta charset="UTF-8">', output[:512])
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', output)
        self.assertIn("</head>\n", output)
        self.assertIn('<body style="', output)
        self.assertIn('<section id="frontier-signals-body" style="', output)
        self.assertTrue(output.endswith("</body>\n</html>\n"))
        self.assertIn('style="', output)
        self.assertNotIn("<style", output.lower())
        self.assertNotIn("class=", output.lower())
        self.assertNotIn("<script", output.lower())
        self.assertNotIn("<h1", output.lower())
        self.assertIn("#155EEF", output)
        self.assertIn(
            '<h2 style="margin:0 0 16px;padding:0 0 0 12px;border-left:3px solid #155EEF;',
            output,
        )
        self.assertNotIn("30 秒速读", output)
        self.assertNotIn("<strong style=\"color:#101114;font-weight:650;\">判断边界</strong>", output)
        self.assertNotIn("本节依据", output)
        self.assertNotIn("<figcaption", output.lower())
        self.assertNotIn("图源", output)
        self.assertIn("GPT-4o 的文本和图像能力首先进入 ChatGPT", output)
        self.assertNotIn("微软在发布同日宣布 GPT-4o 进入 Azure OpenAI Service 预览", output)
        self.assertNotIn("Frontier Signals 编辑部", output)
        self.assertNotIn("更新于", output)
        self.assertNotIn("延伸阅读", output)
        self.assertNotIn('id="source-S1"', output)
        self.assertIn(
            '<strong style="color:#101114;font-weight:700;">统一模型减少接口间的信息损失</strong>',
            output,
        )

    def test_markdown_contains_signal_without_default_sources_or_fixed_discussion_block(self) -> None:
        record = deepcopy(self.record)
        record["media"][1]["show_caption"] = True
        output = render_markdown(record)

        self.assertIn("# OpenAI 发布 GPT-4o", output)
        self.assertIn("## The Signal", output)
        self.assertNotIn("## 延伸阅读", output)
        self.assertNotIn("留给你一个问题", output)
        self.assertNotIn("访问于", output)
        self.assertNotIn("判断边界", output)
        self.assertNotIn("本节依据", output)
        self.assertNotIn("图源", output)
        self.assertIn("*GPT-4o 的文本和图像能力首先进入 ChatGPT*", output)
        self.assertNotIn("*微软在发布同日宣布 GPT-4o 进入 Azure OpenAI Service 预览*", output)
        self.assertNotIn("Frontier Signals 编辑部", output)
        self.assertNotIn("更新于", output)
        self.assertIn("**统一模型减少接口间的信息损失**", output)
        self.assertIn("## 发生了什么", output)

    def test_bold_span_escapes_html_and_markdown_content(self) -> None:
        record = deepcopy(self.record)
        paragraph = "这是一个包含 <标签> 与 & 符号的完整测试段落，用于确认局部加粗不会注入页面。"
        record["sections"][1]["paragraphs"][2] = paragraph
        record["sections"][1]["bold_spans"] = [
            {"paragraph": 3, "text": "<标签> 与 & 符号"}
        ]

        html = render_html(record)
        markdown = render_markdown(record)

        self.assertIn(
            '<strong style="color:#101114;font-weight:700;">&lt;标签&gt; 与 &amp; 符号</strong>',
            html,
        )
        self.assertNotIn("<标签>", html)
        self.assertIn("**\\<标签\\> 与 & 符号**", markdown)

    def test_media_placements_interleave_images_with_paragraphs(self) -> None:
        html = render_html(self.record)
        markdown = render_markdown(self.record)
        first_section = self.record["sections"][0]
        before = first_section["paragraphs"][2]
        after = first_section["paragraphs"][3]
        image_path = self.record["media"][1]["path"]

        self.assertLess(html.index(before), html.index(image_path))
        self.assertLess(html.index(image_path), html.index(after))
        self.assertLess(markdown.index(before), markdown.index(image_path))
        self.assertLess(markdown.index(image_path), markdown.index(after))

    def test_legacy_sections_without_media_placements_keep_images_at_the_end(self) -> None:
        record = deepcopy(self.record)
        first_section = record["sections"][0]
        first_section.pop("media_placements")
        last_paragraph = first_section["paragraphs"][-1]
        image_path = record["media"][1]["path"]

        self.assertTrue(validate_record(record, strict=True)["ok"])
        html = render_html(record)
        markdown = render_markdown(record)
        self.assertLess(html.index(last_paragraph), html.index(image_path))
        self.assertLess(markdown.index(last_paragraph), markdown.index(image_path))

    def test_discussion_question_is_optional_and_never_auto_rendered(self) -> None:
        cases = (
            ("missing", None),
            ("null", None),
            ("legacy_string", "你愿意先把哪类可回滚任务交给这个 Agent？"),
        )
        for mode, value in cases:
            with self.subTest(mode=mode):
                record = deepcopy(self.record)
                if mode == "missing":
                    record.pop("discussion_question", None)
                else:
                    record["discussion_question"] = value

                result = validate_record(record, strict=True)
                self.assertTrue(result["ok"])
                self.assertNotIn("留给你一个问题", render_html(record))
                if value:
                    self.assertNotIn(value, render_markdown(record))

    def test_brief_30s_is_optional_and_only_renders_when_present(self) -> None:
        record = deepcopy(self.record)
        record.pop("brief_30s", None)

        self.assertTrue(validate_record(record, strict=True)["ok"])
        self.assertNotIn("30 秒速读", render_html(record))
        self.assertNotIn("## 30 秒速读", render_markdown(record))

        record["brief_30s"] = [
            "OpenAI 发布 GPT-4o，并先在 ChatGPT 开放文本和图像能力。",
            "语音延迟下降提供了方向，真实场景的可靠性仍要继续验证。",
        ]
        self.assertTrue(validate_record(record, strict=True)["ok"])
        self.assertIn("30 秒速读", render_html(record))
        self.assertIn("## 30 秒速读", render_markdown(record))

    def test_thesis_card_can_be_hidden_without_removing_internal_thesis(self) -> None:
        record = deepcopy(self.record)
        record["show_thesis"] = False

        self.assertTrue(validate_record(record, strict=True)["ok"])
        self.assertNotIn("THE SIGNAL", render_html(record))
        self.assertNotIn("## The Signal", render_markdown(record))
        self.assertNotIn(record["thesis"]["core"], render_markdown(record))

        record["show_thesis"] = "false"
        result = validate_record(record)
        self.assertIn("schema.type", {issue["code"] for issue in result["issues"]})

    def test_section_heading_can_be_hidden_without_removing_content(self) -> None:
        record = deepcopy(self.record)
        section = record["sections"][1]
        section["show_heading"] = False

        self.assertTrue(validate_record(record, strict=True)["ok"])
        html = render_html(record)
        markdown = render_markdown(record)
        self.assertNotIn(f'>{section["heading"]}</h2>', html)
        self.assertNotIn(f'## {section["heading"]}', markdown)
        self.assertIn(section["paragraphs"][0], html)
        self.assertIn(section["paragraphs"][0], markdown)

        section["show_heading"] = "false"
        result = validate_record(record)
        self.assertIn("schema.type", {issue["code"] for issue in result["issues"]})

    def test_present_discussion_question_still_has_editorial_validation(self) -> None:
        cases = (
            (42, "schema.type"),
            ("这不是一个合格的讨论问题", "discussion.not_question"),
        )
        for value, expected_code in cases:
            with self.subTest(value=value):
                record = deepcopy(self.record)
                record["discussion_question"] = value
                result = validate_record(record)
                self.assertIn(expected_code, {issue["code"] for issue in result["issues"]})

    def test_reader_facing_sources_use_explicit_subset_and_order(self) -> None:
        record = deepcopy(self.record)
        for index in range(4, 7):
            record["sources"].append(
                {
                    "id": f"S{index}",
                    "kind": "secondary",
                    "title": f"补充来源 {index}",
                    "publisher": "示例出版方",
                    "url": f"https://example.com/source-{index}",
                    "published_at": "2024-05-13",
                    "accessed_at": "2024-08-09",
                }
            )
        record["public_source_ids"] = ["S6", "S1", "S4"]
        record["show_public_sources"] = True
        record["sources"][5]["public_label"] = "来源六原文"

        html = render_html(record)
        markdown = render_markdown(record)

        self.assertLess(html.index('id="source-S6"'), html.index('id="source-S1"'))
        self.assertLess(html.index('id="source-S1"'), html.index('id="source-S4"'))
        self.assertNotIn('id="source-S2"', html)
        self.assertLess(markdown.index("source-6"), markdown.index("hello-gpt-4o"))
        self.assertLess(markdown.index("hello-gpt-4o"), markdown.index("source-4"))
        self.assertNotIn("gpt-4o-system-card", markdown)
        self.assertIn("来源六原文", html)
        self.assertIn("来源六原文", markdown)
        self.assertNotIn("示例出版方", html)
        self.assertNotIn("示例出版方", markdown)
        self.assertNotIn("· OpenAI", html)

    def test_reader_facing_sources_remain_hidden_without_explicit_opt_in(self) -> None:
        record = deepcopy(self.record)
        record.pop("public_source_ids")
        for index in range(4, 7):
            record["sources"].append(
                {
                    "id": f"S{index}",
                    "kind": "secondary",
                    "title": f"补充来源 {index}",
                    "publisher": "示例出版方",
                    "url": f"https://example.com/source-{index}",
                    "published_at": "2024-05-13",
                    "accessed_at": "2024-08-09",
                }
            )

        html = render_html(record)

        self.assertNotIn("延伸阅读", html)
        self.assertNotIn('id="source-S1"', html)
        self.assertNotIn('id="source-S6"', html)

    def test_renderer_cli_writes_both_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            html_path = output_dir / "article.html"
            markdown_path = output_dir / "article.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_wechat.py"),
                    str(ASSETS / "signal.example.json"),
                    "--html",
                    str(html_path),
                    "--markdown",
                    str(markdown_path),
                    "--require-ready",
                    "--strict",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertTrue(result["publication_ready"])
            html_bytes = html_path.read_bytes()
            self.assertIn(b'<meta charset="UTF-8">', html_bytes[:512])
            self.assertIn("发生了什么".encode("utf-8"), html_bytes)
            self.assertIn("FRONTIER SIGNALS", html_bytes.decode("utf-8"))
            self.assertIn("FRONTIER SIGNALS", markdown_path.read_text(encoding="utf-8"))
            for translated_label in ("信号快报", "深度报道", "人物侧写"):
                self.assertNotIn(translated_label, html_bytes.decode("utf-8"))
                self.assertNotIn(translated_label, markdown_path.read_text(encoding="utf-8"))
            self.assertIn(">FRONTIER SIGNALS</p>", html_bytes.decode("utf-8"))
            self.assertTrue(markdown_path.read_text(encoding="utf-8").startswith("FRONTIER SIGNALS\n\n"))

    def test_local_draft_renders_but_does_not_pass_require_ready(self) -> None:
        record = deepcopy(self.record)
        record["publication"]["state"] = "local_draft"
        record["publication"]["checks"] = {
            "facts": "pending",
            "media_rights": "pending",
            "editorial": "pending",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            input_path = output_dir / "signal.json"
            input_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            base_command = [
                sys.executable,
                str(SCRIPTS / "render_wechat.py"),
                str(input_path),
                "--html",
                str(output_dir / "article.html"),
                "--markdown",
                str(output_dir / "article.md"),
            ]

            rendered = subprocess.run(base_command, check=False, capture_output=True, text=True)
            blocked = subprocess.run(
                [*base_command, "--require-ready"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertFalse(json.loads(rendered.stdout)["publication_ready"])
            self.assertEqual(blocked.returncode, 1)

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow is optional")
    def test_cover_wrap_keeps_ascii_product_name_intact(self) -> None:
        image = Image.new("RGB", (WIDTH, HEIGHT), (250, 250, 247))
        draw = ImageDraw.Draw(image)
        title = "超 70 亿美元，Stripe 被曝收购 OpenRouter"

        lines = _wrap(draw, title, _font(48, bold=True), 610)

        self.assertEqual("".join(lines), title)
        self.assertTrue(any("OpenRouter" in line for line in lines))

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow is optional")
    def test_cover_is_exact_size_and_deterministic(self) -> None:
        first = render_cover(self.record)
        second = render_cover(self.record)

        self.assertEqual(first.size, (WIDTH, HEIGHT))
        self.assertEqual(first.mode, "RGB")
        self.assertEqual(first.tobytes(), second.tobytes())
        palette = {color for _, color in first.getcolors(maxcolors=WIDTH * HEIGHT)}
        self.assertIn((21, 94, 239), palette)
        self.assertIn((16, 17, 20), palette)
        self.assertIn((250, 250, 247), palette)
        self.assertNotIn((11, 59, 88), palette)
        self.assertEqual(
            first.crop((0, 0, 18, HEIGHT)).getcolors(maxcolors=1),
            [(18 * HEIGHT, (250, 250, 247))],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "cover.png"
            first.save(output_path, format="PNG", optimize=False)
            with Image.open(output_path) as saved:
                self.assertEqual(saved.size, (900, 383))

        changed_date = deepcopy(self.record)
        changed_date["meta"]["event_at"] = "2030-01-01T00:00:00+08:00"
        self.assertEqual(first.tobytes(), render_cover(changed_date).tobytes())

        changed_format = deepcopy(self.record)
        changed_format["meta"]["format"] = "report"
        self.assertEqual(first.tobytes(), render_cover(changed_format).tobytes())

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow is optional")
    def test_cover_accepts_transparent_subject_without_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            subject_path = output_dir / "subject.png"
            subject = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
            subject_draw = ImageDraw.Draw(subject)
            subject_draw.ellipse((4, 4, 124, 124), fill=(21, 94, 239, 255))
            subject.save(subject_path, format="PNG")

            first = render_cover(self.record, subject_path=subject_path)
            second = render_cover(self.record, subject_path=subject_path)

            self.assertEqual(first.size, (WIDTH, HEIGHT))
            self.assertEqual(first.mode, "RGB")
            self.assertEqual(first.tobytes(), second.tobytes())
            self.assertNotEqual(first.tobytes(), render_cover(self.record).tobytes())
            self.assertNotEqual(first.getpixel((764, 154)), (250, 250, 247))
            self.assertEqual(first.crop((68, 54, 105, 68)).getcolors(maxcolors=1), [(518, (250, 250, 247))])
            self.assertEqual(
                first.crop((68, 313, 650, 365)).getcolors(maxcolors=1),
                [(30264, (250, 250, 247))],
            )
            footer_colors = {
                color
                for _, color in first.crop((680, 330, 833, 360)).getcolors(maxcolors=153 * 30)
            }
            self.assertIn((21, 94, 239), footer_colors)
            header_colors = {
                color
                for _, color in first.crop((68, 24, 290, 62)).getcolors(maxcolors=222 * 38)
            }
            self.assertIn((21, 94, 239), header_colors)
            self.assertEqual(
                first.crop((30, 20, 65, 72)).getcolors(maxcolors=1),
                [(1820, (250, 250, 247))],
            )

            changed_date = deepcopy(self.record)
            changed_date["meta"]["event_at"] = "2030-01-01T00:00:00+08:00"
            self.assertEqual(first.tobytes(), render_cover(changed_date, subject_path=subject_path).tobytes())

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow is optional")
    def test_cover_accepts_text_free_concept_background(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            background_path = output_dir / "concept.png"
            background = Image.new("RGB", (1922, 818), (245, 244, 240))
            background_draw = ImageDraw.Draw(background)
            background_draw.ellipse((1100, 180, 1760, 760), fill=(21, 94, 239))
            background.save(background_path, format="PNG")

            first = render_cover(self.record, background_path=background_path)
            second = render_cover(self.record, background_path=background_path)

            self.assertEqual(first.size, (WIDTH, HEIGHT))
            self.assertEqual(first.mode, "RGB")
            self.assertEqual(first.tobytes(), second.tobytes())
            self.assertNotEqual(first.tobytes(), render_cover(self.record).tobytes())
            self.assertEqual(first.getpixel((120, 260)), (250, 250, 247))
            self.assertNotEqual(first.getpixel((760, 180)), (250, 250, 247))

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow is optional")
    def test_cover_cli_rejects_unsafe_or_invalid_background(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            input_path = output_dir / "signal.json"
            input_path.write_text(json.dumps(self.record, ensure_ascii=False), encoding="utf-8")
            background_path = output_dir / "concept.png"
            Image.new("RGB", (900, 383), (250, 250, 247)).save(background_path, format="PNG")
            base_command = [
                sys.executable,
                str(SCRIPTS / "render_cover.py"),
                str(input_path),
                "--background",
                str(background_path),
            ]

            original_input = input_path.read_bytes()
            input_alias = subprocess.run(
                [*base_command, "--output", f"{output_dir}/./signal.json"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(input_alias.returncode, 1)
            self.assertEqual(json.loads(input_alias.stderr)["error"], "output_must_not_overwrite_input")
            self.assertEqual(input_path.read_bytes(), original_input)

            overwrite = subprocess.run(
                [*base_command, "--output", str(background_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(overwrite.returncode, 1)
            self.assertEqual(json.loads(overwrite.stderr)["error"], "output_must_not_overwrite_background")

            subject_path = output_dir / "subject.png"
            Image.new("RGBA", (128, 128), (21, 94, 239, 255)).save(subject_path, format="PNG")
            both = subprocess.run(
                [*base_command, "--subject", str(subject_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(both.returncode, 1)
            self.assertEqual(
                json.loads(both.stderr)["error"],
                "background_and_subject_mutually_exclusive",
            )

            missing_subject = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_cover.py"),
                    str(input_path),
                    "--subject",
                    str(output_dir / "missing.png"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(missing_subject.returncode, 1)
            self.assertEqual(json.loads(missing_subject.stderr)["error"], "subject_not_found")

            subject_output = output_dir / "subject-cover.png"
            rendered_subject = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_cover.py"),
                    str(input_path),
                    "--subject",
                    str(subject_path),
                    "--output",
                    str(subject_output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(rendered_subject.returncode, 0, rendered_subject.stderr)
            self.assertEqual(json.loads(rendered_subject.stdout)["subject"], str(subject_path))
            with Image.open(subject_output) as rendered:
                self.assertEqual(rendered.size, (900, 383))

            overwrite_subject = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_cover.py"),
                    str(input_path),
                    "--subject",
                    str(subject_path),
                    "--output",
                    str(subject_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(overwrite_subject.returncode, 1)
            self.assertEqual(
                json.loads(overwrite_subject.stderr)["error"],
                "output_must_not_overwrite_subject",
            )

            corrupt_path = output_dir / "corrupt.png"
            corrupt_path.write_text("not an image", encoding="utf-8")
            invalid = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_cover.py"),
                    str(input_path),
                    "--background",
                    str(corrupt_path),
                    "--output",
                    str(output_dir / "cover.png"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(invalid.returncode, 1)
            self.assertEqual(json.loads(invalid.stderr)["error"], "background_read_failed")

            invalid_subject = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_cover.py"),
                    str(input_path),
                    "--subject",
                    str(corrupt_path),
                    "--output",
                    str(output_dir / "subject-cover-invalid.png"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(invalid_subject.returncode, 1)
            self.assertEqual(json.loads(invalid_subject.stderr)["error"], "subject_read_failed")


if __name__ == "__main__":
    unittest.main()
