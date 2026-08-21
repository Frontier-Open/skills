#!/usr/bin/env python3
"""Update one existing WeChat draft from the current Markdown package.

Dry-run is the default. A remote update requires the exact current hashes,
target account, and existing draft ID. This script never calls draft/add.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Any

from push_markdown_draft import build_preflight, _exclusive_lock, _frozen_preflight
from push_wechat_draft import (
    AMBIGUOUS_DRAFT_ADD_ERROR_CODES,
    CONTENT_MAX_BYTES,
    CONTENT_MAX_CHARACTERS,
    LOCAL_SOURCE_PATTERN,
    DraftAdapterError,
    WeChatAPIError,
    WeChatClient,
    _atomic_write_json,
    _canonical_json_hash,
    _file_hash,
    _iso_now,
    _load_json,
    _record_verified_draft,
    _replace_image_sources,
    _upload_content_images,
    _verify_approved_account_identity,
    _verify_account_binding,
    _verify_remote_draft,
)


RECEIPT_STATES = {
    "created_unverified",
    "verified",
    "updated_unverified",
    "update_result_unknown",
}


def _public_result(preflight: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in preflight.items() if not key.startswith("_")}


def build_update_preflight(article_value: Path) -> dict[str, Any]:
    preflight = build_preflight(article_value)
    blockers = preflight.setdefault("blockers", [])
    warnings = preflight.setdefault("warnings", [])
    receipt_path = Path(preflight.get("receipt_path", ""))
    receipt: dict[str, Any] = {}
    if not receipt_path.is_file():
        blockers.append("existing draft receipt is missing")
    else:
        receipt = _load_json(receipt_path)

    plan = preflight.get("plan") if isinstance(preflight.get("plan"), dict) else {}
    draft_id = receipt.get("draft_id")
    if receipt:
        if receipt.get("article_id") != plan.get("article_id"):
            blockers.append("existing draft receipt belongs to another article")
        if receipt.get("target_account") != plan.get("target_account"):
            blockers.append("existing draft receipt target account does not match")
        if not isinstance(draft_id, str) or not draft_id:
            blockers.append("existing draft receipt has no draft ID")
        if receipt.get("status") not in RECEIPT_STATES:
            blockers.append(f"existing draft receipt state cannot be updated: {receipt.get('status')}")
        if receipt.get("package_hash") == plan.get("package_hash"):
            warnings.append("existing draft receipt already uses the current package hash")

    preflight["ok"] = not blockers
    preflight["validation"] = {
        **(preflight.get("validation") or {}),
        "ok": not blockers,
        "operation": "update_existing_draft",
    }
    preflight["update_existing_draft"] = {
        "draft_id": draft_id,
        "previous_content_hash": receipt.get("content_hash"),
        "previous_package_hash": receipt.get("package_hash"),
        "current_content_hash": plan.get("content_hash"),
        "current_package_hash": plan.get("package_hash"),
        "creates_new_draft": False,
    }
    preflight["_receipt"] = receipt
    return preflight


def _remote_item(response: dict[str, Any]) -> dict[str, Any]:
    items = response.get("news_item")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise DraftAdapterError("draft/get response did not contain news_item")
    return items[0]


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or update an existing Markdown-native WeChat draft")
    parser.add_argument("article", type=Path)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--approved-hash")
    parser.add_argument("--approved-package-hash")
    parser.add_argument("--target-account")
    parser.add_argument("--target-principal")
    parser.add_argument("--target-app-id-fingerprint")
    parser.add_argument("--draft-id")
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def _confirmed_update(args: argparse.Namespace, preflight: dict[str, Any]) -> int:
    if not preflight.get("ok"):
        raise DraftAdapterError("update preflight has blocking issues; run without --confirm for details")
    if not all((
        args.approved_hash,
        args.approved_package_hash,
        args.target_account,
        args.target_principal,
        args.target_app_id_fingerprint,
        args.draft_id,
    )):
        raise DraftAdapterError(
            "--confirm requires --approved-hash, --approved-package-hash, "
            "--target-account, --target-principal, --target-app-id-fingerprint, "
            "and --draft-id"
        )

    plan = preflight["plan"]
    update_plan = preflight["update_existing_draft"]
    if args.approved_hash != plan["content_hash"]:
        raise DraftAdapterError("--approved-hash does not match article.md")
    if args.approved_package_hash != plan["package_hash"]:
        raise DraftAdapterError("--approved-package-hash does not match the current WeChat package")
    _verify_approved_account_identity(
        plan,
        confirmed_account=args.target_account,
        confirmed_principal=args.target_principal,
        confirmed_app_id_fingerprint=args.target_app_id_fingerprint,
    )
    if args.draft_id != update_plan["draft_id"]:
        raise DraftAdapterError("--draft-id does not match the existing draft receipt")

    app_id = os.environ.get("WECHAT_APP_ID", "")
    app_secret = os.environ.get("WECHAT_APP_SECRET", "")
    configured_account = os.environ.get("WECHAT_TARGET_ACCOUNT", "")
    configured_principal = os.environ.get("WECHAT_TARGET_PRINCIPAL", "")
    if not app_id or not app_secret:
        raise DraftAdapterError("WECHAT_APP_ID and WECHAT_APP_SECRET are required")
    _verify_account_binding(
        plan,
        app_id=app_id,
        configured_account=configured_account,
        configured_principal=configured_principal,
    )

    with _frozen_preflight(preflight) as frozen:
        release_path = Path(preflight["release_path"])
        receipt_path = Path(preflight["receipt_path"])
        release = preflight["_release"]
        previous_receipt = preflight["_receipt"]
        client = WeChatClient(app_id, app_secret, timeout=args.timeout)
        access_token = client.stable_token()

        current_remote = client.get_draft(args.draft_id, access_token)
        current_item = _remote_item(current_remote)
        if current_item.get("title") != previous_receipt.get("title"):
            raise DraftAdapterError("existing draft title does not match its local receipt")

        replacements, uploads = _upload_content_images(
            frozen["_local_images"],
            client=client,
            access_token=access_token,
        )
        content = _replace_image_sources(frozen["_content"], replacements)
        if LOCAL_SOURCE_PATTERN.search(content):
            raise DraftAdapterError("rewritten content still contains a local source")
        if len(content) >= CONTENT_MAX_CHARACTERS or len(content.encode("utf-8")) >= CONTENT_MAX_BYTES:
            raise DraftAdapterError("rewritten content exceeds WeChat content limits")

        approved_cover_path = Path(frozen["_cover_path"])
        cover_media_id = client.upload_cover(approved_cover_path, access_token)
        article = {
            "article_type": "news",
            "title": plan["title"],
            "author": plan["author"],
            "digest": plan["digest"],
            "content": content,
            "content_source_url": plan["content_source_url"],
            "thumb_media_id": cover_media_id,
            "need_open_comment": int(plan["comments"]["enabled"]),
            "only_fans_can_comment": int(plan["comments"]["fans_only"]),
        }

        attempt_id = secrets.token_hex(16)
        started_at = _iso_now()
        release.setdefault("approvals", {})["draft_update"] = {
            "approved_at": started_at,
            "source_hash": plan["content_hash"],
            "wechat_package_hash": plan["package_hash"],
            "target_account_fingerprint": plan["target_account"]["app_id_fingerprint"],
            "draft_id": args.draft_id,
        }
        release["wechat"] = {
            **(release.get("wechat") or {}),
            "status": "submitting",
            "draft_id": args.draft_id,
            "submitted_hash": plan["content_hash"],
            "submitted_package_hash": plan["package_hash"],
            "submitted_content_hash": _canonical_json_hash(article),
            "uploads": uploads,
            "cover": {
                "sha256": _file_hash(approved_cover_path),
                "media_id": cover_media_id,
            },
            "attempt": {
                "id": attempt_id,
                "kind": "update",
                "state": "submitting",
                "approved_hash": plan["content_hash"],
                "approved_package_hash": plan["package_hash"],
                "started_at": started_at,
                "draft_id": args.draft_id,
            },
        }
        pending_receipt = {
            "article_id": plan["article_id"],
            "content_hash": plan["content_hash"],
            "package_hash": plan["package_hash"],
            "previous_package_hash": previous_receipt.get("package_hash"),
            "target_account": plan["target_account"],
            "account_app_id_fingerprint": plan["target_account"]["app_id_fingerprint"],
            "title": plan["title"],
            "draft_id": args.draft_id,
            "status": "update_submitting",
            "previous_receipt": previous_receipt,
            "previous_remote_snapshot_hash": _canonical_json_hash(current_item),
            "created_at": previous_receipt.get("created_at") or started_at,
            "updated_at": started_at,
            "verified_at": None,
            "content_images": replacements,
            "cover_media_id": cover_media_id,
            "external_links_before_save": plan["external_links"],
            "topics": plan.get("topics", []),
            "native_topics_applied": False,
            "verification": None,
        }
        _atomic_write_json(release_path, release)
        _atomic_write_json(receipt_path, pending_receipt)

        try:
            client.update_draft(args.draft_id, article, access_token)
        except WeChatAPIError as error:
            if error.errcode not in AMBIGUOUS_DRAFT_ADD_ERROR_CODES:
                release["wechat"]["status"] = "draft_created_unverified"
                release["wechat"]["attempt"]["state"] = "update_rejected"
                release["last_error"] = {
                    "step": "draft_update",
                    "errcode": error.errcode,
                    "errmsg": error.errmsg[:240],
                    "retryable": False,
                    "outcome": "not_updated",
                    "attempt_id": attempt_id,
                    "at": _iso_now(),
                }
                _atomic_write_json(release_path, release)
                _atomic_write_json(receipt_path, previous_receipt)
                raise
            release["wechat"]["status"] = "remote_result_unknown"
            release["wechat"]["attempt"]["state"] = "update_result_unknown"
            pending_receipt["status"] = "update_result_unknown"
            _atomic_write_json(release_path, release)
            _atomic_write_json(receipt_path, pending_receipt)
            raise DraftAdapterError(
                "draft/update result is unknown; read back the same draft before any retry"
            ) from error
        except Exception as error:
            release["wechat"]["status"] = "remote_result_unknown"
            release["wechat"]["attempt"]["state"] = "update_result_unknown"
            pending_receipt["status"] = "update_result_unknown"
            _atomic_write_json(release_path, release)
            _atomic_write_json(receipt_path, pending_receipt)
            raise DraftAdapterError(
                "draft/update result is unknown; read back the same draft before any retry"
            ) from error

        release["wechat"]["attempt"]["state"] = "updated"
        pending_receipt["status"] = "updated_unverified"
        _atomic_write_json(release_path, release)
        _atomic_write_json(receipt_path, pending_receipt)

        try:
            remote = client.get_draft(args.draft_id, access_token)
            verification = _verify_remote_draft(
                remote,
                title=plan["title"],
                author=plan["author"],
                digest=plan["digest"],
                cover_media_id=cover_media_id,
                comments_enabled=plan["comments"]["enabled"],
                comments_fans_only=plan["comments"]["fans_only"],
                uploaded_urls=list(replacements.values()),
                expected_content=content,
                content_source_url=plan["content_source_url"],
            )
        except Exception as error:
            release["wechat"]["status"] = "draft_created_unverified"
            release["wechat"]["attempt"]["state"] = "verification_failed"
            release["last_error"] = {
                "step": "draft_get",
                "errcode": getattr(error, "errcode", None),
                "errmsg": str(error)[:240] or "updated draft verification failed",
                "retryable": True,
                "outcome": "updated_unverified",
                "attempt_id": attempt_id,
                "at": _iso_now(),
            }
            _atomic_write_json(release_path, release)
            raise DraftAdapterError(
                f"draft {args.draft_id} was updated but verification failed; do not create a duplicate"
            ) from error

        result = _record_verified_draft(
            release=release,
            release_path=release_path,
            receipt_path=receipt_path,
            plan=plan,
            draft_id=args.draft_id,
            verification=verification,
            content_images=replacements,
            cover_media_id=cover_media_id,
            created_at=pending_receipt["created_at"],
            remote_write=True,
        )
        result["updated_existing_draft"] = True
        result["created_new_draft"] = False
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        if not args.confirm:
            result = _public_result(build_update_preflight(args.article))
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0 if result["ok"] else 1
        article_dir = args.article.resolve()
        if article_dir.is_file():
            article_dir = article_dir.parent
        with _exclusive_lock(article_dir / ".frontier-build" / "wechat-draft.lock"):
            return _confirmed_update(args, build_update_preflight(args.article))
    except DraftAdapterError as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
