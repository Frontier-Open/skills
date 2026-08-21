from __future__ import annotations

import hashlib
import fcntl
import io
import json
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import push_markdown_draft as markdown_draft  # noqa: E402
import push_wechat_draft as draft  # noqa: E402
import reconcile_markdown_draft as markdown_reconcile  # noqa: E402
import update_markdown_draft as markdown_update  # noqa: E402


def _png(width: int, height: int) -> bytes:
    data = bytearray(24)
    data[:8] = b"\x89PNG\r\n\x1a\n"
    data[16:24] = struct.pack(">II", width, height)
    return bytes(data)


class MarkdownPackage:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)
        self.build = self.path / ".frontier-build"
        (self.path / "images").mkdir()
        self.build.mkdir()
        self.article_path = self.path / "article.md"
        self.source_notes_path = self.path / "source-notes.md"
        self.release_path = self.path / "release.json"
        self.manifest_path = self.build / "channel-manifest.json"
        self.html_path = self.build / "wechat.html"
        self.cover_path = self.path / "wechat-cover.png"
        self.image_path = self.path / "images" / "chart.png"
        self.article_path.write_text("# Markdown source\n\n## Section\n\nBody.\n", encoding="utf-8")
        self.source_notes_path.write_text("# Source notes\n\nVerified evidence.\n", encoding="utf-8")
        self.cover_path.write_bytes(_png(900, 383))
        self.image_path.write_bytes(_png(1000, 600))
        self.html_path.write_text(
            "<!doctype html><html><body><section id=\"frontier-signals-body\">"
            "<p>Body.</p><img src=\"images/chart.png\" alt=\"chart\">"
            "</section></body></html>\n",
            encoding="utf-8",
        )
        source_hash = "sha256:" + hashlib.sha256(self.article_path.read_bytes()).hexdigest()
        content = draft._extract_body(self.html_path.read_text(encoding="utf-8"))
        package_hash = draft._package_hash(
            signal_hash=source_hash,
            content=content,
            local_images={
                "images/chart.png": self.image_path,
            },
            cover_path=self.cover_path,
        )
        manifest = {
            "schema_version": 1,
            "renderer": "frontier-signals-markdown-v2",
            "article_id": "2026-08-18/markdown-source",
            "source": "article.md",
            "source_hash": source_hash,
            "title": "Markdown source",
            "description": "Description",
            "author": "Frontier World",
            "digest": "Description",
            "content_source_url": "https://signals.frontierworld.ai/2026/08/18/markdown-source/",
            "topics": ["AI"],
            "comments": {"enabled": True, "fans_only": False},
            "cover": "wechat-cover.png",
            "hero": "wechat-cover.png",
            "content_images": ["images/chart.png"],
            "wechat_package_hash": package_hash,
            "site_package_hash": "sha256:site",
        }
        release = {
            "schema_version": 2,
            "article_id": manifest["article_id"],
            "canonical": {"path": "article.md", "source_hash": source_hash},
            "renders": {
                "wechat_package_hash": package_hash,
                "site_package_hash": "sha256:site",
                "site_bundle_hash": None,
            },
            "target_account": {
                "name": "Frontier World",
                "principal": "Frontier World",
                "app_id_fingerprint": "sha256:placeholder",
            },
            "approvals": {},
            "wechat": {"status": "local_rendered", "draft_id": None},
            "site": {"status": "not_deployed"},
            "last_error": None,
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.release_path.write_text(json.dumps(release), encoding="utf-8")

    def close(self) -> None:
        self.temporary.cleanup()


class MarkdownDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.package = MarkdownPackage()

    def tearDown(self) -> None:
        self.package.close()

    def test_preflight_binds_article_html_images_and_cover(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        self.assertTrue(preflight["ok"], preflight["blockers"])
        self.assertEqual(1, preflight["plan"]["content_image_count"])
        self.assertEqual(
            preflight["plan"]["package_hash"],
            json.loads(self.package.release_path.read_text())["renders"]["wechat_package_hash"],
        )

    def test_default_dry_run_has_no_network_and_no_writes(self) -> None:
        before = self.package.release_path.read_bytes()
        stdout = io.StringIO()
        with (
            patch.object(markdown_draft, "WeChatClient", side_effect=AssertionError("network client created")),
            patch.object(markdown_draft, "_atomic_write_json", side_effect=AssertionError("dry-run wrote state")),
            redirect_stdout(stdout),
        ):
            result = markdown_draft.main([str(self.package.path)])
        self.assertEqual(0, result)
        self.assertTrue(json.loads(stdout.getvalue())["dry_run"])
        self.assertEqual(before, self.package.release_path.read_bytes())

    def test_source_mutation_invalidates_preflight(self) -> None:
        self.package.article_path.write_text("changed", encoding="utf-8")
        preflight = markdown_draft.build_preflight(self.package.path)
        self.assertFalse(preflight["ok"])
        self.assertTrue(any("article.md" in blocker for blocker in preflight["blockers"]))

    def test_body_image_alt_text_must_be_non_empty_and_unique(self) -> None:
        html = (
            '<!doctype html><html><body><section id="frontier-signals-body">'
            '<p>Body.</p><img src="images/chart.png" alt="Repeated evidence">'
            '<img src="images/chart.png" alt="Repeated evidence">'
            "</section></body></html>\n"
        )
        self.package.html_path.write_text(html, encoding="utf-8")
        source_hash = "sha256:" + hashlib.sha256(self.package.article_path.read_bytes()).hexdigest()
        content = draft._extract_body(html)
        package_hash = draft._package_hash(
            signal_hash=source_hash,
            content=content,
            local_images={"images/chart.png": self.package.image_path},
            cover_path=self.package.cover_path,
        )
        manifest = json.loads(self.package.manifest_path.read_text())
        manifest["wechat_package_hash"] = package_hash
        self.package.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        release = json.loads(self.package.release_path.read_text())
        release["renders"]["wechat_package_hash"] = package_hash
        self.package.release_path.write_text(json.dumps(release), encoding="utf-8")

        preflight = markdown_draft.build_preflight(self.package.path)

        self.assertFalse(preflight["ok"])
        self.assertTrue(any("alt text must be unique" in item for item in preflight["blockers"]))

    def test_confirm_without_exact_arguments_stops_before_network(self) -> None:
        stderr = io.StringIO()
        with (
            patch.object(markdown_draft, "WeChatClient", side_effect=AssertionError("network client created")),
            redirect_stderr(stderr),
        ):
            result = markdown_draft.main([str(self.package.path), "--confirm"])
        self.assertEqual(1, result)
        self.assertIn("--confirm requires", stderr.getvalue())

    def test_confirm_rejects_principal_drift_before_network(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        target = preflight["plan"]["target_account"]
        stderr = io.StringIO()
        with (
            patch.object(markdown_draft, "WeChatClient", side_effect=AssertionError("network client created")),
            redirect_stderr(stderr),
        ):
            result = markdown_draft.main([
                str(self.package.path),
                "--confirm",
                "--approved-hash", preflight["plan"]["content_hash"],
                "--approved-package-hash", preflight["plan"]["package_hash"],
                "--target-account", target["name"],
                "--target-principal", "Different principal",
                "--target-app-id-fingerprint", target["app_id_fingerprint"],
            ])
        self.assertEqual(1, result)
        self.assertIn("--target-principal does not match", stderr.getvalue())

    def test_update_confirm_requires_complete_identity_before_network(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        target = preflight["plan"]["target_account"]
        receipt = {
            "article_id": preflight["plan"]["article_id"],
            "content_hash": "sha256:old-source",
            "package_hash": "sha256:old-package",
            "target_account": target,
            "title": preflight["plan"]["title"],
            "draft_id": "existing-draft-id",
            "status": "created_unverified",
            "cover_media_id": "existing-cover-id",
        }
        (self.package.path / "wechat-draft-receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        update = markdown_update.build_update_preflight(self.package.path)
        self.assertTrue(update["ok"], update["blockers"])
        stderr = io.StringIO()
        with (
            patch.object(markdown_update, "WeChatClient", side_effect=AssertionError("network client created")),
            redirect_stderr(stderr),
        ):
            result = markdown_update.main([
                str(self.package.path),
                "--confirm",
                "--approved-hash", update["plan"]["content_hash"],
                "--approved-package-hash", update["plan"]["package_hash"],
                "--target-account", target["name"],
                "--target-principal", target["principal"],
                "--draft-id", "existing-draft-id",
            ])
        self.assertEqual(1, result)
        self.assertIn("--target-app-id-fingerprint", stderr.getvalue())

    def test_reconcile_confirm_rejects_fingerprint_drift_before_network(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        target = preflight["plan"]["target_account"]
        receipt = {
            "article_id": preflight["plan"]["article_id"],
            "content_hash": preflight["plan"]["content_hash"],
            "package_hash": preflight["plan"]["package_hash"],
            "target_account": target,
            "title": preflight["plan"]["title"],
            "draft_id": "existing-draft-id",
            "status": "updated_unverified",
            "content_images": {
                source: f"https://mmbiz.qpic.cn/test/{index}/0"
                for index, source in enumerate(preflight["plan"]["content_images"])
            },
            "cover_media_id": "existing-cover-id",
        }
        (self.package.path / "wechat-draft-receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        reconcile = markdown_reconcile.build_reconcile_preflight(self.package.path)
        self.assertTrue(reconcile["ok"], reconcile["blockers"])
        stderr = io.StringIO()
        with (
            patch.object(markdown_reconcile, "WeChatClient", side_effect=AssertionError("network client created")),
            redirect_stderr(stderr),
        ):
            result = markdown_reconcile.main([
                str(self.package.path),
                "--confirm",
                "--approved-hash", reconcile["plan"]["content_hash"],
                "--approved-package-hash", reconcile["plan"]["package_hash"],
                "--target-account", target["name"],
                "--target-principal", target["principal"],
                "--target-app-id-fingerprint", "sha256:different-app",
                "--draft-id", "existing-draft-id",
            ])
        self.assertEqual(1, result)
        self.assertIn("--target-app-id-fingerprint does not match", stderr.getvalue())

    def test_review_confirmed_can_never_create_another_draft(self) -> None:
        release = json.loads(self.package.release_path.read_text())
        release["wechat"]["status"] = "review_confirmed"
        release["wechat"]["draft_id"] = "reviewed-draft"
        self.package.release_path.write_text(json.dumps(release), encoding="utf-8")

        preflight = markdown_draft.build_preflight(self.package.path)
        self.assertFalse(preflight["ok"])
        self.assertTrue(any("immutable" in blocker for blocker in preflight["blockers"]))

    def test_reconcile_unknown_only_rejects_state_drift_before_client_or_network(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        target = preflight["plan"]["target_account"]
        stderr = io.StringIO()
        with (
            patch.object(markdown_draft, "WeChatClient", side_effect=AssertionError("network client created")),
            redirect_stderr(stderr),
        ):
            result = markdown_draft.main([
                str(self.package.path),
                "--confirm",
                "--approved-hash", preflight["plan"]["content_hash"],
                "--approved-package-hash", preflight["plan"]["package_hash"],
                "--target-account", target["name"],
                "--target-principal", target["principal"],
                "--target-app-id-fingerprint", target["app_id_fingerprint"],
                "--reconcile-unknown-only",
            ])
        self.assertEqual(1, result)
        self.assertIn("requires an unknown draft/add result", stderr.getvalue())

    def test_cover_path_is_fixed_to_the_approved_wechat_cover(self) -> None:
        manifest = json.loads(self.package.manifest_path.read_text())
        manifest["cover"] = "images/chart.png"
        self.package.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        preflight = markdown_draft.build_preflight(self.package.path)
        self.assertFalse(preflight["ok"])
        self.assertTrue(any("cover must be wechat-cover.png" in blocker for blocker in preflight["blockers"]))

    def test_known_not_created_failure_can_be_retried_but_unknown_cannot(self) -> None:
        release = json.loads(self.package.release_path.read_text())
        release["wechat"]["status"] = "failed"
        release["last_error"] = {"outcome": "not_created"}
        self.package.release_path.write_text(json.dumps(release), encoding="utf-8")
        self.assertTrue(markdown_draft.build_preflight(self.package.path)["ok"])

        release["last_error"] = {"outcome": "unknown"}
        self.package.release_path.write_text(json.dumps(release), encoding="utf-8")
        self.assertFalse(markdown_draft.build_preflight(self.package.path)["ok"])

    def test_confirm_uses_an_article_level_process_lock(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        lock_path = self.package.build / "wechat-draft.lock"
        lock_path.touch()
        stderr = io.StringIO()
        with lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with (
                patch.object(markdown_draft, "WeChatClient", side_effect=AssertionError("network client created")),
                redirect_stderr(stderr),
            ):
                result = markdown_draft.main([
                    str(self.package.path),
                    "--confirm",
                    "--approved-hash", preflight["plan"]["content_hash"],
                    "--approved-package-hash", preflight["plan"]["package_hash"],
                    "--target-account", preflight["plan"]["target_account"]["name"],
                ])
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        self.assertEqual(1, result)
        self.assertIn("already running", stderr.getvalue())

    def test_remote_operation_uses_a_frozen_approved_media_snapshot(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        approved_image = self.package.image_path.read_bytes()
        approved_cover = self.package.cover_path.read_bytes()

        with markdown_draft._frozen_preflight(preflight) as frozen:
            self.package.image_path.write_bytes(_png(200, 200))
            self.package.cover_path.write_bytes(_png(900, 383) + b"changed")
            self.assertEqual(approved_image, frozen["_local_images"]["images/chart.png"].read_bytes())
            self.assertEqual(approved_cover, frozen["_cover_path"].read_bytes())

    def test_existing_draft_update_preflight_binds_the_old_draft_to_the_new_package(self) -> None:
        receipt = {
            "article_id": "2026-08-18/markdown-source",
            "content_hash": "sha256:old-source",
            "package_hash": "sha256:old-package",
            "target_account": {
                "name": "Frontier World",
                "principal": "Frontier World",
                "app_id_fingerprint": "sha256:placeholder",
            },
            "title": "Markdown source",
            "draft_id": "existing-draft-id",
            "status": "created_unverified",
            "cover_media_id": "existing-cover-id",
        }
        (self.package.path / "wechat-draft-receipt.json").write_text(
            json.dumps(receipt),
            encoding="utf-8",
        )

        preflight = markdown_update.build_update_preflight(self.package.path)

        self.assertTrue(preflight["ok"], preflight["blockers"])
        self.assertEqual(
            "existing-draft-id",
            preflight["update_existing_draft"]["draft_id"],
        )
        self.assertEqual(
            "sha256:old-package",
            preflight["update_existing_draft"]["previous_package_hash"],
        )
        self.assertFalse(preflight["update_existing_draft"]["creates_new_draft"])

    def test_existing_draft_update_preflight_fails_without_a_receipt(self) -> None:
        preflight = markdown_update.build_update_preflight(self.package.path)
        self.assertFalse(preflight["ok"])
        self.assertTrue(any("receipt is missing" in item for item in preflight["blockers"]))

    def test_existing_draft_reconcile_preflight_is_remote_read_only(self) -> None:
        preflight = markdown_draft.build_preflight(self.package.path)
        receipt = {
            "article_id": preflight["plan"]["article_id"],
            "content_hash": preflight["plan"]["content_hash"],
            "package_hash": preflight["plan"]["package_hash"],
            "target_account": preflight["plan"]["target_account"],
            "title": preflight["plan"]["title"],
            "draft_id": "existing-draft-id",
            "status": "updated_unverified",
            "content_images": {
                source: f"https://mmbiz.qpic.cn/test/{index}/0"
                for index, source in enumerate(preflight["plan"]["content_images"])
            },
            "cover_media_id": "existing-cover-id",
        }
        for status in ("updated_unverified", "update_submitting"):
            with self.subTest(status=status):
                receipt["status"] = status
                (self.package.path / "wechat-draft-receipt.json").write_text(
                    json.dumps(receipt),
                    encoding="utf-8",
                )

                reconcile = markdown_reconcile.build_reconcile_preflight(self.package.path)

                self.assertTrue(reconcile["ok"], reconcile["blockers"])
                self.assertEqual(
                    "existing-draft-id",
                    reconcile["reconcile_existing_draft"]["draft_id"],
                )
                self.assertFalse(reconcile["reconcile_existing_draft"]["remote_write"])

    def test_interrupted_update_can_identify_an_unchanged_remote_draft(self) -> None:
        remote = {
            "news_item": [{
                "title": "Markdown source",
                "content": "<section><p>Old remote body</p></section>",
            }]
        }
        receipt = {
            "status": "update_submitting",
            "previous_receipt": {"status": "created_unverified"},
            "previous_remote_snapshot_hash": draft._canonical_json_hash(
                remote["news_item"][0]
            ),
        }

        self.assertTrue(
            markdown_reconcile._matches_pre_update_snapshot(receipt, remote)
        )
        remote["news_item"][0]["content"] = "<section><p>Changed</p></section>"
        self.assertFalse(
            markdown_reconcile._matches_pre_update_snapshot(receipt, remote)
        )


if __name__ == "__main__":
    unittest.main()
