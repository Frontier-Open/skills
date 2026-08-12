import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { assertNormativeArticle } from "./normative.mjs";

const fixture = JSON.parse(await readFile(new URL("../assets/article.example.json", import.meta.url), "utf8"));

test("validates the normative Frontier Signals contract", () => {
  assert.equal(assertNormativeArticle(structuredClone(fixture)).mode, "quick");
  const invalid = structuredClone(fixture);
  delete invalid.mode;
  assert.throws(() => assertNormativeArticle(invalid), /article\.mode/u);
});

test("recomputes declared editorial length outside the structural example", () => {
  const invalid = structuredClone(fixture);
  invalid.warnings = [];
  assert.throws(() => assertNormativeArticle(invalid), /word_count must equal computed count/u);
});

test("requires two independent chains for high-risk claims", () => {
  const invalid = structuredClone(fixture);
  invalid.fact_check[0].high_risk = true;
  assert.throws(() => assertNormativeArticle(invalid), /high-risk claim needs two independent chains/u);
});
