# Article contract

`article.json` is the canonical source for every channel. Use `assets/article.example.json` as a structural starter and `schemas/article.schema.json` as the normative contract for new articles.

## Identity and state

- `schema_version`: currently `1`.
- `series`: exactly `Frontier Signals`.
- `publisher` and `author`: exactly `Frontier World` unless explicitly overridden by the user.
- `id`: stable `YYYY-MM-DD/slug` identifier.
- `date`, `slug`, `timezone`, `generated_at`.
- `status`: `draft`, `reviewed`, `approved`, or `published`.
- `mode`: authoritative editorial mode, `quick` or `deep`.
- `format`: temporary renderer compatibility field. Use `analysis` for new `quick` articles and `deep-dive` for `deep` articles. Do not use it to make editorial decisions. Until the renderer is updated, the web metadata label will still display `ANALYSIS` or `DEEP-DIVE`, not the authoritative `QUICK` or `DEEP` value.

Only `approved` content may be promoted to `published`.

Keeping `schema_version: 1` and legacy `format` allows the current scripts to render new records without modification. Older version-1 records without `mode` remain renderable by the current JavaScript validator but do not satisfy the normative new-article schema.

## Mode budgets

| Mode | Chinese characters | Reading time | Sections | Sources | Production visuals |
| --- | ---: | ---: | ---: | ---: | ---: |
| `quick` | 1,400–2,200 | 5–8 minutes | 3–4 | at least 3 | 3–5 |
| `deep` | 3,200–5,000 | 12–18 minutes | 4–6 | at least 6 | 5–8 |

Count production visuals as `media.cover`, `media.og`, and section `image` objects. Because the current renderer supports at most one image per section, use 1–3 inline images for `quick` and 3–6 for `deep`. This count never overrides the media purpose, rights, and provenance requirements.

## Editorial fields

- `title`, `subtitle`, `thesis`, `excerpt`, `reading_minutes`, and computed `word_count`. Count visible non-whitespace characters in `intro`, section paragraphs/callouts/points, and conclusion paragraphs; exclude metadata, captions, and the source list.
- `title_candidates`: exactly three objects: `factual`, `judgment`, and `question`. Each contains `text` and `claim_check`. The selected `title` must exactly match one candidate after fact-checking.
- `reader_payoff`: one concrete sentence stating what the target reader can understand, notice, or do differently.
- `hook`: structured `event`, `tension`, and `judgment` used to produce the visible intro.
- `counterargument`: the strongest credible objection, its evidence, the boundary that would make the thesis wrong, the response, and source IDs. It is mandatory and must also appear in a rendered section for `deep`; it may be `null` for `quick`.
- `watchlist`: two or three observable indicators, each with `indicator`, `why_it_matters`, and supporting source IDs.
- `fact_check`: one entry for every material claim. Each entry records `claim`, `kind`, `status`, `source_ids`, `high_risk`, `independent_source_count`, and `note`. Drafts may use `pending` or `rejected`; review and publication allow only `verified` or explicitly bounded `qualified` claims.
- `story_keys`: stable keys for underlying events used by the article.
- `angle_key`: stable key for the thesis. Do not change it for superficial title rewrites.
- `continuation_of`: prior article ID when revisiting a story; otherwise `null`.
- `material_update`: concrete new fact justifying a continuation; otherwise `null`.
- `intro`: one to four paragraphs, plus `intro_source_ids` for facts used in the opening.
- `sections`: three to six ordered sections.
- `conclusion`: closing paragraphs, `source_ids`, and an optional question.

Each section contains `label`, `title`, `role`, `paragraphs`, and `source_ids`. It may also contain `callout`, `points`, and one local `image` object. Allowed roles are `context`, `evidence`, `mechanism`, `counterargument`, `implication`, and `watchlist`.

## Sources

Every source needs:

