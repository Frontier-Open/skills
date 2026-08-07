const ENTITY_MAP = {
  amp: "&",
  apos: "'",
  gt: ">",
  lt: "<",
  nbsp: " ",
  quot: '"',
};

export function decodeEntities(value = "") {
  return value
    .replace(/&#x([0-9a-f]+);/giu, (_, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#([0-9]+);/gu, (_, number) => String.fromCodePoint(Number.parseInt(number, 10)))
    .replace(/&([a-z]+);/giu, (entity, name) => ENTITY_MAP[name.toLowerCase()] ?? entity);
}

export function cleanText(value = "") {
  return decodeEntities(value)
    .replace(/<!\[CDATA\[|\]\]>/gu, "")
    .replace(/<[^>]+>/gu, " ")
    .replace(/\s+/gu, " ")
    .trim();
}

function tag(block, name) {
  const match = block.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)<\\/${name}>`, "iu"));
  return match ? cleanText(match[1]) : "";
}

export function parseTechmeme(xml) {
  return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/giu)].map(([, block]) => {
    const description = block.match(/<description[^>]*>([\s\S]*?)<\/description>/iu)?.[1] ?? "";
    const sourceUrls = [...description.matchAll(/href=["'](https?:\/\/[^"']+)["']/giu)]
      .map((match) => decodeEntities(match[1]))
      .filter((url) => !url.includes("techmeme.com"));
    return {
      title: tag(block, "title"),
      url: sourceUrls[0] || tag(block, "link"),
      aggregator_url: tag(block, "link"),
      published_at: tag(block, "pubDate"),
    };
  });
}

export function parseGitHubTrending(html) {
  const blocks = [...html.matchAll(/<article class="Box-row">([\s\S]*?)<\/article>/giu)];
  return blocks.flatMap(([, block]) => {
    const heading = block.match(/<h2[^>]*>([\s\S]*?)<\/h2>/iu)?.[1] ?? "";
    const repository = heading.match(/href="(\/[^"/]+\/[^"/]+)"[^>]*>([\s\S]*?)<\/a>/iu);
    if (!repository) return [];

    const name = cleanText(repository[2]).replace(/\s+/gu, "").replace(/\/$/u, "");
    const description = block.match(/<p class="col-9 color-fg-muted my-1 [^"]*">([\s\S]*?)<\/p>/iu)?.[1];
    const language = block.match(/itemprop="programmingLanguage"[^>]*>([\s\S]*?)<\/span>/iu)?.[1];
    const starsToday = block.match(/([0-9,]+) stars today/iu)?.[1];
    const starsTotal = block.match(/href="[^"]+\/stargazers"[^>]*>[\s\S]*?<\/svg>\s*([0-9,.kK]+)/iu)?.[1];

    return [{
      name,
      url: `https://github.com${repository[1]}`,
      description: cleanText(description),
      language: cleanText(language) || null,
      stars_today: starsToday || null,
      stars_total: starsTotal || null,
    }];
  });
}

export function parseProductHunt(xml) {
  return [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/giu)].map(([, block]) => {
    const url = block.match(/<link[^>]*rel="alternate"[^>]*href="([^"]+)"/iu)?.[1] ?? "";
    const content = block.match(/<content[^>]*>([\s\S]*?)<\/content>/iu)?.[1] ?? "";
    const firstParagraph = decodeEntities(content).match(/<p>([\s\S]*?)<\/p>/iu)?.[1] ?? "";
    return {
      name: tag(block, "title"),
      url: decodeEntities(url),
      description: cleanText(firstParagraph),
      published_at: tag(block, "published"),
      updated_at: tag(block, "updated"),
      author: tag(block, "name"),
    };
  });
}

export function parseDailyDev(html) {
  const section = html.match(/data-track-section="blog-highlights"([\s\S]*?)data-track-section="final-cta"/iu)?.[1] ?? html;
  const items = [];
  for (const match of section.matchAll(/<a href="(\/blog\/[^"]+)"[\s\S]*?<h3[^>]*>([\s\S]*?)<\/h3>[\s\S]*?<p[^>]*>([^<]*?(?:min read|\d{4}))<\/p>/giu)) {
    items.push({
      title: cleanText(match[2]),
      url: `https://daily.dev${decodeEntities(match[1])}`,
      published_label: cleanText(match[3]),
    });
  }
  return items;
}

export function parseHelloGitHub(payload) {
  const data = typeof payload === "string" ? JSON.parse(payload) : payload;
  if (!data?.success || !Array.isArray(data.data)) throw new Error("HelloGitHub returned an invalid payload");
  return data.data.map((item) => ({
    name: item.full_name,
    url: `https://github.com/${item.full_name}`,
    title: item.title,
    description: item.summary,
    language: item.primary_lang || null,
    clicks_total: Number.isFinite(item.clicks_total) ? item.clicks_total : null,
    updated_at: item.updated_at || null,
  }));
}

export function safeWarning(error) {
  const message = error instanceof Error ? error.message : String(error);
  return message.replace(/(token|key|secret|authorization)\s*[:=]\s*\S+/giu, "$1=[redacted]").slice(0, 240);
}
