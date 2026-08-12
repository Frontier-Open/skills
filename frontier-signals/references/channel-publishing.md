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

1. Use user identity.
2. Resolve the configured `Frontier Signals` wiki node and list its children.
3. Reuse an existing `YYYY-MM-DD · title` child when its article ID matches; otherwise create one directly under the configured node.
4. Import the generated Markdown, then insert local cover and inline images with the Feishu media workflow.
5. Fetch the document back and verify title, thesis, section order, images, sources, and parent node.
6. Check access. Do not widen sharing automatically.

## Reviewer delivery

The Feishu card contains the cover, title, excerpt, two or three key judgments, reading time, and two buttons: Feishu full text first, official web article second. Send only after web and Feishu verification succeed. Use `frontier-signals-review-YYYY-MM-DD-slug` as the idempotency key.

## Publication state

Use this state progression independently per channel:

`draft → reviewed → approved → published`

Record failures without advancing state. A successful web deployment does not imply WeChat approval, and saving a WeChat draft does not imply public publication.
