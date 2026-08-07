import assert from "node:assert/strict";
import test from "node:test";
import { findIssueDuplicates } from "./history.mjs";

function issue(date, suffix = "today") {
  return {
    date,
    signals: [{ title: `Story ${suffix}`, source_url: `https://example.com/story-${suffix}?utm_source=x`, dedupe_key: `story:${suffix}` }],
    repositories: [{ name: `owner/repo-${suffix}`, url: `https://github.com/owner/repo-${suffix}/`, dedupe_key: `github:owner/repo-${suffix}` }],
    products: [{ name: `Product ${suffix}`, url: `https://producthunt.com/products/${suffix}`, dedupe_key: `producthunt:${suffix}` }],
  };
}

test("accepts unique items and ignores a rerun of the same issue date", () => {
  const current = issue("2026-08-07");
  assert.deepEqual(findIssueDuplicates(current, [issue("2026-08-06", "prior"), current]), []);
});

test("rejects reused keys and canonical URLs from prior issues", () => {
  const prior = issue("2026-08-06", "prior");
  const current = issue("2026-08-07", "today");
  current.signals[0].dedupe_key = prior.signals[0].dedupe_key;
  current.products[0].url = `${prior.products[0].url}/?ref=ranking`;
  const errors = findIssueDuplicates(current, [prior]);
  assert.ok(errors.some((error) => error.includes("dedupeKey")));
  assert.ok(errors.some((error) => error.includes("normalizedUrl")));
});

test("rejects missing dedupe keys", () => {
  const current = issue("2026-08-07");
  delete current.repositories[0].dedupe_key;
  assert.ok(findIssueDuplicates(current).some((error) => error.includes("missing dedupe_key")));
});
