#!/usr/bin/env node
import { access, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

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
if (issue.products.length && !html.includes('class="product-heading"')) errors.push("Missing Product Hunt icon/title rows");

for (const [index, product] of issue.products.entries()) {
  if (!/^\.\/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:avif|jpe?g|png|svg|webp)$/u.test(product.icon || "")) {
    errors.push(`products[${index}].icon must be a local image next to the rendered issue`);
    continue;
  }
  if (!html.includes(`src="${product.icon}"`)) errors.push(`Rendered HTML is missing product icon: ${product.icon}`);
  try {
    await access(resolve(dirname(htmlPath), product.icon));
  } catch {
    errors.push(`Missing product icon file: ${product.icon}`);
  }
}

const links = [
  ...issue.signals.map((item) => item.source_url),
  ...issue.github_trending.map((item) => item.url),
  ...issue.hello_github.map((item) => item.url),
  ...issue.products.flatMap((item) => [item.url, item.icon_source_url]),
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
