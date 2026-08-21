#!/usr/bin/env python3
"""Read back and verify one existing Markdown-native WeChat draft.

Dry-run is local-only. --confirm performs stable_token + draft/get, then
updates only the local receipt and release state. It never uploads or writes
the remote draft.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from push_markdown_draft import build_preflight, _exclusive_lock
from push_wechat_draft import (
    DraftAdapterError,
    WeChatClient,
    _atomic_write_json,
    _canonical_json_hash,
    _iso_now,
    _load_json,
    _record_verified_draft,
    _replace_image_sources,
    _verify_approved_account_identity,
    _verify_account_binding,
    _verify_remote_draft,
)


RECONCILABLE_STATES = {
    "created_unverified",
    "update_submitting",
    "updated_unverified",
    "update_result_unknown",
    "verified",
}


def _public_result(preflight: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in preflight.items() if not key.startswith("_")}


def _remote_item(response: dict[str, Any]) -> dict[str, Any]:
    items = response.get("news_item")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise DraftAdapterError("draft/get response did not contain news_item")
    return items[0]


def _matches_pre_update_snapshot(receipt: dict[str, Any], remote: dict[str, Any]) -> bool:
    expected = receipt.get("previous_remote_snapshot_hash")
    return (
        receipt.get("status") == "update_submitting"
        and isinstance(expected, str)
        and expected == _canonical_json_hash(_remote_item(remote))
        and isinstance(receipt.get("previous_receipt"), dict)
    )


def build_reconcile_preflight(article_value: Path) -> dict[str, Any]:
    preflight = build_preflight(article_value)
    blockers = preflight.setdefault("blockers", [])
    receipt_path = Path(preflight.get("receipt_path", ""))
    receipt: dict[str, Any] = {}
    if not receipt_path.is_file():
        blockers.append("existing draft receipt is missing")
    else:
        receipt = _load_json(receipt_path)

    plan = preflight.get("plan") if isinstance(preflight.get("plan"), dict) else {}
    if receipt:
        if receipt.get("article_id") != plan.get("article_id"):
            blockers.append("existing draft receipt belongs to another article")
        if receipt.get("target_account") != plan.get("target_account"):
            blockers.append("existing draft receipt target account does not match")
        if receipt.get("content_hash") != plan.get("content_hash"):
            blockers.append("existing draft receipt content hash does not match")
        if receipt.get("package_hash") != plan.get("package_hash"):
            blockers.append("existing draft receipt package hash does not match")
        if not isinstance(receipt.get("draft_id"), str) or not receipt["draft_id"]:
            blockers.append("existing draft receipt has no draft ID")
        if receipt.get("status") not in RECONCILABLE_STATES:
            blockers.append(
                f"existing draft receipt state cannot be reconciled: {receipt.get('status')}"
            )
        images = receipt.get("content_images")
        if not isinstance(images, dict) or len(images) != plan.get("content_image_count"):
            blockers.append("existing draft receipt content images do not match the package")
        if not isinstance(receipt.get("cover_media_id"), str) or not receipt["cover_media_id"]:
            blockers.append("existing draft receipt has no cover media ID")

    preflight["ok"] = not blockers
    preflight["validation"] = {
        **(preflight.get("validation") or {}),
        "ok": not blockers,
        "operation": "reconcile_existing_draft",
    }
    preflight["reconcile_existing_draft"] = {
        "draft_id": receipt.get("draft_id"),
        "content_hash": plan.get("content_hash"),
        "package_hash": plan.get("package_hash"),
        "remote_write": False,
    }
    preflight["_receipt"] = receipt
    return preflight


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or reconcile an existing WeChat draft")
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


def _confirmed_reconcile(args: argparse.Namespace, preflight: dict[str, Any]) -> int:
    if not preflight.get("ok"):
        raise DraftAdapterError("reconcile preflight has blocking issues")
    plan = preflight["plan"]
    reconcile = preflight["reconcile_existing_draft"]
    required = (
        args.approved_hash,
        args.approved_package_hash,
        args.target_account,
        args.target_principal,
        args.target_app_id_fingerprint,
        args.draft_id,
    )
    if not all(required):
        raise DraftAdapterError(
            "--confirm requires --approved-hash, --approved-package-hash, "
            "--target-account, --target-principal, --target-app-id-fingerprint, "
            "and --draft-id"
        )
    if args.approved_hash != plan["content_hash"]:
        raise DraftAdapterError("--approved-hash does not match article.md")
    if args.approved_package_hash != plan["package_hash"]:
        raise DraftAdapterError("--approved-package-hash does not match the current package")
    _verify_approved_account_identity(
        plan,
        confirmed_account=args.target_account,
        confirmed_principal=args.target_principal,
        confirmed_app_id_fingerprint=args.target_app_id_fingerprint,
    )
    if args.draft_id != reconcile["draft_id"]:
        raise DraftAdapterError("--draft-id does not match the existing receipt")

    app_id = os.environ.get("WECHAT_APP_ID", "")
    app_secret = os.environ.get("WECHAT_APP_SECRET", "")
    _verify_account_binding(
        plan,
        app_id=app_id,
        configured_account=os.environ.get("WECHAT_TARGET_ACCOUNT", ""),
        configured_principal=os.environ.get("WECHAT_TARGET_PRINCIPAL", ""),
    )

    receipt = preflight["_receipt"]
    client = WeChatClient(app_id, app_secret, timeout=args.timeout)
    access_token = client.stable_token()
    remote = client.get_draft(args.draft_id, access_token)
    expected_content = _replace_image_sources(
        preflight["_content"],
        receipt["content_images"],
    )
    try:
        verification = _verify_remote_draft(
            remote,
            title=plan["title"],
            author=plan["author"],
            digest=plan["digest"],
            cover_media_id=receipt["cover_media_id"],
            comments_enabled=plan["comments"]["enabled"],
            comments_fans_only=plan["comments"]["fans_only"],
            uploaded_urls=list(receipt["content_images"].values()),
            expected_content=expected_content,
            content_source_url=plan["content_source_url"],
        )
    except DraftAdapterError:
        if not _matches_pre_update_snapshot(receipt, remote):
            raise
        previous_receipt = receipt["previous_receipt"]
        release = preflight["_release"]
        release["wechat"] = {
            "status": "local_rendered",
            "draft_id": None,
            "verified_at": None,
            "public": (release.get("wechat") or {}).get("public")
            or {"status": "not_recorded", "url": None, "published_at": None},
        }
        release["last_error"] = {
            "step": "draft_update_reconcile",
            "errmsg": "interrupted update did not change the remote draft",
            "retryable": True,
            "outcome": "not_updated",
            "at": _iso_now(),
        }
        _atomic_write_json(Path(preflight["release_path"]), release)
        _atomic_write_json(Path(preflight["receipt_path"]), previous_receipt)
        result = {
            "ok": True,
            "remote_write": False,
            "reconciled_existing_draft": True,
            "update_applied": False,
            "restored_previous_receipt": True,
            "draft_id": args.draft_id,
            "release": preflight["release_path"],
            "receipt": preflight["receipt_path"],
        }
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    result = _record_verified_draft(
        release=preflight["_release"],
        release_path=Path(preflight["release_path"]),
        receipt_path=Path(preflight["receipt_path"]),
        plan=plan,
        draft_id=args.draft_id,
        verification=verification,
        content_images=receipt["content_images"],
        cover_media_id=receipt["cover_media_id"],
        created_at=receipt.get("created_at"),
        remote_write=False,
    )
    result["reconciled_existing_draft"] = True
    result["remote_update_performed"] = False
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        if not args.confirm:
            result = _public_result(build_reconcile_preflight(args.article))
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0 if result["ok"] else 1
        article_dir = args.article.resolve()
        if article_dir.is_file():
            article_dir = article_dir.parent
        with _exclusive_lock(article_dir / ".frontier-build" / "wechat-draft.lock"):
            return _confirmed_reconcile(args, build_reconcile_preflight(args.article))
    except DraftAdapterError as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
