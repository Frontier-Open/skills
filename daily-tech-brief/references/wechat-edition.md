# WeChat Edition

Create the WeChat Official Account edition only after the day's ten briefing items pass sourcing and cross-issue duplicate checks.

## Editorial shape

- Use the strongest daily thesis as the article spine. Do not reproduce the briefing as a ten-item list.
- Connect three to five verified facts into one original argument, then give the reader a practical implication.
- Keep the title concise and curiosity-driven without using clickbait or unsupported certainty.
- Attribute metrics and claims in the prose when their source matters. List every source used at the end.
- Keep the article useful to a public audience. Do not mention a private recipient or internal delivery workflow.
- Use `Frontier World` exactly as the default publication brand. Never present the edition as a private briefing for one person.

## Layout contract

- Produce `wechat-article.json`, `wechat.md`, `wechat.html`, and `wechat-cover.jpg` together under `drafts/wechat/YYYY/MM/DD/`.
- Use `scripts/render-wechat.mjs` to render both text editions from `wechat-article.json`.
- Use a 2.35:1 cover, preferably 900 by 383 pixels. Keep focal content inside the center crop-safe area and avoid text in generated cover art.
- Keep all WeChat HTML styling inline. Do not use scripts, external CSS, CSS variables, Grid, or interactive controls.
- Use a 677 px maximum article width, 16 px body text, approximately 1.9 line height, clear section titles, restrained callouts, and visible source links.
- Treat the output as a draft. Do not upload or publish it to a WeChat Official Account unless the user explicitly authorizes publication and confirms the account and final draft.

## Structured article

Use this shape:

```json
{
  "brand": "PUBLICATION NAME",
  "author": "Publication Name",
  "date": "YYYY-MM-DD",
  "title": "Article title",
  "subtitle": "One-sentence premise",
  "cover": "./cover.jpg",
  "intro": ["Paragraph"],
  "sections": [
    {
      "label": "01",
      "title": "Section title",
      "paragraphs": ["Paragraph"],
      "callout": "Optional key judgment",
      "points": ["Optional action"]
    }
  ],
  "conclusion": {
    "title": "写在最后",
    "paragraphs": ["Paragraph"],
    "question": "Closing question"
  },
  "sources": [{ "label": "Publisher · Story", "url": "https://..." }],
  "footer": "Optional publication description"
}
```
