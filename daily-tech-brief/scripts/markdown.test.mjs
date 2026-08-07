import assert from "node:assert/strict";
import test from "node:test";
import { buildMarkdown } from "./markdown.mjs";

const issue = {
  brand: "CLAIRE'S MORNING SIGNALS",
  date: "2026-08-07",
  dek: "10 分钟读完 · 10 条精选",
  headline: "今日信号",
  signals: Array.from({ length: 4 }, (_, index) => ({
    title: `信号 ${index + 1}`,
    summary: "摘要",
    why: "原因",
    source: "来源",
    source_url: `https://example.com/signals/${index + 1}`,
  })),
  repositories: Array.from({ length: 4 }, (_, index) => ({
    name: `owner/repo-${index + 1}`,
    url: `https://github.com/owner/repo-${index + 1}`,
    summary: "项目简介",
    stars_total: "1,000",
  })),
  products: Array.from({ length: 2 }, (_, index) => ({
    name: `Product ${index + 1}`,
    url: `https://www.producthunt.com/products/product-${index + 1}`,
    summary: "产品简介",
  })),
  topic: "一个值得继续想的问题",
};

test("renders a dated ten-item Markdown edition with four numbered sections", () => {
  const markdown = buildMarkdown(issue);
  assert.match(markdown, /^# CLAIRE'S MORNING SIGNALS · 2026\.08\.07/mu);
  assert.match(markdown, /10 分钟读完 · 10 条精选/u);
  assert.match(markdown, /## 04 \/ THINK · 今日思考/u);
  assert.equal((markdown.match(/^### \d{2} ·/gmu) || []).length, 4);
  assert.equal((markdown.match(/^\d+\. \[owner\/repo-/gmu) || []).length, 4);
  assert.equal((markdown.match(/^- \[Product /gmu) || []).length, 2);
});
