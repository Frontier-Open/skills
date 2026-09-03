// Multi-page Xiaohongshu carousel ("图文 deck") renderer.
//
// One JSON document describes a whole deck: a palette, an author bar, and N pages.
// Every page is a list of typed blocks, so a 7-page deck and an 18-page deck use
// the same vocabulary. Design units are the 810x1080 grid; output is scaled up.

export const DECK_CANVAS = { width: 810, height: 1080 };

const FONT_STACK =
  '"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", system-ui, sans-serif';
const MONO_STACK = '"SF Mono", Menlo, Consolas, "Noto Sans Mono", monospace';
const EMOJI_STACK = '"Apple Color Emoji", "Noto Color Emoji", "Segoe UI Emoji", sans-serif';

// Each palette keeps the same slot meanings so pages are portable across themes.
export const DECK_THEMES = {
  peach: {
    name: '蜜桃暖调',
    bg: '#fef7f3', bgSoft: '#fff1ea', surface: '#ffffff', surface2: '#fff5ef',
    ink: '#3a1f18', ink2: '#6f4a3e', ink3: '#a68676',
    accent: '#ff6b8b', accent2: '#ffa94d', accent3: '#ffd166',
    good: '#5fb36a', bad: '#ff5c5c',
    glow: ['rgba(255,209,102,.35)', 'rgba(255,107,139,.22)', 'rgba(122,200,255,.18)'],
  },
  mint: {
    name: '薄荷清透',
    bg: '#f2faf5', bgSoft: '#e7f5ec', surface: '#ffffff', surface2: '#eef8f1',
    ink: '#173a2c', ink2: '#3d6553', ink3: '#7c9a8b',
    accent: '#22a06b', accent2: '#4bc0c8', accent3: '#c9ec7a',
    good: '#22a06b', bad: '#ef6461',
    glow: ['rgba(201,236,122,.38)', 'rgba(75,192,200,.22)', 'rgba(34,160,107,.16)'],
  },
  lilac: {
    name: '雾紫少女',
    bg: '#f8f4fd', bgSoft: '#f0e8fb', surface: '#ffffff', surface2: '#f6f0fd',
    ink: '#2e2140', ink2: '#584a70', ink3: '#9287a8',
    accent: '#8b5cf6', accent2: '#f472b6', accent3: '#ffd6f0',
    good: '#5fb36a', bad: '#ef476f',
    glow: ['rgba(244,114,182,.26)', 'rgba(139,92,246,.22)', 'rgba(186,230,253,.24)'],
  },
  butter: {
    name: '奶油黄油',
    bg: '#fffaf0', bgSoft: '#fff3d9', surface: '#ffffff', surface2: '#fff6e5',
    ink: '#3d2c12', ink2: '#6b5327', ink3: '#a89168',
    accent: '#f4801f', accent2: '#ffc233', accent3: '#ffe9a8',
    good: '#69a844', bad: '#e5484d',
    glow: ['rgba(255,194,51,.34)', 'rgba(244,128,31,.18)', 'rgba(160,220,255,.16)'],
  },
};

export const DEFAULT_DECK_THEME = 'peach';

const STICKER_TONES = { white: 'surface', pink: '#ffd3e0', yellow: '#ffe788', blue: '#cfeaff', green: '#d4f2c8' };

function escapeHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Inline markup shared by every text-bearing block:
//   ==x== marker band   **x** bold ink   [[x]] accent colour   \n line break
function inline(text) {
  return inlineScan(String(text ?? '').replace(/\\n/g, '\n'));
}

function inlineScan(source) {
  let out = '';
  let i = 0;
  const patterns = [
    { open: '==', close: '==', wrap: (s) => `<span class="mark">${s}</span>` },
    { open: '**', close: '**', wrap: (s) => `<b class="strong">${s}</b>` },
    { open: '[[', close: ']]', wrap: (s) => `<span class="hot">${s}</span>` },
  ];
  outer: while (i < source.length) {
    for (const p of patterns) {
      if (source.startsWith(p.open, i)) {
        const end = source.indexOf(p.close, i + p.open.length);
        if (end !== -1) {
          // Nested scan so line breaks and other marks survive inside a span.
          out += p.wrap(inlineScan(source.slice(i + p.open.length, end)));
          i = end + p.close.length;
          continue outer;
        }
      }
    }
    out += source[i] === '\n' ? '<br>' : escapeHtml(source[i]);
    i += 1;
  }
  return out;
}

function styleAttr(pairs) {
  const body = pairs.filter(Boolean).join(';');
  return body ? ` style="${body}"` : '';
}

