# 图文 deck schema

Multi-page mode renders a whole Xiaohongshu carousel from one JSON document:
`scripts/deck.js` builds the HTML, `scripts/make-deck.mjs` shoots each page with headless Chrome.
Design units are the 810x1080 grid; the deck is scaled to `width` x `height` on output, so a
`"top": 120` sticker lands in the same relative spot at any size.

## Deck object

| field | default | meaning |
| --- | --- | --- |
| `title` | `小红书图文` | document title only, never drawn |
| `theme` | `peach` | `peach` 蜜桃暖调 / `mint` 薄荷清透 / `lilac` 雾紫少女 / `butter` 奶油黄油 |
| `width` / `height` | `1080` / `1440` | output pixels, keep 3:4 |
| `author` | none | `{ "name": "@小熊不困了", "initial": "小" }`, used by any page with a footer |
| `pageDots` | `true` | the `3 / 9` pill in the top-right corner |
| `pages` | required | array of page objects, in swipe order |

## Page object

| field | default | meaning |
| --- | --- | --- |
| `name` | none | becomes part of the output filename (`05-step-1.png`) |
| `justify` | `center` | `start` / `center` / `end` / `between`, vertical placement of the block column |
| `align` | `left` | `left` / `center`, text alignment for the whole page |
| `gap` | `18` | default vertical space between blocks, any block can override with its own `gap` |
| `stickers` | `[]` | dashed sticker notes, positioned absolutely |
| `footer` | none | `true` or `{ "right": "← 左滑 查看" }` draws the avatar + handle bar |
| `pageDot` | auto | a string overrides the pill text, `false` hides it on that page |
| `blocks` | `[]` | the page content, rendered top to bottom |

## Blocks

| type | fields | renders |
| --- | --- | --- |
| `title` | `text`, `level` (1 = 72px/900, 2 = 54px/800) | the headline |
| `eyebrow` | `text`, `tone` | 24px bold kicker above a title |
| `text` | `text`, `size`, `tone`, `strong` | body copy, 26px by default |
| `emoji` | `text` | 180px centered emoji |
| `badge` | `text`, `tone` | numbered circle for step pages |
| `cards` | `items: [{ title, note, tone }]` | stack of dashed sticker cards |
| `box` | `label`, `text`, `labelSize`, `size`, `tone` | one sticker card with a label line |
| `tags` | `items: [...]`, `align` | 话题 chips row |
| `space` | `size` | explicit vertical gap in design px |

`tone` picks a palette slot: `accent` / `accent2` / `accent3` / `good` / `bad` / `ink` / `dim` / `dim2`
for text and badges, and `soft` / `highlight` for cards and boxes. Sticker `tone` is
`white` / `pink` / `yellow` / `blue` / `green`.

Stickers take `top`, `bottom`, `left`, `right` in design px plus `rotate` in degrees;
`"left": "center"` centers horizontally.

## Inline markup

Available in every text-bearing field, and nestable:

- `==payoff==` marker band in `accent3`, the highlighter look from the cover
- `**bold**` heavier weight in the primary ink colour
- `[[hot]]` accent colour
- `\n` line break

## Commands

```bash
node scripts/make-deck.mjs --sample --outdir ./out        # the built-in 9-page reference deck
node scripts/make-deck.mjs --deck my.json --outdir ./out  # your deck
node scripts/make-deck.mjs --deck my.json --theme mint    # swap palette without touching content
node scripts/make-deck.mjs --deck my.json --page 1 --out cover.png
node scripts/make-deck.mjs --deck my.json --html out.html # all pages in one scrollable preview
node scripts/make-deck.mjs --themes
```

Rendering costs about 2.5s per page. `--html` costs nothing and is the fast way to check copy fit
before committing to a full render.
