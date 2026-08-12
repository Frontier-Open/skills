import { assertArticle } from "./article.mjs";

const MODE_BUDGETS = {
  quick: { format: "analysis", minCharacters: 1400, maxCharacters: 2200, minMinutes: 5, maxMinutes: 8, minSections: 3, maxSections: 4, minSources: 3, minVisuals: 3, maxVisuals: 5, minFactChecks: 3 },
  deep: { format: "deep-dive", minCharacters: 3200, maxCharacters: 5000, minMinutes: 12, maxMinutes: 18, minSections: 4, maxSections: 6, minSources: 6, minVisuals: 5, maxVisuals: 8, minFactChecks: 6 },
};
const TITLE_TYPES = new Set(["factual", "judgment", "question"]);
const SECTION_ROLES = new Set(["context", "evidence", "mechanism", "counterargument", "implication", "watchlist"]);
const FACT_KINDS = new Set(["fact", "attributed-reporting", "interpretation", "recommendation"]);
const FACT_STATUSES = new Set(["pending", "verified", "qualified", "rejected"]);
const MEDIA_PURPOSES = new Set(["brand", "evidence", "explanation", "scene", "atmosphere"]);
const CHANNEL_STATES = new Set(["draft", "reviewed", "approved", "published", "failed"]);

function requireText(value, label) {
  if (!String(value || "").trim()) throw new Error(`Missing ${label}`);
}

function requireSourceIds(ids, sourceIds, label) {
  if (!Array.isArray(ids) || !ids.length) throw new Error(`${label} must contain source IDs`);
  if (new Set(ids).size !== ids.length) throw new Error(`${label} must contain unique source IDs`);
  for (const id of ids) {
    if (!sourceIds.has(id)) throw new Error(`${label} contains unknown source ID: ${id}`);
  }
}

function editorialParts(article) {
  return [
    ...article.intro,
    ...article.sections.flatMap((section) => [
      ...section.paragraphs,
      section.callout || "",
      ...(section.points || []),
    ]),
    ...article.conclusion.paragraphs,
  ];
}

export function editorialCharacterCount(article) {
  return editorialParts(article).join("").replace(/\s/gu, "").length;
}

function assertNormativeMedia(media, label) {
  requireText(media?.purpose, `${label}.purpose`);
  requireText(media?.rights, `${label}.rights`);
  if (!MEDIA_PURPOSES.has(media.purpose)) throw new Error(`${label}.purpose is invalid`);
  if (typeof media.generated !== "boolean") throw new Error(`${label}.generated must be boolean`);
}

function isStructuralExample(article) {
  return article.status === "draft" && article.warnings?.some((warning) => warning.startsWith("STRUCTURAL EXAMPLE ONLY:"));
}

