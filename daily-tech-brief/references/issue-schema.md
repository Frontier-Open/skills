# Issue JSON contract

## Required top-level fields

```json
{
  "date": "2026-08-07",
  "timezone": "Asia/Shanghai",
  "generated_at": "2026-08-07T09:57:00+08:00",
  "canonical_url": "https://brief.example.com/2026/08/07/",
  "brand": "FRONTIER WORLD",
  "headline": "One editorial thesis",
  "dek": "10 分钟读完 · 10 条精选",
  "signals": [],
  "repositories": [],
  "products": [],
  "topic": "One actionable content topic",
  "warnings": []
}
```

## Signal

```json
{
  "title": "Short Chinese title",
  "dedupe_key": "stable-story-key",
  "source": "Techmeme · Bloomberg",
  "source_url": "https://...",
  "summary": "What happened",
  "why": "Why it matters",
  "published_at": "2026-08-06T20:10:00-04:00"
}
```

## Repository

```json
{
  "name": "owner/repo",
  "dedupe_key": "github:owner/repo",
  "url": "https://github.com/owner/repo",
  "summary": "What it does and why it matters",
  "stars_total": "4,837",
  "source": "GitHub Trending"
}
```

`stars_total` is required and must come from the public GitHub repository page at collection time. The page renders only this total; do not show daily growth, HelloGitHub clicks, or secondary metric labels.

## Product

```json
{
  "name": "Product name",
  "dedupe_key": "producthunt:product-slug",
  "url": "https://...",
  "icon": "./product-name.png",
  "icon_source_url": "https://ph-files.imgix.net/...",
  "summary": "What it does and why it matters",
  "source": "Product Hunt official feed"
}
```

`icon` is required for each selected product. Download the real Product Hunt project icon into the same dated directory as `index.html`; do not depend on a remote image at render time. Keep the original Product Hunt asset URL in `icon_source_url` for provenance.

## Constraints

- `signals`: 1-6 items.
- `repositories`: exactly 4 items curated jointly from GitHub Trending and HelloGitHub.
- `products`: exactly 2 curated items by default.
- Order `repositories` by audience relevance, not source rank or Star count.
- Every signal, repository, and product needs a stable `dedupe_key`. Reuse the same key for the same underlying story or project even when its title, source, rank, or URL parameters change.
- No `dedupe_key`, normalized canonical URL, or normalized title/name may match any prior issue in the versioned history.
- All selected items need an absolute HTTP(S) URL.
- Every product needs a local `./filename.ext` icon and an absolute `icon_source_url`.
- `canonical_url` must use `/YYYY/MM/DD/` and end with `/`.
- Store warnings as concise strings; never store secrets or raw authentication errors.
