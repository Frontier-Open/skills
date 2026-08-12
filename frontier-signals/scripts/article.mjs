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

function webFigure(image, hero = false) {
  if (!image) return "";
  const caption = [image.caption, image.credit ? `来源：${image.credit}` : ""].filter(Boolean).join(" · ");
  return `<figure class="${hero ? "hero-media" : "article-media"}"><img src="${escapeHtml(image.path)}" alt="${escapeHtml(image.alt)}">${caption ? `<figcaption>${escapeHtml(caption)}</figcaption>` : ""}</figure>`;
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

  const css = `:root{--blue:${BRAND.blue};--ink:${BRAND.ink};--canvas:${BRAND.canvas};--white:${BRAND.white};--mist:${BRAND.mist};--muted:${BRAND.muted};--line:rgba(16,17,20,.15)}*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--canvas)}body{margin:0;color:var(--ink);background:var(--canvas);font-family:"Avenir Next","SF Pro Display","PingFang SC","Helvetica Neue",sans-serif;-webkit-font-smoothing:antialiased}a{color:inherit}.site-header{height:72px;display:flex;align-items:center;justify-content:space-between;padding:0 4.5vw;border-bottom:1px solid var(--line);background:rgba(250,250,247,.92);backdrop-filter:blur(16px)}.brand{display:flex;align-items:center;gap:11px;text-decoration:none;font-size:18px;font-weight:800}.mark{width:26px;height:26px;background:var(--blue);clip-path:polygon(0 0,100% 0,100% 100%,68% 100%,79% 24%,64% 24%,43% 100%,0 100%)}.archive-link{text-decoration:none;font-size:12px;font-weight:750}.archive-link:hover{color:var(--blue)}main{overflow:hidden}.article-head{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,.72fr);gap:6vw;align-items:end;padding:7vw 4.5vw 5vw}.kicker{margin-bottom:24px;color:var(--blue);font-size:12px;font-weight:800;letter-spacing:.13em}.article-head h1{max-width:900px;margin:0;font-size:clamp(48px,6.2vw,100px);line-height:.97;letter-spacing:-.045em}.subtitle{max-width:720px;margin:32px 0 0;color:var(--muted);font-size:19px;line-height:1.75}.meta{display:flex;gap:18px;margin-top:28px;font-size:12px;font-weight:700}.hero-media{margin:0;background:var(--blue)}.hero-media img{display:block;width:100%;height:auto;aspect-ratio:1.91/1;object-fit:cover}.hero-media figcaption,.article-media figcaption{padding:10px 0;color:var(--muted);font-size:12px;line-height:1.6}.article-body{width:min(760px,calc(100% - 40px));margin:0 auto;padding:80px 0 120px}.lede{font-size:21px;line-height:1.9}.lede p{margin:0 0 28px}.article-section{padding:64px 0 0}.section-label{color:var(--blue);font-size:11px;font-weight:800;letter-spacing:.13em}.article-section h2,.conclusion h2{margin:14px 0 30px;font-size:clamp(32px,4vw,52px);line-height:1.12;letter-spacing:-.03em}.article-section p,.conclusion p{margin:0 0 24px;font-size:18px;line-height:1.95}.article-section blockquote,.conclusion blockquote{margin:38px -5vw;padding:34px 5vw;border-left:5px solid var(--blue);background:var(--mist);font-size:24px;font-weight:750;line-height:1.55}.article-media{margin:38px 0}.article-media img{display:block;width:100%;height:auto}.points{counter-reset:point;margin:34px 0;padding:0;list-style:none}.points li{counter-increment:point;display:grid;grid-template-columns:36px 1fr;gap:14px;padding:18px 0;border-top:1px solid var(--line);font-size:17px;line-height:1.7}.points li:before{content:counter(point,decimal-leading-zero);color:var(--blue);font-size:11px;font-weight:800}.citations{display:flex;align-items:center;gap:8px;margin-top:28px;color:var(--muted);font-size:12px}.citations a{display:inline-grid;place-items:center;width:24px;height:24px;border:1px solid var(--line);border-radius:50%;color:var(--blue);text-decoration:none}.conclusion{margin-top:78px;padding-top:48px;border-top:2px solid var(--ink)}.sources{margin-top:80px;padding-top:36px;border-top:1px solid var(--line)}.sources h2{font-size:18px}.sources ol{margin:0;padding:0;list-style:none}.sources li{display:grid;grid-template-columns:36px 1fr;gap:12px;padding:13px 0;border-bottom:1px solid var(--line);font-size:13px;line-height:1.6}.sources li span{color:var(--blue);font-weight:800}.sources a{text-decoration:none}.sources a:hover{text-decoration:underline}.site-footer{display:flex;justify-content:space-between;gap:20px;padding:34px 4.5vw;color:var(--white);background:var(--blue);font-size:12px;font-weight:750}@media(max-width:820px){.article-head{grid-template-columns:1fr;padding-top:70px}.article-head h1{font-size:54px}.hero-media{margin-top:24px}.article-section blockquote,.conclusion blockquote{margin-left:0;margin-right:0;padding-left:24px;padding-right:24px}.site-footer{flex-direction:column}}@media(max-width:520px){.site-header{height:64px;padding:0 20px}.article-head{padding:54px 20px 38px}.article-head h1{font-size:42px}.subtitle{font-size:17px}.meta{flex-wrap:wrap}.article-body{padding-top:54px}.lede{font-size:18px}.article-section{padding-top:52px}.article-section h2,.conclusion h2{font-size:32px}.article-section p,.conclusion p{font-size:17px}.article-section blockquote,.conclusion blockquote{font-size:20px}.site-footer{padding:30px 20px}}`;

  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(article.title)} · Frontier Signals</title><meta name="description" content="${escapeHtml(article.excerpt)}"><meta name="robots" content="${robots}"><link rel="canonical" href="${escapeHtml(article.canonical_url)}"><meta property="og:type" content="article"><meta property="og:title" content="${escapeHtml(article.title)}"><meta property="og:description" content="${escapeHtml(article.excerpt)}"><meta property="og:url" content="${escapeHtml(article.canonical_url)}"><meta property="og:image" content="${escapeHtml(ogUrl)}"><meta property="og:image:alt" content="${escapeHtml(article.media.og.alt)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:site_name" content="Frontier Signals"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${escapeHtml(article.title)}"><meta name="twitter:description" content="${escapeHtml(article.excerpt)}"><meta name="twitter:image" content="${escapeHtml(ogUrl)}"><script type="application/ld+json">${safeJson(jsonLd)}</script><style>${css}</style></head><body><header class="site-header"><a class="brand" href="/"><span class="mark" aria-hidden="true"></span><span>Frontier Signals</span></a><a class="archive-link" href="/">全部文章 ↗</a></header><main><header class="article-head"><div><div class="kicker">FRONTIER SIGNALS · ${dateLabel(article.date)}</div><h1>${escapeHtml(article.title)}</h1><p class="subtitle">${escapeHtml(article.subtitle)}</p><div class="meta"><span>${escapeHtml(modeLabel)}</span><span>${article.reading_minutes} 分钟阅读</span><span>${escapeHtml(article.author)}</span></div></div>${webFigure(article.media.og, true)}</header><article class="article-body"><section class="lede">${article.intro.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}${introCitations}</section>${sectionHtml}<section class="conclusion"><h2>${escapeHtml(article.conclusion.title || "写在最后")}</h2>${article.conclusion.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}${article.conclusion.question ? `<blockquote>${escapeHtml(article.conclusion.question)}</blockquote>` : ""}${conclusionCitations}</section><section class="sources"><h2>参考资料</h2><ol>${sourceHtml}</ol></section></article></main><footer class="site-footer"><span>Frontier World · 前沿之境</span><span>Turn the frontier into practice.</span></footer></body></html>\n`;
}
