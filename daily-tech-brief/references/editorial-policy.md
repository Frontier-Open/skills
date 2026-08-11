# Editorial policy

## Selection score

Use this as judgment support, not a fake numerical certainty:

- audience relevance: 40%
- freshness: 20%
- momentum: 20%
- source credibility: 10%
- content potential: 10%

Prefer fewer, stronger items. Do not fill a quota with weak candidates.

## Cross-issue uniqueness

- Read the complete versioned issue history before final selection.
- Never repeat a previously published article, story, repository, or product.
- Treat a materially identical story as a repeat even when a different outlet, headline, ranking, or URL is used.
- Use stable `dedupe_key` values and run `scripts/check-history.mjs` before publication. A failure blocks publishing and sending.

## Audience lens

Default interests for Frontier World:

- AI products and agents;
- startups, business models, and consumer technology;
- investment and industry structure;
- content, media, creator businesses, and future work;
- overseas signals with practical relevance to Chinese founders, builders, investors, and knowledge workers.

## Summary pattern

Each item should answer three questions:

1. What happened or what does the project do?
2. What reliable number or concrete feature supports it?
3. Why should this broader audience care now?

Use plain Chinese. Keep names and technical terms in their established English form.

## Source rules

- Attribute reports and allegations. Use “报道称” or “消息称” when facts are not official.
- Do not treat an aggregator headline as independent corroboration.
- Avoid copying source prose. Summarize and link.
- A missing number is better than a fabricated number.
- Record the collection time and timezone for volatile values.

## Failure rules

- One unavailable source must not erase the issue.
- Show the missing source in `warnings` and omit unsupported claims.
- Do not bypass login, CAPTCHA, rate limiting, robots restrictions, or anti-bot controls.
- If a personalized source cannot be accessed, use its public material only and label the limitation.
