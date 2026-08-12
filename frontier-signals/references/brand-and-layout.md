# Brand and layout

## Identity

- Series: `Frontier Signals`.
- Publisher: `Frontier World`.
- Chinese brand: `前沿之境` when the parent brand needs to appear.
- Core idea: a passage into a future world, expressed through continuous structure and spatial depth rather than stock science-fiction decoration.

## Tokens

- blue: `#155EEF`;
- ink: `#101114`;
- canvas: `#FAFAF7`;
- white: `#FFFFFF`;
- mist: `#E8EEFF`;
- muted: `#5D626D`.

Use the Passage mark from `assets/`. Do not rotate, mirror, stretch, outline, glow, or place it inside another decorative symbol.

## Web

- Use semantic `<article>`, `<header>`, `<section>`, `<figure>`, and source list elements.
- Keep the reading column near 720 px and let the surrounding layout carry the brand.
- Use generous white space, strong typographic hierarchy, and blue as a decisive accent rather than a gradient wash.
- Use the platform system text stack for body copy and optical sizing where supported. For Chinese display text, keep tracking close to natural spacing (roughly `-0.012em` for H1 and `-0.01em` for H2); keep body tracking near zero and line height around `1.84–1.88`.
- Treat the OG image as social metadata. Do not repeat it in the article hero when the image already contains the title, date, or reading metadata; only render an in-page hero when it is an independent editorial visual.
- Use translucent material only for floating functional chrome such as a sticky header. Keep editorial callouts solid, legible, and restrained rather than turning every surface into glass.
- Give links and citation targets visible `:focus-visible` states, immediate `:active` feedback, and touch targets near 44 px. Provide `prefers-reduced-motion`, `prefers-reduced-transparency`, and `prefers-contrast` fallbacks.
- Include canonical metadata, Open Graph, JSON-LD `Article`, accessible image alt text, RSS, and sitemap.
- Published pages are indexable. Draft preview pages are private or `noindex`.

## WeChat

- Use inline styles only: no scripts, external CSS, CSS variables, Grid, or interactive controls.
- Maximum content width: 677 px; body text: 16 px; line height: roughly 1.9.
- Test at 375 px. Keep headings from becoming isolated single characters.
- Use the blue brand token for labels and callouts. Avoid ornamental borders around every paragraph.

## Feishu

- Preserve the same title, subtitle, section order, images, captions, and sources.
- Use Markdown for the first import and the media insertion workflow for local images.
- Keep one H1 title. Body sections begin at H2.

## Media rhythm

Follow the mode budgets in `editorial-playbook.md`: 3–5 production visuals for `quick` and 5–8 for `deep`, counting cover, OG, and inline visuals. The count never overrides the purpose test; place each inline image only after the reader has enough context to understand it.
