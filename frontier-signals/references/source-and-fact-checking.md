# Source and fact-checking

## Source hierarchy

Prefer, in order:

1. official announcement, paper, filing, repository, product documentation, or transcript;
2. named reporting from a credible newsroom;
3. a specialist analyst with disclosed evidence;
4. an aggregator only as discovery input.

An aggregator headline is not corroboration. Social posts can establish what their author said, not that the underlying claim is true.

## Fact card

Before drafting, record for each usable claim:

- claim in neutral language;
- source ID and canonical URL;
- publisher and source type;
- published and accessed time;
- direct support visible in the source;
- confidence: confirmed, attributed, or interpretation;
- story key for the underlying event.

## Attribution

- Use direct factual language for official, unambiguous information.
- Use “报道称”, “文件显示”, or “消息称” for attributed reporting.
- Identify estimates, forecasts, and anonymous claims as such.
- Separate the article’s interpretation from a source’s statement.
- Preserve uncertainty when sources disagree.

## Numbers and quotes

- Never infer a metric that the source does not expose.
- Timestamp volatile values such as pricing, valuation, usage, and repository stars.
- Verify units, currencies, time periods, and whether a figure is cumulative or incremental.
- Use quotation marks only for verified wording. Prefer paraphrase unless the exact wording matters.

## Cross-source verification

Use a second independent source for claims that are consequential, disputed, or likely to move markets or reputations. Two articles repeating the same unnamed source count as one chain, not two confirmations.

## Access constraints

Do not bypass login, paywalls, CAPTCHA, robots rules, rate limits, or anti-bot controls. When only a headline or feed excerpt is accessible, limit the claim to what it supports and record the limitation in `warnings`.

## Corrections

After publication, record substantive corrections in `article.json` with time, changed claim, reason, and source. Do not silently rewrite an archival article in a way that changes its thesis or evidence.
