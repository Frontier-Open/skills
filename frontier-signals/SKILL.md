---
name: frontier-signals
description: Research, write, render, verify, archive, and prepare distribution of Frontier Signals, Frontier World’s daily public AI and technology article series. Use when Codex is asked to turn current AI or technology news into a sourced QUICK article or DEEP analysis; create brand-consistent WeChat Official Account, web, or Feishu editions; maintain the Signals article archive; or run the daily multi-channel publishing workflow.
---

# Frontier Signals

Publish one useful argument, not a rewritten news list. Use current events as evidence for a clear thesis aimed at Chinese founders, builders, investors, creators, and knowledge workers.

## Workflow

1. Resolve the publication date in `Asia/Shanghai`, audience, review deadline, repository root, and authorized delivery targets. Use `Frontier Signals` as the series and `Frontier World` as publisher and author.
2. Collect a broad research pool:

   ```bash
   node scripts/collect.mjs --out work/raw.json
   ```

   Continue when one source fails and preserve the failure under `warnings`. Never replace missing current data with stale content.
3. Read [editorial-playbook.md](references/editorial-playbook.md), [source-and-fact-checking.md](references/source-and-fact-checking.md), and [article-schema.md](references/article-schema.md). Load prior `research.json` and `article.json` history before choosing the angle.
4. Select a single thesis and choose one editorial mode:
   - `quick`: 1,400–2,200 Chinese characters, at least 3 independent sources, 3–4 sections, 5–8 minutes, and 3–5 production visuals;
   - `deep`: 3,200–5,000 characters, at least 6 independent sources, 4–6 sections, 12–18 minutes, and 5–8 production visuals. Require a credible counterargument and the condition that would make the thesis wrong.

   Use `quick` by default. Choose `deep` only when the evidence supports a structural question, competing explanations, and forward indicators. When no single story is strong enough, connect only closely related events that support the same thesis. Never fill the day with unrelated headlines.
5. Verify claims from primary sources whenever available. Record a stable `story_key` for each underlying event, an `angle_key` for the article thesis, access timestamps, and source IDs used by every section. A material follow-up may revisit a story only with `continuation_of` and a concrete `material_update`.
6. Write one canonical `article.json` using `assets/article.example.json`. Set `mode`, `word_count`, three typed `title_candidates`, `reader_payoff`, structured `hook`, `counterargument`, two or three observable `watchlist` items, and a material-claim `fact_check` ledger. Keep legacy `format` only as a renderer bridge: use `analysis` for new `quick` articles and `deep-dive` for `deep`. All channel editions must derive from this file; do not independently rewrite WeChat, web, and Feishu versions.
7. Plan media with [media-policy.md](references/media-policy.md). Count production visuals as `media.cover` + `media.og` + section images: require 3–5 for `quick` and 5–8 for `deep`. With the current renderer this means 1–3 inline section images for `quick` and 3–6 for `deep`. These required ranges supersede the earlier typical-count examples in `brand-and-layout.md`; its visual-purpose and layout rules still apply. Every visual must pass the purpose test. Prefer primary-source charts, product screenshots, timelines, or original explanatory diagrams over decorative imagery. Permit at most one purely editorial AI illustration, label generated media, and keep local copies, alt text, captions, credits, rights notes, and source URLs.
8. Validate the article and history before rendering:

   ```bash
   node scripts/validate-article.mjs --article article.json --normative
   node scripts/check-article-history.mjs --article article.json --history-dir /path/to/signals/data/articles
   ```

   Any out-of-range mode budget, unsupported material claim, unresolved `fact_check`, missing source, duplicate angle, invalid media credit, title promise not supported in the first 20% of the article, missing `deep` counterargument, or repeated story without a material update blocks review and publication. The existing validator protects the renderer contract; apply the stricter gates in [article-schema.md](references/article-schema.md) and `schemas/article.schema.json` as the normative new-article contract.
9. Render all text editions from the same canonical file:

   ```bash
   node scripts/render-article.mjs \
     --article article.json \
     --media-root media/YYYY/MM/DD/slug \
     --web public/YYYY/MM/DD/slug/index.html \
     --markdown public/YYYY/MM/DD/slug/article.md \
     --wechat-html drafts/wechat/YYYY/MM/DD/slug/wechat.html \
     --wechat-markdown drafts/wechat/YYYY/MM/DD/slug/wechat.md
   ```

10. Generate deterministic brand covers when an original editorial illustration is not warranted:

    ```bash
    python3 scripts/render-covers.py \
      --article article.json \
      --og public/YYYY/MM/DD/slug/og.png \
      --wechat drafts/wechat/YYYY/MM/DD/slug/wechat-cover.jpg
    ```

    Then require the generated channel media from their actual output roots:

    ```bash
    node scripts/validate-article.mjs \
      --article article.json \
      --normative \
      --require-media \
      --web-root public/YYYY/MM/DD/slug \
      --wechat-root drafts/wechat/YYYY/MM/DD/slug
    ```

