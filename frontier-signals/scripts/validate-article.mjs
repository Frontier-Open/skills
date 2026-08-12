#!/usr/bin/env node
import { access, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { assertArticle } from "./article.mjs";
import { assertNormativeArticle } from "./normative.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const articlePath = resolve(valueOf("--article") || "article.json");
const article = assertArticle(JSON.parse(await readFile(articlePath, "utf8")));
const normative = args.includes("--normative");
if (normative) assertNormativeArticle(article);
const requireMedia = args.includes("--require-media");
const root = resolve(valueOf("--root") || dirname(articlePath));
const webRoot = valueOf("--web-root") ? resolve(valueOf("--web-root")) : root;
const wechatRoot = valueOf("--wechat-root") ? resolve(valueOf("--wechat-root")) : root;

if (requireMedia) {
  const sectionMedia = article.sections.map((section) => section.image).filter(Boolean);
  await Promise.all([
    access(resolve(webRoot, article.media.og.path)),
    access(resolve(wechatRoot, article.media.cover.path)),
    ...sectionMedia.flatMap((item) => [
      access(resolve(webRoot, item.path)),
      access(resolve(wechatRoot, item.path)),
    ]),
  ]);
}

console.log(`Validated ${article.id}${normative ? " against the normative contract" : ""}${requireMedia ? " with local media" : ""}`);
