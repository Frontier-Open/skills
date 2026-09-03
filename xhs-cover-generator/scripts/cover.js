// Shared cover renderer: config -> standalone HTML for one 1080x1440 Xiaohongshu cover.
// Templates are data specs (geometry + structure + decoration), so new layouts are declarative and
// custom ones can be loaded from JSON. The first three port the canvas generator at https://xhs.haha.ai.

export const CANVAS = { width: 1080, height: 1440 };

export const THEMES = {
  braun: {
    name: '博朗经典',
    desc: '温暖现代，高对比度',
    style: '科技、设计、商务类内容',
    colors: ['#F5F1EB', '#E8D5B7', '#FF6B35', '#4A90E2'],
  },
  melon: {
    name: '青提甜瓜',
    desc: '清新自然，治愈系',
    style: '生活、美食、健康类内容',
    colors: ['#FBFFE4', '#B3D8A8', '#A3D1C6', '#3D8D7A'],
  },
  sunset: {
    name: '日落黄昏',
    desc: '温暖浪漫，高级感',
    style: '情感、艺术、旅行类内容',
    colors: ['#FFF8E1', '#FFE0B2', '#FF8A65', '#D84315'],
  },
  ocean: {
    name: '深海蓝调',
    desc: '沉稳专业，商务感',
    style: '教育、金融、专业类内容',
    colors: ['#F3F8FF', '#B3D9FF', '#4A90E2', '#1565C0'],
  },
};

export const DEFAULT_THEME = 'melon';
export const DEFAULT_TEMPLATE = 'thinking';

export const EMOJI_CHOICES = ['🤔', '👍', '😣', '💡', '🎯', '✨', '🔥', '💪'];

// Copy banks behind the site's "一键生成" button, kept as inspiration seeds.
export const SEEDS = {
  mainText: [
    '一个人做内容\n先定一个主张\n再开始动手',
    '一篇长文\n拆成7张图\n真的没那么难',
    '把选题讲清楚\n比把画面做满\n更重要',
    '没有灵感\n先做一件\n能发布的事',
    '内容做不完\n通常不是\n时间不够',
  ],
  highlightText: ['主张', '7张图', '讲清楚', '能发布', '时间'],
  tag: ['可执行版', '创作者友好', '亲测有效', '轻量工作流', '收藏备用'],
  emoji: ['🧭', '✨', '💡', '🎙️', '📝', '📌', '👍', '🎯'],
};

const STYLE = {
  ink: '#1f2937',
  inkOnDark: '#ffffff',
  highlight: '#fbbf24',
  sub: '#6b7280',
  card: '#ffffff',
  cardBorder: '#e5e7eb',
  paper: '#FFFDF5',
  rule: '#e5e7eb',
  tagStrong: '#3b82f6',
  tagSoft: '#93c5fd',
};

const FONT_STACK =
  '"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", system-ui, sans-serif';

