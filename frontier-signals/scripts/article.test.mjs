import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { assertArticle, buildArticleMarkdown, buildWebHtml, buildWechatHtml } from "./article.mjs";

const fixture = JSON.parse(await readFile(new URL("../assets/article.example.json", import.meta.url), "utf8"));

test("validates the canonical Frontier Signals article contract", () => {
  assert.equal(assertArticle(structuredClone(fixture)).id, "2026-08-12/example-signal");
  const invalid = structuredClone(fixture);
  invalid.sections[0].source_ids = ["missing-source"];
  assert.throws(() => assertArticle(invalid), /Unknown source id/u);
});

test("renders consistent Markdown, WeChat, and web editions", () => {
  const markdown = buildArticleMarkdown(fixture);
  const wechat = buildWechatHtml(fixture);
  const web = buildWebHtml(fixture);
  assert.equal((markdown.match(/^# /gmu) || []).length, 1);
  assert.match(markdown, /本节来源：\[1\]/u);
  assert.match(wechat, /max-width:677px/u);
  assert.doesNotMatch(wechat, /<style|<script/iu);
  assert.match(wechat, /#155EEF/iu);
  assert.match(web, /application\/ld\+json/u);
  assert.match(web, /og:image:width/u);
  assert.match(web, /twitter:title/u);
  assert.match(web, /twitter:image/u);
  assert.match(web, /noindex,nofollow,noarchive/u);
  assert.match(web, /Frontier Signals/u);
  assert.match(web, />QUICK</u);
  assert.match(web, /-apple-system/u);
  assert.match(web, /font-optical-sizing: auto/u);
  assert.match(web, /a:focus-visible/u);
  assert.match(web, /prefers-reduced-motion: reduce/u);
  assert.match(web, /prefers-reduced-transparency: reduce/u);
  assert.match(web, /prefers-contrast: more/u);
  assert.match(web, /min-width: 2\.75rem/u);
  assert.match(web, /loading="lazy" decoding="async"/u);
  assert.match(web, /viewport-fit=cover/u);
  assert.match(web, /class="skip-link" href="#article-body"/u);
  assert.match(web, /<article class="article-page">/u);
  assert.match(web, /class="article-body" id="article-body" tabindex="-1"/u);
  assert.doesNotMatch(web, /<figure class="hero-media">/u);
});

test("published web editions are indexable", () => {
  const published = structuredClone(fixture);
  published.status = "published";
  assert.match(buildWebHtml(published), /index,follow,max-image-preview:large/u);
});
