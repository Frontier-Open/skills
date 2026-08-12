#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildLarkCard } from "./lark-card.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const articlePath = resolve(valueOf("--article") || "article.json");
const outputPath = resolve(valueOf("--out") || "lark-card.json");
const article = JSON.parse(await readFile(articlePath, "utf8"));
const card = buildLarkCard(article, {
  imageKey: valueOf("--image-key"),
  documentUrl: valueOf("--document-url"),
});
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(card, null, 2)}\n`, "utf8");
console.log(`Rendered ${outputPath}`);
