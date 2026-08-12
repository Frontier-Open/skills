import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { buildLarkCard } from "./lark-card.mjs";

const fixture = JSON.parse(await readFile(new URL("../assets/article.example.json", import.meta.url), "utf8"));

test("renders a Frontier Signals reviewer card", () => {
  const card = buildLarkCard(fixture, {
    imageKey: "img_example",
    documentUrl: "https://example.feishu.cn/docx/docxExample123",
  });
  assert.equal(card.header.template, "blue");
  assert.match(card.header.title.content, /Frontier Signals · 2026\.08\.12/u);
  const serialized = JSON.stringify(card);
  assert.match(serialized, /飞书全文/u);
  assert.match(serialized, /查看官网 · 7分钟/u);
  assert.doesNotMatch(serialized, /科技早报/u);
});

test("requires a valid Feishu document URL", () => {
  assert.throws(() => buildLarkCard(fixture, { documentUrl: "https://example.com/" }), /Feishu document URL/u);
});
