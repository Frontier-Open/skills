function escapeMarkdown(value = "") {
  return String(value)
    .replace(/\\/gu, "\\\\")
    .replace(/([`*_\[\]$~])/gu, "\\$1")
    .replace(/</gu, "\\<");
}

function dateLabel(date) {
  return date.replaceAll("-", ".");
}

export function buildMarkdown(issue) {
  const lines = [
    `# ${escapeMarkdown(issue.brand)} · ${dateLabel(issue.date)}`,
    "",
    escapeMarkdown(issue.dek),
    "",
    `> 今日信号：${escapeMarkdown(issue.headline)}`,
    "",
    "## 01 / SIGNAL · 科技与商业",
    "",
  ];

  issue.signals.forEach((item, index) => {
    lines.push(
      `### ${String(index + 1).padStart(2, "0")} · ${escapeMarkdown(item.title)}`,
      "",
      escapeMarkdown(item.summary),
      "",
      `**值得看：** ${escapeMarkdown(item.why)}`,
      "",
      `[${escapeMarkdown(item.source)}](${item.source_url})`,
      "",
    );
  });

  lines.push(
    "## 02 / BUILD · 开源项目精选",
    "",
    "GitHub Trending 与 HelloGitHub 合并筛选，按内容和工作流相关性排序。",
    "",
  );
  issue.repositories.forEach((item, index) => {
    lines.push(`${index + 1}. [${escapeMarkdown(item.name)}](${item.url}) — ${escapeMarkdown(item.summary)} **总 Star：** ${escapeMarkdown(item.stars_total)} ★`);
  });

  lines.push(
    "",
    "## 03 / SHIP · Product Hunt 今日精选",
    "",
    "从官方 Feed 候选中筛选，不按榜单照搬。",
    "",
  );
  issue.products.forEach((item) => {
    lines.push(`- [${escapeMarkdown(item.name)}](${item.url}) — ${escapeMarkdown(item.summary)}`);
  });

  lines.push(
    "",
    "## 04 / THINK · 今日思考",
    "",
    escapeMarkdown(issue.topic),
    "",
    "---",
    "",
    "数据说明：仓库总 Star 为发布时快照；Product Hunt 项目来自官方 Feed。",
    "",
  );

  return lines.join("\n");
}
