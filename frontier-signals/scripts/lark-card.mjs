import { assertArticle, dateLabel } from "./article.mjs";

function validDocumentUrl(value) {
  return /^https:\/\/[^/]+\/(?:docx|wiki)\/[A-Za-z0-9_-]+/u.test(value || "");
}

export function buildLarkCard(article, { imageKey, documentUrl } = {}) {
  assertArticle(article);
  if (!validDocumentUrl(documentUrl)) throw new Error("A valid Feishu document URL is required");

  const judgments = article.sections
    .map((section) => section.callout || section.title)
    .slice(0, 3)
    .map((text, index) => `${index + 1}. **${text}**`)
    .join("\n");
  const elements = [];
  if (imageKey) {
    elements.push({
      tag: "img",
      img_key: imageKey,
      mode: "crop_center",
      compact_width: false,
      alt: { tag: "plain_text", content: article.media.cover.alt },
    });
  }
  elements.push(
    {
      tag: "div",
      text: { tag: "lark_md", content: `**${article.title}**\n${article.excerpt}` },
    },
    { tag: "hr" },
    {
      tag: "div",
      text: { tag: "lark_md", content: `**三个判断**\n${judgments}` },
    },
    {
      tag: "note",
      elements: [{ tag: "plain_text", content: `${article.mode || article.format} · ${article.reading_minutes} 分钟阅读 · 待审核` }],
    },
    {
      tag: "action",
      actions: [
        {
          tag: "button",
          type: "default",
          text: { tag: "plain_text", content: "飞书全文" },
          url: documentUrl,
        },
        {
          tag: "button",
          type: "primary",
          text: { tag: "plain_text", content: `查看官网 · ${article.reading_minutes}分钟` },
          url: article.canonical_url,
        },
      ],
    },
  );
  return {
    config: { wide_screen_mode: true, enable_forward: true },
    header: {
      template: "blue",
      title: { tag: "plain_text", content: `Frontier Signals · ${dateLabel(article.date)}` },
    },
    elements,
  };
}
