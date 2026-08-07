#!/usr/bin/env node
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const publicDir = resolve(valueOf("--public-dir") || "public");
const outputPath = resolve(valueOf("--out") || join(publicDir, "index.html"));
const origin = new URL(valueOf("--origin") || "https://brief.clairesparlor.com").origin;

const escapeHtml = (value = "") => String(value).replace(/[&<>"']/gu, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));

const decodeHtml = (value = "") => value
  .replace(/&#39;|&apos;/gu, "'")
  .replace(/&quot;/gu, '"')
  .replace(/&lt;/gu, "<")
  .replace(/&gt;/gu, ">")
  .replace(/&amp;/gu, "&");

function meta(html, key, value) {
  for (const match of html.matchAll(/<meta\s+([^>]+)>/giu)) {
    const attributes = Object.fromEntries([...match[1].matchAll(/([\w:-]+)=["']([^"']*)["']/gu)].map((item) => [item[1], item[2]]));
    if (attributes[key] === value) return decodeHtml(attributes.content || "");
  }
  return "";
}

const entries = await readdir(publicDir, { withFileTypes: true });
const issueDirs = entries
  .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/u.test(entry.name))
  .map((entry) => entry.name)
  .sort((a, b) => b.localeCompare(a));

if (!issueDirs.length) throw new Error(`No dated issues found in ${publicDir}`);

const issues = await Promise.all(issueDirs.map(async (date) => {
  const html = await readFile(join(publicDir, date, "index.html"), "utf8");
  return {
    date,
    headline: meta(html, "property", "og:title") || date,
    description: meta(html, "property", "og:description") || meta(html, "name", "description"),
    image: `/${date}/og.png`,
    url: `/${date}/`,
  };
}));

const latest = issues[0];
const groups = new Map();
for (const issue of issues) {
  const month = issue.date.slice(0, 7);
  if (!groups.has(month)) groups.set(month, []);
  groups.get(month).push(issue);
}

const dateParts = (date) => {
  const parsed = new Date(`${date}T00:00:00Z`);
  return {
    day: new Intl.DateTimeFormat("en-GB", { day: "2-digit", timeZone: "UTC" }).format(parsed),
    weekday: new Intl.DateTimeFormat("zh-CN", { weekday: "short", timeZone: "UTC" }).format(parsed),
    long: new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }).format(parsed),
  };
};

const monthSections = [...groups.entries()].map(([month, monthIssues]) => {
  const parsed = new Date(`${month}-01T00:00:00Z`);
  const label = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", timeZone: "UTC" }).format(parsed);
  const rows = monthIssues.map((issue) => {
    const date = dateParts(issue.date);
    const current = issue.date === latest.date ? '<span class="new">LATEST</span>' : "";
    return `<a class="issue-row" href="${escapeHtml(issue.url)}"><div class="date-block"><strong>${escapeHtml(date.day)}</strong><span>${escapeHtml(date.weekday)}</span></div><div class="issue-copy"><div class="issue-kicker">${escapeHtml(issue.date)} ${current}</div><h3>${escapeHtml(issue.headline)}</h3><p>${escapeHtml(issue.description)}</p></div><span class="arrow" aria-hidden="true">↗</span></a>`;
  }).join("");
  return `<section class="month"><div class="month-head"><span>${escapeHtml(label)}</span><span>${monthIssues.length} ISSUES</span></div>${rows}</section>`;
}).join("");

