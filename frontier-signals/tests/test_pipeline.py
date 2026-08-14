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
    from render_cover import HEIGHT, WIDTH, render_cover

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
        self.assertIn("source.primary_count", codes)
        self.assertIn("claim.source_missing", codes)
        self.assertIn("format.body_length", codes)
        self.assertIn("media.inline_count", codes)
        self.assertIn("media.rights_pending", codes)
        self.assertIn("publication.check_not_passed", codes)
        self.assertFalse(result["gates"]["editorial"])
        self.assertFalse(result["gates"]["sources"])
        self.assertFalse(result["gates"]["media"])
        self.assertFalse(result["gates"]["status"])

    def test_hype_blacklist_rejects_fixed_amplifiers(self) -> None:
        record = deepcopy(load_json(ASSETS / "signal.example.json"))
        hype_title = "刚刚，OpenAI 彻底颠覆所有 AI 产品"
        record["headlines"]["primary"] = hype_title
        record["headlines"]["candidates"][0] = hype_title

        result = validate_record(record)
        issues = [issue for issue in result["issues"] if issue["code"] == "headline.hype_blacklist"]

        self.assertFalse(result["ok"])
        self.assertEqual({"刚刚", "彻底颠覆"}, {issue["message"].split("“")[1].split("”")[0] for issue in issues})

    def test_public_source_selection_is_small_unique_and_resolvable(self) -> None:
        cases = (
            (["S1", "S2"], "source.public_count"),
            (["S1", "S1", "S2"], "source.public_duplicate"),
            (["S1", "S2", "S404"], "source.public_missing"),
            ("S1", "schema.type"),
        )
        for value, expected_code in cases:
            with self.subTest(value=value):
                record = deepcopy(load_json(ASSETS / "signal.example.json"))
                record["public_source_ids"] = value
                result = validate_record(record)
                codes = {issue["code"] for issue in result["issues"]}
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
        output = render_html(self.record)

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
        self.assertNotIn("30 秒速读", output)
        self.assertNotIn("<strong style=\"color:#101114;font-weight:650;\">判断边界</strong>", output)
        self.assertNotIn("本节依据", output)
        self.assertNotIn("<figcaption", output.lower())
        self.assertNotIn("图源", output)
        self.assertNotIn("Frontier Signals 编辑部", output)
        self.assertNotIn("更新于", output)
        self.assertIn('id="source-S1"', output)

    def test_markdown_contains_signal_and_sources_without_fixed_discussion_block(self) -> None:
        output = render_markdown(self.record)

        self.assertIn("# OpenAI 发布 GPT-4o", output)
        self.assertIn("## The Signal", output)
        self.assertIn("## 延伸阅读", output)
        self.assertNotIn("留给你一个问题", output)
        self.assertNotIn("访问于", output)
        self.assertNotIn("判断边界", output)
        self.assertNotIn("本节依据", output)
        self.assertNotIn("图源", output)
        self.assertNotIn("Frontier Signals 编辑部", output)
        self.assertNotIn("更新于", output)

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

        html = render_html(record)
        markdown = render_markdown(record)

        self.assertLess(html.index('id="source-S6"'), html.index('id="source-S1"'))
        self.assertLess(html.index('id="source-S1"'), html.index('id="source-S4"'))
        self.assertNotIn('id="source-S2"', html)
        self.assertLess(markdown.index("source-6"), markdown.index("hello-gpt-4o"))
        self.assertLess(markdown.index("hello-gpt-4o"), markdown.index("source-4"))
        self.assertNotIn("gpt-4o-system-card", markdown)

    def test_reader_facing_sources_fallback_caps_old_records_at_five(self) -> None:
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

        self.assertIn('id="source-S5"', html)
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
