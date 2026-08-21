# 微信公众号草稿与发布

## 目录

- [状态](#状态)
- [安全边界](#安全边界)
- [保存远端草稿前的条件](#保存远端草稿前的条件)
- [官方 API 草稿适配器](#官方-api-草稿适配器)
- [幂等、收据与回读](#幂等收据与回读)
- [更新已有草稿](#更新已有草稿)
- [微信响应兼容](#微信响应兼容)
- [失败阶段与恢复](#失败阶段与恢复)
- [浏览器人工草稿流程](#浏览器人工草稿流程)
- [公开发布不属于本适配器](#公开发布不属于本适配器)

## 状态

每个渠道独立记录状态：

~~~text
local_draft
editor_reviewed
owner_approved
submitting
remote_result_unknown
draft_created_unverified
remote_draft
review_confirmed
published_manual
failed
~~~

`remote_draft` 只表示草稿已写入并通过回读。`review_confirmed` 表示用户已经打开并确认该草稿无误，因此允许同哈希网站版本上线。`published_manual` 只记录用户后来在公众号后台手动公开；代码不执行微信发布或群发。

## 安全边界

默认停止在本地待审稿。新稿使用 `scripts/push_markdown_draft.py`；它默认也是 dry-run，只读取并检查 `article.md` 与派生稿件包，不请求微信凭据、不上传图片、不创建草稿。旧 `push_wechat_draft.py` 只保留给历史 `signal.json` 稿件。

该适配器只调用微信公众号官方素材与草稿接口，作用域止于“保存到草稿箱”。它不调用发布或群发接口，也不发送手机预览。草稿授权不能解释为发布、群发或预览授权。

不要使用隐藏接口，不复制浏览器 token，不把 AppSecret、access_token、Cookie、二维码或真实凭据写进仓库、稿件、命令参数、收据和日志。

开发、调试或配置适配器的授权，只允许搭建和验证本地流程，不等于任何一篇稿件的远端上传授权。即使凭据已经存在，每篇稿件仍必须根据目标账号和当前内容哈希单独取得明确确认。

## 保存远端草稿前的条件

执行远端写入前同时确认：

1. 目标公众号名称、主体和 AppID 指纹已经写入 `release.json`；
2. 稿件 title、date、slug、`article.md` 精确字节的 SHA-256 与本地整包哈希已确定；
3. `article.md` frontmatter 与 `source-notes.md` 已完成编辑审核和本轮事实新鲜度检查；
4. 批准记录同时绑定当前 `content_hash` 与 `package_hash`，正文、标题、微信元数据或媒体改变后重新计算并重新批准；
5. `wechat.html`、`wechat-cover.png` 和所有正文图片均为这次批准的版本；
6. 微信作者、摘要、原文链接和评论开关已经确定；作者默认留空，只有用户明确指定署名时才填写；
7. 一至三个微信原生话题已经确定，或明确本篇不添加话题；
8. 用户明确允许把这两个哈希对应的稿件写入这个公众号的草稿箱；
9. 目标账号拥有素材和草稿接口权限，调用出口满足微信 IP 白名单要求。

`release.json.canonical.source_hash` 使用 `sha256:` 加 `article.md` 精确文件字节的 SHA-256。`renders.wechat_package_hash` 还绑定确定性渲染出的正文 HTML、每张正文图片的文件哈希和 900×383 封面文件哈希；网站 package hash 独立绑定网站板式与头图。正文、frontmatter、渲染器、模板、封面或图片文件发生变化时，旧批准自动失效。即使 `article.md` 的 source hash 没变，只要 renderer 让 HTML 变化，也必须生成新 package hash 并重新批准。

## 官方 API 草稿适配器

### 凭据

在仓库之外，通过当前进程环境或受控的密钥管理器提供：

~~~text
WECHAT_APP_ID
WECHAT_APP_SECRET
WECHAT_TARGET_ACCOUNT
WECHAT_TARGET_PRINCIPAL
~~~

`WECHAT_TARGET_ACCOUNT` 与 `WECHAT_TARGET_PRINCIPAL` 必须和 `release.json.target_account` 完全一致；`WECHAT_APP_ID` 的 SHA-256 必须匹配其中的 `app_id_fingerprint`。不要把真实值写进 `.env` 后提交，也不要把 AppSecret 作为命令行参数。

当前 Mac 使用钥匙串服务 `com.frontierworld.frontier-signals.wechat` 保存四项凭据，并通过 `/Users/chenjie/.local/bin/frontier-wechat-keychain-run` 注入单次子进程。不得把钥匙串回读内容打印到日志。Security Framework 写入的 Data 通过 `security` CLI 读取时可能表现为十六进制；读取器应兼容解码，不能把它误判为损坏后要求用户反复输入。

需要首次导入时，临时明文文件放在仓库外并设为 `0600`。先用 Security Framework 逐字节回读确认，再删除临时文件。账号名称、主体和 AppID 指纹可以进入 `release.json`；AppID、AppSecret、access token、Cookie 和二维码不能进入稿件包、收据或命令参数。

账号权限因主体和认证状态而异。调用前在公众号后台确认素材和草稿接口权限。Cloudflare 等无固定出口 IP 的环境要先解决白名单，不能把白名单失败交给循环重试。

`stable_token` 返回 `40164 invalid ip` 表示调用尚未取得 token，也没有上传素材。可以在确认当前出口 IP 后修复白名单，再从 dry-run 重试。若连续请求显示不同出口 IP，说明出口会轮换；停止逐个追加白名单，改用固定出口后再继续。

### 1. 默认 dry-run

先运行不带 `--confirm` 的预检：

~~~bash
python3 scripts/push_markdown_draft.py /absolute/path/to/article-directory
~~~

dry-run 不需要微信凭据，也不发生远端写入。它必须检查并展示：

- 严格稿件校验与媒体校验；
- `owner_approved` 状态、批准时间和事实新鲜度时间；
- 当前 `article.md` 哈希、整包哈希与 `release.json` 是否一致；
- `.frontier-build/wechat.html`、媒体清单与 Markdown 渲染 manifest 是否一致；
- 目标公众号名称、主体和 AppID 指纹；
- 标题、作者（默认空）、摘要、原文链接与评论设置；
- `wechat.topics` 中准备添加的原生话题，以及它们是否仍需人工添加；
- `wechat.html` 中的图片是否全部登记、存在并满足格式和大小限制；
- 900×383 封面、正文长度、危险标签、本地地址和外部链接警告；
- 远端已有记录或结果不确定时应走的恢复路径。

任何 blocker 都必须先修复。不要为了通过预检而跳过校验或手改远端状态。

### 2. 逐稿确认

把 dry-run 的目标公众号、标题、内容哈希、整包哈希、正文图片数量、封面和所有 warning 展示给用户。只有用户对这篇稿件、这个账号和这两个精确哈希明确确认后，才能执行远端命令。

确认后正文、标题、微信元数据、封面或关键图片发生变化，原确认失效。重新生成稿件、更新哈希、再跑 dry-run，并重新确认。

### 3. 创建并回读草稿

确认环境变量已经在受控进程中设置后，使用 dry-run 输出的原样值执行：

~~~bash
/Users/chenjie/.local/bin/frontier-wechat-keychain-run \
  python3 scripts/push_markdown_draft.py /absolute/path/to/article-directory \
  --confirm \
  --approved-hash 'sha256:DRY_RUN_OUTPUT' \
  --approved-package-hash 'sha256:DRY_RUN_PACKAGE_OUTPUT' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT'
~~~

三个目标身份参数必须逐字来自同一次 dry-run；缺少任意一项或与 `release.json`、当前 Keychain 凭据不一致时，在任何网络请求前停止。`--confirm` 只授权这一次草稿写入。适配器依次：

1. 取得官方 access token；
2. 通过 `media/uploadimg` 上传正文图片并把本地相对路径替换为微信 HTTPS URL；
3. 通过 `material/add_material` 上传 900×383 封面并取得 MediaID；
4. 通过 `draft/add` 创建单篇图文草稿；
5. 通过 `draft/get` 立即回读；
6. 核对标题、作者字段、摘要、封面、评论设置、正文标准化文本、图片数量、正文图片和本地地址残留；作者为空时确认远端没有显示署名；
7. 只有回读通过后才写入 `remote_draft`，并保存本地收据。

适配器不调用 publish、freepublish、mass send 或 preview 类接口。完成后只得到草稿，不会公开、不群发，也不会发到任何微信号预览。

当前微信公众号官方 `draft/add` 文档没有原生话题字段。适配器会把 `wechat.topics` 显示在 dry-run 与本地收据中，并明确记录 `native_topics_applied: false`，但不会把普通 `#话题` 文本塞进正文冒充原生话题。需要话题时，创建草稿后在公众号编辑器中人工添加，再重新打开草稿确认。

### 图片消息（贴图）草稿

公众号后台的“贴图”对应官方草稿接口的图片消息类型 `newspic`，不要把它包装成只有一张图的普通文章。使用 `scripts/push_image_draft.py`：

~~~bash
python3 scripts/push_image_draft.py /absolute/path/to/image-draft-package
~~~

本地包以 `draft-package.json` 为唯一文字与账号配置源，1–20 张图片按 `images` 数组顺序单独保存，首图为封面。dry-run 校验完整目标账号、标题、纯文本配文、有序图片字节与尺寸、两次 dbs 复核、humanizer 评分，以及精确内容哈希和整包哈希，不读取微信凭据、不上传素材。

用户明确确认这条贴图、目标账号和两个哈希后，通过钥匙串执行：

~~~bash
/Users/chenjie/.local/bin/frontier-wechat-keychain-run \
  python3 scripts/push_image_draft.py /absolute/path/to/image-draft-package \
  --confirm \
  --approved-hash 'sha256:DRY_RUN_CONTENT_HASH' \
  --approved-package-hash 'sha256:DRY_RUN_PACKAGE_HASH' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT'
~~~

适配器先用 `material/add_material` 按顺序上传所有图片，再调用 `draft/add`，其中 `article_type` 为 `newspic`，永久 MediaID 写入 `image_info.image_list`。创建后立即通过 `draft/get` 核对类型、标题、配文、评论设置、图片顺序、数量和全部 MediaID；只有全部一致才写入 `image-draft-receipt.json` 的 `verified`。

已有验证贴图的配文或图片变化时，dry-run 显示原 draft ID、旧/新内容哈希、旧/新整包哈希和新图片列表。用户确认新版本后，额外传入原 draft ID：

~~~bash
/Users/chenjie/.local/bin/frontier-wechat-keychain-run \
  python3 scripts/push_image_draft.py /absolute/path/to/image-draft-package \
  --confirm \
  --approved-hash 'sha256:NEW_CONTENT_HASH' \
  --approved-package-hash 'sha256:NEW_PACKAGE_HASH' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT' \
  --draft-id 'EXACT_EXISTING_DRAFT_ID'
~~~

更新前先通过 `draft/get` 核对旧标题、配文哈希、评论和有序 MediaID；一致后才上传新图片并调用 `draft/update` 同一 ID。更新后再次回读完整新包。若更新结果不确定，只能用 `--reconcile` 回读该 ID：匹配新包则完成，匹配旧快照则恢复旧收据，两者都不匹配则停止人工核对。禁止重试 `draft/update` 或回退到 `draft/add`。

## 幂等、收据与回读

成功后把草稿 MediaID 记录为 `release.json.wechat.draft_id`，并在稿件目录生成 `wechat-draft-receipt.json`。收据记录目标账号、内容哈希、整包哈希、草稿 ID、素材结果和回读结果，不记录密钥或 access token。该收据是本地运行证据，必须被 Git 忽略。

再次执行同一稿件时，先根据收据和 `release.json` 调用 `draft/get` 复核已有草稿；能确认同一版本时复用，不能再创建重复稿。远端回读至少确认：

- 标题、作者字段和非空摘要与批准值一致；作者可以按默认规则为空；
- 封面 MediaID 与本次上传一致；
- 正文图片能与批准版本一一对应。微信可以重托管图片、改写 URL、把 `src` 变成 `data-src`；按官方图片域名、图片数量、顺序、唯一非空 alt 与正文文字验证，不要求 URL 逐字一致；
- 正文标准化文本和图片数量与批准版本一致；
- 正文不再包含 `file://`、localhost、`127.0.0.1` 或本地相对素材地址；
- 评论设置一致；
- 外部链接若被微信过滤，结果中明确给出 warning。

`draft/add` 返回 MediaID 但 `draft/get` 校验失败时，状态必须停在 `draft_created_unverified`。这表示草稿可能已经存在，不能再创建一份。

## 更新已有草稿

已有 receipt 和 draft ID 后，任何正文、封面、排版或正文图片变化都生成新的 package hash，旧批准随即失效。此时必须：

1. 对新稿件包重新运行 dry-run；
2. 展示原 draft ID、新内容哈希、新整包哈希、图片和 warning；
3. 取得明确的新版本授权；
4. 使用 `scripts/update_markdown_draft.py` 调用官方 `draft/update`；
5. 更新前先用 `draft/get` 确认原 draft 标题，更新后再回读全文、图片、封面和设置；
6. 任何未知结果只协调这个 draft ID，禁止回退到 `draft/add`。

更新适配器不创建新草稿。原草稿无法定位、receipt 不匹配、账号不一致或 draft ID 漂移时必须停止。

更新 dry-run：

~~~bash
python3 scripts/update_markdown_draft.py /absolute/path/to/article-directory
~~~

确认后通过钥匙串更新原 draft ID：

~~~bash
/Users/chenjie/.local/bin/frontier-wechat-keychain-run \
  python3 scripts/update_markdown_draft.py /absolute/path/to/article-directory \
  --confirm \
  --approved-hash 'sha256:DRY_RUN_SOURCE_HASH' \
  --approved-package-hash 'sha256:DRY_RUN_PACKAGE_HASH' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT' \
  --draft-id 'EXACT_EXISTING_DRAFT_ID'
~~~

只读协调 dry-run：

~~~bash
python3 scripts/reconcile_markdown_draft.py /absolute/path/to/article-directory
~~~

确认后只执行 `stable_token + draft/get`：

~~~bash
/Users/chenjie/.local/bin/frontier-wechat-keychain-run \
  python3 scripts/reconcile_markdown_draft.py /absolute/path/to/article-directory \
  --confirm \
  --approved-hash 'sha256:DRY_RUN_SOURCE_HASH' \
  --approved-package-hash 'sha256:DRY_RUN_PACKAGE_HASH' \
  --target-account 'EXACT_DRY_RUN_ACCOUNT' \
  --target-principal 'EXACT_DRY_RUN_PRINCIPAL' \
  --target-app-id-fingerprint 'sha256:EXACT_DRY_RUN_APP_ID_FINGERPRINT' \
  --draft-id 'EXACT_EXISTING_DRAFT_ID'
~~~

协调脚本不上传素材、不调用 `draft/update` 或 `draft/add`。更新适配器在 pending receipt 中保存上一版 receipt 与更新前远端快照哈希：进程停在 `update_submitting` 时，协调脚本先判断远端是否已变成新包；若仍是更新前快照，恢复上一版 receipt 并标记 `not_updated`，随后才能重新 dry-run 和授权。远端既不匹配新包也不匹配旧快照时停止并人工核对，不能猜测或再次更新。

## 微信响应兼容

- `media/uploadimg` 可能返回 `http://mmbiz.qpic.cn/...`。只允许把微信官方 `mmbiz.qpic.cn` 响应升级为 HTTPS；任何其他 HTTP 主机继续拒绝。
- 微信保存正文后可能把图片重新托管到 `mmbiz.qpic.cn` 或 `sz_mmbiz.qpic.cn`，把尺寸路径从 `/0` 改成 `/640`，并把 `src` 改成 `data-src`。回读器同时读取 `src` 与 `data-src`，按官方主机、图片数量、顺序、alt 和正文文字验证，不要求上传 URL 逐字不变。
- 微信草稿清洗会移除 `figure`，图片也可能随之消失。正文独占图片使用 `section + img`，不使用 `p > figure`、空段落或重复封面；图片块只保留一次 20 px 间距。
- `draft/add` 不支持原生话题字段。话题只记录在本地收据，发布前在公众号编辑器人工添加并复核。
- 用户手动发表后，原 draft ID 可能在 `draft/get` 返回 `40007 invalid media_id`。此时停止草稿回读和更新，不能把它当成草稿丢失而重建；取得公开 `https://mp.weixin.qq.com/s/...` URL 后记录 `published_manual`。
- 用户已明确说明手动发表、但公开 URL 暂时不可得时，网站可以先走 `article:publish-manual`：记录 `published_manual / published_unrecorded`，不上报伪链接，不渲染 `sameAs`。该动作只部署网站，不访问微信；拿到 URL 后再补录。

## 失败阶段与恢复

| 失败阶段 | 远端可能状态 | 允许动作 | 禁止动作 |
| --- | --- | --- | --- |
| `stable_token` 失败 | 无远端写入 | 修复账号、权限或固定 IP，重新 dry-run | 循环重试、盲目追加动态 IP |
| 正文图或封面上传失败，尚未进入 `draft/add` | 无草稿；可能留下未引用的临时素材 | 修复响应兼容或素材后，重新 dry-run | 声称草稿已创建 |
| `draft/add` 明确拒绝 | 确认未创建 | 记录 `failed/not_created`，修复后按同哈希重试 | 把拒绝当成未知结果 |
| `draft/add` 超时、断连或系统错误 | 可能已创建 | 记录 `remote_result_unknown`，通过列表与 `draft/get` 协调 | 再次 `draft/add` |
| 已取得 draft ID，但回读失败 | 草稿已存在 | 保留 receipt 与 draft ID，只做 `draft/get` 诊断 | 创建第二份草稿 |
| 稿件或媒体变化 | 旧草稿、旧 package hash | 重新渲染、展示新哈希、重新授权后 `draft/update` 同一 ID | 沿用旧批准、调用 `draft/add` |
| `draft/update` 结果未知或回读失败 | 同一草稿可能已更新 | 只对该 ID 运行 `reconcile_markdown_draft.py` | 再次更新或新建 |
| 用户已手动发表 | 公开文章存在，draft ID 可能失效 | 停止草稿操作，记录公开 URL | 继续协调、更新或删除草稿 |

补充规则：

- token、图片或封面上传失败且尚未进入 `draft/add` 时，可以在排除原因后重新从 dry-run 开始；
- `draft/add` 超时、断连或返回结果不确定时，写入 `remote_result_unknown`，禁止立即重试；
- 若未知结果没有 draft ID，但已经保存了本次图片与封面上传记录，只能以 `--reconcile-unknown-only` 重新进入 Markdown 适配器：它在稿件锁内再次确认仍为 unknown + no-ID，再用 `draft/batchget` 寻找唯一候选并 `draft/get` 回读；状态漂移时必须在任何上传或 `draft/add` 前停止；
- 结果不确定时，先用已有上传记录和草稿列表查找候选，再通过 `draft/get` 回读；只有唯一候选完全匹配时才恢复为 `remote_draft`；
- 找到零个或多个候选时停止，要求人工核对草稿箱，不能猜测或盲重试；
- 草稿已创建但回读失败时，保留 draft ID 与上传记录，只做回读恢复，不重复 `draft/add`；
- 权限、白名单、账号绑定、素材限制或微信明确拒绝时，修复原因并重新执行 dry-run；
- 任何失败都不得降级为发布、群发、手机预览或隐藏接口。

## 浏览器人工草稿流程

### 本地排版与剪贴板

独立的 `frontier-composer` 仓库是浏览器人工流程的本地准备工具。它直接读取 `article.md` 或完整文章目录，用微信兼容的内联样式预览正文，并把富文本、纯文本和本地图片写入剪贴板。

从 `frontier-composer` 仓库运行：

~~~bash
npm ci
npm run dev
~~~

随后打开 `http://127.0.0.1:8900`，导入包含 `article.md` 和图片的完整文章目录。H1 默认提取为微信标题并单独复制，正文通过“复制到公众号”写入剪贴板。该工具不上传稿件、不登录微信，也不覆盖稿件包内由 Markdown 确定性生成的 `.frontier-build/wechat.html`。

剪贴板写入成功只说明本机已经准备好富文本。粘贴到公众号以后仍要检查标题、粗体、小标题、链接和每张图片；保存草稿并重新打开，确认图片已由微信转存，正文中不再残留 `data:`、`blob:`、`file:`、localhost、`127.0.0.1` 或相对路径。没有完成这一步，不能把本地复制描述成草稿已保存。

### 公众号后台操作

官方 API 权限不可用时，可以在获得同样的逐稿授权后使用已登录的浏览器会话：

1. 确认公众号名称与主体；
2. 新建图文，填写已批准的标题、摘要和封面；作者栏默认留空，只有用户明确指定署名时才填写；
3. 优先用本地排版工具导入完整文章包并粘贴富文本；工具不可用时再使用 `.frontier-build/wechat.html` 或按 `article.md` 录入；
4. 逐张确认正文图片已经显示并可读，缺失图片再手动上传；
5. 检查原文链接、声明、来源和微信清洗后的样式；
6. 按 `wechat.topics` 在文末使用微信原生话题功能添加一至三个话题，不输入普通 `#标签` 代替；
7. 只保存草稿，不点击发表、群发或手机预览；
8. 回到草稿列表重新打开并核对正文、图片和话题，记录草稿时间、账号和版本。

相对路径图片不会随 HTML 自动上传，不能把本地 HTML 当成已经可发布。浏览器出现登录失效、验证码、频控或账号异常时立即停止。

## 公开发布不属于本适配器

公开发布、定时发布、群发和手机预览均是新的外部动作，不属于草稿适配器，也不能沿用草稿批准。若将来实现这些能力，必须使用独立工具、单独审批和单独审计；在此之前保持 `remote_draft`。

## 当前工作区检查

每次使用都重新检查 live code、命令帮助与当前稿件状态，不根据文档假设适配器或账号权限一定可用。

在没有逐稿批准、真实 draft ID、成功回读与本地收据的情况下，任何“已保存草稿”都属于错误陈述；没有发布结果和公开 URL 时，任何“已发布”都属于错误陈述。
