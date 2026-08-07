#!/usr/bin/env node
import { readFile, readdir } from "node:fs/promises";
import { join, resolve } from "node:path";
import { findIssueDuplicates } from "./history.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

async function jsonFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await jsonFiles(path));
    else if (entry.isFile() && entry.name.endsWith(".json")) files.push(path);
  }
  return files;
}

const issuePath = resolve(valueOf("--issue") || "issue.json");
const historyDir = resolve(valueOf("--history-dir") || "data/issues");
const currentIssue = JSON.parse(await readFile(issuePath, "utf8"));
const historicalIssues = await Promise.all((await jsonFiles(historyDir)).map(async (path) => JSON.parse(await readFile(path, "utf8"))));
const errors = findIssueDuplicates(currentIssue, historicalIssues);

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`No repeats found across ${historicalIssues.length} archived issue${historicalIssues.length === 1 ? "" : "s"}`);
