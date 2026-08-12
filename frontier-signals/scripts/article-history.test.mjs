import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { findArticleConflicts } from "./article-history.mjs";

const base = JSON.parse(await readFile(new URL("../assets/article.example.json", import.meta.url), "utf8"));

test("rejects duplicate angles and stories", () => {
  const current = structuredClone(base);
  current.id = "2026-08-13/another-signal";
  current.date = "2026-08-13";
  current.slug = "another-signal";
  current.canonical_url = "https://signals.frontierworld.ai/2026/08/13/another-signal/";
  const conflicts = findArticleConflicts(current, [base]);
  assert.ok(conflicts.some((conflict) => conflict.type === "angle_key"));
  assert.ok(conflicts.some((conflict) => conflict.type === "story_key"));
});

test("allows a material continuation with a new angle", () => {
  const current = structuredClone(base);
  current.id = "2026-08-13/material-update";
  current.date = "2026-08-13";
  current.slug = "material-update";
  current.canonical_url = "https://signals.frontierworld.ai/2026/08/13/material-update/";
  current.angle_key = "new-angle-after-material-update";
  current.continuation_of = base.id;
  current.material_update = "A new official filing changed the factual basis.";
  assert.deepEqual(findArticleConflicts(current, [base]), []);
});

test("requires the declared continuation target to exist", () => {
  const current = structuredClone(base);
  current.id = "2026-08-13/missing-continuation";
  current.date = "2026-08-13";
  current.slug = "missing-continuation";
  current.canonical_url = "https://signals.frontierworld.ai/2026/08/13/missing-continuation/";
  current.angle_key = "new-angle";
  current.story_keys = ["new-story"];
  current.sources = current.sources.map((source, index) => ({ ...source, url: `https://new.example.com/${index}` }));
  current.continuation_of = "2026-08-01/unknown";
  current.material_update = "New evidence.";
  assert.ok(findArticleConflicts(current, [base]).some((conflict) => conflict.type === "continuation_of"));
});
