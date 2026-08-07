import assert from "node:assert/strict";
import test from "node:test";
import { buildLarkCard } from "./lark-card.mjs";

const issue = {
  date: "2026-08-07",
  generated_at: "2026-08-07T09:57:00+08:00",
  canonical_url: "https://brief.example.com/2026-08-07/",
  headline: "AI 正在争夺工作、成本与入口。",
  topic: "《今天的内容选题》",
  signals: [{ title: "信号一" }, { title: "信号二" }, { title: "信号三" }, { title: "信号四" }],
  repositories: [{}, {}, {}, {}],
  products: [{}, {}],
};

test("renders a compact Feishu card with an uploaded cover", () => {
  const card = buildLarkCard(issue, { imageKey: "img_v3_test" });
  assert.equal(card.header.template, "orange");
  assert.equal(card.elements[0].tag, "img");
  assert.equal(card.elements[0].img_key, "img_v3_test");
  assert.equal(card.elements.at(-2).actions[0].url, issue.canonical_url);
  assert.match(card.elements[2].fields[0].text.content, /\*\*4\*\*/u);
});

test("omits the cover when no image key is supplied", () => {
  const card = buildLarkCard(issue);
  assert.notEqual(card.elements[0].tag, "img");
});
