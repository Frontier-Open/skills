import assert from "node:assert/strict";
import test from "node:test";
import {
  parseDailyDev,
  parseGitHubTrending,
  parseHelloGitHub,
  parseProductHunt,
  parseTechmeme,
  safeWarning,
} from "./lib.mjs";

test("parses Techmeme RSS and prefers the reporting link", () => {
  const items = parseTechmeme(`<rss><channel><item><title>AI &amp; work</title><link>https://www.techmeme.com/p1</link><description><![CDATA[<a href="https://example.com/story">Story</a>]]></description><pubDate>Fri</pubDate></item></channel></rss>`);
  assert.deepEqual(items[0], {
    title: "AI & work",
    url: "https://example.com/story",
    aggregator_url: "https://www.techmeme.com/p1",
    published_at: "Fri",
  });
});

test("parses GitHub Trending metrics", () => {
  const html = `<article class="Box-row"><h2><a href="/owner/repo"><span>owner /</span> repo</a></h2><p class="col-9 color-fg-muted my-1 tmp-pr-4">Useful agent tool.</p><span itemprop="programmingLanguage">TypeScript</span><a href="/owner/repo/stargazers"><svg></svg> 4,837</a><span>2,802 stars today</span></article>`;
  assert.deepEqual(parseGitHubTrending(html)[0], {
    name: "owner/repo",
    url: "https://github.com/owner/repo",
    description: "Useful agent tool.",
    language: "TypeScript",
    stars_today: "2,802",
    stars_total: "4,837",
  });
});

test("parses Product Hunt official feed", () => {
  const items = parseProductHunt(`<feed><entry><title>Product</title><link rel="alternate" href="https://product.example"/><content>&lt;p&gt;Does one thing well.&lt;/p&gt;</content><published>now</published><updated>later</updated><author><name>Ada</name></author></entry></feed>`);
  assert.equal(items[0].name, "Product");
  assert.equal(items[0].description, "Does one thing well.");
});

test("parses daily.dev public blog cards", () => {
  const html = `<section data-track-section="blog-highlights"><a href="/blog/post/"><h3>How agents work</h3><p>Aug 7, 2026 · 6 min read</p></a></section><section data-track-section="final-cta"></section>`;
  assert.deepEqual(parseDailyDev(html)[0], {
    title: "How agents work",
    url: "https://daily.dev/blog/post/",
    published_label: "Aug 7, 2026 · 6 min read",
  });
});

test("parses HelloGitHub and redacts secret-like warnings", () => {
  const items = parseHelloGitHub({ success: true, data: [{ full_name: "owner/repo", title: "标题", summary: "摘要", primary_lang: "Go", clicks_total: 12 }] });
  assert.equal(items[0].url, "https://github.com/owner/repo");
  assert.equal(safeWarning(new Error("token=abc123 failed")), "token=[redacted] failed");
});
