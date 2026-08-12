#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { assertArticle } from "./article.mjs";
import { findArticleConflicts, loadArticleHistory } from "./article-history.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const articlePath = resolve(valueOf("--article") || "article.json");
const historyDir = resolve(valueOf("--history-dir") || "data/articles");
const article = assertArticle(JSON.parse(await readFile(articlePath, "utf8")));
const history = await loadArticleHistory(historyDir);
const conflicts = findArticleConflicts(article, history);

if (conflicts.length) {
  console.error(JSON.stringify({ ok: false, article: article.id, conflicts }, null, 2));
  process.exitCode = 1;
} else {
  console.log(`No article-history conflicts across ${history.length} prior article(s)`);
}
