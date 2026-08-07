# Issue JSON contract

## Required top-level fields

```json
{
  "date": "2026-08-07",
  "timezone": "Asia/Shanghai",
  "generated_at": "2026-08-07T09:57:00+08:00",
  "canonical_url": "https://brief.example.com/2026-08-07/",
  "brand": "CLAIRE'S MORNING SIGNALS",
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
  "url": "https://github.com/owner/repo",
  "summary": "What it does and why it matters",
  "metric": "+2,802 ★",
  "metric_note": "today · 4,837 total",
  "source": "GitHub Trending"
}
```

`metric` and `metric_note` are optional. Never derive Product Hunt votes, ranks, or GitHub growth from unrelated values.

## Product

```json
{
  "name": "Product name",
  "url": "https://...",
  "summary": "What it does and why it matters",
  "source": "Product Hunt official feed"
}
```

## Constraints

- `signals`: 1-6 items.
- `repositories`: 1-6 items.
- `products`: 0-4 items.
- All selected items need an absolute HTTP(S) URL.
- `canonical_url` must end with `/`.
- Store warnings as concise strings; never store secrets or raw authentication errors.
