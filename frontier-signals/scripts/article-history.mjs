import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

function canonicalUrl(value) {
  const url = new URL(value);
  url.hash = "";
  for (const key of [...url.searchParams.keys()]) {
    if (/^(?:utm_|fbclid|gclid)/iu.test(key)) url.searchParams.delete(key);
  }
  url.hostname = url.hostname.toLowerCase();
  url.pathname = url.pathname.replace(/\/+$/u, "") || "/";
  return url.toString();
}

async function filesRecursively(directory) {
  const entries = await readdir(directory, { withFileTypes: true }).catch((error) => {
    if (error.code === "ENOENT") return [];
    throw error;
  });
  const files = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await filesRecursively(path));
    else if (entry.isFile() && entry.name.endsWith(".json")) files.push(path);
  }
  return files;
}

export async function loadArticleHistory(directory) {
  const articles = [];
  for (const path of await filesRecursively(directory)) {
    const value = JSON.parse(await readFile(path, "utf8"));
    if (value?.series === "Frontier Signals" && value?.id) articles.push({ ...value, __path: path });
  }
  return articles;
}

export function findArticleConflicts(article, history) {
  const others = history.filter((prior) => prior.id !== article.id);
  const conflicts = [];
  const continuation = others.find((prior) => prior.id === article.continuation_of);
  const continuationAllowed = Boolean(continuation && String(article.material_update || "").trim());

  for (const prior of others) {
    if (prior.angle_key === article.angle_key) {
      conflicts.push({ type: "angle_key", value: article.angle_key, prior: prior.id });
    }
  }

  const currentStories = new Set(article.story_keys || []);
  for (const prior of others) {
    for (const key of prior.story_keys || []) {
      if (currentStories.has(key) && !(continuationAllowed && prior.id === continuation.id)) {
        conflicts.push({ type: "story_key", value: key, prior: prior.id });
      }
    }
  }

  const currentSources = new Set((article.sources || []).map((source) => canonicalUrl(source.url)));
  for (const prior of others) {
    for (const source of prior.sources || []) {
      const url = canonicalUrl(source.url);
      if (currentSources.has(url) && !(continuationAllowed && prior.id === continuation.id)) {
        conflicts.push({ type: "source_url", value: url, prior: prior.id });
      }
    }
  }

  if (article.continuation_of && !continuation) {
    conflicts.push({ type: "continuation_of", value: article.continuation_of, prior: null });
  }
  return conflicts;
}
