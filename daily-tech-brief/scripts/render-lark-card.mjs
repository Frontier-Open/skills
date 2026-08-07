#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { buildLarkCard } from "./lark-card.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const issuePath = resolve(valueOf("--issue") || "issue.json");
const outputPath = resolve(valueOf("--out") || "lark-card.json");
const imageKey = valueOf("--image-key");
const documentUrl = valueOf("--document-url");
const withoutImage = args.includes("--without-image");

if (!imageKey && !withoutImage) {
  throw new Error("Pass --image-key img_xxx after uploading the cover, or explicitly use --without-image");
}
if (imageKey && !/^img_/u.test(imageKey)) {
  throw new Error("--image-key must be a Feishu image key beginning with img_");
}
if (!documentUrl) {
  throw new Error("Pass --document-url after creating and verifying the Feishu cloud document");
}

const issue = JSON.parse(await readFile(issuePath, "utf8"));
const card = buildLarkCard(issue, { imageKey, documentUrl });
await writeFile(outputPath, `${JSON.stringify(card, null, 2)}\n`, "utf8");
console.log(`Rendered ${outputPath}`);