// structure: plain | card | frame | paper | band
// decoration: none | wave | quote | grid | rule
// highlight: fill | outline | underline | none
// markers: none | number | dot
// tag: none | top-right | top-left | bottom-center
const BUILTIN_SPECS = [
  {
    key: 'thinking',
    name: '思考型',
    desc: '简洁专业',
    useCase: '知识分享、教程、方法论',
    slot: 1,
    structure: 'plain',
    highlight: 'fill',
    tag: 'top-right',
    text: { x: 100, y: 200, w: 880, h: 900, size: 96, align: 'left', lineHeight: 1.28, min: 44 },
    sub: { x: 100, y: 1180, w: 880, size: 42, align: 'left' },
    emoji: { x: 80, y: 80, size: 100, base: 150 },
    sample: { mainText: '一个人做内容\n先定一个主张\n再开始动手', highlightText: '一个主张', emoji: '🧭' },
  },
  {
    key: 'dialog',
    name: '对话框型',
    desc: '互动友好',
    useCase: '问答、避坑、经验交流',
    slot: 2,
    structure: 'card',
    highlight: 'fill',
    tag: 'top-right',
    surface: { x: 100, y: 200, w: 880, h: 520, radius: 28, border: STYLE.cardBorder },
    text: { x: 164, y: 260, w: 752, h: 320, size: 72, align: 'center', lineHeight: 1.32, min: 40 },
    sub: { x: 164, y: 604, w: 752, size: 40, align: 'center', rule: true },
    emoji: { x: 50, y: 85, size: 120, base: 200 },
    sample: {
      mainText: '写内容总卡住？\n先别急着改\n把主张写出来',
      highlightText: '主张',
      subText: '给拖延创作者的一个办法',
      emoji: '🗒️',
    },
  },
  {
    key: 'emotion',
    name: '情绪型',
    desc: '情感共鸣',
    useCase: '情感表达、生活感悟、吐槽',
    slot: 3,
    structure: 'plain',
    decoration: 'wave',
    highlight: 'fill',
    tag: 'top-right',
    text: { x: 100, y: 300, w: 880, h: 620, size: 84, align: 'center', lineHeight: 1.32, min: 40 },
    emoji: { x: 50, y: 75, size: 100, base: 150 },
    sample: { mainText: '不是没有灵感\n是每天都在\n重新开始', tag: '创作者日常', emoji: '😮‍💨' },
  },
  {
    key: 'quote',
    name: '引用型',
    desc: '安静有质感',
    useCase: '金句、书摘、播客片段',
    slot: 2,
    structure: 'card',
    decoration: 'quote',
    highlight: 'underline',
    tag: 'none',
    surface: { x: 90, y: 230, w: 900, h: 880, radius: 32 },
    text: { x: 190, y: 430, w: 700, h: 440, size: 76, align: 'center', lineHeight: 1.52, min: 40 },
    sub: { x: 190, y: 950, w: 700, size: 38, align: 'center' },
    emoji: { x: 50, y: 16, size: 90, base: 150 },
    sample: {
      mainText: '真正的效率\n不是做更多\n而是少做重复的事',
      subText: '—— 写给每个忙碌的创作者',
      highlightText: '少做',
      emoji: '💡',
    },
  },
  {
    key: 'note',
    name: '便签型',
    desc: '手账感、亲切',
    useCase: '清单、备忘、日常记录',
    slot: 1,
    structure: 'paper',
    decoration: 'rule',
    highlight: 'underline',
    tag: 'top-right',
    surface: { x: 90, y: 190, w: 900, h: 1000, radius: 18, color: STYLE.paper },
    text: { x: 170, y: 330, w: 740, h: 600, size: 78, align: 'left', lineHeight: 1.62, min: 40 },
    sub: { x: 170, y: 1020, w: 740, size: 36, align: 'left' },
    emoji: { x: 82, y: 84, size: 85, base: 130 },
    sample: {
      mainText: '今天只做三件事\n写一个标题\n发一张图',
      subText: '给拖延症创作者的轻量计划',
      highlightText: '三件事',
      emoji: '📌',
    },
  },
  {
    key: 'list',
    name: '清单型',
    desc: '信息密度高',
    useCase: '几个方法、几个工具、几个坑',
    slot: 1,
    structure: 'plain',
    highlight: 'fill',
    markers: 'number',
    tag: 'top-right',
    text: { x: 120, y: 400, w: 840, h: 700, size: 72, align: 'left', lineHeight: 1.5, min: 38 },
    sub: { x: 120, y: 220, w: 840, size: 60, align: 'left', strong: true },
    emoji: { x: 86, y: 88, size: 80, base: 130 },
    sample: {
      mainText: '先定一个主张\n再做三张图\n最后加行动',
      subText: '内容发布前的三步',
      highlightText: '主张',
      tag: '可执行版',
      emoji: '✅',
    },
  },
];

const registry = new Map();

function specDefaults(spec) {
  return {
    structure: 'plain',
    decoration: 'none',
    highlight: 'fill',
    markers: 'none',
    tag: 'top-right',
    slot: 1,
    sample: {},
    ...spec,
    text: { x: 100, y: 300, w: 880, h: 700, size: 88, align: 'center', lineHeight: 1.32, min: 40, ...(spec.text || {}) },
    emoji: { x: 50, y: 80, size: 100, base: 150, ...(spec.emoji || {}) },
    sub: spec.sub ? { size: 40, align: 'center', ...spec.sub } : null,
    surface: spec.surface || null,
  };
}

function register(spec) {
  const full = specDefaults(spec);
  registry.set(full.key, full);
  return full;
}

for (const spec of BUILTIN_SPECS) register(spec);

