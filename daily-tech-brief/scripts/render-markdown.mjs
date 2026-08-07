#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildMarkdown } from "./markdown.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const issuePath = resolve(valueOf("--issue") || "issue.json");
const outputPath = resolve(valueOf("--out") || "brief.md");
const issue = JSON.parse(await readFile(issuePath, "utf8"));
const markdown = buildMarkdown(issue);

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, markdown, "utf8");
console.log(`Rendered ${outputPath}`);
