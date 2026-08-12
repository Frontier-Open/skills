#!/usr/bin/env node
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { assertArticle, escapeHtml } from "./article.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const articlesDir = resolve(valueOf("--articles-dir") || "data/articles");
const publicDir = resolve(valueOf("--public-dir") || "public");
const origin = new URL(valueOf("--origin") || "https://signals.frontierworld.ai").origin;

async function files(directory) {
  const entries = await readdir(directory, { withFileTypes: true }).catch((error) => {
    if (error.code === "ENOENT") return [];
    throw error;
  });
  const found = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) found.push(...await files(path));
    else if (entry.isFile() && entry.name === "article.json") found.push(path);
  }
  return found;
}

const articles = [];
for (const path of await files(articlesDir)) {
  const article = assertArticle(JSON.parse(await readFile(path, "utf8")));
  if (article.status === "published") articles.push(article);
}
articles.sort((a, b) => b.date.localeCompare(a.date) || a.slug.localeCompare(b.slug));
if (!articles.length) throw new Error(`No published Frontier Signals articles found in ${articlesDir}`);

const css = `:root{--blue:#155eef;--ink:#101114;--canvas:#fafaf7;--white:#fff;--mist:#e8eeff;--muted:#5d626d;--line:rgba(16,17,20,.15)}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--canvas);font-family:"Avenir Next","SF Pro Display","PingFang SC","Helvetica Neue",sans-serif;-webkit-font-smoothing:antialiased}a{color:inherit;text-decoration:none}.page{width:min(1240px,100%);margin:auto;padding:0 4.5vw 80px}.top{height:74px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:10px;font-weight:800}.mark{width:25px;height:25px;background:var(--blue);clip-path:polygon(0 0,100% 0,100% 100%,68% 100%,79% 24%,64% 24%,43% 100%,0 100%)}.top span:last-child{font-size:11px;letter-spacing:.12em}.intro{display:grid;grid-template-columns:1.3fr .7fr;gap:7vw;align-items:end;padding:8vw 0 5vw}.eyebrow{color:var(--blue);font-size:11px;font-weight:800;letter-spacing:.14em}.intro h1{margin:20px 0 0;font-size:clamp(58px,9vw,128px);line-height:.88;letter-spacing:-.055em}.intro h1 em{display:inline-block}.intro p{margin:0;color:var(--muted);font-size:17px;line-height:1.8}.latest{display:grid;grid-template-columns:1fr 1fr;background:var(--blue);color:var(--white)}.latest img{display:block;width:100%;height:100%;min-height:360px;object-fit:cover}.latest-copy{display:flex;flex-direction:column;padding:44px}.label{font-size:10px;font-weight:800;letter-spacing:.14em}.latest h2{margin:30px 0 18px;font-size:42px;line-height:1.12;letter-spacing:-.035em}.latest p{margin:0;color:#dce7ff;font-size:15px;line-height:1.75}.latest footer{display:flex;justify-content:space-between;margin-top:auto;padding-top:34px;font-size:12px;font-weight:750}.archive-head{display:flex;justify-content:space-between;align-items:end;margin:80px 0 20px}.archive-head h2{margin:0;font-size:34px}.archive-head span{color:var(--muted);font-size:12px}.issue{display:grid;grid-template-columns:130px 1fr 80px;gap:28px;align-items:start;padding:30px 0;border-top:1px solid var(--line)}.issue-date{color:var(--blue);font-size:12px;font-weight:800;letter-spacing:.09em}.issue h3{margin:0 0 10px;font-size:25px;line-height:1.25}.issue p{margin:0;color:var(--muted);font-size:14px;line-height:1.65}.issue-meta{text-align:right;color:var(--muted);font-size:11px;text-transform:uppercase}.site-footer{display:flex;justify-content:space-between;margin-top:70px;padding:28px 0;border-top:1px solid var(--ink);font-size:12px;font-weight:750}@media(max-width:760px){.page{padding-left:20px;padding-right:20px}.intro{grid-template-columns:1fr;padding:70px 0 46px}.intro h1{font-size:64px}.intro p{max-width:440px}.latest{grid-template-columns:1fr}.latest img{min-height:210px}.latest-copy{min-height:340px;padding:28px}.latest h2{font-size:32px}.issue{grid-template-columns:1fr 35px;gap:12px}.issue-date{grid-column:1/-1}.issue-meta{grid-column:2;text-align:right}.issue>div:nth-child(2){grid-column:1;grid-row:2}.site-footer{flex-direction:column;gap:10px}}`;

const displayDate = (value) => value.replaceAll("-", ".");
const articlePath = (article) => new URL(article.canonical_url).pathname;
const articleOg = (article) => new URL(article.media.og.path, article.canonical_url).href;
const articleOgPath = (article) => new URL(article.media.og.path, article.canonical_url).pathname;

function rows(items) {
  return items.map((article) => `<a class="issue" href="${escapeHtml(articlePath(article))}"><div class="issue-date">${displayDate(article.date)}</div><div><h3>${escapeHtml(article.title)}</h3><p>${escapeHtml(article.excerpt)}</p></div><div class="issue-meta">${escapeHtml(article.mode || article.format)}<br>${article.reading_minutes} min ↗</div></a>`).join("");
}