/** Add or override templates from plain JSON. `extends` inherits a built-in spec. */
export function registerTemplates(input) {
  const list = Array.isArray(input) ? input : [input];
  const added = [];
  for (const raw of list) {
    const base = raw.extends ? registry.get(resolveTemplateKey(raw.extends)) : null;
    const rawSpec = Object.fromEntries(Object.entries(raw).filter(([key]) => key !== 'id'));
    const merged = {
      ...(base || {}),
      ...rawSpec,
      key: raw.key || (base ? uniqueKey(base.key + '-custom') : uniqueKey('custom-template')),
      name: raw.name || raw.key || (base ? base.name + '·自定义' : '自定义'),
      text: { ...(base?.text || {}), ...(rawSpec.text || {}) },
      emoji: { ...(base?.emoji || {}), ...(rawSpec.emoji || {}) },
      sub: rawSpec.sub === null ? null : { ...(base?.sub || {}), ...(rawSpec.sub || {}) },
      surface: rawSpec.surface === null ? null : rawSpec.surface || base?.surface || null,
      sample: { ...(base?.sample || {}), ...(rawSpec.sample || {}) },
    };
    if (merged.sub && !Object.keys(merged.sub).length) merged.sub = null;
    added.push(register(merged));
  }
  return added;
}

function uniqueKey(prefix) {
  let key = prefix;
  let suffix = 2;
  while (registry.has(key)) key = prefix + '-' + suffix++;
  return key;
}

function specs() {
  return [...registry.values()];
}

/** key -> spec, kept as a live object for the editor and CLI. */
export const TEMPLATES = new Proxy(
  {},
  {
    get: (_, prop) => (prop === Symbol.iterator ? undefined : registry.get(String(prop))),
    has: (_, prop) => typeof prop === 'string' && registry.has(prop),
    ownKeys: () => specs().map((s) => s.key),
    getOwnPropertyDescriptor: (_, prop) => ({
      value: registry.get(prop),
      enumerable: true,
      configurable: true,
    }),
  },
);

export function listTemplates() {
  return specs();
}

export function resolveTemplateKey(value) {
  if (value == null || value === '') return DEFAULT_TEMPLATE;
  const raw = String(value).trim();
  const byKey = specs().find((s) => s.key === raw || s.name === raw);
  if (byKey) return byKey.key;
  throw new Error('Unknown template "' + raw + '". Use a template key from --list.');
}

export function resolveThemeKey(value) {
  if (!value) return DEFAULT_THEME;
  const raw = String(value).trim();
  if (THEMES[raw]) return raw;
  return Object.keys(THEMES).find((k) => THEMES[k].name === raw) || DEFAULT_THEME;
}

/** Each template reads a fixed slot of the palette, so themes deepen with the layout. */
export function themeColor(themeKey, templateKey) {
  const theme = THEMES[resolveThemeKey(themeKey)];
  const spec = registry.get(resolveTemplateKey(templateKey));
  const index = Math.min(Math.max((spec?.slot ?? 1) - 1, 0), theme.colors.length - 1);
  return theme.colors[index];
}

export function defaultConfig(templateKey = DEFAULT_TEMPLATE, themeKey = DEFAULT_THEME) {
  const spec = registry.get(resolveTemplateKey(templateKey));
  const theme = resolveThemeKey(themeKey);
  return {
    template: spec.key,
    theme,
    mainText: '',
    subText: '',
    highlightText: '',
    tag: '',
    emoji: spec.emoji.emojiChar || '✨',
    showEmoji: true,
    emojiX: spec.emoji.x,
    emojiY: spec.emoji.y,
    emojiSize: spec.emoji.size,
    ...spec.sample,
    backgroundColor: themeColor(theme, spec.key),
  };
}

export function normalizeConfig(input = {}) {
  const template = resolveTemplateKey(input.template ?? input.templateKey);
  const spec = registry.get(template);
  const theme = resolveThemeKey(input.theme);
  const height = Number(input.height) || CANVAS.height;
  const width = Number(input.width) || Math.round((height * CANVAS.width) / CANVAS.height);
  // With no copy at all the caller is asking to see the template, so the whole sample is used.
  // Once any copy is supplied, empty fields stay empty instead of inheriting stray sample text.
  const sample = input.mainText == null && input.main == null ? spec.sample : {};
  return {
    template,
    theme,
    width,
    height,
    mainText: String(input.mainText ?? input.main ?? spec.sample.mainText ?? ''),
    subText: String(input.subText ?? input.sub ?? sample.subText ?? ''),
    highlightText: String(input.highlightText ?? input.highlight ?? sample.highlightText ?? ''),
    tag: String(input.tag ?? sample.tag ?? ''),
    backgroundColor: input.backgroundColor || input.background || themeColor(theme, template),
    accentColor: input.accentColor || THEMES[theme].colors[2],
    textColor: input.textColor || '',
    emoji: input.emoji ?? spec.sample.emoji ?? '✨',
    showEmoji: input.showEmoji === undefined ? true : Boolean(input.showEmoji),
    emojiX: clamp(Number(input.emojiX ?? spec.emoji.x), 2, 98),
    emojiY: clamp(Number(input.emojiY ?? spec.emoji.y), 2, 98),
    emojiSize: clamp(Number(input.emojiSize ?? spec.emoji.size), 30, 260),
  };
}

