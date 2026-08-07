# Feishu delivery

Use an interactive card when the recipient should scan the thesis and open the full issue. Treat Open Graph link previews as a fallback for plain pasted links, not as a replacement for the card.

## Prepare the card

1. Upload the issue cover as a Feishu message image and retain its `image_key`:

   ```bash
   lark-cli im images create --data '{"image_type":"message"}' --file ./public/YYYY-MM-DD/og.png --as bot
   ```

2. Render a send-ready card:

   ```bash
   node scripts/render-lark-card.mjs \
     --issue issue.json \
     --image-key img_xxx \
     --out lark-card.json
   ```

3. Inspect `lark-card.json`. Confirm the recipient, exact card content, and whether the sender is `user` or `bot`.
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

If image upload is unavailable, render with `--without-image`. Never put a public image URL into `img_key`; Feishu cards require an uploaded `img_xxx` key.
