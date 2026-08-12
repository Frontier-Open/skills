const BRAND = {
  blue: "#155EEF",
  ink: "#101114",
  canvas: "#FAFAF7",
  white: "#FFFFFF",
  mist: "#E8EEFF",
  muted: "#5D626D",
};

const STATUS = new Set(["draft", "reviewed", "approved", "published"]);
const FORMATS = new Set(["commentary", "analysis", "deep-dive"]);
const SOURCE_TYPES = new Set(["primary", "reporting", "analysis", "social"]);

export const escapeHtml = (value = "") => String(value).replace(/[&<>"']/gu, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
})[character]);

const escapeMarkdown = (value = "") => String(value)
  .replace(/\\/gu, "\\\\")
  .replace(/([`*_\[\]$~])/gu, "\\$1")
  .replace(/</gu, "\\<");

export const dateLabel = (date) => String(date || "").replaceAll("-", ".");

function validHttpUrl(value, label) {
  try {
    const url = new URL(value);
    if (!/^https?:$/u.test(url.protocol)) throw new Error();
    return url;
  } catch {
    throw new Error(`${label} must be an HTTP(S) URL`);
  }
}

function assertText(value, label) {
  if (!String(value || "").trim()) throw new Error(`Missing ${label}`);
}

function assertMedia(media, label) {
  if (!media || typeof media !== "object") throw new Error(`Missing ${label}`);
  for (const field of ["path", "alt", "credit"]) assertText(media[field], `${label}.${field}`);
  if (/^(?:https?:|\/)/u.test(media.path) || media.path.includes("..")) {
    throw new Error(`${label}.path must be a safe local relative path`);
  }
  if (media.generated) {
    assertText(media.prompt_note, `${label}.prompt_note`);
  } else {
    validHttpUrl(media.source_url, `${label}.source_url`);
  }
}

export function assertArticle(article) {
  if (!article || typeof article !== "object") throw new Error("Article must be an object");
  if (article.schema_version !== 1) throw new Error("article.schema_version must be 1");
  if (article.series !== "Frontier Signals") throw new Error("article.series must be Frontier Signals");
  if (article.publisher !== "Frontier World") throw new Error("article.publisher must be Frontier World");
  if (article.author !== "Frontier World") throw new Error("article.author must be Frontier World");

  for (const field of [
    "id", "date", "slug", "timezone", "generated_at", "status", "format", "title",
    "subtitle", "thesis", "excerpt", "canonical_url", "angle_key",
  ]) assertText(article[field], `article.${field}`);

  if (!/^\d{4}-\d{2}-\d{2}$/u.test(article.date)) throw new Error("article.date must use YYYY-MM-DD");
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(article.slug)) throw new Error("article.slug must use lowercase hyphen-case");
  if (article.id !== `${article.date}/${article.slug}`) throw new Error("article.id must equal YYYY-MM-DD/slug");
  if (!STATUS.has(article.status)) throw new Error("article.status is invalid");
  if (!FORMATS.has(article.format)) throw new Error("article.format is invalid");
  if (!Number.isInteger(article.reading_minutes) || article.reading_minutes < 3 || article.reading_minutes > 20) {
    throw new Error("article.reading_minutes must be an integer from 3 to 20");
  }

  const canonical = validHttpUrl(article.canonical_url, "article.canonical_url");
  if (canonical.protocol !== "https:" || !canonical.pathname.endsWith(`/${article.slug}/`)) {
    throw new Error("article.canonical_url must be permanent HTTPS and end with /slug/");
  }

  if (!Array.isArray(article.story_keys) || !article.story_keys.length) {
    throw new Error("article.story_keys must contain at least one stable story key");
  }
  if (new Set(article.story_keys).size !== article.story_keys.length) throw new Error("article.story_keys must be unique");
  if (article.continuation_of && !String(article.material_update || "").trim()) {
    throw new Error("A continuation requires article.material_update");
  }
  if (!article.continuation_of && article.material_update) {
    throw new Error("article.material_update requires article.continuation_of");
  }

  if (!Array.isArray(article.intro) || article.intro.length < 1 || article.intro.length > 4) {
    throw new Error("article.intro must contain one to four paragraphs");
  }
  article.intro.forEach((paragraph, index) => assertText(paragraph, `article.intro[${index}]`));

  if (!Array.isArray(article.sections) || article.sections.length < 3 || article.sections.length > 6) {
    throw new Error("article.sections must contain three to six sections");
  }
  if (!Array.isArray(article.sources) || article.sources.length < 3) {
    throw new Error("article.sources must contain at least three sources");
  }

  const sourceIds = new Set();
  for (const [index, source] of article.sources.entries()) {
    for (const field of ["id", "publisher", "title", "url", "accessed_at", "source_type"]) {
      assertText(source[field], `article.sources[${index}].${field}`);
    }
    if (sourceIds.has(source.id)) throw new Error(`Duplicate source id: ${source.id}`);
    sourceIds.add(source.id);
    validHttpUrl(source.url, `article.sources[${index}].url`);
    if (!SOURCE_TYPES.has(source.source_type)) throw new Error(`Invalid source type: ${source.source_type}`);
  }

  const usedSourceIds = new Set();
  const recordSourceIds = (ids, label) => {
    if (ids === undefined) return;
    if (!Array.isArray(ids) || !ids.length) throw new Error(`${label} must not be empty`);
    ids.forEach((id) => {
      if (!sourceIds.has(id)) throw new Error(`Unknown source id in ${label}: ${id}`);
      usedSourceIds.add(id);
    });
  };
  recordSourceIds(article.intro_source_ids, "article.intro_source_ids");
  for (const [index, section] of article.sections.entries()) {
    for (const field of ["label", "title"]) assertText(section[field], `article.sections[${index}].${field}`);
    if (!Array.isArray(section.paragraphs) || !section.paragraphs.length) {
      throw new Error(`article.sections[${index}].paragraphs must not be empty`);
    }
    if (!Array.isArray(section.source_ids) || !section.source_ids.length) {
      throw new Error(`article.sections[${index}].source_ids must not be empty`);
    }
    recordSourceIds(section.source_ids, `section ${section.label}`);
    if (section.image) assertMedia(section.image, `article.sections[${index}].image`);
  }

  if (!article.conclusion || !Array.isArray(article.conclusion.paragraphs) || !article.conclusion.paragraphs.length) {
    throw new Error("article.conclusion.paragraphs must not be empty");
  }
  recordSourceIds(article.conclusion.source_ids, "article.conclusion.source_ids");
  const unused = [...sourceIds].filter((id) => !usedSourceIds.has(id));
  if (unused.length) throw new Error(`Unused sources: ${unused.join(", ")}`);
  assertMedia(article.media?.cover, "article.media.cover");
  assertMedia(article.media?.og, "article.media.og");
  return article;
}

function sourceIndex(article) {
  return new Map(article.sources.map((source, index) => [source.id, { ...source, index: index + 1 }]));
}

function markdownImage(image) {
  if (!image) return "";
  const caption = [image.caption, image.credit ? `来源：${image.credit}` : ""].filter(Boolean).join(" · ");
  return `![${escapeMarkdown(image.alt)}](${image.path})${caption ? `\n\n*${escapeMarkdown(caption)}*` : ""}`;
}

export function buildArticleMarkdown(article) {
  assertArticle(article);
  const sources = sourceIndex(article);
  const lines = [
    `# ${escapeMarkdown(article.title)}`,
    "",
    `> ${escapeMarkdown(article.subtitle)}`,
    "",
    `**${article.series} · ${dateLabel(article.date)} · ${article.reading_minutes} 分钟**`,
    "",
  ];

  article.intro.forEach((paragraph) => lines.push(escapeMarkdown(paragraph), ""));
  if (article.intro_source_ids?.length) {
    lines.push(`开篇来源：${article.intro_source_ids.map((id) => `[${sources.get(id).index}]`).join(" ")}`, "");
  }
  article.sections.forEach((section) => {
    lines.push(`## ${escapeMarkdown(section.label)} · ${escapeMarkdown(section.title)}`, "");
    section.paragraphs.forEach((paragraph) => lines.push(escapeMarkdown(paragraph), ""));
    if (section.image) lines.push(markdownImage(section.image), "");
    if (section.callout) lines.push(`> ${escapeMarkdown(section.callout)}`, "");
    if (Array.isArray(section.points) && section.points.length) {
      lines.push(...section.points.map((point) => `- ${escapeMarkdown(point)}`), "");
    }
    const sectionSources = section.source_ids.map((id) => sources.get(id));
    lines.push(`本节来源：${sectionSources.map((source) => `[${source.index}]`).join(" ")}`, "");
  });

  lines.push(`## ${escapeMarkdown(article.conclusion.title || "写在最后")}`, "");
  article.conclusion.paragraphs.forEach((paragraph) => lines.push(escapeMarkdown(paragraph), ""));
  if (article.conclusion.question) lines.push(`> ${escapeMarkdown(article.conclusion.question)}`, "");
  if (article.conclusion.source_ids?.length) {
    lines.push(`结尾来源：${article.conclusion.source_ids.map((id) => `[${sources.get(id).index}]`).join(" ")}`, "");
  }
  lines.push("## 参考资料", "");
  article.sources.forEach((source, index) => {
    lines.push(`${index + 1}. [${escapeMarkdown(source.publisher)} · ${escapeMarkdown(source.title)}](${source.url})`);
  });
  lines.push("", `— ${article.author}`, "");
  return lines.join("\n").replace(/\n{3,}/gu, "\n\n");
}

function inlineParagraphs(paragraphs = []) {
  return paragraphs.map((paragraph) => `<p style="margin:0 0 22px;color:${BRAND.ink};font-size:16px;line-height:1.95;text-align:justify;letter-spacing:0;">${escapeHtml(paragraph)}</p>`).join("");
}

function inlineFigure(image) {
  if (!image) return "";
  const caption = [image.caption, image.credit ? `来源：${image.credit}` : ""].filter(Boolean).join(" · ");
  return `<figure style="margin:30px 0 32px;"><img src="${escapeHtml(image.path)}" alt="${escapeHtml(image.alt)}" style="display:block;width:100%;height:auto;border:0;">${caption ? `<figcaption style="margin:9px 0 0;color:${BRAND.muted};font-size:12px;line-height:1.65;text-align:left;">${escapeHtml(caption)}</figcaption>` : ""}</figure>`;
}

function inlineCallout(text) {
  return text ? `<blockquote style="margin:28px 0;padding:19px 20px;border-left:4px solid ${BRAND.blue};background:${BRAND.mist};color:${BRAND.ink};font-size:17px;font-weight:700;line-height:1.8;">${escapeHtml(text)}</blockquote>` : "";
}

function inlinePoints(points = []) {
  if (!points.length) return "";
  return `<section style="margin:26px 0;padding:20px 22px;background:${BRAND.canvas};border:1px solid #D7DDEA;">${points.map((point, index) => `<p style="margin:${index ? "14px" : "0"} 0 0;color:${BRAND.ink};font-size:15px;line-height:1.85;"><strong style="color:${BRAND.blue};">${String(index + 1).padStart(2, "0")}</strong>&nbsp;&nbsp;${escapeHtml(point)}</p>`).join("")}</section>`;
}

export function buildWechatHtml(article) {
  assertArticle(article);
  const sources = sourceIndex(article);
  const introCitations = article.intro_source_ids?.map((id) => sources.get(id).index).join(" · ");
  const conclusionCitations = article.conclusion.source_ids?.map((id) => sources.get(id).index).join(" · ");
  const sections = article.sections.map((section) => {
    const citations = section.source_ids.map((id) => sources.get(id).index).join(" · ");
    return `<section style="margin:48px 0 0;">
      <p style="margin:0 0 9px;color:${BRAND.blue};font-size:12px;font-weight:700;line-height:1.4;letter-spacing:1px;">${escapeHtml(section.label)} / FRONTIER SIGNALS</p>
      <h2 style="margin:0 0 24px;color:${BRAND.ink};font-size:23px;font-weight:800;line-height:1.45;">${escapeHtml(section.title)}</h2>
      ${inlineParagraphs(section.paragraphs)}
      ${inlineFigure(section.image)}
      ${inlineCallout(section.callout)}
      ${inlinePoints(section.points)}
      <p style="margin:18px 0 0;color:#858A95;font-size:11px;line-height:1.6;">本节来源 ${citations}</p>
    </section>`;
  }).join("");
  const sourceHtml = article.sources.map((source, index) => `<p style="margin:${index ? "10px" : "0"} 0 0;color:#737985;font-size:12px;line-height:1.7;">${index + 1}. <a href="${escapeHtml(source.url)}" style="color:#737985;text-decoration:underline;">${escapeHtml(source.publisher)} · ${escapeHtml(source.title)}</a></p>`).join("");

  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(article.title)} · Frontier Signals</title></head>
<body style="margin:0;background:#ffffff;color:${BRAND.ink};font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">
  <article style="box-sizing:border-box;max-width:677px;margin:0 auto;padding:24px 20px 52px;background:#ffffff;">
    <p style="margin:0 0 18px;color:${BRAND.blue};font-size:12px;font-weight:700;line-height:1.4;letter-spacing:1px;">FRONTIER SIGNALS · ${dateLabel(article.date)}</p>
    <h1 style="margin:0;color:${BRAND.ink};font-size:30px;font-weight:900;line-height:1.35;">${escapeHtml(article.title)}</h1>
    <p style="margin:18px 0 28px;color:${BRAND.muted};font-size:15px;line-height:1.8;">${escapeHtml(article.subtitle)}</p>
    ${inlineFigure(article.media.cover)}
    <section style="margin:0;padding:0 0 8px;">${inlineParagraphs(article.intro)}${introCitations ? `<p style="margin:4px 0 0;color:#858A95;font-size:11px;line-height:1.6;">开篇来源 ${introCitations}</p>` : ""}</section>
    ${sections}
    <section style="margin:50px 0 0;padding-top:30px;border-top:2px solid ${BRAND.ink};">
      <h2 style="margin:0 0 24px;color:${BRAND.ink};font-size:23px;font-weight:800;line-height:1.45;">${escapeHtml(article.conclusion.title || "写在最后")}</h2>
      ${inlineParagraphs(article.conclusion.paragraphs)}
      ${inlineCallout(article.conclusion.question)}
      ${conclusionCitations ? `<p style="margin:18px 0 0;color:#858A95;font-size:11px;line-height:1.6;">结尾来源 ${conclusionCitations}</p>` : ""}
    </section>
    <section style="margin:44px 0 0;padding:22px 0 0;border-top:1px solid #D9DCE4;"><p style="margin:0 0 14px;color:${BRAND.ink};font-size:13px;font-weight:700;letter-spacing:1px;">参考资料</p>${sourceHtml}</section>
    <footer style="margin:42px 0 0;padding:22px 0 0;border-top:1px solid ${BRAND.ink};text-align:center;"><p style="margin:0;color:${BRAND.ink};font-size:13px;font-weight:800;letter-spacing:1px;">FRONTIER SIGNALS</p><p style="margin:8px 0 0;color:#858A95;font-size:11px;line-height:1.7;">Frontier World · 把前沿变成实践</p></footer>
  </article>
</body></html>\n`;
}

function webFigure(image) {
  if (!image) return "";
  const caption = [image.caption, image.credit ? `来源：${image.credit}` : ""].filter(Boolean).join(" · ");
  return `<figure class="article-media"><img src="${escapeHtml(image.path)}" alt="${escapeHtml(image.alt)}" loading="lazy" decoding="async">${caption ? `<figcaption>${escapeHtml(caption)}</figcaption>` : ""}</figure>`;
}

function safeJson(value) {
  return JSON.stringify(value).replace(/</gu, "\\u003c");
}

export function buildWebHtml(article) {
  assertArticle(article);
  const sources = sourceIndex(article);
  const modeLabel = String(article.mode || article.format).toUpperCase();
  const ogUrl = new URL(article.media.og.path, article.canonical_url).href;
  const robots = article.status === "published" ? "index,follow,max-image-preview:large" : "noindex,nofollow,noarchive";
  const sectionHtml = article.sections.map((section) => {
    const citations = section.source_ids.map((id) => {
      const source = sources.get(id);
      return `<a href="#source-${source.index}" aria-label="参考资料 ${source.index}">${source.index}</a>`;
    }).join("");
    return `<section class="article-section"><div class="section-label">${escapeHtml(section.label)} / FRONTIER SIGNALS</div><h2>${escapeHtml(section.title)}</h2>${section.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}${webFigure(section.image)}${section.callout ? `<blockquote>${escapeHtml(section.callout)}</blockquote>` : ""}${Array.isArray(section.points) && section.points.length ? `<ol class="points">${section.points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ol>` : ""}<div class="citations">本节来源 ${citations}</div></section>`;
  }).join("");
  const sourceHtml = article.sources.map((source, index) => `<li id="source-${index + 1}"><span>${String(index + 1).padStart(2, "0")}</span><a href="${escapeHtml(source.url)}" rel="noopener noreferrer">${escapeHtml(source.publisher)} · ${escapeHtml(source.title)}</a></li>`).join("");
  const inlineCitations = (ids = [], label) => ids.length ? `<div class="citations">${label} ${ids.map((id) => `<a href="#source-${sources.get(id).index}" aria-label="参考资料 ${sources.get(id).index}">${sources.get(id).index}</a>`).join("")}</div>` : "";
  const introCitations = inlineCitations(article.intro_source_ids, "开篇来源");
  const conclusionCitations = inlineCitations(article.conclusion.source_ids, "结尾来源");
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.excerpt,
    datePublished: article.date,
    dateModified: article.generated_at,
    mainEntityOfPage: article.canonical_url,
    image: [ogUrl],
    author: { "@type": "Organization", name: article.author },
    publisher: { "@type": "Organization", name: article.publisher, url: "https://frontierworld.ai/" },
  };

  const css = `
:root {
  --blue: ${BRAND.blue};
  --ink: ${BRAND.ink};
  --canvas: ${BRAND.canvas};
  --white: ${BRAND.white};
  --mist: ${BRAND.mist};
  --muted: ${BRAND.muted};
  --line: rgba(16, 17, 20, .14);
  --surface: rgba(255, 255, 255, .64);
  --font-text: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
html {
  scroll-behavior: smooth;
  scroll-padding-top: 6rem;
  background: var(--canvas);
}
body {
  min-width: 320px;
  margin: 0;
  color: var(--ink);
  background: var(--canvas);
  font-family: var(--font-text);
  font-optical-sizing: auto;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
::selection { color: var(--white); background: var(--blue); }
a {
  color: inherit;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
a:focus-visible {
  outline: 3px solid var(--blue);
  outline-offset: 3px;
  border-radius: .25rem;
}
.skip-link {
  position: fixed;
  top: .75rem;
  left: .75rem;
  z-index: 40;
  padding: .75rem 1rem;
  color: var(--white);
  background: var(--blue);
  font-size: .875rem;
  font-weight: 700;
  text-decoration: none;
  transform: translateY(-150%);
}
.skip-link:focus { transform: translateY(0); }
#article-body:focus { outline: none; }
.site-header {
  position: sticky;
  top: 0;
  z-index: 20;
  min-height: 4.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: env(safe-area-inset-top) max(1.25rem, 4.5vw) 0;
  background: rgba(250, 250, 247, .76);
  -webkit-backdrop-filter: blur(22px) saturate(180%);
  backdrop-filter: blur(22px) saturate(180%);
  box-shadow: 0 1px 0 rgba(16, 17, 20, .08), 0 .75rem 2rem rgba(16, 17, 20, .025);
}
.brand, .archive-link, .citations a, .sources a {
  transition: color 160ms ease, background-color 160ms ease, transform 100ms ease-out;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: .625rem;
  min-height: 2.75rem;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.0625rem;
  font-weight: 800;
  letter-spacing: -.018em;
  text-decoration: none;
  transform-origin: left center;
}
.mark {
  width: 1.5rem;
  height: 1.5rem;
  flex: 0 0 auto;
  background: var(--blue);
  clip-path: polygon(0 0, 100% 0, 100% 100%, 68% 100%, 79% 24%, 64% 24%, 43% 100%, 0 100%);
}
.archive-link {
  display: inline-flex;
  align-items: center;
  min-height: 2.75rem;
  margin-right: -.75rem;
  padding: 0 .75rem;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 600;
  letter-spacing: .025em;
  text-decoration: none;
  transform-origin: right center;
}
main { overflow: clip; }
.article-head {
  width: min(56rem, calc(100% - 2.5rem));
  margin: 0 auto;
  padding: clamp(4.75rem, 8vw, 7rem) 0 clamp(3.5rem, 6vw, 5rem);
}
.kicker {
  margin-bottom: 1.5rem;
  color: var(--blue);
  font-size: .75rem;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: .085em;
  text-transform: uppercase;
}
.article-head h1 {
  max-width: 14em;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.75rem, 5.6vw, 5.25rem);
  font-weight: 800;
  line-height: 1.07;
  letter-spacing: -.012em;
  text-wrap: balance;
}
.subtitle {
  max-width: 42rem;
  margin: 1.875rem 0 0;
  color: var(--muted);
  font-size: clamp(1.0625rem, 1.4vw, 1.1875rem);
  line-height: 1.72;
  letter-spacing: 0;
  text-wrap: pretty;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
  margin-top: 1.75rem;
  color: var(--muted);
  font-size: .6875rem;
  font-weight: 600;
  letter-spacing: .045em;
}
.meta span {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0 .75rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
}
.article-body {
  width: min(43.5rem, calc(100% - 2.5rem));
  margin: 0 auto;
  padding: clamp(3.5rem, 6vw, 5rem) 0 clamp(6rem, 10vw, 9rem);
  border-top: 1px solid var(--line);
}
.lede {
  color: var(--ink);
  font-size: clamp(1.125rem, 1.5vw, 1.25rem);
  line-height: 1.84;
  letter-spacing: 0;
}
.lede p { margin: 0 0 1.5em; text-wrap: pretty; }
.article-section {
  padding-top: clamp(4.75rem, 8vw, 6.25rem);
  scroll-margin-top: 6rem;
}
.section-label {
  color: var(--blue);
  font-size: .6875rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: .105em;
  text-transform: uppercase;
}
.article-section h2, .conclusion h2 {
  margin: .875rem 0 1.75rem;
  font-family: var(--font-display);
  font-size: clamp(1.875rem, 3.5vw, 2.75rem);
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: -.01em;
  text-wrap: balance;
}
.article-section p, .conclusion p {
  margin: 0 0 1.35em;
  font-size: 1.125rem;
  line-height: 1.86;
  letter-spacing: .002em;
  text-wrap: pretty;
}
.article-section blockquote, .conclusion blockquote {
  width: min(48rem, calc(100vw - 2.5rem));
  margin: 2.75rem 50%;
  padding: 1.75rem 2rem;
  border: 1px solid rgba(21, 94, 239, .13);
  border-radius: 1rem;
  color: var(--ink);
  background: var(--mist);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .62);
  font-size: clamp(1.125rem, 2vw, 1.3125rem);
  font-weight: 600;
  line-height: 1.65;
  letter-spacing: -.003em;
  text-wrap: pretty;
  transform: translateX(-50%);
}
.article-media {
  width: min(52rem, calc(100vw - 2.5rem));
  margin: 3rem 50%;
  transform: translateX(-50%);
}
.article-media img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid rgba(16, 17, 20, .08);
  border-radius: .75rem;
  background: var(--white);
  box-shadow: 0 1.5rem 4rem rgba(16, 17, 20, .08);
}
.article-media figcaption {
  max-width: 43.5rem;
  margin: .75rem auto 0;
  color: var(--muted);
  font-size: .75rem;
  line-height: 1.6;
  letter-spacing: .01em;
}
.points {
  counter-reset: point;
  margin: 2.25rem 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 1rem;
  background: var(--surface);
  list-style: none;
}
.points li {
  counter-increment: point;
  display: grid;
  grid-template-columns: 2.25rem 1fr;
  gap: .875rem;
  padding: 1.25rem;
  font-size: 1.0625rem;
  line-height: 1.72;
}
.points li + li { border-top: 1px solid var(--line); }
.points li::before {
  content: counter(point, decimal-leading-zero);
  padding-top: .15rem;
  color: var(--blue);
  font-size: .6875rem;
  font-weight: 700;
  letter-spacing: .06em;
}
.citations {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .5rem;
  margin-top: 1.75rem;
  color: var(--muted);
  font-size: .75rem;
  line-height: 1.4;
}
.citations a {
  display: inline-grid;
  place-items: center;
  min-width: 2.75rem;
  min-height: 2.75rem;
  border: 1px solid var(--line);
  border-radius: 50%;
  color: var(--blue);
  background: var(--surface);
  font-weight: 700;
  text-decoration: none;
}
.conclusion {
  margin-top: clamp(5.5rem, 9vw, 7.5rem);
  padding-top: clamp(3.5rem, 6vw, 4.75rem);
  border-top: 1px solid var(--ink);
  scroll-margin-top: 6rem;
}
.sources {
  margin-top: clamp(5rem, 8vw, 7rem);
  padding: 2rem;
  border: 1px solid var(--line);
  border-radius: 1.25rem;
  background: var(--surface);
}
.sources h2 {
  margin: 0 0 1rem;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: .01em;
}
.sources ol { margin: 0; padding: 0; list-style: none; }
.sources li {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  gap: .75rem;
  padding: .875rem 0;
  border-bottom: 1px solid var(--line);
  font-size: .8125rem;
  line-height: 1.65;
  scroll-margin-top: 6rem;
}
.sources li:last-child { padding-bottom: 0; border-bottom: 0; }
.sources li span { color: var(--blue); font-weight: 700; }
.sources a {
  overflow-wrap: anywhere;
  text-decoration: underline;
  text-decoration-color: rgba(16, 17, 20, .24);
  text-underline-offset: .2em;
  transform-origin: left center;
}
.site-footer {
  display: flex;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 2.25rem max(1.25rem, 4.5vw) max(2.25rem, env(safe-area-inset-bottom));
  color: var(--white);
  background: var(--blue);
  font-size: .75rem;
  font-weight: 600;
  letter-spacing: .015em;
}
.brand:active, .archive-link:active, .citations a:active, .sources a:active { transform: scale(.97); }
@media (hover: hover) {
  .archive-link:hover, .sources a:hover { color: var(--blue); }
  .archive-link:hover, .citations a:hover { background: rgba(21, 94, 239, .08); }
}
@media (max-width: 760px) {
  .article-head { padding-top: 4.25rem; padding-bottom: 3.25rem; }
  .article-head h1 { font-size: clamp(2.625rem, 11vw, 3.5rem); line-height: 1.1; }
  .article-body { padding-top: 3.5rem; }
  .article-section { padding-top: 4.5rem; }
  .article-section p, .conclusion p { font-size: 1.0625rem; line-height: 1.84; }
  .article-section blockquote, .conclusion blockquote {
    width: 100%;
    margin: 2.25rem 0;
    padding: 1.5rem;
    transform: none;
  }
  .article-media { width: 100%; margin: 2.5rem 0; transform: none; }
  .points li { padding: 1.125rem; }
  .sources { padding: 1.5rem; }
  .site-footer { flex-direction: column; }
}
@media (max-width: 420px) {
  .site-header { padding-left: 1.25rem; padding-right: 1.25rem; }
  .brand { font-size: 1rem; }
  .archive-link { margin-right: -.625rem; padding: 0 .625rem; }
  .article-head, .article-body { width: calc(100% - 2.5rem); }
  .article-head h1 { font-size: clamp(2.5rem, 11.25vw, 3rem); }
  .subtitle { margin-top: 1.5rem; font-size: 1.0625rem; }
  .article-section h2, .conclusion h2 { font-size: 1.875rem; }
  .article-section blockquote, .conclusion blockquote { border-radius: .875rem; }
  .points { border-radius: .875rem; }
  .sources { border-radius: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .brand, .archive-link, .citations a, .sources a { transition: color 120ms linear, background-color 120ms linear; }
  .brand:active, .archive-link:active, .citations a:active, .sources a:active { transform: none; }
}
@media (prefers-reduced-transparency: reduce) {
  .site-header {
    background: var(--canvas);
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
  }
  .meta span, .points, .citations a, .sources { background: var(--white); }
}
@media (prefers-contrast: more) {
  :root { --muted: #34363B; --line: rgba(16, 17, 20, .44); }
  .site-header { background: var(--canvas); box-shadow: 0 2px 0 var(--ink); }
  .meta span, .points, .citations a, .sources { background: var(--white); border-color: var(--ink); }
}
`;

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>${escapeHtml(article.title)} · Frontier Signals</title>
  <meta name="description" content="${escapeHtml(article.excerpt)}">
  <meta name="robots" content="${robots}">
  <link rel="canonical" href="${escapeHtml(article.canonical_url)}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="${escapeHtml(article.title)}">
  <meta property="og:description" content="${escapeHtml(article.excerpt)}">
  <meta property="og:url" content="${escapeHtml(article.canonical_url)}">
  <meta property="og:image" content="${escapeHtml(ogUrl)}">
  <meta property="og:image:alt" content="${escapeHtml(article.media.og.alt)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:site_name" content="Frontier Signals">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${escapeHtml(article.title)}">
  <meta name="twitter:description" content="${escapeHtml(article.excerpt)}">
  <meta name="twitter:image" content="${escapeHtml(ogUrl)}">
  <script type="application/ld+json">${safeJson(jsonLd)}</script>
  <style>${css}</style>
</head>
<body>
  <a class="skip-link" href="#article-body">跳到正文</a>
  <header class="site-header">
    <a class="brand" href="/"><span class="mark" aria-hidden="true"></span><span>Frontier Signals</span></a>
    <a class="archive-link" href="/">全部文章 ↗</a>
  </header>
  <main>
    <article class="article-page">
      <header class="article-head">
        <div class="kicker">FRONTIER SIGNALS · ${dateLabel(article.date)}</div>
        <h1>${escapeHtml(article.title)}</h1>
        <p class="subtitle">${escapeHtml(article.subtitle)}</p>
        <div class="meta" aria-label="文章信息"><span>${escapeHtml(modeLabel)}</span><span>${article.reading_minutes} 分钟阅读</span><span>${escapeHtml(article.author)}</span></div>
      </header>
      <div class="article-body" id="article-body" tabindex="-1">
        <section class="lede">${article.intro.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}${introCitations}</section>
        ${sectionHtml}
        <section class="conclusion"><h2>${escapeHtml(article.conclusion.title || "写在最后")}</h2>${article.conclusion.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}${article.conclusion.question ? `<blockquote>${escapeHtml(article.conclusion.question)}</blockquote>` : ""}${conclusionCitations}</section>
        <section class="sources"><h2>参考资料</h2><ol>${sourceHtml}</ol></section>
      </div>
    </article>
  </main>
  <footer class="site-footer"><span>Frontier World · 前沿之境</span><span>Turn the frontier into practice.</span></footer>
</body>
</html>
`;
}
