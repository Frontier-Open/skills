#!/usr/bin/env python3
"""Save a rendered Markdown-native Frontier Signals article to WeChat drafts.

The canonical content is article.md. The command is a zero-write, zero-network
dry-run unless --confirm is present with the exact source/package hashes and
target account returned by the dry-run.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from push_wechat_draft import (
    AUTHOR_MAX_CHARACTERS,
    CONTENT_MAX_BYTES,
    CONTENT_MAX_CHARACTERS,
    DIGEST_MAX_CHARACTERS,
    PUSHABLE_RELEASE_STATES,
    RECOVERABLE_RELEASE_STATES,
    TITLE_MAX_CHARACTERS,
    DraftAdapterError,
    WeChatClient,
    _article_directory,
    _atomic_write_json,
    _collect_links,
    _external_links,
    _extract_body,
    _file_hash,
    _load_json,
    _package_hash,
    _public_result,
    _safe_local_path,
    _verify_approved_account_identity,
    _verify_account_binding,
    _validate_image_file,
    push_draft,
)


MARKDOWN_PUSHABLE_STATES = {"local_rendered", "owner_approved"}


def _source_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown_article_directory(value: Path) -> Path:
    path = value.expanduser().resolve()
    if path.is_file() and path.name == "article.md":
        return path.parent
    return _article_directory(path)


@contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise DraftAdapterError("another WeChat draft operation is already running") from error
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _frozen_preflight(preflight: dict[str, Any]):
    """Freeze approved source and media bytes for the complete remote operation."""
    with tempfile.TemporaryDirectory(prefix="frontier-wechat-approved-") as temporary:
        snapshot_root = Path(temporary)
        article_snapshot = snapshot_root / "article.md"
        article_snapshot.write_bytes(Path(preflight["article_path"]).read_bytes())
        frozen_images: dict[str, Path] = {}
        for source, original in preflight["_local_images"].items():
            destination = snapshot_root / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(Path(original).read_bytes())
            frozen_images[source] = destination
        cover_snapshot = snapshot_root / "wechat-cover.png"
        cover_snapshot.write_bytes(Path(preflight["plan"]["cover"]).read_bytes())
        snapshot_source_hash = _source_hash(article_snapshot)
        snapshot_package_hash = _package_hash(
            signal_hash=snapshot_source_hash,
            content=preflight["_content"],
            local_images=frozen_images,
            cover_path=cover_snapshot,
        )
        if snapshot_source_hash != preflight["plan"]["content_hash"]:
            raise DraftAdapterError("article.md changed while freezing the approved package")
        if snapshot_package_hash != preflight["plan"]["package_hash"]:
            raise DraftAdapterError("media changed while freezing the approved package")
        frozen = dict(preflight)
        frozen["_local_images"] = frozen_images
        frozen["_cover_path"] = cover_snapshot
        yield frozen


def build_preflight(article_value: Path) -> dict[str, Any]:
    article_dir = _markdown_article_directory(article_value)
    article_path = article_dir / "article.md"
    release_path = article_dir / "release.json"
    build_dir = article_dir / ".frontier-build"
    manifest_path = build_dir / "channel-manifest.json"
    html_path = build_dir / "wechat.html"
    blockers: list[str] = []
    warnings: list[str] = []

    for required in (article_path, article_dir / "source-notes.md", release_path, manifest_path, html_path):
        if not required.is_file():
            blockers.append(f"missing required file: {required.relative_to(article_dir)}")
    if blockers:
        return {
            "ok": False,
            "dry_run": True,
            "article_dir": str(article_dir),
            "blockers": blockers,
            "warnings": warnings,
        }

    manifest = _load_json(manifest_path)
    release = _load_json(release_path)
    actual_hash = _source_hash(article_path)
    if manifest.get("renderer") != "frontier-signals-markdown-v2":
        blockers.append("channel manifest was not created by the Markdown v2 renderer")
    if manifest.get("source_hash") != actual_hash:
        blockers.append("channel manifest source_hash does not match article.md")
    if release.get("schema_version") != 2:
        blockers.append("release.json must use schema_version 2")
    if release.get("article_id") != manifest.get("article_id"):
        blockers.append("release.json article_id does not match the rendered article")
    if release.get("canonical", {}).get("source_hash") != actual_hash:
        blockers.append("release.json canonical.source_hash does not match article.md")

    target_account = release.get("target_account")
    if not isinstance(target_account, dict):
        blockers.append("release.json target_account must be an account identity object")
        target_account = {}
    account_name = target_account.get("name")
    account_principal = target_account.get("principal")
    account_fingerprint = target_account.get("app_id_fingerprint")
    if not isinstance(account_name, str) or not account_name.strip():
        blockers.append("release.json target_account.name is not set")
    if not isinstance(account_principal, str) or not account_principal.strip():
        blockers.append("release.json target_account.principal is not set")
    if not isinstance(account_fingerprint, str) or not account_fingerprint.startswith("sha256:"):
        blockers.append("release.json target_account.app_id_fingerprint is not set")

    wechat_release = release.get("wechat")
    if not isinstance(wechat_release, dict):
        blockers.append("release.json wechat must be an object")
        wechat_release = {}
    release_state = wechat_release.get("status")
    if release_state in {"review_confirmed", "published_manual"}:
        blockers.append(f"wechat release state is immutable after owner review: {release_state}")
    elif release_state in RECOVERABLE_RELEASE_STATES or release_state == "remote_draft":
        warnings.append(f"existing WeChat state will be reconciled instead of creating a new draft: {release_state}")
    elif release_state == "failed" and isinstance(release.get("last_error"), dict) and release["last_error"].get("outcome") == "not_created":
        warnings.append("previous WeChat request was explicitly rejected before draft creation; a same-hash retry is allowed")
    elif release_state not in MARKDOWN_PUSHABLE_STATES | PUSHABLE_RELEASE_STATES:
        blockers.append(f"wechat release state cannot be pushed: {release_state}")

    title = manifest.get("title")
    author = manifest.get("author")
    digest = manifest.get("digest")
    content_source_url = manifest.get("content_source_url")
    topics = manifest.get("topics", [])
    comments = manifest.get("comments")
    if not isinstance(title, str) or not title.strip():
        blockers.append("rendered title is missing")
        title = ""
    elif len(title) > TITLE_MAX_CHARACTERS:
        blockers.append(f"title exceeds WeChat limit: {len(title)}/{TITLE_MAX_CHARACTERS} characters")
    if not isinstance(author, str):
        blockers.append("rendered author must be a string")
        author = ""
    elif len(author) > AUTHOR_MAX_CHARACTERS:
        blockers.append(f"author exceeds WeChat limit: {len(author)}/{AUTHOR_MAX_CHARACTERS} characters")
    if not isinstance(digest, str):
        blockers.append("rendered digest must be a string")
        digest = ""
    elif len(digest) > DIGEST_MAX_CHARACTERS:
        blockers.append(f"digest exceeds WeChat limit: {len(digest)}/{DIGEST_MAX_CHARACTERS} characters")
    if not isinstance(content_source_url, str):
        blockers.append("rendered content_source_url must be a string")
        content_source_url = ""
    elif content_source_url:
        parsed = urlsplit(content_source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            blockers.append("rendered content_source_url must be an absolute HTTP(S) URL")
        elif len(content_source_url.encode("utf-8")) >= 1024:
            blockers.append("rendered content_source_url exceeds 1KB")
    if not isinstance(topics, list) or any(not isinstance(topic, str) or not topic.strip() for topic in topics):
        blockers.append("rendered topics must be an array of non-empty strings")
        topics = []
    elif not 1 <= len(topics) <= 3:
        blockers.append("rendered topics must contain one to three items")
    if not isinstance(comments, dict):
        blockers.append("rendered comments must be an object")
        comments = {}
    comments_enabled = comments.get("enabled")
    comments_fans_only = comments.get("fans_only")
    if not isinstance(comments_enabled, bool) or not isinstance(comments_fans_only, bool):
        blockers.append("rendered WeChat comment settings must be booleans")
        comments_enabled = False
        comments_fans_only = False
    if comments_fans_only and not comments_enabled:
        blockers.append("fans_only comments require comments.enabled=true")

    html = html_path.read_text(encoding="utf-8")
    try:
        content = _extract_body(html)
    except DraftAdapterError as error:
        blockers.append(str(error))
        content = ""
    collector = _collect_links(content) if content else None
    if collector and collector.forbidden_tags:
        blockers.append(f"forbidden HTML tags found: {', '.join(sorted(collector.forbidden_tags))}")
    if collector and not collector.image_sources:
        blockers.append("wechat.html contains no images")
    if collector and any(not alt.strip() for alt in collector.image_alts):
        blockers.append("wechat.html body images must have non-empty alt text")
    if collector and len(set(collector.image_alts)) != len(collector.image_alts):
        blockers.append("wechat.html body image alt text must be unique")

    registered_images = manifest.get("content_images")
    if not isinstance(registered_images, list) or any(not isinstance(path, str) for path in registered_images):
        blockers.append("channel manifest content_images must be an array of paths")
        registered_images = []
    local_images: dict[str, Path] = {}
    if collector:
        body_sources = list(dict.fromkeys(collector.image_sources))
        if set(body_sources) != set(registered_images):
            blockers.append("wechat.html body images do not match channel manifest content_images")
        for source in body_sources:
            try:
                local_path = _safe_local_path(article_dir, source)
                if local_path is None:
                    blockers.append(f"external body images are not accepted by the draft adapter: {source}")
                    continue
                _validate_image_file(local_path)
                local_images[source] = local_path
            except DraftAdapterError as error:
                blockers.append(str(error))

    if manifest.get("cover") != "wechat-cover.png":
        blockers.append("channel manifest cover must be wechat-cover.png")
    cover_path = article_dir / "wechat-cover.png"
    cover_is_valid = True
    try:
        _validate_image_file(cover_path, cover=True)
    except DraftAdapterError as error:
        blockers.append(str(error))
        cover_is_valid = False

    package_hash: str | None = None
    if content and cover_is_valid and len(local_images) == len(set(registered_images)):
        package_hash = _package_hash(
            signal_hash=actual_hash,
            content=content,
            local_images=local_images,
            cover_path=cover_path,
        )
        if manifest.get("wechat_package_hash") != package_hash:
            blockers.append("channel manifest package hash does not match article.md, HTML, and media")
        if release.get("renders", {}).get("wechat_package_hash") != package_hash:
            blockers.append("release.json WeChat package hash does not match the approved local package")

    if len(content) >= CONTENT_MAX_CHARACTERS:
        blockers.append(f"HTML content exceeds character limit: {len(content)}/{CONTENT_MAX_CHARACTERS}")
    content_bytes = len(content.encode("utf-8"))
    if content_bytes >= CONTENT_MAX_BYTES:
        blockers.append(f"HTML content exceeds byte limit: {content_bytes}/{CONTENT_MAX_BYTES}")
    external_links = _external_links(collector.links) if collector else []
    if external_links:
        warnings.append(f"{len(external_links)} external links may be filtered by WeChat and require draft verification")
    if topics:
        warnings.append(
            "native WeChat topics are not supported by draft/add; add them manually before publishing: "
            + ", ".join(topics)
        )

    plan = {
        "article_id": release.get("article_id"),
        "content_hash": actual_hash,
        "package_hash": package_hash,
        "target_account": {
            "name": account_name,
            "principal": account_principal,
            "app_id_fingerprint": account_fingerprint,
        },
        "title": title,
        "author": author,
        "digest": digest,
        "content_source_url": content_source_url,
        "topics": topics,
        "native_topics_supported_by_api": False,
        "content_characters": len(content),
        "content_bytes": content_bytes,
        "content_image_count": len(local_images),
        "content_images": {source: str(path) for source, path in local_images.items()},
        "cover": str(cover_path),
        "cover_hash": _file_hash(cover_path) if cover_is_valid else None,
        "external_links": external_links,
        "comments": {"enabled": comments_enabled, "fans_only": comments_fans_only},
    }
    return {
        "ok": not blockers,
        "dry_run": True,
        "article_dir": str(article_dir),
        "article_path": str(article_path),
        "release_path": str(release_path),
        "receipt_path": str(article_dir / "wechat-draft-receipt.json"),
        "blockers": blockers,
        "warnings": warnings,
        "validation": {"ok": not blockers, "source": "article.md", "schema": "markdown-v2"},
        "plan": plan,
        "_release": release,
        "_content": content,
        "_local_images": local_images,
    }


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or save a Markdown-native article to WeChat drafts")
    parser.add_argument("article", type=Path, help="article directory or article.md")
    parser.add_argument("--confirm", action="store_true", help="perform the remote draft write")
    parser.add_argument("--approved-hash", help="exact article.md sha256 from dry-run")
    parser.add_argument("--approved-package-hash", help="exact WeChat package sha256 from dry-run")
    parser.add_argument("--target-account", help="exact target account from dry-run")
    parser.add_argument("--target-principal", help="exact account principal from dry-run")
    parser.add_argument(
        "--target-app-id-fingerprint",
        help="exact AppID fingerprint from dry-run",
    )
    parser.add_argument(
        "--reconcile-unknown-only",
        action="store_true",
        help="read-only discovery for an unknown draft/add result with no draft ID",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def _confirmed_push(args: argparse.Namespace, preflight: dict[str, Any]) -> int:
    if not preflight.get("ok"):
        raise DraftAdapterError("preflight has blocking issues; run without --confirm for details")
    if not all((
        args.approved_hash,
        args.approved_package_hash,
        args.target_account,
        args.target_principal,
        args.target_app_id_fingerprint,
    )):
        raise DraftAdapterError(
            "--confirm requires --approved-hash, --approved-package-hash, "
            "--target-account, --target-principal, and --target-app-id-fingerprint"
        )
    plan = preflight["plan"]
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
    if args.reconcile_unknown_only:
        release_wechat = preflight.get("_release", {}).get("wechat", {})
        if not isinstance(release_wechat, dict):
            raise DraftAdapterError("reconcile-only authorization requires WeChat release state")
        if release_wechat.get("status") not in {"submitting", "remote_result_unknown"}:
            raise DraftAdapterError("reconcile-only authorization requires an unknown draft/add result")
        if release_wechat.get("draft_id"):
            raise DraftAdapterError("reconcile-only authorization expected no recorded draft ID")
        if not release_wechat.get("uploads") or not isinstance(release_wechat.get("cover"), dict) \
                or not release_wechat["cover"].get("media_id"):
            raise DraftAdapterError(
                "unknown remote result lacks upload records; inspect the draft box manually"
            )

    app_id = os.environ.get("WECHAT_APP_ID", "")
    app_secret = os.environ.get("WECHAT_APP_SECRET", "")
    configured_account = os.environ.get("WECHAT_TARGET_ACCOUNT", "")
    configured_principal = os.environ.get("WECHAT_TARGET_PRINCIPAL", "")
    if not app_id or not app_secret:
        raise DraftAdapterError("WECHAT_APP_ID and WECHAT_APP_SECRET are required")
    if not configured_account or not configured_principal:
        raise DraftAdapterError("WECHAT_TARGET_ACCOUNT and WECHAT_TARGET_PRINCIPAL are required")
    _verify_account_binding(
        plan,
        app_id=app_id,
        configured_account=configured_account,
        configured_principal=configured_principal,
    )

    with _frozen_preflight(preflight) as frozen:
        release = preflight["_release"]
        release.setdefault("approvals", {})["draft_upload"] = {
            "approved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_hash": plan["content_hash"],
            "wechat_package_hash": plan["package_hash"],
            "target_account_fingerprint": plan["target_account"]["app_id_fingerprint"],
        }
        _atomic_write_json(Path(preflight["release_path"]), release)
        client = WeChatClient(app_id, app_secret, timeout=args.timeout)
        result = push_draft(
            frozen,
            confirmed_hash=args.approved_hash,
            confirmed_package_hash=args.approved_package_hash,
            confirmed_account=args.target_account,
            client=client,
            reconcile_unknown_only=args.reconcile_unknown_only,
        )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        preflight = build_preflight(args.article)
        if not args.confirm:
            result = _public_result(preflight)
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0 if result["ok"] else 1
        article_dir = _markdown_article_directory(args.article)
        with _exclusive_lock(article_dir / ".frontier-build" / "wechat-draft.lock"):
            locked_preflight = build_preflight(args.article)
            return _confirmed_push(args, locked_preflight)
    except DraftAdapterError as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
