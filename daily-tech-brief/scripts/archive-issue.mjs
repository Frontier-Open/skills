#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const issuePath = resolve(valueOf("--issue") || "issue.json");
const historyDir = resolve(valueOf("--history-dir") || "data/issues");
const issue = JSON.parse(await readFile(issuePath, "utf8"));
if (!/^\d{4}-\d{2}-\d{2}$/u.test(issue.date || "")) throw new Error("issue.date must be YYYY-MM-DD");
const [year, month, day] = issue.date.split("-");
const outputDir = join(historyDir, year, month);
const outputPath = join(outputDir, `${day}.json`);

await mkdir(outputDir, { recursive: true });
await writeFile(outputPath, `${JSON.stringify(issue, null, 2)}\n`, "utf8");
console.log(`Archived structured issue to ${outputPath}`);