function toneColor(tone) {
  const map = { accent: 'var(--accent)', accent2: 'var(--accent2)', accent3: 'var(--accent3)', good: 'var(--good)', bad: 'var(--bad)', ink: 'var(--ink)', dim: 'var(--ink2)', dim2: 'var(--ink3)' };
  return map[tone] || map.dim;
}

function renderBlock(block) {
  const b = typeof block === 'string' ? { type: 'text', text: block } : block || {};
  const gap = b.gap === undefined ? '' : `margin-top:${Number(b.gap)}px`;
  const align = b.align ? `text-align:${b.align}` : '';

  switch (b.type) {
    case 'space':
      return `<div class="blk" style="height:${Number(b.size ?? 40)}px;margin-top:0"></div>`;

    case 'eyebrow':
      return `<p class="blk eyebrow"${styleAttr([gap, align, `color:${toneColor(b.tone || 'accent')}`])}>${inline(b.text)}</p>`;

    case 'title': {
      const level = Number(b.level ?? 2);
      return `<h${level === 1 ? 1 : 2} class="blk h${level}"${styleAttr([gap, align])}>${inline(b.text)}</h${level === 1 ? 1 : 2}>`;
    }

    case 'emoji':
      return `<div class="blk big-emoji"${styleAttr([gap])}>${escapeHtml(b.text)}</div>`;

    case 'badge':
      return `<div class="blk badge-row"${styleAttr([gap, align])}><span class="num-circle"${styleAttr([
        `background:${toneColor(b.tone || 'accent')}`,
        b.tone === 'accent3' ? 'color:var(--ink)' : '',
      ])}>${inline(b.text)}</span></div>`;

    case 'text':
      return `<p class="blk lede"${styleAttr([
        gap,
        align,
        b.size ? `font-size:${Number(b.size)}px` : '',
        b.tone ? `color:${toneColor(b.tone)}` : '',
        b.strong ? 'font-weight:700' : '',
      ])}>${inline(b.text)}</p>`;

    case 'cards': {
      const items = (b.items || []).map((raw) => {
        const item = typeof raw === 'string' ? { title: raw } : raw || {};
        const bg = item.tone === 'highlight' ? 'background:var(--accent3)' : item.tone === 'soft' ? 'background:var(--surface2)' : '';
        const note = item.note ? `<p class="card-note">${inline(item.note)}</p>` : '';
        return `<div class="hand-box"${styleAttr([bg])}><b class="card-title">${inline(item.title)}</b>${note}</div>`;
      });
      return `<div class="blk stack"${styleAttr([gap])}>${items.join('')}</div>`;
    }

    case 'box': {
      const bg = b.tone === 'soft' ? 'background:var(--surface2)' : b.tone === 'highlight' ? 'background:var(--accent3)' : '';
      const label = b.label
        ? `<p class="box-label"${styleAttr([b.labelSize ? `font-size:${Number(b.labelSize)}px` : ''])}>${inline(b.label)}</p>`
        : '';
      const text = b.text
        ? `<p class="box-text"${styleAttr([
            b.label ? 'margin-top:10px' : '',
            b.size ? `font-size:${Number(b.size)}px` : '',
          ])}>${inline(b.text)}</p>`
        : '';
      return `<div class="blk hand-box"${styleAttr([gap, bg])}>${label}${text}</div>`;
    }

    case 'tags': {
      const chips = (b.items || []).map((t) => `<span class="ht">${escapeHtml(t)}</span>`).join('');
      return `<div class="blk tag-row"${styleAttr([gap, b.align === 'center' ? 'justify-content:center' : ''])}>${chips}</div>`;
    }

    default:
      return `<p class="blk lede"${styleAttr([gap, align])}>${inline(b.text)}</p>`;
  }
}

function renderSticker(raw) {
  const s = raw || {};
  const pos = [];
  if (s.top !== undefined) pos.push(`top:${Number(s.top)}px`);
  if (s.bottom !== undefined) pos.push(`bottom:${Number(s.bottom)}px`);
  const centered = s.left === 'center';
  if (centered) pos.push('left:50%');
  else if (s.left !== undefined) pos.push(`left:${Number(s.left)}px`);
  if (s.right !== undefined) pos.push(`right:${Number(s.right)}px`);
  const rotate = Number(s.rotate ?? -3);
  pos.push(`transform:${centered ? 'translateX(-50%) ' : ''}rotate(${rotate}deg)`);
  const tone = STICKER_TONES[s.tone] || STICKER_TONES.white;
  pos.push(`background:${tone === 'surface' ? 'var(--surface)' : tone}`);
  return `<div class="sticker"${styleAttr(pos)}>${inline(s.text)}</div>`;
}

