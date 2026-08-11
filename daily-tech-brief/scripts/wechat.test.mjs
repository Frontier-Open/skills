import assert from "node:assert/strict";
import test from "node:test";
import { buildWechatHtml, buildWechatMarkdown } from "./wechat.mjs";

const article = {
  brand: "FRONTIER WORLD",
  author: "Frontier World",
  date: "2026-08-11",
  title: "测试文章",
  subtitle: "一个用于测试的副标题",
  cover: "./cover.jpg",
  intro: ["开头第一段。"],
  sections: Array.from({ length: 3 }, (_, index) => ({
    label: String(index + 1).padStart(2, "0"),
    title: `章节 ${index + 1}`,
    paragraphs: ["章节正文。"],
    callout: index === 0 ? "重点判断。" : undefined,
    points: index === 2 ? ["第一步", "第二步"] : undefined,
  })),
  conclusion: { title: "写在最后", paragraphs: ["结语。"], question: "一个问题？" },
  sources: [{ label: "Example", url: "https://example.com/" }],
};

test("renders one-H1 Markdown and inline-style WeChat HTML", () => {
  const markdown = buildWechatMarkdown(article);
  const html = buildWechatHtml(article);
  assert.equal((markdown.match(/^# /gmu) || []).length, 1);
  assert.match(markdown, /^# 测试文章/mu);
  assert.match(markdown, /FRONTIER WORLD · 2026\.08\.11/u);
  assert.match(html, /max-width:677px/u);
  assert.match(html, /style="[^"]+"/u);
  assert.doesNotMatch(html, /<script|<style/iu);
  assert.match(html, /https:\/\/example\.com\//u);
});
