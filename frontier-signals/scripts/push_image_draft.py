#!/usr/bin/env python3
"""Dry-run, create, update, or reconcile a WeChat newspic draft safely.

The canonical input is draft-package.json. A changed reviewed package updates
the same verified draft ID; it never falls back to draft/add. Every remote
write is bound to exact source/package hashes and full account identity.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import struct
import sys
import tempfile
import zlib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from push_wechat_draft import (
    COVER_MAX_BYTES,
    TITLE_MAX_CHARACTERS,
    DraftAdapterError,
    WeChatAPIError,
    WeChatClient,
    _app_id_fingerprint,
    _atomic_write_json,
    _canonical_json_hash,
    _file_hash,
    _load_json,
    _public_result,
)


IMAGE_CONTENT_MAX_BYTES = 2_048
IMAGE_MESSAGE_MAX_IMAGES = 20
CANONICAL_NAME = "draft-package.json"
RECEIPT_NAME = "image-draft-receipt.json"
AMBIGUOUS_ERROR_CODES = {-1, "-1"}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _source_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _caption_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _package_directory(value: Path) -> Path:
    path = value.expanduser().resolve()
    if path.is_file() and path.name == CANONICAL_NAME:
        return path.parent
    if path.is_dir():
        return path
    raise DraftAdapterError(f"image draft package does not exist: {path}")


def _safe_image_path(package_dir: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise DraftAdapterError("image.path must be a non-empty relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise DraftAdapterError("image.path must stay inside the package directory")
    path = (package_dir / relative).resolve()
    try:
        path.relative_to(package_dir)
    except ValueError as error:
        raise DraftAdapterError("image.path escapes the package directory") from error
    return path


def _png_dimensions(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise DraftAdapterError(f"image file does not exist: {path}")
    if path.suffix.lower() != ".png":
        raise DraftAdapterError("image messages currently require PNG images")
    size = path.stat().st_size
    if size >= COVER_MAX_BYTES:
        raise DraftAdapterError(f"image exceeds WeChat permanent-material limit: {size} bytes")
    data = path.read_bytes()
    if len(data) < 45 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DraftAdapterError(f"image is not a valid PNG: {path.name}")
    ihdr_length = struct.unpack(">I", data[8:12])[0]
    if ihdr_length != 13 or data[12:16] != b"IHDR":
        raise DraftAdapterError(f"image has an invalid PNG IHDR chunk: {path.name}")
    expected_crc = struct.unpack(">I", data[29:33])[0]
    if zlib.crc32(data[12:29]) & 0xFFFFFFFF != expected_crc or b"IEND" not in data[33:]:
        raise DraftAdapterError(f"image has an invalid PNG structure: {path.name}")
    return struct.unpack(">II", data[16:24])


def _configured_images(package: dict[str, Any]) -> list[dict[str, Any]]:
    images = package.get("images")
    if images is None and isinstance(package.get("image"), dict):
        images = [package["image"]]
    if not isinstance(images, list):
        raise DraftAdapterError("images must be an ordered array")
    if not 1 <= len(images) <= IMAGE_MESSAGE_MAX_IMAGES:
        raise DraftAdapterError(f"images must contain 1-{IMAGE_MESSAGE_MAX_IMAGES} items")
    if any(not isinstance(item, dict) for item in images):
        raise DraftAdapterError("each images item must be an object")
    return images


def _crop_percent_list(width: int, height: int) -> list[dict[str, str]]:
    aspect = width / height
    crops: list[dict[str, str]] = []
    for ratio_name, target in (("1_1", 1.0), ("16_9", 16 / 9), ("2.35_1", 2.35)):
        if aspect < target:
            crop_height = aspect / target
            y1 = (1 - crop_height) / 2
            crops.append({
                "ratio": ratio_name,
                "x1": "0",
                "y1": f"{y1:.7f}",
                "x2": "1",
                "y2": f"{1 - y1:.7f}",
            })
        else:
            crop_width = target / aspect
            x1 = (1 - crop_width) / 2
            crops.append({
                "ratio": ratio_name,
                "x1": f"{x1:.7f}",
                "y1": "0",
                "x2": f"{1 - x1:.7f}",
                "y2": "1",
            })
    return crops


def _article(plan: dict[str, Any], image_media_ids: list[str]) -> dict[str, Any]:
    first = plan["images"][0]
    return {
        "article_type": "newspic",
        "title": plan["title"],
        "content": plan["content"],
        "need_open_comment": int(plan["comments"]["enabled"]),
        "only_fans_can_comment": int(plan["comments"]["fans_only"]),
        "image_info": {
            "image_list": [{"image_media_id": media_id} for media_id in image_media_ids]
        },
        "cover_info": {
            "crop_percent_list": _crop_percent_list(first["width"], first["height"])
        },
    }


def _remote_snapshot(response: dict[str, Any]) -> dict[str, Any]:
    items = response.get("news_item")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise DraftAdapterError("draft/get response must contain exactly one news_item")
    item = items[0]
    image_info = item.get("image_info")
    image_list = image_info.get("image_list") if isinstance(image_info, dict) else None
    if not isinstance(image_list, list) or any(not isinstance(value, dict) for value in image_list):
        raise DraftAdapterError("draft/get did not contain a valid image list")
    media_ids = [value.get("image_media_id") for value in image_list]
    if any(not isinstance(value, str) or not value for value in media_ids):
        raise DraftAdapterError("draft/get image list contains an invalid media ID")
    content = item.get("content")
    if not isinstance(content, str):
        raise DraftAdapterError("draft/get returned invalid image-message content")
    return {
        "article_type": item.get("article_type"),
        "title": item.get("title"),
        "caption_hash": _caption_hash(content),
        "image_media_ids": media_ids,
        "comments": {
            "enabled": item.get("need_open_comment"),
            "fans_only": item.get("only_fans_can_comment"),
        },
    }


def _verify_remote_draft(
    response: dict[str, Any],
    *,
    plan: dict[str, Any],
    image_media_ids: list[str],
) -> dict[str, Any]:
    snapshot = _remote_snapshot(response)
    expected = {
        "article_type": "newspic",
        "title": plan["title"],
        "caption_hash": plan["caption_hash"],
        "image_media_ids": image_media_ids,
        "comments": {
            "enabled": int(plan["comments"]["enabled"]),
            "fans_only": int(plan["comments"]["fans_only"]),
        },
    }
    if snapshot != expected:
        raise DraftAdapterError("draft/get does not match the approved newspic package")
    return {
        **snapshot,
        "image_count": len(image_media_ids),
        "snapshot_hash": _canonical_json_hash(snapshot),
    }


def _legacy_receipt_media_ids(receipt: dict[str, Any]) -> list[str]:
    values = receipt.get("image_media_ids")
    if isinstance(values, list) and all(isinstance(value, str) and value for value in values):
        return values
    value = receipt.get("image_media_id")
    if isinstance(value, str) and value:
        return [value]
    images = receipt.get("images")
    if isinstance(images, list):
        media_ids = [item.get("media_id") for item in images if isinstance(item, dict)]
        if media_ids and all(isinstance(value, str) and value for value in media_ids):
            return media_ids
    raise DraftAdapterError("existing receipt is missing ordered image media IDs")


def _expected_snapshot_from_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    snapshot = receipt.get("remote_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    verification = receipt.get("verification")
    if not isinstance(verification, dict):
        raise DraftAdapterError("existing receipt is missing remote verification")
    caption_hash = verification.get("caption_hash") or verification.get("content_hash")
    comments = verification.get("comments")
    if not isinstance(caption_hash, str) or not isinstance(comments, dict):
        raise DraftAdapterError("existing receipt verification is incomplete")
    return {
        "article_type": verification.get("article_type"),
        "title": verification.get("title") or receipt.get("title"),
        "caption_hash": caption_hash,
        "image_media_ids": _legacy_receipt_media_ids(receipt),
        "comments": comments,
    }


def _verify_account(plan: dict[str, Any], app_id: str, args: argparse.Namespace) -> None:
    target = plan["target_account"]
    if args.target_account != target["name"]:
        raise DraftAdapterError("--target-account does not match draft-package.json")
    if args.target_principal != target["principal"]:
        raise DraftAdapterError("--target-principal does not match draft-package.json")
    if args.target_app_id_fingerprint != target["app_id_fingerprint"]:
        raise DraftAdapterError("--target-app-id-fingerprint does not match draft-package.json")
    if target["name"] != os.environ.get("WECHAT_TARGET_ACCOUNT"):
        raise DraftAdapterError("WECHAT_TARGET_ACCOUNT does not match draft-package.json")
    if target["principal"] != os.environ.get("WECHAT_TARGET_PRINCIPAL"):
        raise DraftAdapterError("WECHAT_TARGET_PRINCIPAL does not match draft-package.json")
    if target["app_id_fingerprint"] != _app_id_fingerprint(app_id):
        raise DraftAdapterError("WECHAT_APP_ID does not match the approved account fingerprint")


def build_preflight(value: Path) -> dict[str, Any]:
    package_dir = _package_directory(value)
    source_path = package_dir / CANONICAL_NAME
    receipt_path = package_dir / RECEIPT_NAME
    blockers: list[str] = []
    warnings: list[str] = []
    if not source_path.is_file():
        return {
            "ok": False,
            "dry_run": True,
            "package_dir": str(package_dir),
            "blockers": [f"missing required file: {CANONICAL_NAME}"],
            "warnings": warnings,
        }
    package = _load_json(source_path)
    if package.get("schema") not in {
        "frontier-signals/wechat-image-draft@1",
        "frontier-signals/wechat-image-draft@2",
    }:
        blockers.append("unsupported image draft package schema")
    if package.get("surface") != "wechat_image_message":
        blockers.append("surface must be wechat_image_message")
    if package.get("status") != "local_reviewed":
        blockers.append("image draft package must be local_reviewed")

    target = package.get("target_account")
    if not isinstance(target, dict):
        blockers.append("target_account must be an object")
        target = {}
    for key in ("name", "principal", "app_id_fingerprint"):
        if not isinstance(target.get(key), str) or not target[key].strip():
            blockers.append(f"target_account.{key} is missing")
    if isinstance(target.get("app_id_fingerprint"), str) and not target["app_id_fingerprint"].startswith("sha256:"):
        blockers.append("target_account.app_id_fingerprint must be a sha256 fingerprint")

    title = package.get("title")
    content = package.get("caption")
    if not isinstance(title, str) or not title.strip():
        blockers.append("title is missing")
        title = ""
    elif len(title) > TITLE_MAX_CHARACTERS:
        blockers.append(f"title exceeds WeChat limit: {len(title)}/{TITLE_MAX_CHARACTERS}")
    if not isinstance(content, str) or not content.strip():
        blockers.append("caption is missing")
        content = ""
    elif "<" in content or ">" in content:
        blockers.append("image-message caption must be plain text")
    content_bytes = len(content.encode("utf-8"))
    if content_bytes >= IMAGE_CONTENT_MAX_BYTES:
        blockers.append(f"caption exceeds image-message limit: {content_bytes}/{IMAGE_CONTENT_MAX_BYTES} bytes")

    reviews = package.get("reviews")
    if not isinstance(reviews, dict):
        blockers.append("reviews must be an object")
        reviews = {}

    review_override = reviews.get("override")
    explicit_user_override = False
    if isinstance(review_override, dict) and review_override.get("type") == "explicit_user_override":
        authorized_by = review_override.get("authorized_by")
        authorized_at = review_override.get("authorized_at")
        reason = review_override.get("reason")
        explicit_user_override = all(
            isinstance(value, str) and value.strip()
            for value in (authorized_by, authorized_at, reason)
        )
        if explicit_user_override:
            warnings.append(
                "explicit user override: routine dbs/humanizer reviews were skipped; "
                f"authorized_by={authorized_by}; authorized_at={authorized_at}; reason={reason}"
            )
        else:
            blockers.append("explicit user override requires authorized_by, authorized_at, and reason")

    if not explicit_user_override:
        if reviews.get("selection_result") != "pass" or reviews.get("final_result") != "pass":
            blockers.append("dbs selection and final reviews must both pass")
        if not isinstance(reviews.get("humanizer_score"), int) or reviews.get("humanizer_score", 0) < 45:
            blockers.append("humanizer score must be at least 45/50")

    comments = package.get("comments")
    if not isinstance(comments, dict):
        blockers.append("comments must be an object")
        comments = {}
    if not isinstance(comments.get("enabled"), bool) or not isinstance(comments.get("fans_only"), bool):
        blockers.append("comments settings must be booleans")
    if comments.get("fans_only") and not comments.get("enabled"):
        blockers.append("fans_only comments require comments.enabled=true")

    image_entries: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    try:
        configured = _configured_images(package)
    except DraftAdapterError as error:
        blockers.append(str(error))
        configured = []
    for index, image in enumerate(configured):
        try:
            image_path = _safe_image_path(package_dir, image.get("path"))
            relative_path = str(image_path.relative_to(package_dir))
            if relative_path in seen_paths:
                raise DraftAdapterError(f"duplicate image path: {relative_path}")
            seen_paths.add(relative_path)
            width, height = _png_dimensions(image_path)
            image_hash = _file_hash(image_path)
            if image.get("sha256") != image_hash:
                blockers.append(f"images[{index}].sha256 does not match the image bytes")
            if image.get("width") != width or image.get("height") != height:
                blockers.append(f"images[{index}] dimensions do not match draft-package.json")
            image_entries.append({
                "index": index,
                "path": relative_path,
                "absolute_path": str(image_path),
                "sha256": image_hash,
                "width": width,
                "height": height,
            })
        except DraftAdapterError as error:
            blockers.append(str(error))

    source_hash = _source_hash(source_path)
    ordered_image_hashes = [entry["sha256"] for entry in image_entries]
    package_hash = _canonical_json_hash({
        "source_hash": source_hash,
        "ordered_image_hashes": ordered_image_hashes,
    })
    existing = _load_json(receipt_path) if receipt_path.is_file() else None
    operation = "create"
    existing_draft_id = None
    if existing:
        existing_status = existing.get("status")
        if existing_status == "verified" and isinstance(existing.get("draft_id"), str):
            existing_draft_id = existing["draft_id"]
            if existing.get("content_hash") == source_hash and existing.get("package_hash") == package_hash:
                operation = "reuse"
                warnings.append("matching verified image-message draft already exists and will be reused")
            else:
                operation = "update"
                warnings.append("current package differs from the verified remote draft; update the same draft ID after approval")
        elif existing_status in {"update_result_unknown", "updated_unverified"}:
            operation = "reconcile"
            blockers.append("image draft update result is uncertain; run --reconcile before another write")
        else:
            blockers.append("existing image draft receipt is not in a reusable or updatable state")

    plan = {
        "operation": operation,
        "draft_id": existing_draft_id,
        "content_hash": source_hash,
        "package_hash": package_hash,
        "previous_content_hash": existing.get("content_hash") if existing else None,
        "previous_package_hash": existing.get("package_hash") if existing else None,
        "target_account": {
            "name": target.get("name"),
            "principal": target.get("principal"),
            "app_id_fingerprint": target.get("app_id_fingerprint"),
        },
        "article_type": "newspic",
        "title": title,
        "content": content,
        "caption_hash": _caption_hash(content),
        "content_bytes": content_bytes,
        "image_count": len(image_entries),
        "images": image_entries,
        "comments": {
            "enabled": comments.get("enabled"),
            "fans_only": comments.get("fans_only"),
        },
    }
    return {
        "ok": not blockers,
        "dry_run": True,
        "package_dir": str(package_dir),
        "source_path": str(source_path),
        "receipt_path": str(receipt_path),
        "blockers": blockers,
        "warnings": warnings,
        "plan": plan,
        "_package": package,
        "_existing_receipt": existing,
    }


@contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise DraftAdapterError("another image draft operation is already running") from error
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _frozen_preflight(preflight: dict[str, Any]):
    with tempfile.TemporaryDirectory(prefix="frontier-wechat-newspic-") as temporary:
        root = Path(temporary)
        source = root / CANONICAL_NAME
        source.write_bytes(Path(preflight["source_path"]).read_bytes())
        frozen_images: list[Path] = []
        hashes: list[str] = []
        for image in preflight["plan"]["images"]:
            destination = root / f"{image['index']:02d}.png"
            destination.write_bytes(Path(image["absolute_path"]).read_bytes())
            frozen_images.append(destination)
            hashes.append(_file_hash(destination))
        source_hash = _source_hash(source)
        package_hash = _canonical_json_hash({
            "source_hash": source_hash,
            "ordered_image_hashes": hashes,
        })
        if source_hash != preflight["plan"]["content_hash"]:
            raise DraftAdapterError("draft-package.json changed while freezing the approved package")
        if package_hash != preflight["plan"]["package_hash"]:
            raise DraftAdapterError("one or more images changed while freezing the approved package")
        frozen = dict(preflight)
        frozen["_frozen_images"] = frozen_images
        yield frozen


def _verified_receipt(
    preflight: dict[str, Any],
    *,
    draft_id: str,
    media_ids: list[str],
    verification: dict[str, Any],
    operation: str,
) -> dict[str, Any]:
    plan = preflight["plan"]
    return {
        "schema_version": 2,
        "surface": "wechat_image_message",
        "status": "verified",
        "operation": operation,
        "package_id": preflight["_package"].get("id"),
        "target_account": plan["target_account"],
        "content_hash": plan["content_hash"],
        "source_hash": plan["content_hash"],
        "package_hash": plan["package_hash"],
        "caption_hash": plan["caption_hash"],
        "title": plan["title"],
        "images": [
            {
                "index": image["index"],
                "path": image["path"],
                "sha256": image["sha256"],
                "width": image["width"],
                "height": image["height"],
                "media_id": media_ids[image["index"]],
            }
            for image in plan["images"]
        ],
        "image_media_ids": media_ids,
        "draft_id": draft_id,
        "remote_snapshot": {
            key: verification[key]
            for key in ("article_type", "title", "caption_hash", "image_media_ids", "comments")
        },
        "remote_snapshot_hash": verification["snapshot_hash"],
        "verification": verification,
        "error": None,
        "updated_at": _now(),
    }


def _pending_receipt(
    preflight: dict[str, Any],
    *,
    status: str,
    draft_id: str | None,
    media_ids: list[str],
    previous_receipt: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
    error: str | None = None,
) -> dict[str, Any]:
    plan = preflight["plan"]
    return {
        "schema_version": 2,
        "surface": "wechat_image_message",
        "status": status,
        "attempt_id": secrets.token_hex(16),
        "operation": plan["operation"],
        "target_account": plan["target_account"],
        "content_hash": plan["content_hash"],
        "source_hash": plan["content_hash"],
        "package_hash": plan["package_hash"],
        "caption_hash": plan["caption_hash"],
        "title": plan["title"],
        "images": plan["images"],
        "image_media_ids": media_ids,
        "draft_id": draft_id,
        "previous_receipt": previous_receipt,
        "previous_remote_snapshot": previous_snapshot,
        "previous_remote_snapshot_hash": _canonical_json_hash(previous_snapshot) if previous_snapshot else None,
        "error": error,
        "updated_at": _now(),
    }


def _upload_images(
    client: WeChatClient,
    access_token: str,
    paths: list[Path],
    *,
    receipt_path: Path,
    pending: dict[str, Any],
) -> list[str]:
    media_ids: list[str] = []
    for path in paths:
        media_ids.append(client.upload_cover(path, access_token))
        pending["image_media_ids"] = list(media_ids)
        pending["updated_at"] = _now()
        _atomic_write_json(receipt_path, pending)
    return media_ids


def _verify_confirmation(args: argparse.Namespace, plan: dict[str, Any]) -> None:
    if args.approved_hash != plan["content_hash"]:
        raise DraftAdapterError("--approved-hash does not match draft-package.json")
    if args.approved_package_hash != plan["package_hash"]:
        raise DraftAdapterError("--approved-package-hash does not match the current image package")
    if plan["operation"] == "update" and args.draft_id != plan["draft_id"]:
        raise DraftAdapterError("--draft-id does not match the existing newspic draft")
    if plan["operation"] != "update" and args.draft_id:
        raise DraftAdapterError("--draft-id is only valid when updating an existing newspic draft")


def _restore_previous_receipt(
    receipt_path: Path,
    previous: dict[str, Any],
    *,
    error: str,
) -> None:
    restored = dict(previous)
    restored["last_update"] = {
        "status": "not_updated",
        "error": error,
        "at": _now(),
    }
    _atomic_write_json(receipt_path, restored)


def _confirmed_push(args: argparse.Namespace, preflight: dict[str, Any]) -> dict[str, Any]:
    if not preflight.get("ok"):
        raise DraftAdapterError("preflight has blocking issues; run without --confirm for details")
    plan = preflight["plan"]
    _verify_confirmation(args, plan)
    app_id = os.environ.get("WECHAT_APP_ID", "")
    app_secret = os.environ.get("WECHAT_APP_SECRET", "")
    if not app_id or not app_secret:
        raise DraftAdapterError("WECHAT_APP_ID and WECHAT_APP_SECRET are required")
    _verify_account(plan, app_id, args)
    client = WeChatClient(app_id, app_secret, timeout=args.timeout)
    access_token = client.stable_token()
    receipt_path = Path(preflight["receipt_path"])
    operation = plan["operation"]

    if operation == "reuse":
        receipt = preflight["_existing_receipt"]
        media_ids = _legacy_receipt_media_ids(receipt)
        remote = client.get_draft(plan["draft_id"], access_token)
        verification = _verify_remote_draft(remote, plan=plan, image_media_ids=media_ids)
        return {"ok": True, "operation": "reuse", "draft_id": plan["draft_id"], "verification": verification}

    with _frozen_preflight(preflight) as frozen:
        if operation == "create":
            pending = _pending_receipt(
                preflight,
                status="uploading",
                draft_id=None,
                media_ids=[],
                previous_receipt=None,
                previous_snapshot=None,
            )
            _atomic_write_json(receipt_path, pending)
            media_ids = _upload_images(
                client,
                access_token,
                frozen["_frozen_images"],
                receipt_path=receipt_path,
                pending=pending,
            )
            try:
                draft_id = client.add_draft(_article(plan, media_ids), access_token)
            except WeChatAPIError as error:
                pending["status"] = "remote_result_unknown" if error.errcode in AMBIGUOUS_ERROR_CODES else "failed_not_created"
                pending["error"] = str(error)
                pending["updated_at"] = _now()
                _atomic_write_json(receipt_path, pending)
                raise
            except DraftAdapterError as error:
                pending["status"] = "remote_result_unknown"
                pending["error"] = str(error)
                pending["updated_at"] = _now()
                _atomic_write_json(receipt_path, pending)
                raise
            pending["status"] = "draft_created_unverified"
            pending["draft_id"] = draft_id
            pending["updated_at"] = _now()
            _atomic_write_json(receipt_path, pending)
            remote = client.get_draft(draft_id, access_token)
            verification = _verify_remote_draft(remote, plan=plan, image_media_ids=media_ids)
            verified = _verified_receipt(
                preflight,
                draft_id=draft_id,
                media_ids=media_ids,
                verification=verification,
                operation="create",
            )
            _atomic_write_json(receipt_path, verified)
            return {"ok": True, "operation": "create", "draft_id": draft_id, "verification": verification}

        if operation != "update":
            raise DraftAdapterError(f"unsupported image draft operation: {operation}")
        previous = preflight["_existing_receipt"]
        if not isinstance(previous, dict):
            raise DraftAdapterError("update requires an existing verified receipt")
        draft_id = plan["draft_id"]
        old_remote = client.get_draft(draft_id, access_token)
        old_snapshot = _remote_snapshot(old_remote)
        if old_snapshot != _expected_snapshot_from_receipt(previous):
            raise DraftAdapterError("remote newspic draft drifted from the existing verified receipt")
        pending = _pending_receipt(
            preflight,
            status="update_uploading",
            draft_id=draft_id,
            media_ids=[],
            previous_receipt=previous,
            previous_snapshot=old_snapshot,
        )
        _atomic_write_json(receipt_path, pending)
        media_ids = _upload_images(
            client,
            access_token,
            frozen["_frozen_images"],
            receipt_path=receipt_path,
            pending=pending,
        )
        try:
            client.update_draft(draft_id, _article(plan, media_ids), access_token)
        except WeChatAPIError as error:
            if error.errcode in AMBIGUOUS_ERROR_CODES:
                pending["status"] = "update_result_unknown"
                pending["error"] = str(error)
                pending["updated_at"] = _now()
                _atomic_write_json(receipt_path, pending)
            else:
                _restore_previous_receipt(receipt_path, previous, error=str(error))
            raise
        except DraftAdapterError as error:
            pending["status"] = "update_result_unknown"
            pending["error"] = str(error)
            pending["updated_at"] = _now()
            _atomic_write_json(receipt_path, pending)
            raise
        pending["status"] = "updated_unverified"
        pending["updated_at"] = _now()
        _atomic_write_json(receipt_path, pending)
        try:
            remote = client.get_draft(draft_id, access_token)
            verification = _verify_remote_draft(remote, plan=plan, image_media_ids=media_ids)
        except DraftAdapterError as error:
            pending["error"] = str(error)
            pending["updated_at"] = _now()
            _atomic_write_json(receipt_path, pending)
            raise
        verified = _verified_receipt(
            preflight,
            draft_id=draft_id,
            media_ids=media_ids,
            verification=verification,
            operation="update",
        )
        _atomic_write_json(receipt_path, verified)
        return {"ok": True, "operation": "update", "draft_id": draft_id, "verification": verification}


def _reconcile(args: argparse.Namespace, preflight: dict[str, Any]) -> dict[str, Any]:
    receipt_path = Path(preflight["receipt_path"])
    receipt = _load_json(receipt_path)
    if receipt.get("status") not in {"update_result_unknown", "updated_unverified"}:
        raise DraftAdapterError("image draft receipt does not require reconciliation")
    draft_id = receipt.get("draft_id")
    if not isinstance(draft_id, str) or not draft_id:
        raise DraftAdapterError("uncertain image update receipt is missing draft_id")
    plan = preflight["plan"]
    app_id = os.environ.get("WECHAT_APP_ID", "")
    app_secret = os.environ.get("WECHAT_APP_SECRET", "")
    if not app_id or not app_secret:
        raise DraftAdapterError("WECHAT_APP_ID and WECHAT_APP_SECRET are required")
    if args.draft_id != draft_id:
        raise DraftAdapterError("--draft-id does not match the uncertain image update")
    _verify_account(plan, app_id, args)
    client = WeChatClient(app_id, app_secret, timeout=args.timeout)
    token = client.stable_token()
    remote = client.get_draft(draft_id, token)
    snapshot = _remote_snapshot(remote)
    media_ids = receipt.get("image_media_ids")
    if isinstance(media_ids, list) and media_ids:
        try:
            verification = _verify_remote_draft(remote, plan=plan, image_media_ids=media_ids)
        except DraftAdapterError:
            verification = None
        if verification:
            verified = _verified_receipt(
                preflight,
                draft_id=draft_id,
                media_ids=media_ids,
                verification=verification,
                operation="reconcile_update",
            )
            _atomic_write_json(receipt_path, verified)
            return {"ok": True, "outcome": "updated", "draft_id": draft_id, "verification": verification}
    previous = receipt.get("previous_receipt")
    old_snapshot = receipt.get("previous_remote_snapshot")
    if isinstance(previous, dict) and isinstance(old_snapshot, dict) and snapshot == old_snapshot:
        _restore_previous_receipt(receipt_path, previous, error="remote draft still matches the previous verified package")
        return {"ok": True, "outcome": "not_updated", "draft_id": draft_id}
    receipt["status"] = "update_conflict"
    receipt["error"] = "remote draft matches neither the previous nor the proposed package"
    receipt["updated_at"] = _now()
    _atomic_write_json(receipt_path, receipt)
    raise DraftAdapterError("remote image draft is in an unknown conflicting state; inspect it manually")


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run, create, update, or reconcile a WeChat newspic draft")
    parser.add_argument("package", type=Path, help="package directory or draft-package.json")
    parser.add_argument("--confirm", action="store_true", help="perform the approved remote draft write")
    parser.add_argument("--reconcile", action="store_true", help="read back an uncertain update without writing")
    parser.add_argument("--approved-hash")
    parser.add_argument("--approved-package-hash")
    parser.add_argument("--target-account")
    parser.add_argument("--target-principal")
    parser.add_argument("--target-app-id-fingerprint")
    parser.add_argument("--draft-id")
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        package_dir = _package_directory(args.package)
        with _exclusive_lock(package_dir / ".image-draft.lock"):
            preflight = build_preflight(args.package)
            if not args.confirm and not args.reconcile:
                json.dump(_public_result(preflight), sys.stdout, ensure_ascii=False, indent=2)
                sys.stdout.write("\n")
                return 0 if preflight.get("ok") else 1
            if args.reconcile:
                if args.confirm:
                    raise DraftAdapterError("--confirm and --reconcile cannot be combined")
                result = _reconcile(args, preflight)
            else:
                required = (
                    args.approved_hash,
                    args.approved_package_hash,
                    args.target_account,
                    args.target_principal,
                    args.target_app_id_fingerprint,
                )
                if any(not value for value in required):
                    raise DraftAdapterError(
                        "--confirm requires both approved hashes and the complete target account identity"
                    )
                if not preflight.get("ok"):
                    raise DraftAdapterError("preflight has blocking issues; run without --confirm for details")
                result = _confirmed_push(args, preflight)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except DraftAdapterError as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