- `id`: short stable identifier referenced by sections;
- `publisher`;
- `title`;
- absolute HTTP(S) `url`;
- `published_at` when known;
- `accessed_at`;
- `source_type`: `primary`, `reporting`, `analysis`, or `social`.
- `chain_id`: stable identifier for the underlying reporting or evidence chain. Syndicated or repeated reports about the same unnamed source share one chain ID.

All factual sections must cite source IDs. Every listed source must be used by at least one section. The current intro shape has no `source_ids`; any source needed by the intro must also be attached to the supporting section.

Minimum source counts are mode gates, not quotas. Several reports repeating the same anonymous or syndicated claim count as one source chain. Consequential, disputed, reputation-sensitive, market-moving, safety, financing, or personnel claims require at least two independent sources.

## Media

`media.cover` and `media.og` require `path`, `alt`, `credit`, `purpose`, `rights`, and `generated`. Optional fields include `caption` and `source_url`. Generated media requires a concise `prompt_note`; sourced media requires `source_url`.

Section images use the same fields. Store local relative paths; never hotlink a publication image in the final edition.

Use `purpose` values `brand`, `evidence`, `explanation`, `scene`, or `atmosphere`. Reserve `brand` for deterministic cover/OG variants. Permit at most one inline `atmosphere` image per article. Generated media must be labeled and must never impersonate documentary evidence.

## Distribution

- `canonical_url`: permanent HTTPS web URL ending in `/`.
- `distribution.web`, `distribution.wechat`, and `distribution.feishu` contain state and remote IDs or URLs.
- Remote IDs are operational metadata. Keep them in the private article repository, not public HTML.
- Store per-run outward-action results in `publication.json` so retries cannot duplicate a draft or message.

## Renderer bridge

The renderer outputs `title`, `subtitle`, `intro`, nearby intro/section/conclusion citations, sections, conclusion, sources, and media. It does not directly render `reader_payoff`, `hook`, `counterargument`, `watchlist`, or `fact_check`.

- Turn `hook` into the visible intro; do not leave it as hidden planning metadata.
- For `deep`, repeat the top-level counterargument in a section with `role: counterargument`.
- Repeat `watchlist` indicators in a `watchlist`/`implication` section or the conclusion.
- Use `reader_payoff` to edit the intro and conclusion; do not print it as an internal label.
- Keep `fact_check` private; use it to verify the prose and source IDs before review.

Treat any mismatch between these planning fields and the rendered body as a blocking error.

## History rules

- Duplicate `angle_key` is a hard failure.
- Reusing a prior `story_key` is a hard failure unless `continuation_of` points to a prior article and `material_update` is non-empty.
- Reusing a canonical source URL is a hard failure unless it supports an explicitly declared continuation.
- A new event involving the same company or product should receive a new story key.

## Publication gates

Do not advance to `reviewed`, `approved`, or `published` unless:

1. `mode`, `word_count`, `reading_minutes`, section count, source count, and production-visual count satisfy the mode budget;
2. the selected `title` is one of `title_candidates` and its `claim_check` is supported within the first 20% of the article;
3. `reader_payoff` is concrete and `hook` contains event, tension, and judgment;
4. every material claim appears in `fact_check` with `verified` or explicitly bounded `qualified` status;
5. every high-risk claim has at least two independent sources;
6. `deep` includes a non-null `counterargument` and a rendered section with `role: counterargument`;
7. `watchlist` contains two or three observable indicators;
8. every visual has purpose, local path, alt text, credit, rights metadata, and source or generation provenance;
9. facts, attributed reporting, interpretation, and recommendation are visibly distinguishable;
10. unresolved warnings remove the affected claim or block publication.

The JSON Schema enforces shape and numeric budgets. `scripts/validate-article.mjs --normative` additionally recomputes `word_count`, checks source-chain counts, requires planning fields to appear in rendered prose, validates channel-state consistency, and enforces both web and WeChat media roots. Editorial review must still decide whether title evidence is substantively adequate and whether a visual's declared rights are genuinely usable.