function renderFooter(deck, page) {
  const footer = page.footer;
  if (!footer) return '';
  const author = { ...(deck.author || {}), ...(typeof footer === 'object' ? footer.author || {} : {}) };
  const right = typeof footer === 'object' ? footer.right || '' : '';
  const name = author.name || '';
  const initial = author.initial || (name.replace(/^@/, '')[0] || '·');
  const left = name
    ? `<div class="who"><span class="avatar">${escapeHtml(initial)}</span><b>${escapeHtml(name)}</b></div>`
    : '<div></div>';
  return `<div class="bottom-bar">${left}<div>${inline(right)}</div></div>`;
}

export function normalizeDeck(input = {}) {
  const deck = typeof input === 'string' ? JSON.parse(input) : input;
  const themeKey = DECK_THEMES[deck.theme] ? deck.theme : DEFAULT_DECK_THEME;
  const pages = Array.isArray(deck.pages) ? deck.pages : [];
  if (!pages.length) throw new Error('deck.pages must contain at least one page');
  return {
    title: deck.title || '小红书图文',
    theme: themeKey,
    author: deck.author || null,
    pageDots: deck.pageDots !== false,
    width: Number(deck.width) || 1080,
    height: Number(deck.height) || 1440,
    pages: pages.map((p) => ({
      name: p.name || '',
      justify: p.justify || 'center',
      align: p.align || 'left',
      gap: Number(p.gap ?? 18),
      pageDot: p.pageDot,
      stickers: Array.isArray(p.stickers) ? p.stickers : [],
      footer: p.footer || null,
      blocks: Array.isArray(p.blocks) ? p.blocks : [],
    })),
  };
}

function deckCSS(deck, scale) {
  const t = DECK_THEMES[deck.theme];
  const [g1, g2, g3] = t.glow;
  return `
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: ${t.bg}; }
  .stage { width: ${DECK_CANVAS.width}px; height: ${DECK_CANVAS.height}px; transform: scale(${scale}); transform-origin: top left; }
  .page {
    --bg:${t.bg}; --bgSoft:${t.bgSoft}; --surface:${t.surface}; --surface2:${t.surface2};
    --ink:${t.ink}; --ink2:${t.ink2}; --ink3:${t.ink3};
    --accent:${t.accent}; --accent2:${t.accent2}; --accent3:${t.accent3};
    --good:${t.good}; --bad:${t.bad};
    position: relative; width: ${DECK_CANVAS.width}px; height: ${DECK_CANVAS.height}px;
    padding: 70px 64px; overflow: hidden; background: var(--bg);
    display: flex; flex-direction: column;
    font-family: ${FONT_STACK}; color: var(--ink);
    line-height: 1.6; letter-spacing: -.01em; -webkit-font-smoothing: antialiased;
  }
  .page::before {
    content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(45% 30% at 80% 10%, ${g1}, transparent 70%),
      radial-gradient(50% 35% at 10% 95%, ${g2}, transparent 70%),
      radial-gradient(40% 30% at 90% 85%, ${g3}, transparent 70%);
  }
  .page > * { position: relative; z-index: 1; }
  .blk { margin: 0; }
  .blk + .blk { margin-top: var(--gap); }

  .h1 { font-size: 72px; line-height: 1.1; font-weight: 900; letter-spacing: -.02em; color: var(--ink); }
  .h2 { font-size: 54px; line-height: 1.15; font-weight: 800; letter-spacing: -.015em; color: var(--ink); }
  .eyebrow { font-size: 24px; font-weight: 700; line-height: 1.4; }
  .lede { font-size: 26px; line-height: 1.55; color: var(--ink2); }
  .strong { color: var(--ink); font-weight: 800; }
  .hot { color: var(--accent); font-weight: 800; }
  .mark { background: linear-gradient(180deg, transparent 60%, var(--accent3) 60%, var(--accent3) 92%, transparent 92%); padding: 0 10px; }

  .big-emoji { font-size: 180px; line-height: 1; text-align: center; font-family: ${EMOJI_STACK}; }
  .num-circle {
    display: inline-flex; align-items: center; justify-content: center; width: 72px; height: 72px;
    border-radius: 50%; background: var(--accent); color: #fff; font-weight: 900; font-size: 36px;
    border: 3px solid var(--ink); box-shadow: 4px 4px 0 var(--ink);
  }
  .badge-row { line-height: 1; }

  .hand-box { background: var(--surface); border: 2.5px solid var(--ink); border-radius: 22px; padding: 24px 28px; box-shadow: 5px 5px 0 var(--ink); }
  .stack > .hand-box + .hand-box { margin-top: 24px; }
  .card-title { font-size: 22px; font-weight: 800; color: var(--ink); display: block; line-height: 1.35; }
  .card-note { font-size: 16px; color: var(--ink2); margin: 4px 0 0; line-height: 1.5; }
  .box-label { font-size: 22px; font-weight: 700; color: var(--ink); margin: 0; line-height: 1.4; }
  .box-text { font-size: 20px; color: var(--ink2); margin: 0; line-height: 1.7; }

  .sticker {
    position: absolute; z-index: 2; padding: 10px 18px; background: var(--surface);
    border: 2.5px dashed var(--ink); border-radius: 18px; font-weight: 800; font-size: 18px;
    color: var(--ink); box-shadow: 4px 4px 0 var(--ink); white-space: nowrap;
  }
  .page-dot {
    position: absolute; top: 40px; right: 48px; z-index: 3; background: var(--ink); color: #fff;
    border-radius: 999px; padding: 6px 14px; font-family: ${MONO_STACK}; font-size: 14px; font-weight: 700;
  }
  .tag-row { display: flex; flex-wrap: wrap; gap: 10px; }
  .ht { background: var(--surface); color: var(--accent); border: 2px solid var(--ink); padding: 6px 14px; border-radius: 999px; font-weight: 700; font-size: 16px; }

  .bottom-bar {
    position: absolute; bottom: 40px; left: 64px; right: 64px; z-index: 3;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 15px; color: var(--ink3); font-family: ${MONO_STACK};
  }
  .who { display: flex; align-items: center; gap: 10px; }
  .avatar {
    width: 54px; height: 54px; border-radius: 50%; background: var(--accent3); border: 2.5px solid var(--ink);
    box-shadow: 3px 3px 0 var(--ink); display: inline-flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 20px; color: var(--ink); font-family: ${FONT_STACK};
  }
  .who b { color: var(--ink); font-size: 18px; font-family: ${FONT_STACK}; }
`;
}