function page({ canonicalPath, title, eyebrow, heading, intro, items, showLatest = false }) {
  const latest = items[0];
  const latestHtml = showLatest ? `<a class="latest" href="${escapeHtml(articlePath(latest))}"><img src="${escapeHtml(articleOgPath(latest))}" alt="${escapeHtml(latest.media.og.alt)}"><div class="latest-copy"><div class="label">LATEST SIGNAL · ${displayDate(latest.date)}</div><h2>${escapeHtml(latest.title)}</h2><p>${escapeHtml(latest.excerpt)}</p><footer><span>${latest.reading_minutes} 分钟阅读</span><span>阅读全文 ↗</span></footer></div></a>` : "";
  const canonical = `${origin}${canonicalPath}`;
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title><meta name="description" content="Frontier Signals：Frontier World 的 AI 与科技观点文章。"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="${canonical}"><link rel="alternate" type="application/rss+xml" href="${origin}/rss.xml"><meta property="og:type" content="website"><meta property="og:title" content="${escapeHtml(title)}"><meta property="og:description" content="Frontier World 的 AI 与科技观点文章。"><meta property="og:url" content="${canonical}"><meta property="og:image" content="${escapeHtml(articleOg(items[0]))}"><meta property="og:image:alt" content="${escapeHtml(items[0].media.og.alt)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${escapeHtml(title)}"><meta name="twitter:description" content="Frontier World 的 AI 与科技观点文章。"><meta name="twitter:image" content="${escapeHtml(articleOg(items[0]))}"><style>${css}</style></head><body><main class="page"><header class="top"><a class="brand" href="/"><span class="mark"></span>Frontier Signals</a><span>BY FRONTIER WORLD</span></header><section class="intro"><div><div class="eyebrow">${escapeHtml(eyebrow)}</div><h1>${heading}</h1></div><p>${escapeHtml(intro)}</p></section>${latestHtml}<section><div class="archive-head"><h2>文章档案</h2><span>${items.length} SIGNALS</span></div>${rows(items)}</section><footer class="site-footer"><span>Frontier World · 前沿之境</span><span>Turn the frontier into practice.</span></footer></main></body></html>`;
}

const groupBy = (items, keyOf) => items.reduce((map, item) => {
  const key = keyOf(item);
  if (!map.has(key)) map.set(key, []);
  map.get(key).push(item);
  return map;
}, new Map());
const byYear = groupBy(articles, (article) => article.date.slice(0, 4));
const byMonth = groupBy(articles, (article) => article.date.slice(0, 7));

const root = page({ canonicalPath: "/", title: "Frontier Signals · AI 与科技观点", eyebrow: "Signals from the frontier", heading: "看见变化，<br>说清<em style=\"color:#155eef;font-style:normal\">下一步。</em>", intro: "每天从 AI 与科技新闻中提炼一个值得被理解的变化。不是新闻搬运，而是有来源、有判断、能行动的文章。", items: articles, showLatest: true });
await mkdir(publicDir, { recursive: true });
await writeFile(join(publicDir, "index.html"), root, "utf8");

for (const [year, items] of byYear) {
  await mkdir(join(publicDir, year), { recursive: true });
  await writeFile(join(publicDir, year, "index.html"), page({ canonicalPath: `/${year}/`, title: `${year} · Frontier Signals`, eyebrow: "Year archive", heading: `${year} <em style=\"color:#155eef;font-style:normal\">Signals</em>`, intro: `${items.length} 篇 AI 与科技观点文章。`, items }), "utf8");
}
for (const [month, items] of byMonth) {
  const [year, monthNumber] = month.split("-");
  await mkdir(join(publicDir, year, monthNumber), { recursive: true });
  await writeFile(join(publicDir, year, monthNumber, "index.html"), page({ canonicalPath: `/${year}/${monthNumber}/`, title: `${year}.${monthNumber} · Frontier Signals`, eyebrow: "Month archive", heading: `${year}.<em style=\"color:#155eef;font-style:normal\">${monthNumber}</em>`, intro: `${items.length} 篇 AI 与科技观点文章。`, items }), "utf8");
}

const xml = (value = "") => String(value).replace(/[<>&"']/gu, (character) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" })[character]);
const rssItems = articles.slice(0, 30).map((article) => `<item><title>${xml(article.title)}</title><link>${xml(article.canonical_url)}</link><guid isPermaLink="true">${xml(article.canonical_url)}</guid><pubDate>${new Date(`${article.date}T00:00:00+08:00`).toUTCString()}</pubDate><description>${xml(article.excerpt)}</description></item>`).join("");
await writeFile(join(publicDir, "rss.xml"), `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Frontier Signals</title><link>${origin}/</link><description>Frontier World 的 AI 与科技观点文章</description><language>zh-CN</language>${rssItems}</channel></rss>\n`, "utf8");
const sitemapEntries = ["/", ...articles.map(articlePath), ...[...byYear.keys()].map((year) => `/${year}/`), ...[...byMonth.keys()].map((month) => `/${month.replace("-", "/")}/`)];
await writeFile(join(publicDir, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${sitemapEntries.map((path) => `<url><loc>${origin}${xml(path)}</loc></url>`).join("")}</urlset>\n`, "utf8");
console.log(`Rendered Frontier Signals archive for ${articles.length} published article(s)`);
