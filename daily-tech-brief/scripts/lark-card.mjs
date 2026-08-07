function dateLabel(date) {
  return date.replaceAll("-", ".");
}

function countField(count, label) {
  return {
    is_short: true,
    text: {
      tag: "lark_md",
      content: `**${count}**\n${label}`,
    },
  };
}

export function buildLarkCard(issue, { imageKey, documentUrl } = {}) {
  if (!issue?.date || !issue?.headline || !issue?.canonical_url) {
    throw new Error("Issue requires date, headline, and canonical_url");
  }

  if (!/^https:\/\/[^/]+\/(?:docx|wiki)\/[A-Za-z0-9_-]+/u.test(documentUrl || "")) {
    throw new Error("A valid Feishu cloud-document URL is required");
  }

  const highlights = issue.signals
    .slice(0, 3)
    .map((item, index) => `${index + 1}. **${item.title}**`)
    .join("\n");

  const elements = [];
  if (imageKey) {
    elements.push({
      tag: "img",
      img_key: imageKey,
      mode: "crop_center",
      compact_width: false,
      alt: {
        tag: "plain_text",
        content: issue.headline,
      },
    });
  }

  elements.push(
    {
      tag: "div",
      text: {
        tag: "lark_md",
        content: `**今日信号**\n${issue.headline}`,
      },
    },
    {
      tag: "div",
      fields: [
        countField(issue.signals.length, "科技与商业"),
        countField(issue.repositories.length, "开源精选"),
        countField(issue.products.length, "Product Hunt"),
      ],
    },
    { tag: "hr" },
    {
      tag: "div",
      text: {
        tag: "lark_md",
        content: `**三条先看**\n${highlights}`,
      },
    },
    {
      tag: "div",
      text: {
        tag: "lark_md",
        content: `**04 · 今日思考**\n${issue.topic}`,
      },
    },
    {
      tag: "action",
      actions: [
        {
          tag: "button",
          type: "primary",
          text: {
            tag: "plain_text",
            content: `查看网页版 · ${issue.dek.match(/\d+\s*分钟/u)?.[0]?.replace(/\s/gu, "") || "10分钟"}`,
          },
          url: issue.canonical_url,
        },
        {
          tag: "button",
          type: "default",
          text: {
            tag: "plain_text",
            content: "飞书文字版",
          },
          url: documentUrl,
        },
      ],
    },
  );

  return {
    config: {
      wide_screen_mode: true,
      enable_forward: true,
    },
    header: {
      template: "orange",
      title: {
        tag: "plain_text",
        content: `Claire 的科技早报 · ${dateLabel(issue.date)}`,
      },
    },
    elements,
  };
}