function renderPage(deck, page, index) {
  const total = deck.pages.length;
  const dot = deck.pageDots === false || page.pageDot === false
    ? ''
    : `<div class="page-dot">${escapeHtml(page.pageDot || `${index + 1} / ${total}`)}</div>`;
  const justify = { center: 'center', start: 'flex-start', end: 'flex-end', between: 'space-between' }[page.justify] || 'center';
  const body = page.blocks.map(renderBlock).join('\n    ');
  const stickers = page.stickers.map(renderSticker).join('\n    ');
  return `<section class="page" style="justify-content:${justify};text-align:${page.align};--gap:${page.gap}px">
    ${dot}
    ${stickers}
    ${body}
    ${renderFooter(deck, page)}
  </section>`;
}

/** Full standalone HTML document for one page, sized to the deck's output size. */
export function buildPageHTML(input, index) {
  const deck = normalizeDeck(input);
  const scale = deck.width / DECK_CANVAS.width;
  const page = deck.pages[index];
  if (!page) throw new Error(`page ${index} is out of range (deck has ${deck.pages.length})`);
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>${escapeHtml(deck.title)} · ${index + 1}/${deck.pages.length}</title>
<style>${deckCSS(deck, scale)}
  html, body { width: ${deck.width}px; height: ${deck.height}px; overflow: hidden; }
</style></head>
<body><div class="stage">${renderPage(deck, page, index)}</div></body></html>`;
}

/** One scrollable HTML preview of every page, for eyeballing a deck before rendering. */
export function buildDeckPreviewHTML(input) {
  const deck = normalizeDeck(input);
  const pages = deck.pages.map((p, i) => renderPage(deck, p, i)).join('\n');
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>${escapeHtml(deck.title)} · ${deck.pages.length} 页</title>
<style>${deckCSS(deck, 1)}
  body { background: #efe9e2; padding: 40px; display: flex; flex-wrap: wrap; gap: 32px; justify-content: center; }
  .page { border-radius: 28px; box-shadow: 0 18px 44px rgba(60,30,20,.18); flex: none; }
</style></head>
<body>${pages}</body></html>`;
}

export function listDeckThemes() {
  return Object.entries(DECK_THEMES).map(([key, value]) => ({ key, name: value.name }));
}
