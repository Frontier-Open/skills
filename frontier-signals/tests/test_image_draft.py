from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("push_image_draft", SCRIPTS / "push_image_draft.py")
assert SPEC and SPEC.loader
image_draft = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(image_draft)


def png_chunk(name: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)


def png(width: int, height: int, red: int = 0) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = b"\x00" + bytes((red, 0, 0, 255)) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw))
        + png_chunk(b"IEND", b"")
    )


class FakeClient:
    article = None
    add_calls = 0
    update_calls = 0
    upload_calls = 0

    @classmethod
    def reset(cls) -> None:
        cls.article = None
        cls.add_calls = 0
        cls.update_calls = 0
        cls.upload_calls = 0

    def __init__(self, app_id: str, app_secret: str, *, timeout: float) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout

    def stable_token(self) -> str:
        return "token"

    def upload_cover(self, path: Path, access_token: str) -> str:
        assert path.read_bytes().startswith(b"\x89PNG")
        assert access_token == "token"
        FakeClient.upload_calls += 1
        return f"image-media-{FakeClient.upload_calls}"

    def add_draft(self, article: dict, access_token: str) -> str:
        assert access_token == "token"
        FakeClient.add_calls += 1
        FakeClient.article = article
        return "draft-media-id"

    def update_draft(self, media_id: str, article: dict, access_token: str, *, index: int = 0) -> None:
        assert media_id == "draft-media-id"
        assert access_token == "token"
        assert index == 0
        FakeClient.update_calls += 1
        FakeClient.article = article

    def get_draft(self, media_id: str, access_token: str) -> dict:
        assert media_id == "draft-media-id"
        assert access_token == "token"
        return {"news_item": [FakeClient.article]}


class AmbiguousUpdateClient(FakeClient):
    def update_draft(self, media_id: str, article: dict, access_token: str, *, index: int = 0) -> None:
        super().update_draft(media_id, article, access_token, index=index)
        raise image_draft.WeChatAPIError("draft/update", -1, "system busy")


class ImageDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeClient.reset()
        self.environment = {
            "WECHAT_APP_ID": "app-id",
            "WECHAT_APP_SECRET": "app-secret",
            "WECHAT_TARGET_ACCOUNT": "Frontier World",
            "WECHAT_TARGET_PRINCIPAL": "陈杰",
        }

    def package(self, directory: Path, count: int = 3, caption: str = "邮件能直接发出去，责任还得有人承担。") -> Path:
        images = []
        for index in range(count):
            path = directory / f"slide-{index + 1}.png"
            path.write_bytes(png(10, 20, red=index * 20))
            images.append({
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": 10,
                "height": 20,
            })
        package = {
            "schema": "frontier-signals/wechat-image-draft@2",
            "id": "2026-08-19/test-newspic",
            "date": "2026-08-19",
            "target_account": {
                "name": "Frontier World",
                "principal": "陈杰",
                "app_id_fingerprint": image_draft._app_id_fingerprint("app-id"),
            },
            "surface": "wechat_image_message",
            "title": "Claude 能直接发邮件了，人工确认先别关",
            "caption": caption,
            "images": images,
            "reviews": {
                "selection_leaf_skill": "dbs-content",
                "selection_result": "pass",
                "humanizer_score": 47,
                "final_leaf_skill": "dbs-content",
                "final_result": "pass",
            },
            "comments": {"enabled": True, "fans_only": False},
            "status": "local_reviewed",
        }
        source = directory / "draft-package.json"
        source.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
        return source

    def args(self, preflight: dict, *, draft_id: str | None = None) -> argparse.Namespace:
        return argparse.Namespace(
            approved_hash=preflight["plan"]["content_hash"],
            approved_package_hash=preflight["plan"]["package_hash"],
            target_account="Frontier World",
            target_principal="陈杰",
            target_app_id_fingerprint=image_draft._app_id_fingerprint("app-id"),
            draft_id=draft_id,
            timeout=30.0,
        )

    def confirmed(self, source: Path, *, client=FakeClient, draft_id: str | None = None) -> tuple[dict, dict]:
        preflight = image_draft.build_preflight(source)
        self.assertTrue(preflight["ok"], preflight["blockers"])
        with patch.object(image_draft, "WeChatClient", client), patch.dict(os.environ, self.environment, clear=False):
            result = image_draft._confirmed_push(self.args(preflight, draft_id=draft_id), preflight)
        return preflight, result

    def test_explicit_user_override_allows_dry_run_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.package(Path(temporary), count=3)
            value = json.loads(source.read_text(encoding="utf-8"))
            value["reviews"] = {
                "selection_leaf_skill": "skipped_by_user",
                "selection_result": "skipped",
                "humanizer_score": 0,
                "final_leaf_skill": "skipped_by_user",
                "final_result": "skipped",
                "override": {
                    "type": "explicit_user_override",
                    "authorized_by": "陈杰",
                    "authorized_at": "2026-08-20T22:30:00+08:00",
                    "reason": "用户明确要求本次仅对齐排版并保存到草稿箱，跳过常规复核链。",
                },
            }
            source.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            preflight = image_draft.build_preflight(source)
            self.assertTrue(preflight["ok"], preflight["blockers"])
            self.assertEqual(preflight["blockers"], [])
            self.assertTrue(any("explicit user override" in warning for warning in preflight["warnings"]))

    def test_ambiguous_user_override_does_not_bypass_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.package(Path(temporary), count=1)
            value = json.loads(source.read_text(encoding="utf-8"))
            value["reviews"] = {
                "selection_result": "user_override",
                "humanizer_score": 0,
                "final_result": "user_override",
            }
            source.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            preflight = image_draft.build_preflight(source)
            self.assertFalse(preflight["ok"])
            self.assertIn("dbs selection and final reviews must both pass", preflight["blockers"])
            self.assertIn("humanizer score must be at least 45/50", preflight["blockers"])

    def test_create_ordered_multi_image_newspic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.package(Path(temporary), count=3)
            preflight, result = self.confirmed(source)
            self.assertEqual(preflight["plan"]["operation"], "create")
            self.assertEqual(preflight["plan"]["image_count"], 3)
            self.assertEqual(result["operation"], "create")
            self.assertEqual(FakeClient.add_calls, 1)
            self.assertEqual(FakeClient.update_calls, 0)
            self.assertEqual(
                FakeClient.article["image_info"]["image_list"],
                [
                    {"image_media_id": "image-media-1"},
                    {"image_media_id": "image-media-2"},
                    {"image_media_id": "image-media-3"},
                ],
            )
            receipt = json.loads((Path(temporary) / "image-draft-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_version"], 2)
            self.assertEqual(receipt["status"], "verified")
            self.assertEqual(len(receipt["images"]), 3)

    def test_changed_package_updates_same_draft_without_add(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = self.package(directory, count=1)
            self.confirmed(source)
            self.assertEqual(FakeClient.add_calls, 1)

            source = self.package(directory, count=3, caption="更新后的完整配文。")
            preflight = image_draft.build_preflight(source)
            self.assertTrue(preflight["ok"])
            self.assertEqual(preflight["plan"]["operation"], "update")
            self.assertEqual(preflight["plan"]["draft_id"], "draft-media-id")
            with patch.object(image_draft, "WeChatClient", FakeClient), patch.dict(os.environ, self.environment, clear=False):
                result = image_draft._confirmed_push(self.args(preflight, draft_id="draft-media-id"), preflight)
            self.assertEqual(result["operation"], "update")
            self.assertEqual(FakeClient.add_calls, 1)
            self.assertEqual(FakeClient.update_calls, 1)
            self.assertEqual(len(FakeClient.article["image_info"]["image_list"]), 3)

    def test_remote_drift_stops_before_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = self.package(directory, count=1)
            self.confirmed(source)
            uploads = FakeClient.upload_calls
            FakeClient.article["title"] = "Remote changed"
            source = self.package(directory, count=2, caption="new")
            preflight = image_draft.build_preflight(source)
            with patch.object(image_draft, "WeChatClient", FakeClient), patch.dict(os.environ, self.environment, clear=False):
                with self.assertRaisesRegex(image_draft.DraftAdapterError, "drifted"):
                    image_draft._confirmed_push(self.args(preflight, draft_id="draft-media-id"), preflight)
            self.assertEqual(FakeClient.upload_calls, uploads)
            self.assertEqual(FakeClient.update_calls, 0)

    def test_ambiguous_update_is_reconciled_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = self.package(directory, count=1)
            self.confirmed(source)
            source = self.package(directory, count=2, caption="new")
            preflight = image_draft.build_preflight(source)
            with patch.object(image_draft, "WeChatClient", AmbiguousUpdateClient), patch.dict(os.environ, self.environment, clear=False):
                with self.assertRaises(image_draft.WeChatAPIError):
                    image_draft._confirmed_push(self.args(preflight, draft_id="draft-media-id"), preflight)
            receipt = json.loads((directory / "image-draft-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "update_result_unknown")

            uncertain = image_draft.build_preflight(source)
            reconcile_args = self.args(uncertain, draft_id="draft-media-id")
            with patch.object(image_draft, "WeChatClient", FakeClient), patch.dict(os.environ, self.environment, clear=False):
                result = image_draft._reconcile(reconcile_args, uncertain)
            self.assertEqual(result["outcome"], "updated")
            self.assertEqual(FakeClient.update_calls, 1)
            verified = json.loads((directory / "image-draft-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(verified["status"], "verified")

    def test_full_account_identity_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.package(Path(temporary), count=1)
            preflight = image_draft.build_preflight(source)
            args = self.args(preflight)
            args.target_principal = "Wrong"
            with patch.dict(os.environ, self.environment, clear=False):
                with self.assertRaisesRegex(image_draft.DraftAdapterError, "target-principal"):
                    image_draft._verify_account(preflight["plan"], "app-id", args)

    def test_image_order_changes_package_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = self.package(directory, count=2)
            first = image_draft.build_preflight(source)["plan"]["package_hash"]
            value = json.loads(source.read_text(encoding="utf-8"))
            value["images"].reverse()
            source.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            second = image_draft.build_preflight(source)["plan"]["package_hash"]
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
