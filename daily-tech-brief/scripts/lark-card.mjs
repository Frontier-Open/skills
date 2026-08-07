function dateLabel(date) {
  const [year, month, day] = date.split("-");
  return `${year} 年 ${month} 月 ${day} 日`;
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

export function buildLarkCard(issue, { imageKey } = {}) {
  if (!issue?.date || !issue?.headline || !issue?.canonical_url) {
    throw new Error("Issue requires date, headline, and canonical_url");
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
        countField(issue.repositories.length, "开源项目"),
        countField(issue.products.length, "热门新品"),
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
        content: `**今日延伸选题**\n${issue.topic}`,
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
            content: "阅读全文 · 约 10 分钟",
          },
          url: issue.canonical_url,
        },
      ],
    },
    {
      tag: "note",
      elements: [
        {
          tag: "plain_text",
          content: `Techmeme · daily.dev · GitHub Trending · HelloGitHub · Product Hunt｜${issue.generated_at}`,
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