function clamp(value, min, max) {
  if (!Number.isFinite(value)) return min;
  return Math.min(Math.max(value, min), max);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function relativeLuminance(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex).trim());
  if (!m) return 1;
  const int = parseInt(m[1], 16);
  const channels = [(int >> 16) & 255, (int >> 8) & 255, int & 255].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

// Deviation from the original: on deep palette slots the fixed dark ink became unreadable,
// so text sitting on a colored surface picks whichever of ink/white has more contrast.
function readableInk(background, override) {
  if (override) return override;
  const bg = relativeLuminance(background);
  const contrast = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  return contrast(bg, 1) > contrast(bg, relativeLuminance(STYLE.ink)) ? STYLE.inkOnDark : STYLE.ink;
}

function markHTML(word, style) {
  return `<span class="mark mark-${style}">${escapeHtml(word)}</span>`;
}

function renderLines(cfg, spec) {
  const lines = String(cfg.mainText).split('\n');
  let index = 0;
  return lines
    .map((raw) => {
      const line = raw.replace(/\s+$/, '');
      if (!line) return '<div class="line line-blank"></div>';
      index += 1;
      const marker =
        spec.markers === 'number'
          ? `<i class="marker">${index}</i>`
          : spec.markers === 'dot'
            ? '<i class="marker marker-dot"></i>'
            : '';
      const at = cfg.highlightText ? line.indexOf(cfg.highlightText) : -1;
      const body =
        at < 0
          ? escapeHtml(line)
          : escapeHtml(line.slice(0, at)) +
            markHTML(cfg.highlightText, spec.highlight) +
            escapeHtml(line.slice(at + cfg.highlightText.length));
      return `<div class="line">${marker}<span class="line-text">${body}</span></div>`;
    })
    .join('\n      ');
}

function surfaceHTML(spec, cfg) {
  if (!spec.surface) return '';
  const s = spec.surface;
  const rect = `left:${s.x}px;top:${s.y}px;width:${s.w}px;height:${s.h}px;border-radius:${s.radius || 0}px;`;
  switch (spec.structure) {
    case 'card':
      return `<div class="surface card" style="${rect}background:${s.color || STYLE.card};${s.border ? `border:2px solid ${s.border};` : ''}"></div>`;
    case 'frame':
      return `<div class="surface card" style="${rect}background:${s.color || STYLE.card};">
        <div class="frame-inner" style="border-color:${cfg.backgroundColor}"></div>
      </div>`;
    case 'paper':
      return `<div class="surface paper" style="${rect}background:${s.color || STYLE.paper};">
        <span class="tape" style="background:${cfg.accentColor}"></span>
      </div>`;
    case 'band':
      return `<div class="surface band" style="${rect}background:${cfg.backgroundColor};"></div>`;
    default:
      return '';
  }
}

// Waves and grids sit under the surface; quote marks and rules must sit on top of it.
const BACKGROUND_DECORATIONS = new Set(['wave', 'grid']);

function decorationHTML(spec, layer) {
  if (BACKGROUND_DECORATIONS.has(spec.decoration) !== (layer === 'back')) return '';
  switch (spec.decoration) {
    case 'wave':
      return `<svg class="wave" viewBox="0 0 100 133" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 65 Q25 60 50 65 T100 65 L100 133 L0 133 Z" fill="#ffffff" opacity="0.3" />
      </svg>`;
    case 'quote':
      return '<div class="quote-mark quote-open">&ldquo;</div><div class="quote-mark quote-close">&rdquo;</div>';
    case 'rule':
      return '<div class="ruled"></div>';
    case 'grid':
      return '<div class="grid-bg"></div>';
    default:
      return '';
  }
}

function tagHTML(cfg, spec) {
  if (!cfg.tag || spec.tag === 'none') return '';
  const soft = spec.tag === 'bottom-center';
  return `<div class="tag tag-${spec.tag}" style="background:${soft ? STYLE.tagSoft : STYLE.tagStrong};color:${soft ? STYLE.ink : '#fff'}">${escapeHtml(cfg.tag)}</div>`;
}

