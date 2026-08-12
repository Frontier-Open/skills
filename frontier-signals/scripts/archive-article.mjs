#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { assertArticle } from "./article.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const articlePath = resolve(valueOf("--article") || "article.json");
const historyDir = resolve(valueOf("--history-dir") || "data/articles");
const article = assertArticle(JSON.parse(await readFile(articlePath, "utf8")));
const [year, month, day] = article.date.split("-");
const target = join(historyDir, year, month, day, article.slug, "article.json");
await mkdir(dirname(target), { recursive: true });
await writeFile(target, `${JSON.stringify(article, null, 2)}\n`, "utf8");
console.log(`Archived ${article.id} to ${target}`);
