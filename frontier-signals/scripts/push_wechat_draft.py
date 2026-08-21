#!/usr/bin/env python3
"""Save an approved Frontier Signals package to the WeChat draft box.

The command is dry-run by default. A remote write requires --confirm plus an
exact target account and approved content hash. It never publishes or sends.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import secrets
import sys
import struct
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from render_wechat import render_html
from validate_signal import validate_record


TOKEN_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/stable_token"
CONTENT_IMAGE_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
COVER_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/material/add_material"
DRAFT_ADD_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/draft/add"
DRAFT_UPDATE_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/draft/update"
DRAFT_GET_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/draft/get"
DRAFT_BATCHGET_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/draft/batchget"

CONTENT_IMAGE_MAX_BYTES = 1_000_000
COVER_MAX_BYTES = 10_000_000
CONTENT_MAX_CHARACTERS = 20_000
CONTENT_MAX_BYTES = 1_000_000
TITLE_MAX_CHARACTERS = 32
AUTHOR_MAX_CHARACTERS = 16
DIGEST_MAX_CHARACTERS = 120

ALLOWED_CONTENT_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
ALLOWED_COVER_SUFFIXES = {".png"}
PUSHABLE_RELEASE_STATES = {"owner_approved"}
RECOVERABLE_RELEASE_STATES = {
    "submitting",
    "remote_result_unknown",
    "draft_created_unverified",
    "remote_draft",
}
AMBIGUOUS_DRAFT_ADD_ERROR_CODES = {-1, "-1"}

IMG_SRC_PATTERN = re.compile(
    r"(?P<prefix><img\b[^>]*?\bsrc\s*=\s*)(?P<quote>[\"'])(?P<src>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
LOCAL_SOURCE_PATTERN = re.compile(
    r"(?:file:/{1,3}|https?://(?:localhost|127\.0\.0\.1)(?::\d+)?/|"
    r"(?:src|href)=[\"'](?:\.?\.?/|images/|wechat-cover\.))",
    re.IGNORECASE,
)


class DraftAdapterError(RuntimeError):
    """Base error for safe, user-facing adapter failures."""


class WeChatAPIError(DraftAdapterError):
    def __init__(self, endpoint: str, errcode: int | str, errmsg: str) -> None:
        super().__init__(f"{endpoint} failed ({errcode}): {errmsg}")
        self.endpoint = endpoint
        self.errcode = errcode
        self.errmsg = errmsg


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


class _SectionCaptureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.capturing = False
        self.done = False
        self.section_depth = 0
        self.parts: list[str] = []

    @staticmethod
    def _is_target(attrs: list[tuple[str, str | None]]) -> bool:
        return any(name.lower() == "id" and value == "frontier-signals-body" for name, value in attrs)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done:
            return
        if not self.capturing:
            if tag.lower() != "section" or not self._is_target(attrs):
                return
            self.capturing = True
            self.section_depth = 1
            self.parts.append(self.get_starttag_text())
            return
        self.parts.append(self.get_starttag_text())
        if tag.lower() == "section":
            self.section_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.capturing and not self.done:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        if not self.capturing or self.done:
            return
        self.parts.append(f"</{tag}>")
        if tag.lower() == "section":
            self.section_depth -= 1
            if self.section_depth == 0:
                self.done = True
                self.capturing = False

    def handle_data(self, data: str) -> None:
        if self.capturing and not self.done:
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self.capturing and not self.done:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self.capturing and not self.done:
            self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        if self.capturing and not self.done:
            self.parts.append(f"<!--{data}-->")


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.image_sources: list[str] = []
        self.image_alts: list[str] = []
        self.links: list[str] = []
        self.forbidden_tags: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        values = {name.lower(): value for name, value in attrs if value is not None}
        if lowered == "img" and (values.get("data-src") or values.get("src")):
            self.image_sources.append(values.get("data-src") or values["src"])
            self.image_alts.append(values.get("alt", ""))
        elif lowered == "a" and values.get("href"):
            self.links.append(values["href"])
        if lowered in {"iframe", "script", "style"}:
            self.forbidden_tags.add(lowered)


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise DraftAdapterError(f"cannot read {path.name}: {error}") from error
    except json.JSONDecodeError as error:
        raise DraftAdapterError(f"invalid JSON in {path.name}: {error.msg}") from error
    if not isinstance(value, dict):
        raise DraftAdapterError(f"{path.name} must contain a JSON object")
    return value


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _signal_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _app_id_fingerprint(app_id: str) -> str:
    return "sha256:" + hashlib.sha256(app_id.encode("utf-8")).hexdigest()


def _canonical_json_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _package_hash(
    *,
    signal_hash: str,
    content: str,
    local_images: dict[str, Path],
    cover_path: Path,
) -> str:
    manifest = {
        "signal_hash": signal_hash,
        "wechat_body_hash": "sha256:"
        + hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content_images": {
            source: _file_hash(path) for source, path in sorted(local_images.items())
        },
        "cover_hash": _file_hash(cover_path),
    }
    return _canonical_json_hash(manifest)


def _article_directory(value: Path) -> Path:
    path = value.expanduser().resolve()
    if path.is_file() and path.name == "signal.json":
        return path.parent
    return path


def _extract_body(html: str) -> str:
    parser = _SectionCaptureParser()
    parser.feed(html)
    parser.close()
    if not parser.done:
        raise DraftAdapterError("wechat.html is missing a complete #frontier-signals-body section")
    return "".join(parser.parts)


def _collect_links(content: str) -> _LinkCollector:
    parser = _LinkCollector()
    parser.feed(content)
    parser.close()
    return parser


def _normalized_text(content: str) -> str:
    parser = _TextCollector()
    parser.feed(content)
    parser.close()
    text = "".join(parser.parts).replace("\u200b", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _redact(text: str, values: list[str]) -> str:
    output = text
    for value in values:
        if value:
            output = output.replace(value, "[REDACTED]")
    return output


def _safe_local_path(article_dir: Path, source: str) -> Path | None:
    parsed = urlsplit(source)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme == "https":
            return None
        raise DraftAdapterError(f"image source must be a local relative path or HTTPS URL: {source}")
    relative = Path(source)
    if relative.is_absolute() or ".." in relative.parts:
        raise DraftAdapterError(f"unsafe local image path: {source}")
    resolved = (article_dir / relative).resolve()
    try:
        resolved.relative_to(article_dir)
    except ValueError as error:
        raise DraftAdapterError(f"image path escapes article directory: {source}") from error
    return resolved


def _validate_image_file(path: Path, *, cover: bool = False) -> None:
    if not path.is_file():
        raise DraftAdapterError(f"image file does not exist: {path}")
    suffix = path.suffix.lower()
    allowed = ALLOWED_COVER_SUFFIXES if cover else ALLOWED_CONTENT_IMAGE_SUFFIXES
    maximum = COVER_MAX_BYTES if cover else CONTENT_IMAGE_MAX_BYTES
    if suffix not in allowed:
        label = "cover" if cover else "content"
        raise DraftAdapterError(f"unsupported {label} image type: {path.name}")
    size = path.stat().st_size
    if size >= maximum:
        raise DraftAdapterError(f"image exceeds WeChat size limit ({size} bytes): {path.name}")
    signature = path.read_bytes()[:10]
    if suffix == ".png" and not signature.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DraftAdapterError(f"PNG signature does not match extension: {path.name}")
    if suffix in {".jpg", ".jpeg"} and not signature.startswith(b"\xff\xd8\xff"):
        raise DraftAdapterError(f"JPEG signature does not match extension: {path.name}")
    if cover:
        with path.open("rb") as handle:
            header = handle.read(24)
        if len(header) < 24:
            raise DraftAdapterError(f"cover PNG is truncated: {path.name}")
        width, height = struct.unpack(">II", header[16:24])
        if (width, height) != (900, 383):
            raise DraftAdapterError(
                f"cover must be exactly 900x383 pixels, got {width}x{height}: {path.name}"
            )


def _replace_image_sources(content: str, replacements: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        source = match.group("src")
        replacement = replacements.get(source, source)
        return f'{match.group("prefix")}{match.group("quote")}{replacement}{match.group("quote")}'

    return IMG_SRC_PATTERN.sub(replace, content)


def _external_links(links: list[str]) -> list[str]:
    output: list[str] = []
    for link in links:
        parsed = urlsplit(link)
        if parsed.scheme in {"http", "https"} and parsed.netloc not in {"mp.weixin.qq.com", "weixin.qq.com"}:
            output.append(link)
    return list(dict.fromkeys(output))


def _multipart_file(path: Path, field: str = "media") -> tuple[bytes, str]:
    boundary = f"----frontier-signals-{secrets.token_hex(12)}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    body = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


class WeChatClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        opener: Callable[..., Any] | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not app_id or not app_secret:
            raise DraftAdapterError("WECHAT_APP_ID and WECHAT_APP_SECRET are required")
        self.app_id = app_id
        self.app_secret = app_secret
        self.opener = opener or build_opener(_NoRedirect()).open
        self.timeout = timeout

    def _safe_detail(self, detail: str, endpoint: str) -> str:
        query = parse_qs(urlsplit(endpoint).query)
        sensitive = [self.app_secret, *query.get("access_token", [])]
        return _redact(detail, sensitive)

    def _request_json(
        self,
        endpoint: str,
        label: str,
        *,
        payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        content_type: str = "application/json; charset=utf-8",
    ) -> dict[str, Any]:
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={"Content-Type": content_type, "Accept": "application/json"},
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as error:
            try:
                raw = error.read()
            except Exception:
                raw = b""
            detail = "HTTP error"
            try:
                parsed = json.loads(raw.decode("utf-8"))
                detail = str(parsed.get("errmsg") or detail)
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            detail = self._safe_detail(detail, endpoint)
            raise DraftAdapterError(f"{label} failed with HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise DraftAdapterError(f"{label} transport failed; remote state may be uncertain") from error
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DraftAdapterError(f"{label} returned invalid JSON") from error
        if not isinstance(value, dict):
            raise DraftAdapterError(f"{label} returned a non-object response")
        errcode = value.get("errcode")
        if errcode not in (None, 0, "0"):
            detail = self._safe_detail(str(value.get("errmsg") or "unknown error"), endpoint)
            raise WeChatAPIError(label, errcode, detail)
        return value

    @staticmethod
    def _with_token(endpoint: str, access_token: str, **params: str) -> str:
        query = {"access_token": access_token, **params}
        return f"{endpoint}?{urlencode(query)}"

    def stable_token(self) -> str:
        response = self._request_json(
            TOKEN_ENDPOINT,
            "stable_token",
            payload={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
                "force_refresh": False,
            },
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise DraftAdapterError("stable_token response did not include access_token")
        return token

    def upload_content_image(self, path: Path, access_token: str) -> str:
        body, content_type = _multipart_file(path)
        response = self._request_json(
            self._with_token(CONTENT_IMAGE_ENDPOINT, access_token),
            "media/uploadimg",
            body=body,
            content_type=content_type,
        )
        url = response.get("url")
        if not isinstance(url, str):
            raise DraftAdapterError("media/uploadimg response did not include an HTTPS URL")
        parsed = urlsplit(url)
        if parsed.scheme == "http" and parsed.hostname == "mmbiz.qpic.cn":
            url = parsed._replace(scheme="https").geturl()
            parsed = urlsplit(url)
        if parsed.scheme != "https":
            raise DraftAdapterError("media/uploadimg response did not include an HTTPS URL")
        return url

    def upload_cover(self, path: Path, access_token: str) -> str:
        body, content_type = _multipart_file(path)
        response = self._request_json(
            self._with_token(COVER_ENDPOINT, access_token, type="image"),
            "material/add_material",
            body=body,
            content_type=content_type,
        )
        media_id = response.get("media_id")
        if not isinstance(media_id, str) or not media_id:
            raise DraftAdapterError("material/add_material response did not include media_id")
        return media_id

    def add_draft(self, article: dict[str, Any], access_token: str) -> str:
        response = self._request_json(
            self._with_token(DRAFT_ADD_ENDPOINT, access_token),
            "draft/add",
            payload={"articles": [article]},
        )
        media_id = response.get("media_id")
        if not isinstance(media_id, str) or not media_id:
            raise DraftAdapterError("draft/add response did not include media_id")
        return media_id

    def update_draft(
        self,
        media_id: str,
        article: dict[str, Any],
        access_token: str,
        *,
        index: int = 0,
    ) -> None:
        self._request_json(
            self._with_token(DRAFT_UPDATE_ENDPOINT, access_token),
            "draft/update",
            payload={"media_id": media_id, "index": index, "articles": article},
        )

    def get_draft(self, media_id: str, access_token: str) -> dict[str, Any]:
        return self._request_json(
            self._with_token(DRAFT_GET_ENDPOINT, access_token),
            "draft/get",
            payload={"media_id": media_id},
        )

    def batchget_drafts(self, access_token: str) -> dict[str, Any]:
        return self._request_json(
            self._with_token(DRAFT_BATCHGET_ENDPOINT, access_token),
            "draft/batchget",
            payload={"offset": 0, "count": 20, "no_content": 0},
        )


def build_preflight(article_value: Path) -> dict[str, Any]:
    article_dir = _article_directory(article_value)
    signal_path = article_dir / "signal.json"
    release_path = article_dir / "release.json"
    html_path = article_dir / "wechat.html"
    cover_path = article_dir / "wechat-cover.png"
    blockers: list[str] = []
    warnings: list[str] = []

    for required in (signal_path, release_path, html_path, cover_path):
        if not required.is_file():
            blockers.append(f"missing required file: {required.name}")
    if blockers:
        return {
            "ok": False,
            "dry_run": True,
            "article_dir": str(article_dir),
            "blockers": blockers,
            "warnings": warnings,
        }

    signal = _load_json(signal_path)
    release = _load_json(release_path)
    actual_hash = _signal_hash(signal_path)
    validation = validate_record(
        signal,
        strict=True,
        require_media=True,
        media_base=article_dir,
    )
    if not validation["ok"]:
        blockers.append("signal.json failed strict validation")
    if not validation["publication_ready"]:
        blockers.append("signal.json is not owner-approved and publication-ready")

    if release.get("content_hash") != actual_hash:
        blockers.append("release.json content_hash does not match signal.json")
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

    approvals = release.get("approvals")
    if not isinstance(approvals, dict):
        blockers.append("release.json approvals must be an object")
        approvals = {}
    if not approvals.get("editor_reviewed_at"):
        blockers.append("editor review has not been recorded")
    if not approvals.get("owner_approved_at"):
        blockers.append("owner approval has not been recorded")
    if not approvals.get("freshness_checked_at"):
        blockers.append("pre-release freshness check has not been recorded")
    if approvals.get("approved_hash") != actual_hash:
        blockers.append("owner approval is not bound to the current content hash")

    wechat_release = release.get("wechat")
    if not isinstance(wechat_release, dict):
        blockers.append("release.json wechat must be an object")
        wechat_release = {}
    release_state = wechat_release.get("status")
    existing_draft_id = wechat_release.get("draft_id")
    if release_state in RECOVERABLE_RELEASE_STATES:
        warnings.append(f"existing WeChat state will be reconciled instead of creating a new draft: {release_state}")
    elif release_state not in PUSHABLE_RELEASE_STATES:
        blockers.append(f"wechat release state cannot be pushed: {release_state}")

    if signal.get("publication", {}).get("state") != "owner_approved":
        blockers.append("signal.json publication.state must remain owner_approved for a draft push")
    title = signal.get("headlines", {}).get("primary")
    wechat_metadata = signal.get("wechat")
    if not isinstance(wechat_metadata, dict):
        blockers.append("signal.json is missing approved WeChat metadata")
        wechat_metadata = {}
    author = wechat_metadata.get("author")
    digest = wechat_metadata.get("digest")
    content_source_url = wechat_metadata.get("content_source_url")
    topics = wechat_metadata.get("topics", [])
    comments = wechat_metadata.get("comments")
    if not isinstance(title, str) or not title.strip():
        blockers.append("signal.json primary headline is missing")
        title = ""
    elif len(title) > TITLE_MAX_CHARACTERS:
        blockers.append(f"title exceeds WeChat limit: {len(title)}/{TITLE_MAX_CHARACTERS} characters")
    if not isinstance(author, str):
        blockers.append("signal.json wechat.author must be a string")
        author = ""
    elif len(author) > AUTHOR_MAX_CHARACTERS:
        blockers.append(f"author exceeds WeChat limit: {len(author)}/{AUTHOR_MAX_CHARACTERS} characters")
    if not isinstance(digest, str):
        blockers.append("signal.json wechat.digest must be a string")
        digest = ""
    elif len(digest) > DIGEST_MAX_CHARACTERS:
        blockers.append(f"digest exceeds WeChat limit: {len(digest)}/{DIGEST_MAX_CHARACTERS} characters")
    if not isinstance(content_source_url, str):
        blockers.append("signal.json wechat.content_source_url must be a string")
        content_source_url = ""
    elif content_source_url:
        parsed_source = urlsplit(content_source_url)
        if parsed_source.scheme not in {"http", "https"} or not parsed_source.netloc:
            blockers.append("signal.json wechat.content_source_url must be an absolute HTTP(S) URL")
        elif len(content_source_url.encode("utf-8")) >= 1024:
            blockers.append("signal.json wechat.content_source_url exceeds 1KB")
    if not isinstance(topics, list) or any(
        not isinstance(topic, str) or not topic.strip() for topic in topics
    ):
        blockers.append("signal.json wechat.topics must be an array of non-empty strings")
        topics = []
    if not isinstance(comments, dict):
        blockers.append("signal.json wechat.comments must be an object")
        comments = {}
    comments_enabled = comments.get("enabled")
    comments_fans_only = comments.get("fans_only")
    if not isinstance(comments_enabled, bool) or not isinstance(comments_fans_only, bool):
        blockers.append("signal.json WeChat comment settings must be booleans")
        comments_enabled = False
        comments_fans_only = False
    if comments_fans_only and not comments_enabled:
        blockers.append("fans_only comments require comments.enabled=true")

    html = html_path.read_text(encoding="utf-8")
    try:
        disk_content = _extract_body(html)
    except DraftAdapterError as error:
        blockers.append(str(error))
        disk_content = ""
    try:
        rendered_content = _extract_body(render_html(signal))
    except Exception as error:
        blockers.append(f"cannot deterministically render signal.json: {type(error).__name__}")
        rendered_content = ""
    if disk_content and rendered_content and disk_content != rendered_content:
        blockers.append(
            "wechat.html does not match the deterministic render of signal.json; regenerate it"
        )
    content = rendered_content or disk_content
    collector = _collect_links(content) if content else _LinkCollector()
    if collector.forbidden_tags:
        blockers.append(f"forbidden HTML tags found: {', '.join(sorted(collector.forbidden_tags))}")
    if not collector.image_sources:
        blockers.append("wechat.html contains no images")

    local_images: dict[str, Path] = {}
    media_paths = {
        item.get("path")
        for item in signal.get("media", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    for source in dict.fromkeys(collector.image_sources):
        try:
            local_path = _safe_local_path(article_dir, source)
            if local_path is None:
                blockers.append(f"external body images are not accepted by the draft adapter: {source}")
                continue
            if source not in media_paths:
                blockers.append(f"HTML image is not registered in signal.json: {source}")
                continue
            _validate_image_file(local_path)
            local_images[source] = local_path
        except DraftAdapterError as error:
            blockers.append(str(error))

    for item in signal.get("media", []):
        if not isinstance(item, dict) or item.get("role") not in {"cover", "inline"}:
            continue
        path = item.get("path")
        if isinstance(path, str) and path not in collector.image_sources:
            blockers.append(f"registered article image is missing from wechat.html: {path}")

    cover_is_valid = True
    try:
        _validate_image_file(cover_path, cover=True)
    except DraftAdapterError as error:
        blockers.append(str(error))
        cover_is_valid = False

    package_hash: str | None = None
    if (
        content
        and cover_is_valid
        and len(local_images) == len(set(collector.image_sources))
    ):
        package_hash = _package_hash(
            signal_hash=actual_hash,
            content=content,
            local_images=local_images,
            cover_path=cover_path,
        )
        if release.get("package_hash") != package_hash:
            blockers.append("release.json package_hash does not match the approved local package")
        if approvals.get("approved_package_hash") != package_hash:
            blockers.append("owner approval is not bound to the current HTML and media package")

    if len(content) >= CONTENT_MAX_CHARACTERS:
        blockers.append(f"HTML content exceeds character limit: {len(content)}/{CONTENT_MAX_CHARACTERS}")
    content_bytes = len(content.encode("utf-8"))
    if content_bytes >= CONTENT_MAX_BYTES:
        blockers.append(f"HTML content exceeds byte limit: {content_bytes}/{CONTENT_MAX_BYTES}")

    external_links = _external_links(collector.links)
    if external_links:
        warnings.append(
            f"{len(external_links)} external links may be filtered by WeChat and require draft verification"
        )
    if not digest:
        warnings.append("digest is empty; WeChat may derive it from the article body")
    if not author:
        warnings.append("author is empty; WeChat will show no explicit byline")
    if topics:
        warnings.append(
            "native WeChat topics are not supported by the official draft/add API; "
            "add them manually in the WeChat editor before publishing: "
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
        "title_characters": len(title),
        "author": author,
        "author_characters": len(author),
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
        "comments": {
            "enabled": comments_enabled,
            "fans_only": comments_fans_only,
        },
    }
    return {
        "ok": not blockers,
        "dry_run": True,
        "article_dir": str(article_dir),
        "signal_path": str(signal_path),
        "release_path": str(release_path),
        "receipt_path": str(article_dir / "wechat-draft-receipt.json"),
        "blockers": blockers,
        "warnings": warnings,
        "validation": validation,
        "plan": plan,
        "_signal": signal,
        "_release": release,
        "_content": content,
        "_local_images": local_images,
    }


def _public_result(preflight: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in preflight.items() if not key.startswith("_")}


def _verify_remote_draft(
    response: dict[str, Any],
    *,
    title: str,
    author: str,
    digest: str,
    cover_media_id: str,
    comments_enabled: bool,
    comments_fans_only: bool,
    uploaded_urls: list[str],
    expected_content: str,
    content_source_url: str,
) -> dict[str, Any]:
    items = response.get("news_item")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise DraftAdapterError("draft/get response did not contain news_item")
    item = items[0]
    if item.get("title") != title:
        raise DraftAdapterError("draft/get title does not match approved article")
    if author and item.get("author") != author:
        raise DraftAdapterError("draft/get author does not match approved article")
    if digest and item.get("digest") != digest:
        raise DraftAdapterError("draft/get digest does not match approved article")
    if cover_media_id and item.get("thumb_media_id") != cover_media_id:
        raise DraftAdapterError("draft/get cover media ID does not match uploaded cover")
    if item.get("need_open_comment") not in (None, int(comments_enabled)):
        raise DraftAdapterError("draft/get comment setting does not match approved article")
    if item.get("only_fans_can_comment") not in (None, int(comments_fans_only)):
        raise DraftAdapterError("draft/get fan-only comment setting does not match approved article")
    content = item.get("content")
    if not isinstance(content, str) or not content:
        raise DraftAdapterError("draft/get returned empty content")
    if LOCAL_SOURCE_PATTERN.search(content):
        raise DraftAdapterError("draft/get still contains a local image or link source")
    def image_identity(url: str) -> tuple[str, str]:
        parsed = urlsplit(url)
        official_hosts = {"mmbiz.qpic.cn", "sz_mmbiz.qpic.cn"}
        path = parsed.path.rsplit("/", 1)[0] if parsed.hostname in official_hosts else parsed.path
        return parsed.hostname or "", path

    collector = _collect_links(content)
    expected_collector = _collect_links(expected_content)
    remote_identities = {image_identity(url) for url in collector.image_sources}
    missing_urls = [
        url for url in uploaded_urls
        if url not in content and image_identity(url) not in remote_identities
    ]
    if missing_urls:
        official_hosts = {"mmbiz.qpic.cn", "sz_mmbiz.qpic.cn"}
        rehosted_by_wechat = (
            len(collector.image_sources) == len(expected_collector.image_sources)
            and all(alt.strip() for alt in expected_collector.image_alts)
            and len(set(expected_collector.image_alts)) == len(expected_collector.image_alts)
            and collector.image_alts == expected_collector.image_alts
            and all(
                urlsplit(url).scheme == "https"
                and urlsplit(url).hostname in official_hosts
                for url in collector.image_sources
            )
        )
        if not rehosted_by_wechat:
            raise DraftAdapterError("draft/get is missing one or more uploaded content images")
    expected_text = _normalized_text(expected_content)
    remote_text = _normalized_text(content)
    if remote_text != expected_text:
        raise DraftAdapterError("draft/get body text does not match approved article")
    expected_image_count = len(expected_collector.image_sources)
    if len(collector.image_sources) != expected_image_count:
        raise DraftAdapterError("draft/get content image count does not match approved article")
    if content_source_url and item.get("content_source_url") != content_source_url:
        raise DraftAdapterError("draft/get source URL does not match approved article")
    return {
        "title": item.get("title"),
        "author": item.get("author"),
        "digest": item.get("digest"),
        "thumb_media_id": item.get("thumb_media_id"),
        "content_image_count": len(collector.image_sources),
        "content_text_hash": "sha256:"
        + hashlib.sha256(remote_text.encode("utf-8")).hexdigest(),
        "content_source_url": item.get("content_source_url"),
        "external_links": _external_links(collector.links),
    }


def _verify_account_binding(
    plan: dict[str, Any],
    *,
    app_id: str,
    configured_account: str,
    configured_principal: str,
) -> None:
    target = plan["target_account"]
    if target["name"] != configured_account:
        raise DraftAdapterError("WECHAT_TARGET_ACCOUNT does not match release.json")
    if target["principal"] != configured_principal:
        raise DraftAdapterError("WECHAT_TARGET_PRINCIPAL does not match release.json")
    if target["app_id_fingerprint"] != _app_id_fingerprint(app_id):
        raise DraftAdapterError("WECHAT_APP_ID does not match the approved account fingerprint")


def _verify_approved_account_identity(
    plan: dict[str, Any],
    *,
    confirmed_account: str,
    confirmed_principal: str,
    confirmed_app_id_fingerprint: str,
) -> None:
    """Bind one confirmation to the complete dry-run account identity."""
    target = plan["target_account"]
    if confirmed_account != target["name"]:
        raise DraftAdapterError("--target-account does not match release.json")
    if confirmed_principal != target["principal"]:
        raise DraftAdapterError("--target-principal does not match release.json")
    if confirmed_app_id_fingerprint != target["app_id_fingerprint"]:
        raise DraftAdapterError(
            "--target-app-id-fingerprint does not match release.json"
        )


def _batch_candidates(
    response: dict[str, Any],
    *,
    title: str,
    author: str,
    uploaded_urls: list[str],
    expected_content: str,
) -> list[str]:
    items = response.get("item")
    if not isinstance(items, list):
        raise DraftAdapterError("draft/batchget response did not contain item")
    matches: list[str] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        media_id = entry.get("media_id")
        content = entry.get("content")
        news_items = content.get("news_item") if isinstance(content, dict) else None
        if not isinstance(media_id, str) or not isinstance(news_items, list) or not news_items:
            continue
        first = news_items[0]
        if not isinstance(first, dict) or first.get("title") != title:
            continue
        if author and first.get("author") != author:
            continue
        html = first.get("content")
        if not isinstance(html, str) or any(url not in html for url in uploaded_urls):
            continue
        if _normalized_text(html) != _normalized_text(expected_content):
            continue
        matches.append(media_id)
    return matches


def _recorded_content_images(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    images: dict[str, str] = {}
    for upload in value.values():
        if not isinstance(upload, dict) or not isinstance(upload.get("url"), str):
            continue
        sources = upload.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, str):
                    images[source] = upload["url"]
        elif isinstance(upload.get("source"), str):
            images[upload["source"]] = upload["url"]
    return images


def _upload_content_images(
    local_images: dict[str, Path],
    *,
    client: WeChatClient,
    access_token: str,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    replacements: dict[str, str] = {}
    uploads: dict[str, dict[str, Any]] = {}
    for source, path in local_images.items():
        file_hash = _file_hash(path)
        upload = uploads.get(file_hash)
        if upload is None:
            upload = {
                "sha256": file_hash,
                "sources": [],
                "url": client.upload_content_image(path, access_token),
            }
            uploads[file_hash] = upload
        upload["sources"].append(source)
        replacements[source] = upload["url"]
    return replacements, uploads


def _record_verified_draft(
    *,
    release: dict[str, Any],
    release_path: Path,
    receipt_path: Path,
    plan: dict[str, Any],
    draft_id: str,
    verification: dict[str, Any],
    content_images: dict[str, str],
    cover_media_id: str,
    created_at: str | None = None,
    remote_write: bool,
) -> dict[str, Any]:
    verified_at = _iso_now()
    receipt = {
        "article_id": plan["article_id"],
        "content_hash": plan["content_hash"],
        "package_hash": plan["package_hash"],
        "target_account": plan["target_account"],
        "account_app_id_fingerprint": plan["target_account"]["app_id_fingerprint"],
        "title": plan["title"],
        "draft_id": draft_id,
        "status": "verified",
        "created_at": created_at or verified_at,
        "verified_at": verified_at,
        "content_images": content_images,
        "cover_media_id": cover_media_id,
        "external_links_before_save": plan["external_links"],
        "topics": plan.get("topics", []),
        "native_topics_applied": False,
        "verification": verification,
    }
    _atomic_write_json(receipt_path, receipt)
    wechat_release = release["wechat"]
    wechat_release["status"] = "remote_draft"
    wechat_release["draft_id"] = draft_id
    wechat_release["saved_at"] = receipt["created_at"]
    wechat_release["verified_at"] = verified_at
    wechat_release["submitted_hash"] = plan["content_hash"]
    wechat_release["submitted_package_hash"] = plan["package_hash"]
    wechat_release["remote_content_hash"] = _canonical_json_hash(verification)
    attempt = wechat_release.get("attempt")
    if isinstance(attempt, dict):
        attempt["state"] = "verified"
        attempt["draft_id"] = draft_id
        attempt["verified_at"] = verified_at
    release["last_error"] = None
    _atomic_write_json(release_path, release)
    return {
        "ok": True,
        "remote_write": remote_write,
        "reused_existing_draft": not remote_write,
        "draft_id": draft_id,
        "verification": verification,
        "external_link_warning": plan["external_links"] != verification["external_links"],
        "receipt": str(receipt_path),
        "release": str(release_path),
    }


def push_draft(
    preflight: dict[str, Any],
    *,
    confirmed_hash: str,
    confirmed_package_hash: str,
    confirmed_account: str,
    client: WeChatClient,
    reconcile_unknown_only: bool = False,
) -> dict[str, Any]:
    if not preflight.get("ok"):
        raise DraftAdapterError("preflight has blocking issues")
    plan = preflight["plan"]
    if confirmed_hash != plan["content_hash"]:
        raise DraftAdapterError("--approved-hash does not match the current signal.json")
    if confirmed_package_hash != plan["package_hash"]:
        raise DraftAdapterError("--approved-package-hash does not match the current local package")
    if confirmed_account != plan["target_account"]["name"]:
        raise DraftAdapterError("--target-account does not match release.json")

    article_dir = Path(preflight["article_dir"])
    release_path = Path(preflight["release_path"])
    receipt_path = Path(preflight["receipt_path"])
    release = preflight["_release"]
    release_wechat = release["wechat"]
    recorded_images = _recorded_content_images(release_wechat.get("uploads"))
    release_cover = release_wechat.get("cover")
    recorded_cover_id = (
        release_cover.get("media_id") if isinstance(release_cover, dict) else ""
    )
    if reconcile_unknown_only:
        if release_wechat.get("status") not in {"submitting", "remote_result_unknown"}:
            raise DraftAdapterError("reconcile-only authorization requires an unknown draft/add result")
        if release_wechat.get("draft_id"):
            raise DraftAdapterError("reconcile-only authorization expected no recorded draft ID")
        if not recorded_images or not recorded_cover_id:
            raise DraftAdapterError(
                "unknown remote result lacks upload records; inspect the draft box manually"
            )

    access_token = client.stable_token()
    if receipt_path.is_file():
        receipt = _load_json(receipt_path)
        if (
            receipt.get("content_hash") == plan["content_hash"]
            and receipt.get("package_hash") == plan["package_hash"]
            and receipt.get("target_account") == plan["target_account"]
            and receipt.get("draft_id")
        ):
            remote = client.get_draft(str(receipt["draft_id"]), access_token)
            receipt_images = receipt.get("content_images") or {}
            receipt_cover_id = str(receipt.get("cover_media_id") or "")
            expected_content = _replace_image_sources(preflight["_content"], receipt_images)
            verification = _verify_remote_draft(
                remote,
                title=plan["title"],
                author=plan["author"],
                digest=plan["digest"],
                cover_media_id=receipt_cover_id,
                comments_enabled=plan["comments"]["enabled"],
                comments_fans_only=plan["comments"]["fans_only"],
                uploaded_urls=list(receipt_images.values()),
                expected_content=expected_content,
                content_source_url=plan["content_source_url"],
            )
            return _record_verified_draft(
                release=release,
                release_path=release_path,
                receipt_path=receipt_path,
                plan=plan,
                draft_id=str(receipt["draft_id"]),
                verification=verification,
                content_images=receipt_images,
                cover_media_id=receipt_cover_id,
                created_at=receipt.get("created_at"),
                remote_write=False,
            )
        raise DraftAdapterError("a receipt exists but does not match this approved article; reconcile it first")

    recorded_draft_id = release_wechat.get("draft_id")
    if (
        release_wechat.get("status")
        in {"submitting", "remote_result_unknown", "draft_created_unverified", "remote_draft"}
        and isinstance(recorded_draft_id, str)
        and recorded_draft_id
    ):
        expected_content = _replace_image_sources(preflight["_content"], recorded_images)
        remote = client.get_draft(recorded_draft_id, access_token)
        verification = _verify_remote_draft(
            remote,
            title=plan["title"],
            author=plan["author"],
            digest=plan["digest"],
            cover_media_id=str(recorded_cover_id or ""),
            comments_enabled=plan["comments"]["enabled"],
            comments_fans_only=plan["comments"]["fans_only"],
            uploaded_urls=list(recorded_images.values()),
            expected_content=expected_content,
            content_source_url=plan["content_source_url"],
        )
        return _record_verified_draft(
            release=release,
            release_path=release_path,
            receipt_path=receipt_path,
            plan=plan,
            draft_id=recorded_draft_id,
            verification=verification,
            content_images=recorded_images,
            cover_media_id=str(recorded_cover_id or ""),
            created_at=release_wechat.get("saved_at"),
            remote_write=False,
        )

    if release_wechat.get("status") in {"submitting", "remote_result_unknown"}:
        if not recorded_images or not recorded_cover_id:
            raise DraftAdapterError(
                "unknown remote result lacks upload records; inspect the draft box manually"
            )
        expected_content = _replace_image_sources(preflight["_content"], recorded_images)
        candidates = _batch_candidates(
            client.batchget_drafts(access_token),
            title=plan["title"],
            author=plan["author"],
            uploaded_urls=list(recorded_images.values()),
            expected_content=expected_content,
        )
        if len(candidates) != 1:
            raise DraftAdapterError(
                f"draft reconciliation found {len(candidates)} candidates; manual confirmation is required"
            )
        remote = client.get_draft(candidates[0], access_token)
        verification = _verify_remote_draft(
            remote,
            title=plan["title"],
            author=plan["author"],
            digest=plan["digest"],
            cover_media_id=str(recorded_cover_id),
            comments_enabled=plan["comments"]["enabled"],
            comments_fans_only=plan["comments"]["fans_only"],
            uploaded_urls=list(recorded_images.values()),
            expected_content=expected_content,
            content_source_url=plan["content_source_url"],
        )
        return _record_verified_draft(
            release=release,
            release_path=release_path,
            receipt_path=receipt_path,
            plan=plan,
            draft_id=candidates[0],
            verification=verification,
            content_images=recorded_images,
            cover_media_id=str(recorded_cover_id),
            remote_write=False,
        )

    if reconcile_unknown_only:
        raise DraftAdapterError("reconcile-only authorization cannot create or update a remote draft")

    replacements, uploads = _upload_content_images(
        preflight["_local_images"], client=client, access_token=access_token
    )
    content = _replace_image_sources(preflight["_content"], replacements)
    if LOCAL_SOURCE_PATTERN.search(content):
        raise DraftAdapterError("rewritten content still contains a local source")
    if len(content) >= CONTENT_MAX_CHARACTERS or len(content.encode("utf-8")) >= CONTENT_MAX_BYTES:
        raise DraftAdapterError("rewritten content exceeds WeChat content limits")

    approved_cover_path = Path(preflight.get("_cover_path", article_dir / "wechat-cover.png"))
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
    payload_hash = _canonical_json_hash(article)
    release["wechat"]["status"] = "submitting"
    release["wechat"]["submitted_hash"] = plan["content_hash"]
    release["wechat"]["submitted_package_hash"] = plan["package_hash"]
    release["wechat"]["submitted_content_hash"] = payload_hash
    release["wechat"]["uploads"] = uploads
    release["wechat"]["cover"] = {
        "sha256": _file_hash(approved_cover_path),
        "media_id": cover_media_id,
    }
    release["wechat"]["attempt"] = {
        "id": attempt_id,
        "state": "submitting",
        "approved_hash": plan["content_hash"],
        "approved_package_hash": plan["package_hash"],
        "payload_hash": payload_hash,
        "started_at": _iso_now(),
        "draft_id": None,
    }
    _atomic_write_json(release_path, release)

    try:
        draft_id = client.add_draft(article, access_token)
    except WeChatAPIError as error:
        if error.errcode not in AMBIGUOUS_DRAFT_ADD_ERROR_CODES:
            release["wechat"]["status"] = "failed"
            release["wechat"]["attempt"]["state"] = "rejected"
            release["last_error"] = {
                "step": "draft_add",
                "errcode": error.errcode,
                "errmsg": error.errmsg[:240],
                "retryable": False,
                "outcome": "not_created",
                "attempt_id": attempt_id,
                "at": _iso_now(),
            }
            _atomic_write_json(release_path, release)
            raise
        release["wechat"]["status"] = "remote_result_unknown"
        release["wechat"]["attempt"]["state"] = "result_unknown"
        release["last_error"] = {
            "step": "draft_add",
            "errcode": error.errcode,
            "errmsg": "WeChat returned an ambiguous system error",
            "retryable": False,
            "outcome": "unknown",
            "attempt_id": attempt_id,
            "at": _iso_now(),
        }
        _atomic_write_json(release_path, release)
        raise DraftAdapterError(
            "draft/add result is unknown; reconcile recent drafts before any retry"
        ) from error
    except Exception as error:
        release["wechat"]["status"] = "remote_result_unknown"
        release["wechat"]["attempt"]["state"] = "result_unknown"
        release["last_error"] = {
            "step": "draft_add",
            "errcode": None,
            "errmsg": "transport failed or returned no confirmed draft ID",
            "retryable": False,
            "outcome": "unknown",
            "attempt_id": attempt_id,
            "at": _iso_now(),
        }
        _atomic_write_json(release_path, release)
        raise DraftAdapterError(
            "draft/add result is unknown; reconcile recent drafts before any retry"
        ) from error

    release["wechat"]["attempt"]["state"] = "draft_created"
    release["wechat"]["attempt"]["draft_id"] = draft_id
    release["wechat"]["draft_id"] = draft_id
    _atomic_write_json(release_path, release)

    receipt = {
        "article_id": plan["article_id"],
        "content_hash": plan["content_hash"],
        "package_hash": plan["package_hash"],
        "target_account": plan["target_account"],
        "account_app_id_fingerprint": plan["target_account"]["app_id_fingerprint"],
        "title": plan["title"],
        "draft_id": draft_id,
        "status": "created_unverified",
        "created_at": _iso_now(),
        "verified_at": None,
        "content_images": replacements,
        "cover_media_id": cover_media_id,
        "external_links_before_save": plan["external_links"],
        "topics": plan.get("topics", []),
        "native_topics_applied": False,
        "verification": None,
    }
    _atomic_write_json(receipt_path, receipt)

    try:
        remote = client.get_draft(draft_id, access_token)
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
            "errmsg": str(error)[:240] or "draft exists but verification failed",
            "retryable": True,
            "outcome": "created_unverified",
            "attempt_id": attempt_id,
            "at": _iso_now(),
        }
        _atomic_write_json(release_path, release)
        raise DraftAdapterError(
            f"draft {draft_id} was created but verification failed; do not create a duplicate"
        ) from error

    return _record_verified_draft(
        release=release,
        release_path=release_path,
        receipt_path=receipt_path,
        plan=plan,
        draft_id=draft_id,
        verification=verification,
        content_images=replacements,
        cover_media_id=cover_media_id,
        created_at=receipt["created_at"],
        remote_write=True,
    )


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or save an approved Frontier Signals package to the WeChat draft box"
    )
    parser.add_argument("article", type=Path, help="article directory or its signal.json")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="perform the remote draft write; omitted means dry-run only",
    )
    parser.add_argument("--approved-hash", help="exact approved sha256:... content hash")
    parser.add_argument(
        "--approved-package-hash",
        help="exact approved sha256:... rendered HTML and media package hash",
    )
    parser.add_argument("--target-account", help="exact target_account from release.json")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        preflight = build_preflight(args.article)
        if not args.confirm:
            result = _public_result(preflight)
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0 if result["ok"] else 1
        if not preflight.get("ok"):
            raise DraftAdapterError("preflight has blocking issues; run without --confirm for details")
        if not args.approved_hash or not args.approved_package_hash or not args.target_account:
            raise DraftAdapterError(
                "--confirm requires --approved-hash, --approved-package-hash, and --target-account"
            )
        app_id = os.environ.get("WECHAT_APP_ID", "")
        app_secret = os.environ.get("WECHAT_APP_SECRET", "")
        configured_account = os.environ.get("WECHAT_TARGET_ACCOUNT", "")
        configured_principal = os.environ.get("WECHAT_TARGET_PRINCIPAL", "")
        if not app_id or not app_secret:
            raise DraftAdapterError("WECHAT_APP_ID and WECHAT_APP_SECRET are required")
        if not configured_account or not configured_principal:
            raise DraftAdapterError(
                "WECHAT_TARGET_ACCOUNT and WECHAT_TARGET_PRINCIPAL are required"
            )
        _verify_account_binding(
            preflight["plan"],
            app_id=app_id,
            configured_account=configured_account,
            configured_principal=configured_principal,
        )
        client = WeChatClient(app_id, app_secret, timeout=args.timeout)
        result = push_draft(
            preflight,
            confirmed_hash=args.approved_hash,
            confirmed_package_hash=args.approved_package_hash,
            confirmed_account=args.target_account,
            client=client,
        )
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except DraftAdapterError as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