function subHTML(cfg, spec, inkOnBackground) {
  if (!cfg.subText || !spec.sub) return '';
  const s = spec.sub;
  const onColor = s.onSurface || spec.structure === 'plain';
  const color = s.onSurface ? readableInk(cfg.backgroundColor) : onColor ? inkOnBackground : STYLE.sub;
  const style = [
    `left:${s.x}px`,
    `top:${s.y}px`,
    `width:${s.w}px`,
    `font-size:${s.size}px`,
    `text-align:${s.align}`,
    `color:${color}`,
    s.strong ? 'font-weight:700' : '',
    onColor && !s.onSurface ? 'opacity:.75' : '',
  ]
    .filter(Boolean)
    .join(';');
  return `<div class="sub-text${s.rule ? ' sub-rule' : ''}" style="${style}">${escapeHtml(cfg.subText)}</div>`;
}

function emojiHTML(cfg, spec) {
  if (!cfg.showEmoji || !cfg.emoji) return '';
  const size = (spec.emoji.base * cfg.emojiSize) / 100;
  return `<div class="emoji" style="left:${cfg.emojiX}%;top:${cfg.emojiY}%;font-size:${size}px">${escapeHtml(cfg.emoji)}</div>`;
}

export function buildCoverHTML(input = {}) {
  const cfg = normalizeConfig(input);
  const spec = registry.get(cfg.template);
  const scale = cfg.height / CANVAS.height;
  const t = spec.text;
  const onSurface = ['card', 'frame', 'paper'].includes(spec.structure) || spec.structure === 'band';
  const inkOnBackground = readableInk(cfg.backgroundColor, cfg.textColor);
  const textInk = onSurface ? cfg.textColor || STYLE.ink : inkOnBackground;
  const pageBackground = spec.structure === 'band' ? '#ffffff' : cfg.backgroundColor;

  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(spec.name)} · 小红书封面</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { background: #ffffff; }
  body { width: ${cfg.width}px; height: ${cfg.height}px; overflow: hidden; }
  .cover {
    position: relative;
    width: ${CANVAS.width}px;
    height: ${CANVAS.height}px;
    transform: scale(${scale});
    transform-origin: top left;
    background: ${pageBackground};
    font-family: ${FONT_STACK};
    color: ${STYLE.ink};
    overflow: hidden;
  }
  .surface { position: absolute; }
  .frame-inner { position: absolute; inset: 20px; border: 8px solid; border-radius: 12px; }
  .paper .tape {
    position: absolute; top: -24px; left: 50%; transform: translateX(-50%) rotate(-2.5deg);
    width: 240px; height: 52px; border-radius: 3px; opacity: .72;
  }
  .wave { position: absolute; inset: 0; width: 100%; height: 100%; }
  .ruled {
    /* --rule-top and --rule-step are re-set from the real line boxes once the copy has been fitted. */
    --rule-step: ${Math.round(t.size * t.lineHeight)}px;
    --rule-top: ${spec.surface ? spec.surface.y + 120 : 300}px;
    position: absolute; left: ${spec.surface ? spec.surface.x + 50 : 150}px; top: var(--rule-top);
    width: ${spec.surface ? spec.surface.w - 100 : 780}px; height: ${spec.surface ? spec.surface.h - 200 : 700}px;
    background: repeating-linear-gradient(to bottom, transparent 0 calc(var(--rule-step) - 2px), ${STYLE.rule} calc(var(--rule-step) - 2px) var(--rule-step));
  }
  .grid-bg {
    position: absolute; inset: 0;
    background-image: linear-gradient(#00000010 1px, transparent 1px), linear-gradient(90deg, #00000010 1px, transparent 1px);
    background-size: 90px 90px;
  }
  .quote-mark { position: absolute; font-size: 220px; line-height: 1; color: ${STYLE.highlight}; font-family: Georgia, serif; }
  .quote-open { left: 150px; top: 290px; }
  .quote-close { right: 150px; bottom: 210px; }

  .text-box {
    position: absolute;
    display: flex;
    flex-direction: column;
    left: ${t.x}px; top: ${t.y}px; width: ${t.w}px; height: ${t.h}px;
    font-size: ${t.size}px;
    line-height: ${t.lineHeight};
    text-align: ${t.align};
    color: ${textInk};
    align-items: ${t.align === 'left' ? 'flex-start' : t.align === 'right' ? 'flex-end' : 'center'};
    justify-content: ${spec.structure === 'plain' && t.align === 'left' ? 'flex-start' : 'center'};
  }
  .line { font-weight: 700; white-space: nowrap; display: flex; align-items: baseline; gap: .3em; }
  .line-blank { height: 0.6em; }
  .marker {
    font-style: normal; font-size: .52em; font-weight: 700;
    color: ${cfg.backgroundColor === STYLE.card ? STYLE.tagStrong : STYLE.ink};
    opacity: .55; min-width: 1.2em;
  }
  .marker-dot::before { content: '•'; }
  .mark { padding: 0 12px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
  .mark-fill { background: ${STYLE.highlight}; color: ${STYLE.ink}; }
  .mark-outline { border: 5px solid ${STYLE.highlight}; }
  .mark-underline { padding: 0; box-shadow: inset 0 -.18em 0 ${STYLE.highlight}; }
  .mark-none { padding: 0; }

  .sub-text { position: absolute; }
  .sub-rule { padding-top: 28px; border-top: 2px solid ${STYLE.cardBorder}; }
  .emoji {
    position: absolute; transform: translate(-50%, -50%); line-height: 1;
    font-family: "Apple Color Emoji", "Noto Color Emoji", "Segoe UI Emoji", sans-serif;
  }
  .tag {
    position: absolute; display: flex; align-items: center; justify-content: center;
    height: 68px; min-width: 200px; padding: 0 28px; border-radius: 10px;
    font-size: 32px; font-weight: 700;
  }
  .tag-top-right { top: 60px; right: 60px; }
  .tag-top-left { top: 60px; left: 60px; }
  .tag-bottom-center { left: 50%; bottom: 72px; transform: translateX(-50%); }
${spec.css ? `  ${spec.css}\n` : ''}</style>
</head>
<body>
  <div class="cover k-${spec.key}">
      ${decorationHTML(spec, 'back')}
      ${surfaceHTML(spec, cfg)}
      ${decorationHTML(spec, 'front')}
      ${tagHTML(cfg, spec)}
      <div class="text-box fit" data-min="${t.min}">
        ${renderLines(cfg, spec)}
      </div>
      ${subHTML(cfg, spec, inkOnBackground)}
      ${emojiHTML(cfg, spec)}
  </div>
  <script>
    // Shrink oversized copy instead of letting it spill out of the frame.
    // Measured from the line boxes: CJK glyph metrics overflow the line-height slightly,
    // so scrollHeight alone would report a permanent overflow.
    for (const box of document.querySelectorAll('.fit')) {
      const min = Number(box.dataset.min || 32);
      const lines = Array.from(box.children);
      if (!lines.length) continue;
      const fits = () => {
        const maxWidth = box.clientWidth;
        for (const line of lines) {
          if (line.scrollWidth > maxWidth + 1) return false;
        }
        const top = lines[0].getBoundingClientRect().top;
        const bottom = lines[lines.length - 1].getBoundingClientRect().bottom;
        return bottom - top <= box.clientHeight + 2;
      };
      let size = parseFloat(getComputedStyle(box).fontSize);
      while (size > min && !fits()) {
        size -= 2;
        box.style.fontSize = size + 'px';
      }
    }
    // Ruled paper only reads as paper when the rules land under the actual text lines,
    // which is only known after the fit pass above may have shrunk the copy.
    const ruled = document.querySelector('.ruled');
    const fitted = document.querySelector('.fit');
    if (ruled && fitted && fitted.children.length) {
      const lines = Array.from(fitted.children);
      const step = lines.length > 1 ? lines[1].offsetTop - lines[0].offsetTop : lines[0].offsetHeight;
      if (step > 0) {
        ruled.style.setProperty('--rule-step', step + 'px');
        ruled.style.setProperty('--rule-top', fitted.offsetTop + lines[0].offsetTop + 'px');
      }
    }
    document.documentElement.dataset.ready = '1';
  <\/script>
</body>
</html>
`;
}

export function randomSeed(templateKey = DEFAULT_TEMPLATE, themeKey = DEFAULT_THEME) {
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const spec = registry.get(resolveTemplateKey(templateKey));
  return {
    template: spec.key,
    theme: resolveThemeKey(themeKey),
    mainText: pick(SEEDS.mainText),
    highlightText: pick(SEEDS.highlightText),
    tag: spec.tag === 'none' ? '' : pick(SEEDS.tag),
    emoji: pick(SEEDS.emoji),
    backgroundColor: themeColor(themeKey, spec.key),
  };
}
