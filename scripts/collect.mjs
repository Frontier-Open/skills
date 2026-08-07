#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import {
  parseDailyDev,
  parseGitHubTrending,
  parseHelloGitHub,
  parseProductHunt,
  parseTechmeme,
  safeWarning,
} from "./lib.mjs";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const outputPath = resolve(valueOf("--out") || "work/raw.json");
const fixtureDir = valueOf("--fixture-dir") ? resolve(valueOf("--fixture-dir")) : null;
const only = new Set((valueOf("--only") || "").split(",").filter(Boolean));
const timeoutMs = Number.parseInt(valueOf("--timeout-ms") || "20000", 10);

const sources = [
  {
    id: "techmeme",
    url: "https://www.techmeme.com/feed.xml",
    fixture: "techmeme.xml",
    parser: parseTechmeme,
  },
  {
    id: "daily-dev",
    url: "https://daily.dev/",
    fixture: "daily-dev.html",
    parser: parseDailyDev,
  },
  {
    id: "github-trending",
    url: "https://github.com/trending?since=daily",
    fixture: "github-trending.html",
    parser: parseGitHubTrending,
  },
  {
    id: "hellogithub",
    url: "https://api.hellogithub.com/v1/?sort_by=featured&page=1&rank_by=newest&tid=all",
    fixture: "hellogithub.json",
    parser: parseHelloGitHub,
  },
  {
    id: "product-hunt",
    url: "https://www.producthunt.com/feed",
    fixture: "product-hunt.xml",
    parser: parseProductHunt,
  },
].filter((source) => only.size === 0 || only.has(source.id));

async function load(source) {
  if (fixtureDir) return readFile(resolve(fixtureDir, source.fixture), "utf8");

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(source.url, {
      headers: {
        accept: "text/html,application/xml,application/atom+xml,application/json;q=0.9,*/*;q=0.8",
        "user-agent": "daily-tech-brief/0.1 (+sourced editorial digest)",
      },
      redirect: "follow",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.text();
  } finally {
    clearTimeout(timer);
  }
}

const fetchedAt = new Date().toISOString();
const results = await Promise.all(sources.map(async (source) => {
  try {
    const body = await load(source);
    const items = source.parser(body);
    if (!items.length) throw new Error("No items parsed");
    return { id: source.id, url: source.url, status: "ok", items };
  } catch (error) {
    return { id: source.id, url: source.url, status: "failed", items: [], error: safeWarning(error) };
  }
}));

const warnings = results
  .filter((result) => result.status !== "ok")
  .map((result) => `${result.id}: ${result.error}`);

const output = {
  schema_version: "1.0",
  fetched_at: fetchedAt,
  source_timezone_note: "Metrics reflect each source at fetched_at; do not present them as timeless values.",
  sources: results,
  warnings,
};

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
console.log(`Collected ${results.reduce((sum, result) => sum + result.items.length, 0)} items from ${results.length - warnings.length}/${results.length} sources into ${outputPath}`);
if (warnings.length) console.warn(warnings.join("\n"));
