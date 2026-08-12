# Multi-channel publishing

## Canonical source

`article.json` is canonical. Render web, WeChat, Feishu, covers, and delivery cards from the same revision. Channel adapters may change presentation, never thesis or facts.

## WeChat Official Account

1. Render all-inline HTML and Markdown.
2. Preview at 375 px and check title, author, cover crop, inline images, captions, sources, and link behavior.
3. Treat the result as a draft.
4. Save to the confirmed Official Account draft box only when an official connector or permitted browser session supports it.
5. Publishing or mass sending requires a separate explicit confirmation.

When platform automation is unavailable, prepare rich clipboard content and a short manual checklist; do not use hidden endpoints or bypass browser restrictions.

## Web

1. Archive the approved article JSON.
2. Render the dated page, archive, RSS, and sitemap.
3. Run the repository check and a Cloudflare dry run.
4. Commit and push the exact revision.
5. Deploy or wait for the configured build, then require HTTP 200 for page, article Markdown, OG image, RSS, sitemap, and archive.
6. Record the commit, deployment version, and canonical URL in `publication.json`.

Recommended first-party address: `https://signals.frontierworld.ai/`. Keep the content Worker and repository separate from the main brand website so daily publication cannot destabilize the homepage.

## Feishu knowledge base

1. Use user identity and the explicitly configured CLI profile; never fall back to another tenant or application profile.
2. Resolve the configured `Frontier Signals` `space_id` and optional parent node. List the parent node's children when one is configured; otherwise list the space-root nodes.
3. Reuse an existing `YYYY-MM-DD · title` node when its article ID matches; otherwise create one in the configured space, under the optional parent node.
4. Import the generated Markdown, then insert local cover and inline images with the Feishu media workflow.
5. Fetch the document back and verify title, thesis, section order, images, sources, `space_id`, and parent placement.
6. Check access. Do not widen sharing automatically.

### Idempotency and retry rules

- Treat the dated `publication.json` record as the primary index. Its top-level `article_id` plus `feishu.space_id`, `feishu.node_token`, `feishu.obj_token`, `feishu.parent_node_token`, and `feishu.document_url` identify the managed document.
- When that record already contains a node, resolve it and verify the configured space and parent placement before writing. A mismatch is a hard stop; never create a replacement silently.
- When no node is recorded, list the configured parent or space root and look for the exact `YYYY-MM-DD · title`. Reuse one unambiguous match; stop on multiple matches or conflicting content.
- After creating a node, persist its identifiers with a non-published Feishu status before importing content so a retry can resume the same node.
- The workflow owns the full Feishu edition. On create or retry, overwrite it from the canonical Markdown and then restore its managed media; never append the full article or duplicate image blocks.
- Advance Feishu to `published` only after content, media, placement, and access checks pass. Keep the same node and record the failure when any verification fails.

## Reviewer delivery

The Feishu card contains the cover, title, excerpt, two or three key judgments, reading time, and two buttons: Feishu full text first, official web article second. Send only after web and Feishu verification succeed. Use `frontier-signals-review-YYYY-MM-DD-slug` as the idempotency key.

## Publication state

Use this state progression independently per channel:

`draft → reviewed → approved → published`

Record failures without advancing state. A successful web deployment does not imply WeChat approval, and saving a WeChat draft does not imply public publication.
