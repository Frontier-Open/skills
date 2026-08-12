import assert from "node:assert/strict";
import { access, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const fixtureUrl = new URL("../assets/article.example.json", import.meta.url);
const rendererPath = new URL("./render-article.mjs", import.meta.url).pathname;

test("copies section media to both web and WeChat output roots", async () => {
  const root = await mkdtemp(join(tmpdir(), "frontier-signals-render-"));
  try {
    const articlePath = join(root, "article.json");
    const mediaRoot = join(root, "media");
    const webPath = join(root, "public", "index.html");
    const wechatPath = join(root, "drafts", "wechat.html");
    const article = JSON.parse(await readFile(fixtureUrl, "utf8"));
    await mkdir(mediaRoot, { recursive: true });
    await writeFile(articlePath, JSON.stringify(article), "utf8");
    for (const section of article.sections.filter((item) => item.image)) {
      await writeFile(join(mediaRoot, section.image.path), "fixture", "utf8");
    }

    const result = spawnSync(process.execPath, [
      rendererPath,
      "--article", articlePath,
      "--media-root", mediaRoot,
      "--web", webPath,
      "--markdown", join(dirname(webPath), "article.md"),
      "--wechat-html", wechatPath,
      "--wechat-markdown", join(dirname(wechatPath), "wechat.md"),
    ], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    for (const section of article.sections.filter((item) => item.image)) {
      await access(join(dirname(webPath), section.image.path));
      await access(join(dirname(wechatPath), section.image.path));
    }
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