export function assertNormativeArticle(article) {
  assertArticle(article);
  const budget = MODE_BUDGETS[article.mode];
  if (!budget) throw new Error("article.mode must be quick or deep");
  if (article.format !== budget.format) throw new Error(`article.format must be ${budget.format} for ${article.mode}`);

  for (const field of ["reader_payoff"]) requireText(article[field], `article.${field}`);
  if (!Number.isInteger(article.word_count)) throw new Error("article.word_count must be an integer");
  if (!Array.isArray(article.title_candidates) || article.title_candidates.length !== 3) {
    throw new Error("article.title_candidates must contain exactly three candidates");
  }
  const titleTypes = new Set();
  for (const [index, candidate] of article.title_candidates.entries()) {
    if (!TITLE_TYPES.has(candidate?.type)) throw new Error(`article.title_candidates[${index}].type is invalid`);
    requireText(candidate.text, `article.title_candidates[${index}].text`);
    requireText(candidate.claim_check, `article.title_candidates[${index}].claim_check`);
    titleTypes.add(candidate.type);
  }
  if (titleTypes.size !== TITLE_TYPES.size || !article.title_candidates.some((candidate) => candidate.text === article.title)) {
    throw new Error("article.title_candidates must include one of each type and the selected title");
  }
  for (const field of ["event", "tension", "judgment"]) requireText(article.hook?.[field], `article.hook.${field}`);

  const sourceIds = new Set(article.sources.map((source) => source.id));
  const sourceById = new Map(article.sources.map((source) => [source.id, source]));
  const sourceUrls = new Set();
  for (const [index, source] of article.sources.entries()) {
    requireText(source.chain_id, `article.sources[${index}].chain_id`);
    if (sourceUrls.has(source.url)) throw new Error(`Duplicate source URL: ${source.url}`);
    sourceUrls.add(source.url);
  }
  if (new Set(article.sources.map((source) => source.chain_id)).size < budget.minSources) {
    throw new Error(`${article.mode} requires ${budget.minSources} independent source chains`);
  }
  requireSourceIds(article.intro_source_ids, sourceIds, "article.intro_source_ids");
  requireSourceIds(article.conclusion?.source_ids, sourceIds, "article.conclusion.source_ids");

  for (const [index, section] of article.sections.entries()) {
    if (!SECTION_ROLES.has(section.role)) throw new Error(`article.sections[${index}].role is invalid`);
    if (section.image) assertNormativeMedia(section.image, `article.sections[${index}].image`);
  }
  assertNormativeMedia(article.media.cover, "article.media.cover");
  assertNormativeMedia(article.media.og, "article.media.og");
  const visuals = 2 + article.sections.filter((section) => section.image).length;
  if (visuals < budget.minVisuals || visuals > budget.maxVisuals) {
    throw new Error(`${article.mode} requires ${budget.minVisuals}-${budget.maxVisuals} production visuals`);
  }
  if (article.sections.filter((section) => section.image?.purpose === "atmosphere").length > 1) {
    throw new Error("Only one inline atmosphere image is allowed");
  }

  if (!Array.isArray(article.watchlist) || article.watchlist.length < 2 || article.watchlist.length > 3) {
    throw new Error("article.watchlist must contain two or three indicators");
  }
  for (const [index, item] of article.watchlist.entries()) {
    requireText(item.indicator, `article.watchlist[${index}].indicator`);
    requireText(item.why_it_matters, `article.watchlist[${index}].why_it_matters`);
    requireSourceIds(item.source_ids, sourceIds, `article.watchlist[${index}].source_ids`);
  }

  if (!Array.isArray(article.fact_check) || article.fact_check.length < budget.minFactChecks) {
    throw new Error(`${article.mode} requires at least ${budget.minFactChecks} fact-check entries`);
  }
  for (const [index, item] of article.fact_check.entries()) {
    requireText(item.claim, `article.fact_check[${index}].claim`);
    requireText(item.note, `article.fact_check[${index}].note`);
    if (!FACT_KINDS.has(item.kind)) throw new Error(`article.fact_check[${index}].kind is invalid`);
    if (!FACT_STATUSES.has(item.status)) throw new Error(`article.fact_check[${index}].status is invalid`);
    requireSourceIds(item.source_ids, sourceIds, `article.fact_check[${index}].source_ids`);
    const chainCount = new Set(item.source_ids.map((id) => sourceById.get(id).chain_id)).size;
    if (item.independent_source_count !== chainCount) {
      throw new Error(`article.fact_check[${index}].independent_source_count does not match source chains`);
    }
    if (item.high_risk && chainCount < 2) throw new Error(`article.fact_check[${index}] high-risk claim needs two independent chains`);
  }

  if (article.counterargument && typeof article.counterargument === "object") {
    for (const field of ["claim", "evidence", "boundary", "response"]) {
      requireText(article.counterargument?.[field], `article.counterargument.${field}`);
    }
    requireSourceIds(article.counterargument?.source_ids, sourceIds, "article.counterargument.source_ids");
  }
  if (article.mode === "deep") {
    if (!article.counterargument || typeof article.counterargument !== "object") {
      throw new Error("deep articles require a structured counterargument");
    }
    if (!article.sections.some((section) => section.role === "counterargument")) {
      throw new Error("deep articles require a rendered counterargument section");
    }
  } else if (article.counterargument !== null && typeof article.counterargument !== "object") {
    throw new Error("quick counterargument must be an object or null");
  }

  if (article.sections.length < budget.minSections || article.sections.length > budget.maxSections) {
    throw new Error(`${article.mode} requires ${budget.minSections}-${budget.maxSections} sections`);
  }
  if (article.sources.length < budget.minSources) throw new Error(`${article.mode} requires at least ${budget.minSources} sources`);
  if (article.reading_minutes < budget.minMinutes || article.reading_minutes > budget.maxMinutes) {
    throw new Error(`${article.mode} requires ${budget.minMinutes}-${budget.maxMinutes} reading minutes`);
  }

  for (const channel of ["web", "wechat", "feishu"]) {
    if (!CHANNEL_STATES.has(article.distribution?.[channel]?.status)) throw new Error(`article.distribution.${channel}.status is invalid`);
  }
  if (article.distribution.web.status === "published" && article.distribution.web.url !== article.canonical_url) {
    throw new Error("Published web distribution URL must match article.canonical_url");
  }
  if (article.status === "published" && article.distribution.web.status !== "published") {
    throw new Error("Published articles require published web distribution state");
  }

  const structuralExample = isStructuralExample(article);
  const visibleText = editorialParts(article).join("");
  if (!structuralExample) {
    const computedCount = editorialCharacterCount(article);
    if (article.word_count !== computedCount) throw new Error(`article.word_count must equal computed count ${computedCount}`);
    if (computedCount < budget.minCharacters || computedCount > budget.maxCharacters) {
      throw new Error(`${article.mode} requires ${budget.minCharacters}-${budget.maxCharacters} visible non-whitespace characters`);
    }
    const introText = article.intro.join("");
    for (const field of ["event", "tension", "judgment"]) {
      if (!introText.includes(article.hook[field])) throw new Error(`article.hook.${field} must appear verbatim in the visible intro`);
    }
    if (!visibleText.includes(article.reader_payoff)) throw new Error("article.reader_payoff must appear in the rendered prose");
    for (const item of article.watchlist) {
      if (!visibleText.includes(item.indicator)) throw new Error(`Watchlist indicator is missing from rendered prose: ${item.indicator}`);
    }
    if (article.mode === "deep") {
      const counterText = article.sections.filter((section) => section.role === "counterargument")
        .flatMap((section) => [...section.paragraphs, section.callout || "", ...(section.points || [])]).join("");
      for (const field of ["claim", "evidence", "boundary", "response"]) {
        if (!counterText.includes(article.counterargument[field])) throw new Error(`article.counterargument.${field} must appear in the rendered counterargument section`);
      }
    }
  }

  if (article.status !== "draft") {
    if (article.warnings.length) throw new Error("Reviewed or published articles cannot contain unresolved warnings");
    if (article.fact_check.some((item) => !["verified", "qualified"].includes(item.status))) {
      throw new Error("Reviewed or published articles cannot contain unresolved fact checks");
    }
  }
  return article;
}
