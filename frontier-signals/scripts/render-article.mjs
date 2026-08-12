#!/usr/bin/env node
import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildArticleMarkdown, buildWebHtml, buildWechatHtml } from "./article.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const articlePath = resolve(valueOf("--article") || "article.json");
const mediaRoot = resolve(valueOf("--media-root") || dirname(articlePath));
const outputs = {
  web: resolve(valueOf("--web") || "index.html"),
  markdown: resolve(valueOf("--markdown") || "article.md"),
  wechatHtml: resolve(valueOf("--wechat-html") || "wechat.html"),
  wechatMarkdown: resolve(valueOf("--wechat-markdown") || "wechat.md"),
};
const article = JSON.parse(await readFile(articlePath, "utf8"));

await Promise.all(Object.values(outputs).map((path) => mkdir(dirname(path), { recursive: true })));
await Promise.all([
  writeFile(outputs.web, buildWebHtml(article), "utf8"),
  writeFile(outputs.markdown, buildArticleMarkdown(article), "utf8"),
  writeFile(outputs.wechatHtml, buildWechatHtml(article), "utf8"),
  writeFile(outputs.wechatMarkdown, buildArticleMarkdown(article), "utf8"),
]);

const sectionMedia = [...new Set(article.sections.map((section) => section.image?.path).filter(Boolean))];
for (const mediaPath of sectionMedia) {
  const source = resolve(mediaRoot, mediaPath);
  for (const outputDirectory of [dirname(outputs.web), dirname(outputs.wechatHtml)]) {
    const destination = resolve(outputDirectory, mediaPath);
    await mkdir(dirname(destination), { recursive: true });
    await copyFile(source, destination);
  }
}

Object.values(outputs).forEach((path) => console.log(`Rendered ${path}`));
sectionMedia.forEach((path) => console.log(`Copied section media ${path} to web and WeChat editions`));
