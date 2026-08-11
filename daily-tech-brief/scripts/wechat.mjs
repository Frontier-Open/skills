const escapeHtml = (value = "") => String(value)
  .replace(/&/gu, "&amp;")
  .replace(/</gu, "&lt;")
  .replace(/>/gu, "&gt;")
  .replace(/"/gu, "&quot;")
  .replace(/'/gu, "&#39;");

const formatDate = (value) => String(value || "").replace(/-/gu, ".");

function assertArticle(article) {
  for (const field of ["brand", "date", "title", "subtitle", "cover"]) {
    if (!String(article[field] || "").trim()) throw new Error(`Missing article.${field}`);
  }
  if (!Array.isArray(article.intro) || article.intro.length < 1) {
    throw new Error("article.intro must contain at least one paragraph");
  }
  if (!Array.isArray(article.sections) || article.sections.length < 3) {
    throw new Error("article.sections must contain at least three sections");
  }
  if (!Array.isArray(article.sources) || article.sources.length < 1) {
    throw new Error("article.sources must contain at least one source");
  }
  for (const [index, source] of article.sources.entries()) {
    try {
      const url = new URL(source.url);
      if (!/^https?:$/u.test(url.protocol)) throw new Error();
    } catch {
      throw new Error(`article.sources[${index}].url must be an HTTP URL`);
    }
  }
}

function markdownParagraphs(paragraphs = []) {
  return paragraphs.map((paragraph) => `${paragraph}\n`).join("\n");
}

export function buildWechatMarkdown(article) {
  assertArticle(article);
  const lines = [
    `# ${article.title}`,
    "",
    `> ${article.subtitle}`,
    "",
    `**${article.brand} · ${formatDate(article.date)}**`,
    "",
    `![${article.title}](${article.cover})`,
    "",
    markdownParagraphs(article.intro).trimEnd(),
    "",
  ];

  article.sections.forEach((section, index) => {
    lines.push(`## ${section.label || String(index + 1).padStart(2, "0")} · ${section.title}`, "");
    lines.push(markdownParagraphs(section.paragraphs).trimEnd(), "");
    if (section.callout) lines.push(`> ${section.callout}`, "");
    if (Array.isArray(section.points) && section.points.length) {
      lines.push(...section.points.map((point) => `- ${point}`), "");
    }
  });

  if (article.conclusion) {
    lines.push(`## ${article.conclusion.title || "写在最后"}`, "");
    lines.push(markdownParagraphs(article.conclusion.paragraphs).trimEnd(), "");
    if (article.conclusion.question) lines.push(`> ${article.conclusion.question}`, "");
  }

  lines.push("## 参考资料", "");
  lines.push(...article.sources.map((source, index) => `${index + 1}. [${source.label}](${source.url})`), "");
  lines.push(`— ${article.author || article.brand}`, "");
  return `${lines.join("\n").replace(/\n{3,}/gu, "\n\n").trim()}\n`;
}

function htmlParagraphs(paragraphs = []) {
  return paragraphs.map((paragraph) => `<p style="margin:0 0 22px;color:#242424;font-size:16px;line-height:1.95;text-align:justify;letter-spacing:0;">${escapeHtml(paragraph)}</p>`).join("");
}

function htmlCallout(text) {
  if (!text) return "";
  return `<blockquote style="margin:28px 0;padding:18px 20px;border-left:4px solid #ff5733;background:#f7f6f3;color:#191919;font-size:17px;font-weight:700;line-height:1.8;letter-spacing:0;">${escapeHtml(text)}</blockquote>`;
}

function htmlPoints(points = []) {
  if (!points.length) return "";
  return `<section style="margin:26px 0;padding:20px 22px;background:#f7f6f3;border:1px solid #e7e4df;">${points.map((point, index) => `<p style="margin:${index ? "14px" : "0"} 0 0;color:#242424;font-size:15px;line-height:1.85;letter-spacing:0;"><strong style="color:#d4471d;">${String(index + 1).padStart(2, "0")}</strong>&nbsp;&nbsp;${escapeHtml(point)}</p>`).join("")}</section>`;
}

export function buildWechatHtml(article) {
  assertArticle(article);
  const sections = article.sections.map((section, index) => `
    <section style="margin:46px 0 0;">
      <p style="margin:0 0 9px;color:#d4471d;font-size:12px;font-weight:700;line-height:1.4;letter-spacing:1px;">${escapeHtml(section.label || String(index + 1).padStart(2, "0"))} / SIGNAL</p>
      <h2 style="margin:0 0 24px;color:#111111;font-size:23px;font-weight:800;line-height:1.45;letter-spacing:0;">${escapeHtml(section.title)}</h2>
      ${htmlParagraphs(section.paragraphs)}
      ${htmlCallout(section.callout)}
      ${htmlPoints(section.points)}
    </section>`).join("");

  const conclusion = article.conclusion ? `
    <section style="margin:48px 0 0;padding-top:30px;border-top:2px solid #111111;">
      <h2 style="margin:0 0 24px;color:#111111;font-size:23px;font-weight:800;line-height:1.45;letter-spacing:0;">${escapeHtml(article.conclusion.title || "写在最后")}</h2>
      ${htmlParagraphs(article.conclusion.paragraphs)}
      ${htmlCallout(article.conclusion.question)}
    </section>` : "";

  const sources = article.sources.map((source, index) => `<p style="margin:${index ? "10px" : "0"} 0 0;color:#7a7772;font-size:12px;line-height:1.7;letter-spacing:0;">${index + 1}. <a href="${escapeHtml(source.url)}" style="color:#7a7772;text-decoration:underline;">${escapeHtml(source.label)}</a></p>`).join("");

  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>${escapeHtml(article.title)} · ${escapeHtml(article.brand)}</title>
  </head>
  <body style="margin:0;background:#ffffff;color:#111111;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">
    <section style="box-sizing:border-box;max-width:677px;margin:0 auto;padding:24px 20px 52px;background:#ffffff;">
      <p style="margin:0 0 18px;color:#d4471d;font-size:12px;font-weight:700;line-height:1.4;letter-spacing:1px;">${escapeHtml(article.brand.toUpperCase())} · ${formatDate(article.date)}</p>
      <h1 style="margin:0;color:#111111;font-size:30px;font-weight:900;line-height:1.35;letter-spacing:0;">${escapeHtml(article.title)}</h1>
      <p style="margin:18px 0 28px;color:#6f6d69;font-size:15px;line-height:1.8;letter-spacing:0;">${escapeHtml(article.subtitle)}</p>
      <img src="${escapeHtml(article.cover)}" alt="${escapeHtml(article.title)}" style="display:block;width:100%;height:auto;margin:0 0 34px;border:0;">
      <section style="margin:0;padding:0 0 8px;">
        ${htmlParagraphs(article.intro)}
      </section>
      ${sections}
      ${conclusion}
      <section style="margin:44px 0 0;padding:22px 0 0;border-top:1px solid #dedbd6;">
        <p style="margin:0 0 14px;color:#111111;font-size:13px;font-weight:700;line-height:1.5;letter-spacing:1px;">参考资料</p>
        ${sources}
      </section>
      <footer style="margin:42px 0 0;padding:22px 0 0;border-top:1px solid #111111;text-align:center;">
        <p style="margin:0;color:#111111;font-size:13px;font-weight:800;line-height:1.5;letter-spacing:1px;">${escapeHtml(article.brand.toUpperCase())}</p>
        <p style="margin:8px 0 0;color:#8b8883;font-size:11px;line-height:1.7;letter-spacing:0;">${escapeHtml(article.footer || "")}</p>
      </footer>
    </section>
  </body>
</html>
`;
}
