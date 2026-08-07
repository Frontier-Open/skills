#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const issuePath = resolve(valueOf("--issue") || "issue.json");
const outPath = resolve(valueOf("--out") || "public/index.html");
const issue = JSON.parse(await readFile(issuePath, "utf8"));
const css = await readFile(new URL("../assets/brief.css", import.meta.url), "utf8");

const escapeHtml = (value = "") => String(value).replace(/[&<>"']/gu, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[character]));

const absoluteUrl = (value, label) => {
  const url = new URL(value);
  if (!/^https?:$/u.test(url.protocol)) throw new Error(`${label} must use HTTP(S)`);
  return url.toString();
};

const localImage = (value, label) => {
  if (!/^\.\/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:avif|jpe?g|png|svg|webp)$/u.test(value || "")) {
    throw new Error(`${label} must be a local image next to the rendered issue`);
  }
  return value;
};

for (const key of ["date", "timezone", "generated_at", "canonical_url", "brand", "headline", "dek", "topic"]) {
  if (!issue[key]) throw new Error(`Missing ${key}`);
}
for (const key of ["signals", "repositories", "products", "warnings"]) {
  if (!Array.isArray(issue[key])) throw new Error(`${key} must be an array`);
}
if (issue.signals.length < 1 || issue.signals.length > 6) throw new Error("signals must contain 1-6 items");
if (issue.signals.length !== 4) throw new Error("signals must contain 4 curated items");
if (issue.repositories.length !== 4) throw new Error("repositories must contain 4 relevance-ranked items");
if (issue.products.length !== 2) throw new Error("products must contain 2 curated items");

const canonical = absoluteUrl(issue.canonical_url, "canonical_url");
if (!canonical.endsWith("/")) throw new Error("canonical_url must end with /");
const canonicalObject = new URL(canonical);
const [issueYear, issueMonth, issueDayOfMonth] = issue.date.split("-");
const issueRoute = `/${issueYear}/${issueMonth}/${issueDayOfMonth}/`;
if (canonicalObject.pathname !== issueRoute) throw new Error(`canonical_url must end with ${issueRoute}`);
const ogUrl = new URL(`${issueRoute}og.png`, canonicalObject.origin).toString();
const date = new Date(`${issue.date}T00:00:00Z`);
if (Number.isNaN(date.valueOf())) throw new Error("date must be YYYY-MM-DD");
const displayDate = issue.date.replaceAll("-", ".");
const issueDay = issue.date.slice(-2);

const signalCards = issue.signals.map((item, index) => {
  const sourceUrl = absoluteUrl(item.source_url, `signals[${index}].source_url`);
  return `<a class="signal" href="${escapeHtml(sourceUrl)}"><div class="meta"><span class="source">${escapeHtml(item.source)}</span><span>${String(index + 1).padStart(2, "0")}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p><p class="why">值得看 → ${escapeHtml(item.why)}</p></a>`;
}).join("");

const repoRows = issue.repositories.map((item, index) => {
  const url = absoluteUrl(item.url, `repositories[${index}].url`);
  if (!/^\d[\d,]*$/u.test(item.stars_total || "")) throw new Error(`repositories[${index}].stars_total must be a formatted total Star count`);
  const metric = `<div class="repo-stat"><strong>${escapeHtml(item.stars_total)} <span class="repo-star">★</span></strong></div>`;
  return `<a class="repo" href="${escapeHtml(url)}"><div class="repo-index">${String(index + 1).padStart(2, "0")}</div><div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.summary)}</p></div>${metric}</a>`;
}).join("");

const productCards = issue.products.map((item, index) => {
  const url = absoluteUrl(item.url, `products[${index}].url`);
  const icon = localImage(item.icon, `products[${index}].icon`);
  absoluteUrl(item.icon_source_url, `products[${index}].icon_source_url`);
  return `<a class="product" href="${escapeHtml(url)}"><div class="product-heading"><img class="product-icon" src="${escapeHtml(icon)}" width="52" height="52" alt=""><h3>${escapeHtml(item.name)}</h3></div><p>${escapeHtml(item.summary)}</p></a>`;
}).join("");

const description = `${issue.dek}：科技商业、GitHub 热门项目与 Product Hunt 精选。`;
const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>${escapeHtml(issue.brand)} · ${escapeHtml(issue.date)}</title>
    <meta name="description" content="${escapeHtml(description)}">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <link rel="canonical" href="${escapeHtml(canonical)}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="${escapeHtml(issue.brand)}">
    <meta property="og:title" content="${escapeHtml(issue.headline)}">
    <meta property="og:description" content="${escapeHtml(description)}">
    <meta property="og:url" content="${escapeHtml(canonical)}">
    <meta property="og:image" content="${escapeHtml(ogUrl)}">
    <meta property="og:image:secure_url" content="${escapeHtml(ogUrl)}">
    <meta property="og:image:type" content="image/png">
    <meta property="og:image:width" content="1731">
    <meta property="og:image:height" content="909">
    <meta property="og:image:alt" content="${escapeHtml(issue.headline)}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="${escapeHtml(issue.brand)} · ${escapeHtml(displayDate)}">
    <meta name="twitter:description" content="${escapeHtml(issue.headline)}">
    <meta name="twitter:image" content="${escapeHtml(ogUrl)}">
    <style>
${css}
.time a { margin-left: 16px; color: var(--accent); text-decoration: none; }
.time a:hover { text-decoration: underline; text-underline-offset: 4px; }
@media (max-width: 480px) { .time a { margin-left: 8px; } }
    </style>
  </head>
  <body>
    <div class="page" data-day="${escapeHtml(issueDay)}">
      <header>
        <div class="topline">
          <div class="brand"><i class="dot"></i>${escapeHtml(issue.brand)}</div>
          <div class="time">${escapeHtml(displayDate)} <a href="/">往期 ↗</a></div>
        </div>
        <div class="hero">
          <div>
            <div class="eyebrow">Today's signal · 今日信号</div>
            <h1>${escapeHtml(issue.headline)}</h1>
          </div>
          <div class="hero-side">
            <strong>${escapeHtml(issue.dek)}</strong>
            <p>不是榜单搬运。只保留与读者真正相关、可追溯的信号。</p>
          </div>
        </div>
      </header>
      <main>
        <section class="section">
          <div class="section-head">
            <div class="section-no">01 / SIGNAL</div>
            <h2>科技与商业</h2>
            <div class="section-note">过去 24 小时 + 一条近期深读</div>
          </div>
          <div class="signal-grid">${signalCards}</div>
        </section>
        <section class="section">
          <div class="section-head">
            <div class="section-no">02 / BUILD</div>
            <h2>开源项目精选</h2>
            <div class="section-note">GitHub Trending + HelloGitHub · 按内容与工作流相关性排序</div>
          </div>
          <div class="repo-list">${repoRows}</div>
        </section>
        <section class="section">
          <div class="section-head">
            <div class="section-no">03 / SHIP</div>
            <h2>Product Hunt 今日精选</h2>
            <div class="section-note">从官方 Feed 候选中筛选 2 条；不按榜单照搬</div>
          </div>
          <div class="product-grid">${productCards}</div>
        </section>
        <aside class="action">
          <div class="action-no">04 / THINK</div>
          <h2>今日思考</h2>
          <p>${escapeHtml(issue.topic)}</p>
        </aside>
      </main>
      <footer>
        <div>${escapeHtml(issue.brand)}</div>
        <div class="right">更新于 ${escapeHtml(displayDate)} · 榜单数据以发布时为准</div>
      </footer>
    </div>
  </body>
</html>`;

await mkdir(dirname(outPath), { recursive: true });
await writeFile(outPath, html, "utf8");
console.log(`Rendered ${outPath}`);
