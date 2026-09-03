# 设计系统与配置

Ported from the canvas renderer at https://xhs.haha.ai. `scripts/cover.js` owns every value below and
exports `THEMES`, `TEMPLATES`, `SEEDS`, `themeColor()`, `defaultConfig()`, `normalizeConfig()`,
`buildCoverHTML()`, `randomSeed()`, `listTemplates()` and `registerTemplates()`. The CLI and the
editor both consume that module, so a change there lands in both.

Templates are data, not code: every layout below is a plain spec object, and custom ones can be added
from JSON without touching the renderer. See 自定义模板 at the bottom.

## 画布

1080x1440 (3:4), the size Xiaohongshu shows in-feed. `--height` scales the whole cover: the layout is
authored at 1440 and CSS-scaled, so 2160 or 720 stay pixel-consistent. `--width` is derived from the
ratio unless set explicitly.

## 配色

Each theme is four colors ordered light to deep. A template declares which slot it reads (`slot`),
so the same theme moves from pale to saturated across the remaining layouts.

| key | 名称 | 适合 | colors |
| --- | --- | --- | --- |
| `braun` | 博朗经典 | 科技、设计、商务 | `#F5F1EB` `#E8D5B7` `#FF6B35` `#4A90E2` |
| `melon` | 青提甜瓜 | 生活、美食、健康 | `#FBFFE4` `#B3D8A8` `#A3D1C6` `#3D8D7A` |
| `sunset` | 日落黄昏 | 情感、艺术、旅行 | `#FFF8E1` `#FFE0B2` `#FF8A65` `#D84315` |
| `ocean` | 深海蓝调 | 教育、金融、专业 | `#F3F8FF` `#B3D9FF` `#4A90E2` `#1565C0` |

Shared ink: text `#1f2937`, highlight `#fbbf24`, 副标题 `#6b7280`, card `#ffffff`, card border
`#e5e7eb`, 便签 paper `#FFFDF5`, rule `#e5e7eb`, 角标 blue `#3b82f6` (top corners) and `#93c5fd`
(bottom centre). `accentColor` defaults to palette slot 3 and tints the 便签 washi tape.

## 版式几何

Six built-ins remain. Their original IDs are kept at `1`, `2`, `3`, `6`, `7` and `9` so retained
template references do not change when the other three built-ins are removed.

| id | key | 名称 | slot | structure | 用在哪 |
| --- | --- | --- | --- | --- | --- |
| 1 | `thinking` | 思考型 | 1 | plain | 知识分享、教程、方法论 |
| 2 | `dialog` | 对话框型 | 2 | card | 问答、避坑、经验交流 |
| 3 | `emotion` | 情绪型 | 3 | plain + wave | 情感表达、生活感悟、吐槽 |
| 6 | `quote` | 引用型 | 2 | card + 引号 | 金句、书摘、播客片段 |
| 7 | `note` | 便签型 | 1 | paper + 横线 | 清单、备忘、日常记录 |
| 9 | `list` | 清单型 | 1 | plain + 编号 | 几个方法、几个工具、几个坑 |

The three retained originals, in detail:

1. **思考型** — text block at x=100, y=200, 880x900, 96px/1.28, left aligned. Highlight is a filled
   yellow box. Emoji default 80%/80% at 100 (base 150px).
2. **对话框型** — white card at x=100, y=200, 880x520, radius 28, 2px border. Centered 72px/1.32 copy;
   副标题 40px under a hairline rule. Emoji default 50%/85% at 120 (base 200px).
3. **情绪型** — white wave path `M0 65 Q25 60 50 65 T100 65` at 30% opacity from 65% height. Centered
   84px/1.32 block at y=300, height 620. 角标 pinned top-right. Emoji default 50%/75% at 100 (base 150px).
The three additions reuse the same fields, so read their specs in `scripts/cover.js` for exact numbers.
便签型's ruled lines are re-positioned at render time onto the real line boxes (so they stay under the
text even after auto-shrink).

Emoji position is a percentage of the canvas (5-95) and `emojiSize` is a percentage of the template
base size (40-220), matching the drag behaviour of the original tool.

## 配置字段

```json
{
  "template": 1,
  "theme": "melon",
  "mainText": "line one\nline two",
  "subText": "",
  "highlightText": "",
  "tag": "",
  "backgroundColor": "#FBFFE4",
  "textColor": "",
  "emoji": "✨",
  "showEmoji": true,
  "emojiX": 80,
  "emojiY": 80,
  "emojiSize": 100,
  "height": 1440
}
```

`template` accepts an id, a key (`thinking`, `quote`, ...), or the Chinese name; `theme` accepts the
Chinese name. `accentColor` may be set alongside `backgroundColor`. When no `mainText` is supplied at
all, the whole template sample is used, which is how `--template 7` alone renders a complete demo;
once any copy is given, blank fields stay blank.

## 自定义模板

`--template-file <file.json>` registers extra templates before rendering, for both the CLI and the
editor. The file is one spec object or an array of them. Every field except `key` is optional.

```json
{
  "key": "poster",
  "name": "海报型",
  "desc": "上白下色",
  "useCase": "活动预告、日程、报名",
  "slot": 3,
  "structure": "band",
  "decoration": "none",
  "highlight": "fill",
  "markers": "none",
  "tag": "top-right",
  "surface": { "x": 0, "y": 980, "w": 1080, "h": 460, "radius": 0 },
  "text": { "x": 100, "y": 260, "w": 880, "h": 620, "size": 96, "align": "left", "lineHeight": 1.3, "min": 44 },
  "sub": { "x": 100, "y": 1130, "w": 880, "size": 54, "align": "left", "onSurface": true, "strong": true },
  "emoji": { "x": 84, "y": 66, "size": 100, "base": 160 },
  "sample": { "mainText": "...", "subText": "...", "highlightText": "...", "tag": "...", "emoji": "🎯" },
  "css": ".line { letter-spacing: .04em; }"
}
```

Enumerations, each one a branch in the renderer:

- `structure`: `plain` · `card` (white card) · `frame` (card with an inner border) · `paper` (便签 with
  tape) · `band` (white page, colored band at the `surface` rect)
- `decoration`: `none` · `wave` · `quote` · `rule` · `grid`. `wave` and `grid` draw under the surface,
  `quote` and `rule` above it.
- `highlight`: `fill` · `outline` · `underline` · `none`
- `markers`: `none` · `number` · `dot` — a per-line prefix
- `tag`: `none` · `top-right` · `top-left` · `bottom-center`
- `sub.onSurface` colors the 副标题 for a colored band instead of a white card; `sub.rule` adds the
  hairline above it; `sub.strong` bolds it.

`"extends": "thinking"` inherits a built-in and overrides only what you name, and `"id"` is assigned
automatically unless given. A worked pair of both styles lives in
[assets/custom-template.example.json](../assets/custom-template.example.json):

```bash
node scripts/make-cover.mjs --template-file assets/custom-template.example.json --template poster
```

## 与原站的差异

The original draws on a canvas with fixed font sizes and no measurement, so long copy clips and deep
palette slots print dark text on dark backgrounds. This port keeps the geometry and colors but:

- renders in HTML/CSS, so glyphs stay crisp at any `--height`;
- keeps each authored line on one line (`white-space: nowrap`) and shrinks the font until every line
  fits its box, instead of running past the frame;
- picks ink or white for text on the raw background by actual contrast ratio, unless `textColor` is set;
- rounds the dialog and poster cards, matching the site's own DOM preview rather than its canvas export;
- adds the retained `quote`, `note` and `list` layouts and a JSON template registry, which the original
  does not have at all.
