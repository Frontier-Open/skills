# Markdown 双渠道发布

`article.md` 是新稿唯一公开内容源。`release.json` 只记录审批、哈希、微信草稿 ID、网站部署状态和错误；不得保存第二份正文。`source-notes.md` 继续保存研究过程、证据链和图片权利记录。

旧 `signal.json` 稿件只用于历史兼容，不再作为新稿模板。

## 目录

- [文章包](#文章包)
- [渲染](#渲染)
- [微信草稿](#微信草稿)
- [草稿复核与网站发布](#草稿复核与网站发布)
- [微信手动公开](#微信手动公开)
- [状态与失效规则](#状态与失效规则)

## 文章包

把新稿放在 Signals 站点仓库：

~~~text
data/articles/YYYY/MM/DD/slug/
  article.md
  source-notes.md
  images/
  wechat-cover.png
  og.png
  release.json                  # 首次渲染生成
  .frontier-build/             # 派生预览，Git 忽略
  wechat-draft-receipt.json    # 远端草稿回读收据，Git 忽略
~~~

从 [article.example.md](../assets/article.example.md) 建立 `article.md`。该文件是结构模板，必须用真实材料补足对应文章形态的篇幅、来源和配图门槛后才能通过渲染。YAML frontmatter 保存标题、摘要、核心判断、渠道元数据、来源、claim、实测和媒体权利；Markdown 正文保存唯一公开表达与图片顺序。Frontmatter 中的正文图片必须与 Markdown 图片一一对应；`source-notes.md` 必须存在且非空。

新稿只使用段落、H2/H3、列表、引用、局部加粗、链接、代码块和独占一行的图片。禁止 raw HTML、Markdown 表格、外部图片和越过文章目录的路径。正文图使用 PNG/JPEG，封面使用 900×383 PNG。

## 渲染

在 `/Users/chenjie/Workspace/claire/signals` 运行：

~~~bash
export WECHAT_TARGET_ACCOUNT='公众号名称'
export WECHAT_TARGET_PRINCIPAL='公众号主体'
export WECHAT_APP_ID_FINGERPRINT='sha256:APP_ID_FINGERPRINT'
npm run article:prepare -- /absolute/path/to/article.md
~~~

也可以在受控环境提供 `WECHAT_APP_ID`，渲染器只计算并保存其 SHA-256 指纹；AppSecret 永远不进入渲染过程或仓库。缺少账号名称、主体或 AppID 指纹时可以生成本地预览，但微信草稿预检保持 blocked。

该命令从同一 Markdown 生成：

- `.frontier-build/wechat.html`：微信公众号内联样式正文；
- `.frontier-build/web/index.html`：带 `noindex` 的网站板式预览；
- `.frontier-build/channel-manifest.json`：派生哈希和媒体清单；
- `release.json`：渠道状态，不包含正文。

重新渲染同一字节输入必须得到相同 HTML 和 package hash。正文、标题、渲染器、模板、封面或任一图片发生变化时，之前的微信上传批准和网站复核批准全部失效；source hash 没变不能保住已变化的 package 批准。

## 微信草稿

凭据与钥匙串规则统一见 [wechat-release.md](wechat-release.md#凭据)。当前 Mac 的确认命令通过 `/Users/chenjie/.local/bin/frontier-wechat-keychain-run` 注入单次子进程。

先做无网络、无写入预检：

~~~bash
python3 /Users/chenjie/Workspace/claire/skills/frontier-signals/scripts/push_markdown_draft.py \
  /absolute/path/to/article-directory
~~~

展示目标公众号、标题、`article.md` 哈希、微信 package hash、正文图片、封面与 warning。用户明确批准这篇稿、这个账号和这两个哈希后，再原样执行：

~~~bash
/Users/chenjie/.local/bin/frontier-wechat-keychain-run \
  python3 /Users/chenjie/Workspace/claire/skills/frontier-signals/scripts/push_markdown_draft.py \
  /absolute/path/to/article-directory \
  --confirm \
  --approved-hash 'sha256:DRY_RUN_SOURCE_HASH' \
  --approved-package-hash 'sha256:DRY_RUN_PACKAGE_HASH' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT'
~~~

命令行中的账号名称、主体和 AppID 指纹都必须逐字来自同一次 dry-run；它们是批准绑定，不是凭据。凭据只通过 `WECHAT_APP_ID`、`WECHAT_APP_SECRET`、`WECHAT_TARGET_ACCOUNT` 和 `WECHAT_TARGET_PRINCIPAL` 环境变量提供。适配器只上传素材、创建草稿并通过 `draft/get` 回读；不发布、不群发、不发送手机预览。

若 receipt 已记录 draft ID，而稿件包后来发生变化，使用 `scripts/update_markdown_draft.py`。先不带 `--confirm` 展示原 draft ID、新内容哈希和新整包哈希；用户逐项确认后，带相同 draft ID 和哈希执行。该适配器只调用 `draft/update`，不能调用 `draft/add`。

远端写入或更新已完成、但本地验证尚未完成时，使用 `scripts/reconcile_markdown_draft.py`。它只回读现有 draft ID 并更新本地收据，不得上传、更新或创建草稿。`article:prepare` 因新包重置 `release.json.wechat.draft_id` 时，保留的 `wechat-draft-receipt.json` 仍是现有远端草稿身份；不要删除收据或退回 `draft/add`。

## 草稿复核与网站发布

用户在公众号草稿箱打开并检查标题、正文、图片、封面、链接和原生话题后，先运行 dry-run：

~~~bash
cd /Users/chenjie/Workspace/claire/signals
npm run article:review -- /absolute/path/to/article.md
~~~

只有以下条件同时满足才允许继续：

- `wechat.status` 为 `remote_draft`；
- `wechat-draft-receipt.json` 回读状态为 `verified`；
- draft ID、Markdown 哈希和微信 package hash 与当前文件完全一致；
- 网站 package hash 仍是本轮预览版本。

用户明确表示当前草稿无误并允许同步网站后执行：

~~~bash
npm run article:review -- /absolute/path/to/article.md --confirm
~~~

若微信已经由用户手动发表，但本地草稿状态未能验证，也没有公开文章 URL，不得继续调用微信草稿接口或伪造链接。使用人工发表恢复路径：

~~~bash
npm run article:publish-manual -- /absolute/path/to/article.md
~~~

dry-run 展示当前 source hash、WeChat package hash、site package hash、目标账号和网站 URL。用户已明确授权当前版本上线后，原样带入：

~~~bash
npm run article:publish-manual -- /absolute/path/to/article.md \
  --confirm \
  --approved-hash 'sha256:DRY_RUN_SOURCE_HASH' \
  --approved-wechat-package-hash 'sha256:DRY_RUN_WECHAT_PACKAGE_HASH' \
  --approved-site-package-hash 'sha256:DRY_RUN_SITE_PACKAGE_HASH' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT'
~~~

该动作不访问微信 API；它把微信状态记录为 `published_manual / published_unrecorded`，不渲染公众号原文链接或 JSON-LD `sameAs`，然后执行正常网站构建、测试、Cloudflare 部署与逐字节回读。稍后拿到公开微信 URL 和实际发布时间后，再用 `article:record-wechat` 补录。

该命令先使用官方 `draft/get` 再次回读当前草稿；如果标题、摘要、正文、封面、评论设置或图片已经漂移，立即停止。自动网站发布还要求 renderer、Worker、Wrangler 配置、主题 CSS 与依赖锁已经提交且工作区干净，避免把未审查的基础设施改动顺带部署。回读一致后，把本次确认绑定到 draft ID 和所有当前哈希，然后从空的 `dist/` 构建完整站点、计算包含静态站、Worker、Wrangler 配置和依赖锁的 deploy bundle hash、运行测试与校验、部署 Cloudflare，并逐字节回读文章、首页、RSS、sitemap、主题 CSS 和头图。全部匹配时，网站状态才写成 `live`。

本地渲染或测试在上传前失败时，状态明确保持 `failed/not_uploaded`，修复后使用同一批准记录安全重试：

~~~bash
npm run article:retry -- /absolute/path/to/article.md
~~~

部署或验证结果不确定时状态停在 `deployment_result_unknown` 或 `deployed_unverified`，禁止盲目重试。

结果不确定时只做协调回读，不再次部署：

~~~bash
npm run article:reconcile -- /absolute/path/to/article.md
~~~

## 微信手动公开

网站上线后，用户仍在公众号后台手动发表微信文章。代码库不提供微信 publish、freepublish、mass send 或 preview 接口。

公开后可记录微信 URL：

~~~bash
npm run article:record-wechat -- /absolute/path/to/article.md \
  --url 'https://mp.weixin.qq.com/s/...' \
  --published-at '2026-08-18T20:00:00+08:00' \
  --confirm
~~~

该命令的 `--confirm` 同时授权一次网站元数据部署：它记录手动发布的微信 URL，重新生成并部署网站，在文章中补上“公众号原文”和 JSON-LD `sameAs`。它不会调用任何微信发布接口，也不会再次发布微信文章。

## 状态与失效规则

微信：

~~~text
local_rendered -> submitting -> remote_draft -> review_confirmed -> published_manual
~~~

网站：

~~~text
not_deployed -> deploying -> live
~~~

任何正文、frontmatter、封面或正文图片变化都会重新计算哈希，并把渠道状态退回 `local_rendered` / `not_deployed`。微信草稿确认不是微信公开发布授权；网站同步确认也不能解释为微信发布授权。