11. Archive `article.json`, rebuild the web archive, RSS, and sitemap, then run site checks. Read [brand-and-layout.md](references/brand-and-layout.md) and [channel-publishing.md](references/channel-publishing.md) before any outward action.
12. Start an HTTP preview before opening browser tooling; never navigate the browser directly to `file://` artifacts:

    ```bash
    node scripts/preview.mjs --root /path/to/signals --port 4174
    ```

    Preview the web edition at 390, 768, 1024, and 1440 px. Preview the WeChat draft under `/drafts/...` at 375 and 677 px. Reject horizontal overflow, clipped text, broken local images, missing captions, or channel-specific wording drift. If browser policy still blocks the HTTP preview, keep the article in `draft` and report the blocked gate.
13. Create or update the date-and-slug Feishu document under the configured `Frontier Signals` wiki node with user identity. Insert local images through the Feishu media workflow, fetch the document back, and confirm title, sections, sources, and node parent. Do not widen sharing automatically.
14. Treat the WeChat edition as a draft. Only save it to an explicitly confirmed Official Account draft box when the available browser or official connector permits the action. Publishing or mass sending always requires a separate explicit confirmation.
15. Commit and push the article repository, deploy the web edition, and confirm the canonical page, Markdown, cover, RSS, sitemap, and archive return success before delivery. Record channel IDs and URLs in `publication.json` so retries are idempotent.
16. Send the review card only to the configured reviewer. Use a date-and-slug idempotency key. Never send partial output after research, validation, Feishu, deployment, or authentication failure.

## Editorial standard

- Open with a concrete change, tension, and judgment within the first 120–180 Chinese characters.
- Make the thesis explicit, specific, and falsifiable. Each section must advance it with evidence rather than repeat it.
- State `reader_payoff` before drafting: what the target reader will understand, notice, or do differently.
- Draft factual, judgment, and question titles, then choose only after checking every title claim against the evidence.
- Use 40–90-character paragraphs and informative section titles. Keep one idea per paragraph and normally stay below 120 characters.
- Structure each section as judgment → evidence → mechanism → implication. A `deep` article must present the strongest credible objection before its conclusion.
- Distinguish confirmed facts, attributed reporting, interpretation, and recommendation.
- End by returning to the thesis, naming the practical implication, and giving two or three observable indicators. Use a specific open question only when it follows from the argument.
- Use curiosity without clickbait. Never promise certainty that the evidence does not support.
- Keep product and company names in their established form. Write clear Chinese around them.

## Publication gate

Do not advance an article to `reviewed`, `approved`, or `published` unless all checks pass:

- `quick`: 1,400–2,200 Chinese characters, at least 3 sources, and 3–5 production visuals;
- `deep`: 3,200–5,000 characters, at least 6 sources, 5–8 production visuals, and one rendered counterargument section;
- every material factual claim appears in `fact_check` with supporting source IDs and `verified` or explicitly bounded `qualified` status;
- consequential, disputed, reputation-sensitive, market-moving, or safety claims have at least two independent sources;
- the selected title is one of `title_candidates`, and its promise is evidenced within the first 20% of the article;
- `hook` supplies event, tension, and judgment; `reader_payoff` is concrete; `watchlist` contains two or three observable indicators;
- every image has a declared purpose, local path, alt text, credit, and rights/source metadata; no decorative image is used merely to reach the count;
- facts, attributed reporting, interpretation, and recommendation are visibly distinct;
- warnings are resolved or explicitly remove the affected claim. Do not publish around a failed gate.

## Output contract

```text
work/raw.json                                      collected source candidates and warnings
work/research.json                                 curated facts and story keys
article.json                                       canonical article source
data/articles/YYYY/MM/DD/slug/article.json         versioned article history
media/YYYY/MM/DD/slug/source/                      preserved source visuals
public/YYYY/MM/DD/slug/index.html                  canonical web article
public/YYYY/MM/DD/slug/article.md                  Feishu-ready Markdown edition
public/YYYY/MM/DD/slug/og.png                      1.91:1 social preview
drafts/wechat/YYYY/MM/DD/slug/wechat.html          all-inline WeChat edition
drafts/wechat/YYYY/MM/DD/slug/wechat.md            WeChat text edition
drafts/wechat/YYYY/MM/DD/slug/wechat-cover.jpg     900×383 cover
publication/YYYY/MM/DD/slug.json                   per-channel status and remote IDs
public/index.html                                  article archive
public/rss.xml                                     RSS feed
public/sitemap.xml                                 web sitemap
lark-card.json                                     send-ready reviewer card
```

## Safety and publication rules

- Preserve source URLs and factual provenance; never fabricate metrics, quotes, or access.
- Do not bypass login, CAPTCHA, paywall, robots rules, rate limiting, or platform safety restrictions.
- Keep secrets, browser state, recipient IDs, and authentication errors out of repositories and public files.
- Separate `draft`, `reviewed`, `approved`, and `published` states. Rendering is not approval.
- Keep canonical URLs permanent after publication. Correct factual errors transparently instead of silently replacing the record.
- Default the official web edition to indexable only after publication approval. Draft previews must remain private or `noindex`.
- Preserve legacy URLs with explicit permanent redirects during migrations.
