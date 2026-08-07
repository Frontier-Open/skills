#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const issuePath = resolve(valueOf("--issue") || "issue.json");
const htmlPath = resolve(valueOf("--html") || "public/index.html");
const offline = args.includes("--offline");
const issue = JSON.parse(await readFile(issuePath, "utf8"));
const html = await readFile(htmlPath, "utf8");

const errors = [];
for (const text of [issue.brand, issue.headline, issue.topic, issue.canonical_url]) {
  if (!html.includes(String(text).replace(/&/gu, "&amp;").replace(/</gu, "&lt;").replace(/>/gu, "&gt;").replace(/"/gu, "&quot;").replace(/'/gu, "&#39;"))) {
    errors.push(`Rendered HTML is missing: ${text}`);
  }
}
if (!html.includes('name="robots" content="noindex,nofollow,noarchive"')) errors.push("Missing private-by-link robots metadata");
if (!/@media\s*\(max-width:\s*800px\)/u.test(html)) errors.push("Missing mobile layout rules");

const links = [
  ...issue.signals.map((item) => item.source_url),
  ...issue.repositories.map((item) => item.url),
  ...issue.products.map((item) => item.url),
];
for (const link of links) {
  try {
    const url = new URL(link);
    if (!/^https?:$/u.test(url.protocol)) errors.push(`Unsupported URL: ${link}`);
  } catch {
    errors.push(`Invalid URL: ${link}`);
  }
}

if (!offline) {
  const results = await Promise.all(links.map(async (url) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      let response = await fetch(url, { method: "HEAD", redirect: "follow", signal: controller.signal });
      if (response.status === 405 || response.status === 403) response = await fetch(url, { method: "GET", redirect: "follow", signal: controller.signal });
      return response.status < 500 ? null : `${url}: HTTP ${response.status}`;
    } catch (error) {
      return `${url}: ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      clearTimeout(timer);
    }
  }));
  errors.push(...results.filter(Boolean));
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`Verified ${htmlPath} with ${links.length} sourced links${offline ? " (offline)" : ""}`);
