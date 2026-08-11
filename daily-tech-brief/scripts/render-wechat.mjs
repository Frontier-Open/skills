#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildWechatHtml, buildWechatMarkdown } from "./wechat.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const articlePath = resolve(valueOf("--article") || "wechat-article.json");
const htmlPath = resolve(valueOf("--out-html") || "wechat.html");
const markdownPath = resolve(valueOf("--out-markdown") || "wechat.md");
const article = JSON.parse(await readFile(articlePath, "utf8"));

await Promise.all([
  mkdir(dirname(htmlPath), { recursive: true }),
  mkdir(dirname(markdownPath), { recursive: true }),
]);
await Promise.all([
  writeFile(htmlPath, buildWechatHtml(article), "utf8"),
  writeFile(markdownPath, buildWechatMarkdown(article), "utf8"),
]);

console.log(`Rendered ${htmlPath}`);
console.log(`Rendered ${markdownPath}`);