const latestDate = dateParts(latest.date);
const canonical = `${origin}/`;
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Claire's Morning Signals · 晨报档案馆</title><meta name="description" content="Claire 的科技、商业、开源与产品晨报往期目录。"><meta name="robots" content="noindex,nofollow,noarchive"><link rel="canonical" href="${canonical}"><meta property="og:type" content="website"><meta property="og:title" content="Claire's Morning Signals · 晨报档案馆"><meta property="og:description" content="科技、商业、开源与产品晨报往期目录。"><meta property="og:url" content="${canonical}"><meta property="og:image" content="${origin}${latest.image}"><style>
:root{--paper:#f7f6f3;--surface:#fff;--ink:#0b0b0b;--muted:#6f6d69;--line:rgba(11,11,11,.12);--accent:#d4471d;--hot:#ff5733;--soft:#fbe1d7}*{box-sizing:border-box}html{background:#e9e7e3}body{width:min(1080px,100%);min-height:100vh;margin:0 auto;background:radial-gradient(circle at 91% 7%,rgba(255,87,51,.16),transparent 19%),var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Hiragino Sans GB",sans-serif;-webkit-font-smoothing:antialiased}a{color:inherit;text-decoration:none}.page{padding:54px 58px 70px}.topline{display:flex;align-items:center;justify-content:space-between;padding-bottom:22px;border-bottom:1px solid var(--line);font:700 12px ui-monospace,"SFMono-Regular",Menlo,monospace;letter-spacing:.16em;text-transform:uppercase}.brand{display:flex;align-items:center;gap:11px}.dot{width:11px;height:11px;border-radius:50%;background:var(--hot);box-shadow:0 0 0 7px rgba(255,87,51,.1)}.counter{color:var(--muted)}.intro{display:grid;grid-template-columns:1fr 270px;gap:54px;align-items:end;padding:66px 0 44px}.eyebrow,.issue-kicker,.month-head{font-family:ui-monospace,"SFMono-Regular",Menlo,monospace;text-transform:uppercase;letter-spacing:.14em}.eyebrow{margin-bottom:18px;color:var(--accent);font-size:12px;font-weight:800}.intro h1{margin:0;font-size:64px;line-height:.98;letter-spacing:-.065em}.intro h1 em{display:block;color:var(--accent);font-style:normal}.intro aside{border-left:3px solid var(--hot);padding-left:22px;color:var(--muted);font-size:14px;line-height:1.7}.latest{display:grid;grid-template-columns:1.08fr .92fr;overflow:hidden;border:1px solid var(--line);border-radius:26px;background:var(--ink);color:#fff}.latest-image{min-height:315px;background:#f2eeea}.latest-image img{display:block;width:100%;height:100%;min-height:315px;object-fit:cover}.latest-copy{display:flex;flex-direction:column;padding:38px}.latest-label{color:#ff8b68;font:800 11px ui-monospace,monospace;letter-spacing:.16em}.latest h2{margin:24px 0 16px;font-size:32px;line-height:1.15;letter-spacing:-.035em}.latest p{margin:0;color:#aaa;font-size:14px;line-height:1.65}.latest-cta{display:flex;justify-content:space-between;align-items:center;margin-top:auto;padding-top:30px;color:#ff8b68;font:800 12px ui-monospace,monospace;letter-spacing:.1em}.archive-title{display:flex;justify-content:space-between;align-items:end;margin:66px 0 18px}.archive-title h2{margin:0;font-size:30px;letter-spacing:-.04em}.archive-title p{margin:0;color:var(--muted);font:11px ui-monospace,monospace}.month{margin-top:34px}.month-head{display:flex;justify-content:space-between;padding-bottom:12px;border-bottom:1px solid var(--ink);font-size:11px;font-weight:800}.issue-row{display:grid;grid-template-columns:72px 1fr 28px;gap:22px;align-items:center;padding:25px 4px;border-bottom:1px solid var(--line);transition:padding .18s ease,background .18s ease}.issue-row:hover{padding-left:14px;background:rgba(255,255,255,.65)}.date-block{display:flex;align-items:baseline;gap:7px}.date-block strong{font-size:28px;letter-spacing:-.05em}.date-block span{color:var(--muted);font-size:11px}.issue-kicker{color:var(--accent);font-size:10px;font-weight:800}.new{display:inline-block;margin-left:7px;padding:3px 5px;background:var(--soft);border-radius:4px}.issue-row h3{margin:8px 0 5px;font-size:21px;letter-spacing:-.025em}.issue-row p{margin:0;color:var(--muted);font-size:13px;line-height:1.5}.arrow{color:var(--accent);font-size:20px}.footer{display:flex;justify-content:space-between;gap:24px;margin-top:62px;padding-top:20px;border-top:1px solid var(--line);color:var(--muted);font:10px/1.6 ui-monospace,monospace}@media(max-width:720px){.page{padding:32px 22px 50px}.topline{align-items:flex-start;gap:20px}.counter{text-align:right}.intro{grid-template-columns:1fr;gap:30px;padding:50px 0 36px}.intro h1{font-size:48px}.intro aside{max-width:330px}.latest{grid-template-columns:1fr}.latest-image,.latest-image img{min-height:205px}.latest-copy{padding:27px}.latest h2{font-size:27px}.archive-title{align-items:start;gap:16px}.archive-title p{text-align:right}.issue-row{grid-template-columns:54px 1fr 20px;gap:14px}.issue-row p{display:none}.issue-row h3{font-size:18px}.date-block{display:block}.date-block strong,.date-block span{display:block}.footer{flex-direction:column}}
</style></head><body><main class="page"><header><div class="topline"><div class="brand"><i class="dot"></i>Claire's Morning Signals</div><div class="counter">${issues.length} ISSUES · SINCE ${escapeHtml(issues.at(-1).date)}</div></div><div class="intro"><div><div class="eyebrow">Morning intelligence archive</div><h1>每天十分钟，<em>看见下一步。</em></h1></div><aside>不是新闻搬运。这里保存每天从科技商业、开源社区与新产品中筛出的少数有效信号。</aside></div></header><a class="latest" href="${escapeHtml(latest.url)}"><div class="latest-image"><img src="${escapeHtml(latest.image)}" alt="${escapeHtml(latest.headline)}"></div><div class="latest-copy"><div class="latest-label">LATEST ISSUE · ${escapeHtml(latestDate.long)}</div><h2>${escapeHtml(latest.headline)}</h2><p>${escapeHtml(latest.description)}</p><div class="latest-cta"><span>阅读全文 · 约 10 分钟</span><span>↗</span></div></div></a><div class="archive-title"><h2>晨报档案馆</h2><p>按日期永久保存 · 由新到旧</p></div>${monthSections}<footer class="footer"><span>CLAIRE'S PARLOR · MORNING SIGNALS</span><span>TECHMEME · DAILY.DEV · GITHUB · HELLOGITHUB · PRODUCT HUNT</span></footer></main></body></html>`;

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, html, "utf8");
console.log(`Rendered ${outputPath} with ${issues.length} issue${issues.length === 1 ? "" : "s"}`);
