function normalizeText(value = "") {
  return String(value)
    .normalize("NFKC")
    .toLocaleLowerCase("en-US")
    .replace(/[\p{P}\p{S}\s]+/gu, "");
}

function normalizeUrl(value = "") {
  try {
    const url = new URL(value);
    url.hash = "";
    url.search = "";
    url.hostname = url.hostname.toLowerCase();
    url.pathname = url.pathname.replace(/\/+$/u, "").toLowerCase();
    return url.toString();
  } catch {
    return "";
  }
}

export function collectIssueItems(issue) {
  const groups = [
    ["signal", issue.signals || [], "title", "source_url"],
    ["repository", issue.repositories || [], "name", "url"],
    ["product", issue.products || [], "name", "url"],
  ];
  return groups.flatMap(([kind, items, labelField, urlField]) => items.map((item, index) => ({
    kind,
    index,
    label: item[labelField] || "",
    dedupeKey: String(item.dedupe_key || "").trim().toLocaleLowerCase("en-US"),
    normalizedLabel: normalizeText(item[labelField]),
    normalizedUrl: normalizeUrl(item[urlField]),
  })));
}

export function findIssueDuplicates(currentIssue, historicalIssues = []) {
  const errors = [];
  const currentItems = collectIssueItems(currentIssue);
  for (const item of currentItems) {
    if (!item.dedupeKey) errors.push(`${item.kind}[${item.index}] is missing dedupe_key`);
  }

  const seen = { dedupeKey: new Map(), normalizedLabel: new Map(), normalizedUrl: new Map() };
  for (const item of currentItems) {
    for (const field of Object.keys(seen)) {
      const value = item[field];
      if (!value) continue;
      if (seen[field].has(value)) errors.push(`Current issue repeats ${field}: ${item.label}`);
      else seen[field].set(value, item);
    }
  }

  const priorItems = historicalIssues
    .filter((issue) => issue.date !== currentIssue.date)
    .flatMap((issue) => collectIssueItems(issue).map((item) => ({ ...item, date: issue.date || "unknown-date" })));
  const priorIndexes = Object.fromEntries(Object.keys(seen).map((field) => [
    field,
    new Map(priorItems.filter((item) => item[field]).map((item) => [item[field], item])),
  ]));

  for (const item of currentItems) {
    for (const field of Object.keys(priorIndexes)) {
      const prior = priorIndexes[field].get(item[field]);
      if (item[field] && prior) errors.push(`${item.label} repeats ${prior.date} by ${field}`);
    }
  }
  return [...new Set(errors)];
}
