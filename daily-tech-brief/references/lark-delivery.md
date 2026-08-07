# Feishu delivery

Use an interactive card when the recipient should scan the thesis and open the full issue. Treat Open Graph link previews as a fallback for plain pasted links, not as a replacement for the card.

## Create the cloud-document edition

1. Generate `brief.md` from the final issue JSON. Its first and only level-one heading must include the issue date.
2. Resolve the user identity's `my_library` space and list its root nodes. Find exactly one root node titled `Claire's Morning Signals`; this is the permanent briefing directory. Do not create the issue in Drive root or use `drive +move` as a substitute.
3. List the children of that directory. If a child for `YYYY-MM-DD` already exists, update and reuse it rather than creating a duplicate. Otherwise, create the document directly under the directory's wiki node token:

   ```bash
   lark-cli docs +create \
     --api-version v2 \
     --doc-format markdown \
     --parent-token <CLAIRE_MORNING_SIGNALS_NODE_TOKEN> \
     --title YYYY-MM-DD \
     --content @brief.md \
     --as user
   ```

4. Fetch the selected document once with `docs +fetch --api-version v2 --doc-format markdown` and verify its title, all four sections, all ten items, and source links. Re-list the permanent directory and verify that the document's `obj_token` is a child of that exact node.
5. Read the document's `drive permission.public get` settings. Require at least `link_share_entity=tenant_readable` for an internal recipient. Do not widen access automatically; if the intended recipient cannot read it, stop before sending and request the narrowly scoped permission change. Retain its `/docx/` or `/wiki/` URL for the card.

## Prepare the card

1. Upload the issue cover as a Feishu message image and retain its `image_key`:

   ```bash
   lark-cli im images create --data '{"image_type":"message"}' --file ./public/YYYY/MM/DD/og.png --as bot
   ```

2. Render a send-ready card:

   ```bash
   node scripts/render-lark-card.mjs \
     --issue issue.json \
     --image-key img_xxx \
     --document-url https://example.feishu.cn/docx/xxxxxxxx \
     --out lark-card.json
   ```

3. Inspect `lark-card.json`. Confirm the recipient, exact card content, webpage link, cloud-document link, and whether the sender is `user` or `bot`. The Feishu document must be the first `default` button on the left; the webpage must be the second `primary` button on the right.
4. Preview the request before sending:

   ```bash
   lark-cli im +messages-send \
     --user-id ou_xxx \
     --msg-type interactive \
     --content "$(jq -c . lark-card.json)" \
     --idempotency-key daily-brief-YYYY-MM-DD \
     --as user \
     --dry-run
   ```

5. Remove `--dry-run` only after approval. Preserve the date-based idempotency key so retries do not duplicate the delivery.

Because delivery uses `--user-id` with `--as user`, the card is sent as the authorized user into the normal P2P conversation with the recipient and remains visible in both participants' chat history. Using `--as bot` would instead send under the app bot identity.

If image upload is unavailable, render with `--without-image`. Never put a public image URL into `img_key`; Feishu cards require an uploaded `img_xxx` key.
