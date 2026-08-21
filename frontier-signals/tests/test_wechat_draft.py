from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import binascii
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ASSETS = ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

import push_wechat_draft as draft  # noqa: E402
from render_wechat import render_html  # noqa: E402


APP_ID = "wx-frontier-signals-test"
APP_SECRET = "never-print-this-secret"
ACCESS_TOKEN = "never-print-this-access-token"
ACCOUNT_NAME = "Frontier World 测试号"
ACCOUNT_PRINCIPAL = "Frontier World 测试主体"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _png_chunk(name: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(name + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + name + payload + struct.pack(">I", checksum)


def _png_bytes(width: int, height: int) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scanline = b"\x00" + (b"\x00" * width * 4)
    pixels = zlib.compress(scanline * height, level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", pixels)
        + _png_chunk(b"IEND", b"")
    )


class ArticlePackage:
    """Build a strict-valid, entirely local article package for adapter tests."""

    def __init__(self, root: Path, name: str = "article") -> None:
        self.path = root / name
        self.path.mkdir(parents=True)
        image_dir = self.path / "images"
        image_dir.mkdir()

        self.signal = deepcopy(_load_json(ASSETS / "signal.example.json"))
        media_paths = (
            "images/cover-body.png",
            "images/inline-one.png",
            "images/inline-two.png",
        )
        for media, media_path in zip(self.signal["media"], media_paths, strict=True):
            media["path"] = media_path
        (self.path / media_paths[0]).write_bytes(_png_bytes(900, 383))
        (self.path / media_paths[1]).write_bytes(_png_bytes(24, 24))
        (self.path / media_paths[2]).write_bytes(_png_bytes(32, 20))
        (self.path / "wechat-cover.png").write_bytes(_png_bytes(900, 383))

        self.signal["wechat"] = {
            "author": "Frontier World",
            "digest": "GPT-4o 把文本、图像和语音放进同一个模型，交互方式随之改变。",
            "content_source_url": "",
            "topics": ["OpenAI", "多模态"],
            "comments": {"enabled": True, "fans_only": False},
        }
        self.release = {
            "article_id": "2024-05-13/gpt-4o-native-multimodal",
            "content_hash": None,
            "package_hash": None,
            "target_account": {
                "name": ACCOUNT_NAME,
                "principal": ACCOUNT_PRINCIPAL,
                "app_id_fingerprint": draft._app_id_fingerprint(APP_ID),
            },
            "wechat": {
                "status": "owner_approved",
                "draft_id": None,
                "publish_id": None,
                "published_url": None,
                "saved_at": None,
                "published_at": None,
                "sent_at": None,
            },
            "approvals": {
                "editor_reviewed_at": "2026-08-14T09:00:00+08:00",
                "owner_approved_at": "2026-08-14T09:10:00+08:00",
                "freshness_checked_at": "2026-08-14T09:05:00+08:00",
                "approved_hash": None,
                "approved_package_hash": None,
            },
            "last_error": None,
        }
        self.write_signal(update_approval=True)

    @property
    def signal_path(self) -> Path:
        return self.path / "signal.json"

    @property
    def release_path(self) -> Path:
        return self.path / "release.json"

    @property
    def receipt_path(self) -> Path:
        return self.path / "wechat-draft-receipt.json"

    def write_signal(self, *, update_approval: bool) -> str:
        _write_json(self.signal_path, self.signal)
        (self.path / "wechat.html").write_text(render_html(self.signal), encoding="utf-8")
        content_hash = draft._signal_hash(self.signal_path)
        content = draft._extract_body((self.path / "wechat.html").read_text(encoding="utf-8"))
        local_images = {
            item["path"]: self.path / item["path"] for item in self.signal["media"]
        }
        package_hash = draft._package_hash(
            signal_hash=content_hash,
            content=content,
            local_images=local_images,
            cover_path=self.path / "wechat-cover.png",
        )
        if update_approval:
            self.release["content_hash"] = content_hash
            self.release["package_hash"] = package_hash
            self.release["approvals"]["approved_hash"] = content_hash
            self.release["approvals"]["approved_package_hash"] = package_hash
        _write_json(self.release_path, self.release)
        return content_hash

    def write_release(self) -> None:
        _write_json(self.release_path, self.release)

    def preflight(self) -> dict:
        return draft.build_preflight(self.path)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.last_article: dict | None = None
        self.add_error: Exception | None = None
        self.get_error: Exception | None = None
        self.remote_response: dict | None = None
        self.batch_response: dict = {"item": []}
        self.draft_id = "draft-media-id-1"

    def stable_token(self) -> str:
        self.calls.append(("stable_token",))
        return ACCESS_TOKEN

    def upload_content_image(self, path: Path, access_token: str) -> str:
        self.calls.append(("upload_content_image", path.name, access_token))
        return f"https://mmbiz.qpic.cn/test/{path.name}"

    def upload_cover(self, path: Path, access_token: str) -> str:
        self.calls.append(("upload_cover", path.name, access_token))
        return "cover-media-id-1"

    def add_draft(self, article: dict, access_token: str) -> str:
        self.calls.append(("add_draft", access_token))
        self.last_article = deepcopy(article)
        if self.add_error is not None:
            raise self.add_error
        return self.draft_id

    def get_draft(self, media_id: str, access_token: str) -> dict:
        self.calls.append(("get_draft", media_id, access_token))
        if self.get_error is not None:
            raise self.get_error
        if self.remote_response is not None:
            return deepcopy(self.remote_response)
        if self.last_article is None:
            raise AssertionError("test fake needs remote_response when no draft was added")
        return {"news_item": [deepcopy(self.last_article)]}

    def batchget_drafts(self, access_token: str) -> dict:
        self.calls.append(("batchget_drafts", access_token))
        return deepcopy(self.batch_response)


def _call_names(client: FakeClient) -> list[str]:
    return [call[0] for call in client.calls]


def _remote_article(
    plan: dict,
    urls: list[str],
    cover_media_id: str = "cover-media-id-1",
    *,
    content: str | None = None,
) -> dict:
    images = "".join(f'<img src="{url}" />' for url in urls)
    return {
        "article_type": "news",
        "title": plan["title"],
        "author": plan["author"],
        "digest": plan["digest"],
        "content": content or f'<section id="frontier-signals-body">{images}</section>',
        "content_source_url": plan["content_source_url"],
        "thumb_media_id": cover_media_id,
        "need_open_comment": int(plan["comments"]["enabled"]),
        "only_fans_can_comment": int(plan["comments"]["fans_only"]),
    }


def _push(package: ArticlePackage, client: FakeClient) -> dict:
    preflight = package.preflight()
    if not preflight["ok"]:
        raise AssertionError(f"fixture preflight failed: {preflight['blockers']}")
    return draft.push_draft(
        preflight,
        confirmed_hash=preflight["plan"]["content_hash"],
        confirmed_package_hash=preflight["plan"]["package_hash"],
        confirmed_account=preflight["plan"]["target_account"]["name"],
        client=client,
    )


class WeChatDraftSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def make_package(self, name: str = "article") -> ArticlePackage:
        package = ArticlePackage(self.root, name)
        preflight = package.preflight()
        self.assertTrue(preflight["ok"], preflight["blockers"])
        return package

    def test_default_dry_run_performs_zero_network_calls_and_zero_writes(self) -> None:
        package = self.make_package()
        before = {path.relative_to(package.path): path.read_bytes() for path in package.path.rglob("*") if path.is_file()}
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch.object(draft, "WeChatClient", side_effect=AssertionError("network client created")),
            patch.object(draft, "_atomic_write_json", side_effect=AssertionError("dry-run wrote a file")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = draft.main([str(package.path)])

        after = {path.relative_to(package.path): path.read_bytes() for path in package.path.rglob("*") if path.is_file()}
        self.assertEqual(0, result)
        self.assertEqual(before, after)
        self.assertFalse(package.receipt_path.exists())
        self.assertEqual("", stderr.getvalue())
        self.assertTrue(json.loads(stdout.getvalue())["dry_run"])

    def test_preflight_surfaces_native_topics_as_manual_editor_work(self) -> None:
        package = self.make_package()
        preflight = package.preflight()

        self.assertEqual(["OpenAI", "多模态"], preflight["plan"]["topics"])
        self.assertFalse(preflight["plan"]["native_topics_supported_by_api"])
        self.assertTrue(
            any("not supported by the official draft/add API" in item for item in preflight["warnings"])
        )

    def test_missing_confirm_never_turns_approved_arguments_into_a_remote_write(self) -> None:
        package = self.make_package()
        content_hash = draft._signal_hash(package.signal_path)
        stdout = io.StringIO()

        with (
            patch.object(draft, "WeChatClient", side_effect=AssertionError("network client created")),
            patch.object(draft, "_atomic_write_json", side_effect=AssertionError("dry-run wrote a file")),
            redirect_stdout(stdout),
        ):
            result = draft.main(
                [
                    str(package.path),
                    "--approved-hash",
                    content_hash,
                    "--approved-package-hash",
                    package.preflight()["plan"]["package_hash"],
                    "--target-account",
                    ACCOUNT_NAME,
                ]
            )

        self.assertEqual(0, result)
        self.assertTrue(json.loads(stdout.getvalue())["dry_run"])

    def test_missing_approval_hash_or_account_fails_closed_before_network(self) -> None:
        mutations = {
            "owner approval": lambda package: package.release["approvals"].update(owner_approved_at=None),
            "approved hash": lambda package: package.release["approvals"].update(approved_hash="sha256:wrong"),
            "content hash": lambda package: package.release.update(content_hash="sha256:wrong"),
            "account": lambda package: package.release.update(target_account=None),
        }
        for index, (label, mutate) in enumerate(mutations.items()):
            with self.subTest(label=label):
                package = self.make_package(f"missing-{index}")
                mutate(package)
                package.write_release()
                preflight = package.preflight()
                self.assertFalse(preflight["ok"])

                client = FakeClient()
                with self.assertRaises(draft.DraftAdapterError):
                    draft.push_draft(
                        preflight,
                        confirmed_hash=draft._signal_hash(package.signal_path),
                        confirmed_package_hash="sha256:not-used",
                        confirmed_account=ACCOUNT_NAME,
                        client=client,
                    )
                self.assertEqual([], client.calls)

    def test_confirm_requires_both_exact_hash_and_account(self) -> None:
        package = self.make_package()
        for arguments in (
            [str(package.path), "--confirm"],
            [str(package.path), "--confirm", "--approved-hash", draft._signal_hash(package.signal_path)],
            [
                str(package.path),
                "--confirm",
                "--approved-hash",
                draft._signal_hash(package.signal_path),
                "--approved-package-hash",
                package.preflight()["plan"]["package_hash"],
            ],
            [str(package.path), "--confirm", "--target-account", ACCOUNT_NAME],
        ):
            with self.subTest(arguments=arguments):
                stderr = io.StringIO()
                with (
                    patch.object(draft, "WeChatClient", side_effect=AssertionError("network client created")),
                    redirect_stderr(stderr),
                ):
                    result = draft.main(arguments)
                self.assertEqual(1, result)
                self.assertIn("--confirm requires", stderr.getvalue())

        preflight = package.preflight()
        client = FakeClient()
        with self.assertRaisesRegex(draft.DraftAdapterError, "approved-hash"):
            draft.push_draft(
                preflight,
                confirmed_hash="sha256:wrong",
                confirmed_package_hash=preflight["plan"]["package_hash"],
                confirmed_account=ACCOUNT_NAME,
                client=client,
            )
        with self.assertRaisesRegex(draft.DraftAdapterError, "approved-package-hash"):
            draft.push_draft(
                preflight,
                confirmed_hash=preflight["plan"]["content_hash"],
                confirmed_package_hash="sha256:wrong",
                confirmed_account=ACCOUNT_NAME,
                client=client,
            )
        with self.assertRaisesRegex(draft.DraftAdapterError, "target-account"):
            draft.push_draft(
                preflight,
                confirmed_hash=preflight["plan"]["content_hash"],
                confirmed_package_hash=preflight["plan"]["package_hash"],
                confirmed_account="Wrong account",
                client=client,
            )
        self.assertEqual([], client.calls)

    def test_confirm_with_blocked_preflight_stops_before_credentials_or_network(self) -> None:
        package = self.make_package()
        package.release["approvals"]["owner_approved_at"] = None
        package.write_release()
        stderr = io.StringIO()

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(draft, "WeChatClient", side_effect=AssertionError("network client created")),
            redirect_stderr(stderr),
        ):
            result = draft.main(
                [
                    str(package.path),
                    "--confirm",
                    "--approved-hash",
                    draft._signal_hash(package.signal_path),
                    "--approved-package-hash",
                    package.preflight()["plan"]["package_hash"],
                    "--target-account",
                    ACCOUNT_NAME,
                ]
            )

        self.assertEqual(1, result)
        self.assertIn("preflight has blocking issues", stderr.getvalue())
        self.assertNotIn("WECHAT_APP", stderr.getvalue())

    def test_account_binding_checks_name_principal_and_app_id_before_client_use(self) -> None:
        plan = self.make_package().preflight()["plan"]
        bad_values = (
            {"app_id": APP_ID, "configured_account": "Wrong", "configured_principal": ACCOUNT_PRINCIPAL},
            {"app_id": APP_ID, "configured_account": ACCOUNT_NAME, "configured_principal": "Wrong"},
            {"app_id": "wrong-app-id", "configured_account": ACCOUNT_NAME, "configured_principal": ACCOUNT_PRINCIPAL},
        )
        for values in bad_values:
            with self.subTest(values=values):
                with self.assertRaises(draft.DraftAdapterError):
                    draft._verify_account_binding(plan, **values)

    def test_wechat_text_field_limits_are_enforced_by_preflight(self) -> None:
        cases = (
            ("title", lambda package: package.signal["headlines"].update(primary="题" * 33), "title exceeds"),
            ("author", lambda package: package.signal["wechat"].update(author="作" * 17), "author exceeds"),
            ("digest", lambda package: package.signal["wechat"].update(digest="摘" * 121), "digest exceeds"),
            (
                "source URL",
                lambda package: package.signal["wechat"].update(content_source_url="https://example.com/" + "x" * 1010),
                "content_source_url exceeds",
            ),
        )
        for index, (label, mutate, expected) in enumerate(cases):
            with self.subTest(label=label):
                package = ArticlePackage(self.root, f"limit-{index}")
                mutate(package)
                if label == "title":
                    package.signal["headlines"]["candidates"][0] = package.signal["headlines"]["primary"]
                package.write_signal(update_approval=True)
                preflight = package.preflight()
                self.assertFalse(preflight["ok"])
                self.assertTrue(any(expected in blocker for blocker in preflight["blockers"]), preflight["blockers"])

    def test_image_type_size_signature_and_cover_dimensions_are_enforced_locally(self) -> None:
        small = self.root / "small.png"
        small.write_bytes(_png_bytes(10, 10))
        draft._validate_image_file(small)

        unsupported = self.root / "image.gif"
        unsupported.write_bytes(b"GIF89a")
        with self.assertRaisesRegex(draft.DraftAdapterError, "unsupported content image type"):
            draft._validate_image_file(unsupported)

        mismatched = self.root / "mismatched.png"
        mismatched.write_bytes(b"not-a-png")
        with self.assertRaisesRegex(draft.DraftAdapterError, "signature"):
            draft._validate_image_file(mismatched)

        at_limit = self.root / "at-limit.png"
        at_limit.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (draft.CONTENT_IMAGE_MAX_BYTES - 8))
        with self.assertRaisesRegex(draft.DraftAdapterError, "size limit"):
            draft._validate_image_file(at_limit)

        good_cover = self.root / "good-cover.png"
        good_cover.write_bytes(_png_bytes(900, 383))
        draft._validate_image_file(good_cover, cover=True)

        bad_cover = self.root / "bad-cover.png"
        bad_cover.write_bytes(_png_bytes(900, 384))
        with self.assertRaisesRegex(draft.DraftAdapterError, "exactly 900x383"):
            draft._validate_image_file(bad_cover, cover=True)

    def test_content_image_upload_upgrades_only_the_official_wechat_image_host(self) -> None:
        image = self.root / "upload.png"
        image.write_bytes(_png_bytes(10, 10))
        client = draft.WeChatClient(APP_ID, APP_SECRET)

        with patch.object(
            client,
            "_request_json",
            return_value={"url": "http://mmbiz.qpic.cn/test/upload.png"},
        ):
            uploaded = client.upload_content_image(image, ACCESS_TOKEN)
        self.assertEqual("https://mmbiz.qpic.cn/test/upload.png", uploaded)

        with patch.object(
            client,
            "_request_json",
            return_value={"url": "http://example.com/upload.png"},
        ):
            with self.assertRaisesRegex(draft.DraftAdapterError, "HTTPS URL"):
                client.upload_content_image(image, ACCESS_TOKEN)

    def test_draft_update_targets_an_existing_media_id(self) -> None:
        client = draft.WeChatClient(APP_ID, APP_SECRET)
        article = {"title": "Updated title", "content": "<p>Updated body</p>"}
        with patch.object(client, "_request_json", return_value={}) as request:
            client.update_draft("existing-draft-id", article, ACCESS_TOKEN)
        endpoint, label = request.call_args.args[:2]
        self.assertTrue(endpoint.startswith(draft.DRAFT_UPDATE_ENDPOINT))
        self.assertEqual("draft/update", label)
        self.assertEqual(
            {
                "media_id": "existing-draft-id",
                "index": 0,
                "articles": article,
            },
            request.call_args.kwargs["payload"],
        )

    def test_remote_verification_accepts_wechat_image_size_url_rewrite(self) -> None:
        for host in ("mmbiz.qpic.cn", "sz_mmbiz.qpic.cn"):
            with self.subTest(host=host):
                uploaded = f"https://{host}/mmbiz_png/example/0?from=appmsg"
                rewritten = f"https://{host}/mmbiz_png/rehosted-example/640?wx_fmt=png"
                expected = (
                    f'<section id="frontier-signals-body">'
                    f'<img src="{uploaded}" alt="Evidence image"></section>'
                )
                remote = {
                    "news_item": [{
                        "title": "Title",
                        "author": "Frontier World",
                        "digest": "Digest",
                        "thumb_media_id": "cover-id",
                        "need_open_comment": 1,
                        "only_fans_can_comment": 0,
                        "content_source_url": "https://example.com/article",
                        "content": (
                            f'<section id="frontier-signals-body">'
                            f'<img data-src="{rewritten}" alt="Evidence image"></section>'
                        ),
                    }]
                }
                verification = draft._verify_remote_draft(
                    remote,
                    title="Title",
                    author="Frontier World",
                    digest="Digest",
                    cover_media_id="cover-id",
                    comments_enabled=True,
                    comments_fans_only=False,
                    uploaded_urls=[uploaded],
                    expected_content=expected,
                    content_source_url="https://example.com/article",
                )
                self.assertEqual(1, verification["content_image_count"])

    def test_rehosted_image_verification_preserves_count_order_and_unique_alt(self) -> None:
        uploaded = [
            "https://mmbiz.qpic.cn/mmbiz_png/source-one/0?from=appmsg",
            "https://mmbiz.qpic.cn/mmbiz_png/source-two/0?from=appmsg",
        ]
        expected = (
            '<section id="frontier-signals-body">'
            f'<img src="{uploaded[0]}" alt="First evidence">'
            f'<img src="{uploaded[1]}" alt="Second evidence">'
            "</section>"
        )

        def remote_for(alts: list[str]) -> dict:
            images = "".join(
                f'<img data-src="https://mmbiz.qpic.cn/mmbiz_png/rehosted-{index}/640" alt="{alt}">'
                for index, alt in enumerate(alts)
            )
            return {
                "news_item": [{
                    "title": "Title",
                    "author": "Frontier World",
                    "digest": "Digest",
                    "thumb_media_id": "cover-id",
                    "need_open_comment": 1,
                    "only_fans_can_comment": 0,
                    "content_source_url": "https://example.com/article",
                    "content": f'<section id="frontier-signals-body">{images}</section>',
                }]
            }

        verification = draft._verify_remote_draft(
            remote_for(["First evidence", "Second evidence"]),
            title="Title",
            author="Frontier World",
            digest="Digest",
            cover_media_id="cover-id",
            comments_enabled=True,
            comments_fans_only=False,
            uploaded_urls=uploaded,
            expected_content=expected,
            content_source_url="https://example.com/article",
        )
        self.assertEqual(2, verification["content_image_count"])

        for label, alts in (
            ("reordered", ["Second evidence", "First evidence"]),
            ("duplicated", ["First evidence", "First evidence"]),
            ("missing", ["First evidence"]),
        ):
            with self.subTest(label=label):
                with self.assertRaises(draft.DraftAdapterError):
                    draft._verify_remote_draft(
                        remote_for(alts),
                        title="Title",
                        author="Frontier World",
                        digest="Digest",
                        cover_media_id="cover-id",
                        comments_enabled=True,
                        comments_fans_only=False,
                        uploaded_urls=uploaded,
                        expected_content=expected,
                        content_source_url="https://example.com/article",
                    )

    def test_html_and_media_changes_invalidate_the_approved_package(self) -> None:
        html_package = self.make_package("html-tamper")
        html_path = html_package.path / "wechat.html"
        html_path.write_text(
            html_path.read_text(encoding="utf-8").replace("发生了什么", "被改过的正文", 1),
            encoding="utf-8",
        )
        html_preflight = html_package.preflight()
        self.assertFalse(html_preflight["ok"])
        self.assertTrue(
            any("deterministic render" in blocker for blocker in html_preflight["blockers"])
        )

        image_package = self.make_package("image-tamper")
        image_path = image_package.path / "images/inline-one.png"
        image_path.write_bytes(_png_bytes(25, 24))
        image_preflight = image_package.preflight()
        self.assertFalse(image_preflight["ok"])
        self.assertTrue(
            any("package_hash" in blocker for blocker in image_preflight["blockers"])
        )

    def test_happy_path_uses_expected_call_order_and_only_mutates_release_state(self) -> None:
        package = self.make_package()
        signal_before = package.signal_path.read_bytes()
        release_before = package.release_path.read_bytes()
        client = FakeClient()

        result = _push(package, client)

        self.assertEqual(
            [
                "stable_token",
                "upload_content_image",
                "upload_content_image",
                "upload_content_image",
                "upload_cover",
                "add_draft",
                "get_draft",
            ],
            _call_names(client),
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["remote_write"])
        self.assertEqual(signal_before, package.signal_path.read_bytes())
        self.assertNotEqual(release_before, package.release_path.read_bytes())
        self.assertTrue(package.receipt_path.is_file())

        release = _load_json(package.release_path)
        self.assertEqual("remote_draft", release["wechat"]["status"])
        self.assertEqual(client.draft_id, release["wechat"]["draft_id"])
        self.assertEqual("verified", release["wechat"]["attempt"]["state"])
        self.assertNotIn("file://", client.last_article["content"])
        self.assertNotIn("images/", client.last_article["content"])
        self.assertEqual("cover-media-id-1", client.last_article["thumb_media_id"])
        self.assertNotIn("topics", client.last_article)
        receipt = _load_json(package.receipt_path)
        self.assertEqual(["OpenAI", "多模态"], receipt["topics"])
        self.assertFalse(receipt["native_topics_applied"])

    def test_repeated_execution_reuses_verified_draft_without_upload_or_add(self) -> None:
        package = self.make_package()
        first_client = FakeClient()
        first_result = _push(package, first_client)
        self.assertTrue(first_result["remote_write"])

        second_client = FakeClient()
        second_client.remote_response = {"news_item": [deepcopy(first_client.last_article)]}
        second_result = _push(package, second_client)

        self.assertEqual(["stable_token", "get_draft"], _call_names(second_client))
        self.assertFalse(second_result["remote_write"])
        self.assertTrue(second_result["reused_existing_draft"])
        self.assertEqual(first_result["draft_id"], second_result["draft_id"])

    def test_draft_add_timeout_is_recorded_as_unknown_and_is_never_replayed(self) -> None:
        package = self.make_package()
        first_client = FakeClient()
        first_client.add_error = TimeoutError("socket timed out")

        with self.assertRaisesRegex(draft.DraftAdapterError, "result is unknown"):
            _push(package, first_client)
        self.assertEqual(1, _call_names(first_client).count("add_draft"))
        self.assertNotIn("get_draft", _call_names(first_client))
        release = _load_json(package.release_path)
        self.assertEqual("remote_result_unknown", release["wechat"]["status"])
        self.assertEqual("unknown", release["last_error"]["outcome"])

        second_client = FakeClient()
        second_client.batch_response = {"item": []}
        with self.assertRaisesRegex(draft.DraftAdapterError, "found 0 candidates"):
            _push(package, second_client)
        self.assertEqual(["stable_token", "batchget_drafts"], _call_names(second_client))
        self.assertNotIn("add_draft", _call_names(second_client))

    def test_ambiguous_draft_add_error_is_unknown_and_is_never_replayed(self) -> None:
        package = self.make_package()
        client = FakeClient()
        client.add_error = draft.WeChatAPIError("draft/add", -1, "system error")

        with self.assertRaisesRegex(draft.DraftAdapterError, "result is unknown"):
            _push(package, client)

        release = _load_json(package.release_path)
        self.assertEqual("remote_result_unknown", release["wechat"]["status"])
        self.assertEqual("unknown", release["last_error"]["outcome"])
        self.assertFalse(release["last_error"]["retryable"])

    def test_get_failure_preserves_created_draft_id_and_blocks_duplicate_creation(self) -> None:
        package = self.make_package()
        client = FakeClient()
        client.get_error = TimeoutError("read timed out")

        with self.assertRaisesRegex(draft.DraftAdapterError, "was created but verification failed"):
            _push(package, client)

        release = _load_json(package.release_path)
        receipt = _load_json(package.receipt_path)
        self.assertEqual(client.draft_id, release["wechat"]["draft_id"])
        self.assertEqual("draft_created_unverified", release["wechat"]["status"])
        self.assertEqual("created_unverified", release["last_error"]["outcome"])
        self.assertEqual(client.draft_id, receipt["draft_id"])
        self.assertEqual("created_unverified", receipt["status"])
        self.assertEqual(1, _call_names(client).count("add_draft"))

    def test_remote_body_mismatch_preserves_draft_for_manual_review(self) -> None:
        package = self.make_package()
        preflight = package.preflight()
        urls = [
            f"https://mmbiz.qpic.cn/test/{Path(path).name}"
            for path in preflight["plan"]["content_images"].values()
        ]
        expected = draft._replace_image_sources(
            preflight["_content"],
            dict(zip(preflight["plan"]["content_images"], urls, strict=True)),
        )
        client = FakeClient()
        client.remote_response = {
            "news_item": [
                _remote_article(
                    preflight["plan"],
                    urls,
                    content=expected + "<p>unexpected remote text</p>",
                )
            ]
        }

        with self.assertRaisesRegex(draft.DraftAdapterError, "verification failed"):
            _push(package, client)

        release = _load_json(package.release_path)
        self.assertEqual(client.draft_id, release["wechat"]["draft_id"])
        self.assertEqual("draft_created_unverified", release["wechat"]["status"])

    def test_identical_content_images_are_uploaded_once_but_verified_at_each_position(self) -> None:
        package = self.make_package()
        first_inline = package.path / "images/inline-one.png"
        second_inline = package.path / "images/inline-two.png"
        second_inline.write_bytes(first_inline.read_bytes())
        package.write_signal(update_approval=True)
        client = FakeClient()

        result = _push(package, client)

        self.assertTrue(result["ok"])
        self.assertEqual(2, _call_names(client).count("upload_content_image"))
        self.assertEqual(3, result["verification"]["content_image_count"])

    def _make_unknown_package(self, name: str) -> tuple[ArticlePackage, dict, list[str], str]:
        package = self.make_package(name)
        preflight = package.preflight()
        sources = list(preflight["plan"]["content_images"])
        urls = [f"https://mmbiz.qpic.cn/reconcile/{index}.png" for index in range(len(sources))]
        package.release["wechat"].update(
            {
                "status": "remote_result_unknown",
                "uploads": {
                    f"sha256:image-{index}": {"source": source, "url": url}
                    for index, (source, url) in enumerate(zip(sources, urls, strict=True))
                },
                "cover": {"sha256": "sha256:cover", "media_id": "cover-media-id-1"},
                "attempt": {"id": "attempt-1", "state": "result_unknown"},
            }
        )
        package.write_release()
        reconciled_preflight = package.preflight()
        replacements = dict(zip(sources, urls, strict=True))
        expected_content = draft._replace_image_sources(
            reconciled_preflight["_content"],
            replacements,
        )
        return package, reconciled_preflight["plan"], urls, expected_content

    def test_batch_reconciliation_zero_one_and_multiple_candidates(self) -> None:
        for count in (0, 1, 2):
            with self.subTest(candidate_count=count):
                package, plan, urls, expected_content = self._make_unknown_package(f"batch-{count}")
                remote = _remote_article(plan, urls, content=expected_content)
                client = FakeClient()
                client.batch_response = {
                    "item": [
                        {
                            "media_id": f"candidate-{index}",
                            "content": {"news_item": [deepcopy(remote)]},
                        }
                        for index in range(count)
                    ]
                }
                client.remote_response = {"news_item": [deepcopy(remote)]}

                if count == 1:
                    result = _push(package, client)
                    self.assertTrue(result["reused_existing_draft"])
                    self.assertEqual("candidate-0", result["draft_id"])
                    self.assertEqual(
                        ["stable_token", "batchget_drafts", "get_draft"],
                        _call_names(client),
                    )
                    self.assertEqual("remote_draft", _load_json(package.release_path)["wechat"]["status"])
                else:
                    with self.assertRaisesRegex(
                        draft.DraftAdapterError,
                        rf"found {count} candidates",
                    ):
                        _push(package, client)
                    self.assertEqual(["stable_token", "batchget_drafts"], _call_names(client))
                self.assertNotIn("add_draft", _call_names(client))
                self.assertNotIn("upload_content_image", _call_names(client))

    def test_credentials_and_access_token_never_reach_output_or_persisted_files(self) -> None:
        package = self.make_package()
        client = FakeClient()
        client.add_error = TimeoutError("transport failed")
        stderr = io.StringIO()
        stdout = io.StringIO()
        environment = {
            "WECHAT_APP_ID": APP_ID,
            "WECHAT_APP_SECRET": APP_SECRET,
            "WECHAT_TARGET_ACCOUNT": ACCOUNT_NAME,
            "WECHAT_TARGET_PRINCIPAL": ACCOUNT_PRINCIPAL,
        }

        with (
            patch.dict(os.environ, environment, clear=True),
            patch.object(draft, "WeChatClient", return_value=client),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = draft.main(
                [
                    str(package.path),
                    "--confirm",
                    "--approved-hash",
                    draft._signal_hash(package.signal_path),
                    "--approved-package-hash",
                    package.preflight()["plan"]["package_hash"],
                    "--target-account",
                    ACCOUNT_NAME,
                ]
            )

        self.assertEqual(1, result)
        persisted = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in package.path.rglob("*")
            if path.is_file() and path.suffix in {".json", ".html", ".md"}
        )
        observable = stdout.getvalue() + stderr.getvalue() + persisted
        self.assertNotIn(APP_SECRET, observable)
        self.assertNotIn(ACCESS_TOKEN, observable)

    def test_api_error_detail_redacts_secret_and_access_token(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "errcode": 40001,
                        "errmsg": f"bad {APP_SECRET} and {ACCESS_TOKEN}",
                    }
                ).encode("utf-8")

        client = draft.WeChatClient(
            APP_ID,
            APP_SECRET,
            opener=lambda *_args, **_kwargs: Response(),
        )
        with self.assertRaises(draft.WeChatAPIError) as context:
            client._request_json(
                f"https://api.weixin.qq.com/test?access_token={ACCESS_TOKEN}",
                "test",
                payload={},
            )

        message = str(context.exception)
        self.assertNotIn(APP_SECRET, message)
        self.assertNotIn(ACCESS_TOKEN, message)
        self.assertIn("[REDACTED]", message)

    def test_source_contains_no_publish_or_mass_send_endpoints(self) -> None:
        source = Path(draft.__file__).read_text(encoding="utf-8").lower()
        forbidden_endpoint_fragments = (
            "/cgi-bin/freepublish",
            "/cgi-bin/publish",
            "/cgi-bin/message/mass",
            "/cgi-bin/mass/send",
            "freepublish/submit",
        )
        for fragment in forbidden_endpoint_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
