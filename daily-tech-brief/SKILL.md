---
name: daily-tech-brief
description: Collect, curate, fact-check, render, publish, and prepare delivery of a personalized daily technology briefing from Techmeme, daily.dev, GitHub Trending, HelloGitHub, and Product Hunt. Use when Codex is asked to create a morning tech digest, refresh an existing issue, produce a sourced HTML/PNG briefing, maintain a dated briefing archive, or prepare a Feishu/Lark delivery card for a technology-news workflow.
---

# Daily Tech Brief

Produce a short editorial briefing, not a copied ranking. Keep every claim traceable to a source, explain why each item matters to the reader, and never invent metrics.

## Workflow

1. Resolve the issue date, timezone, reader profile, output directory, and delivery channel. Default to the user's local date and timezone.
2. Collect current candidates:

   ```bash
   node scripts/collect.mjs --out work/raw.json
   ```

   Continue when one source fails. Preserve its failure under `warnings`; do not silently replace it with stale data.
3. Read [editorial-policy.md](references/editorial-policy.md). Read [issue-schema.md](references/issue-schema.md) before writing issue JSON.
4. Curate a focused issue. Default composition:
   - 4 technology/business signals;
   - 4 repositories, combining GitHub momentum with HelloGitHub's Chinese editorial context;
   - 2 Product Hunt products;
   - 1 actionable topic for the reader.
5. Open or fetch the selected source pages when a summary depends on details not present in collected metadata. Prefer primary reporting links over aggregator permalinks when both are available.
6. Write a valid `issue.json`. Attribute every item with `source`, `source_url`, and `why`. Include metrics only when the source exposes them explicitly.
7. Render the issue:

   ```bash
   node scripts/render.mjs --issue issue.json --out public/2026-08-07/index.html
   ```

8. Verify structure and links:

   ```bash
   node scripts/verify.mjs --issue issue.json --html public/2026-08-07/index.html
   ```

9. Copy a 1.9:1 issue preview image to `public/YYYY-MM-DD/og.png`. Keep its URL date-specific so Feishu does not reuse an older cached preview.
10. Preview at both desktop and a 430 px mobile viewport when browser tooling is available. Reject horizontal overflow, clipped text, or multi-line section labels caused by layout constraints.
11. For Feishu/Lark delivery, read [lark-delivery.md](references/lark-delivery.md), upload the issue image, and render the card with `scripts/render-lark-card.mjs`.
12. Separate generation from outward actions. Before sending, confirm the destination, exact card, and sending identity. Preserve existing hosting architecture and dated URLs.

## Editorial decisions

- Lead with one sentence that connects the day's items into a useful thesis.
- Select for reader relevance, novelty, momentum, credibility, and future content potential.
- Keep source types distinct: news, developer discussion, repository momentum, Chinese open-source editorial selection, and product launch.
- Treat daily.dev's public pages as public editorial input. A personalized daily.dev feed requires an authorized session; state when it was unavailable.
- Treat Product Hunt's Atom feed as launch discovery. If votes or rank are unavailable, say “今日上榜” or “值得关注”; never guess placement.
- Timestamp volatile metrics, especially GitHub `stars_today`.
- Keep the rendered issue readable in about 10 minutes.

## Output contract

Keep these artifacts together:

```text
work/raw.json                 collected candidates and source warnings
issue.json                    curated, sourced issue data
public/YYYY-MM-DD/index.html  canonical dated issue
public/YYYY-MM-DD/og.png      issue-specific link-preview image
lark-card.json                send-ready Feishu card after image-key injection
```

Use `assets/issue.example.json` as a structural starter, not as content. `assets/brief.css` is the deterministic editorial template used by the renderer.

## Publication rules

- Keep `/YYYY-MM-DD/` permanent after publication.
- Make `/` redirect to the newest issue.
- Set a canonical URL and social-preview metadata for the dated page.
- If the briefing is private-by-link, add `noindex,nofollow,noarchive`. Allow preview crawlers in `robots.txt`; otherwise Feishu may not read the page metadata. Clarify that this is not access control.
- Do not expose API keys, browser state, access tokens, or service credentials in output, logs, Git, or HTML.
- Use an idempotency key for scheduled delivery so a retry cannot send the same issue twice.
