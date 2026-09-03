---
name: xhs-cover-generator
description: Generate Xiaohongshu (小红书) 图文 as 1080x1440 PNGs, rendered locally with headless Chrome. Single covers come from six layouts, four palettes or custom JSON templates; multi-page 图文 deck / 轮播 / carousel mode turns one JSON into N pastel pages with sticker cards, step badges, page dots and 话题 chips. Use for 封面/首图/图文合集 built from copy; not for photographic or AI-illustrated images.
---

# 小红书封面生成器

A local port of the generator at https://xhs.haha.ai, extended: six built-in layouts, four
palettes, JSON-defined custom templates, 1080x1440 output. Copy is the product here, so most of the
work is writing the lines, not running the tool.

Two modes. `make-cover.mjs` makes one text-driven 封面. `make-deck.mjs` makes a whole 图文 deck,
N pages of pastel background, dashed sticker cards and page dots, from a single JSON document.

## Make a cover

```bash
node scripts/make-cover.mjs --template thinking --theme melon \
  --main "一个人做内容\n先定一个主张\n再开始动手" \
  --highlight "一个主张" --emoji 🧭 --out covers/cover.png
```

`--config file.json` takes the same fields as one object, `--batch file.json --outdir dir` renders an
array of them, and `--html` writes the HTML instead of a PNG. `--list` prints the template and palette
tables. Rendering needs Chrome, Chromium, or Edge; the script also finds a Playwright-cached Chromium,
and `XHS_COVER_CHROME` overrides the lookup.

`--template <key>` on its own renders that template's built-in sample, which is the fastest way to show
someone what a layout looks like.

For hand-tuning, `node scripts/make-cover.mjs --editor` serves a local editor: live preview, emoji
drag and resize, 一键生成, and a 保存 PNG button that renders through the same code path into `covers/`
under the directory the server was started from.

## Choose the layout

Pick by the emotional job of the cover, then let the palette follow the topic.

- `thinking` 思考型 — left-aligned statement block, one highlighted phrase. Knowledge, tutorials, methodology.
- `dialog` 对话框型 — white speech card with an optional 副标题. Questions, 避坑, conversational hooks.
- `emotion` 情绪型 — centered lines over a wave, corner 角标. Venting, feelings, relatable moments.
- `quote` 引用型 — quiet card between quote marks, attribution underneath. 金句, 书摘, podcast pull-quotes.
- `note` 便签型 — taped paper with ruled lines under the copy. Checklists, memos, diary-ish posts.
- `list` 清单型 — numbered lines under a bold 副标题 lead. 三件事, tool roundups, mistake lists.

Templates are addressed by their stable key. Use the key rather than a position in the list, because templates can be removed or added without changing other templates.

Palettes: `melon` 青提甜瓜 (life, food, health), `braun` 博朗经典 (tech, design, business),
`sunset` 日落黄昏 (emotion, art, travel), `ocean` 深海蓝调 (education, finance, professional).
Each template reads a deeper slot of the palette, so the same theme moves from pale to saturated
across the remaining layouts. Override with `--background` when a specific slot works better.

## Write the copy

Lines break exactly where you break them and never wrap, so treat each line as a designed unit:
3-4 lines, 5-9 characters each, one idea per line. Font size auto-shrinks when a line runs long, so
an overlong line silently costs you visual weight instead of overflowing.

Give every cover exactly one `--highlight` phrase, and make it the payoff word (`3分钟`, `五万粉丝`,
`神器`), not a verb or particle. 角标 (`--tag`) is social proof in 4-5 characters: `亲测有效`, `听劝版`,
`新手友好`. Templates carry different line budgets: 对话框型 works best in three lines, 便签型 in
three to five lines, and 清单型 with parallel items, so match the copy to the layout rather than
reusing one block everywhere.

For hook formulas, tag vocabulary, and per-template copy shapes, read
[references/copywriting.md](references/copywriting.md).

## Make a 图文 deck

For a carousel rather than a single image, describe the whole thing in one JSON file and render every
page at once:

```bash
node scripts/make-deck.mjs --sample --outdir ./out     # the built-in 9-page reference deck
node scripts/make-deck.mjs --deck my-deck.json --outdir ./out --theme mint
```

A deck is `{ theme, author, pages: [...] }`, and every page is a list of typed blocks, so a 7-page
deck and an 18-page deck share one vocabulary: `title`, `eyebrow`, `text`, `emoji`, `badge`,
`cards`, `box`, `tags`, `space`, plus absolutely positioned `stickers` and an optional author
`footer`. Page dots (`3 / 9`) are numbered automatically. Inline markup works everywhere:
`==payoff==` for the highlighter band, `**bold**`, `[[accent]]`, `\n` for a line break.

Palettes are `peach` 蜜桃暖调, `mint` 薄荷清透, `lilac` 雾紫少女, `butter` 奶油黄油, and swapping one
re-colours the whole deck without touching the copy.

Shape the deck around the swipe, not around the page count: a cover that promises one payoff, a hook
that stops the scroll, the pain the reader recognises, the insight that reframes it, the numbered
steps, the result, and a CTA page carrying 话题 chips. Seven pages is a working minimum and about
eighteen is the ceiling before people stop swiping.

[assets/deck-xhs-post.sample.json](assets/deck-xhs-post.sample.json) is a complete worked example and
doubles as the schema reference; the field-by-field tables are in
[references/deck-schema.md](references/deck-schema.md). Use `--html preview.html` to check copy fit
before spending ~2.5s per page on a full render.

## Add your own template

Templates are data, so a new layout is a JSON object, not a code change:

```bash
node scripts/make-cover.mjs --template-file assets/custom-template.example.json --template poster
```

A spec picks a `structure` (`plain` / `card` / `frame` / `paper` / `band`), a `decoration`, a
`highlight` style, a 角标 position, and the boxes for text, 副标题 and emoji; `"extends": "thinking"`
inherits a built-in and overrides only what you name. The file works with `--editor` too, so custom
layouts show up in the version picker.
[assets/custom-template.example.json](assets/custom-template.example.json) has one of each style.

## Change the design

Layout geometry, palette slots, the full config schema, the custom-template field reference, and the
deliberate deviations from the original site live in
[references/design-system.md](references/design-system.md). Read it before editing `scripts/cover.js`
or when a request needs custom sizes, colors, or emoji placement.
