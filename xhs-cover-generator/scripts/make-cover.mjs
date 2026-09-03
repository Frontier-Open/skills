#!/usr/bin/env node
// CLI for the Xiaohongshu cover generator: config -> 1080x1440 PNG (via headless Chrome) or HTML.
//
//   node make-cover.mjs --template thinking --theme melon --main "一个人做内容\n先定一个主张" \
//        --highlight "一个主张" --emoji 🧭 --out cover.png
//   node make-cover.mjs --config cover.json --out cover.png
//   node make-cover.mjs --batch covers.json --outdir ./out
//   node make-cover.mjs --editor              # local drag-and-tweak editor
//   node make-cover.mjs --template-file my-templates.json --template mine --main "..."
//   node make-cover.mjs --list                # every template and palette
//
// Chrome lookup order: $XHS_COVER_CHROME, installed Chrome/Edge/Chromium, Playwright cache.

import { execFile } from 'node:child_process';
import { createServer } from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import {
  CANVAS,
  TEMPLATES,
  THEMES,
  buildCoverHTML,
  listTemplates,
  normalizeConfig,
  randomSeed,
  registerTemplates,
  resolveTemplateKey,
  resolveThemeKey,
} from './cover.js';

const execFileAsync = promisify(execFile);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(HERE, '..');

let customTemplates = [];

/** --template-file: JSON template spec(s), optionally `extends` a built-in. */
function loadTemplateFile(file) {
  const parsed = JSON.parse(fs.readFileSync(path.resolve(String(file)), 'utf8'));
  customTemplates = Array.isArray(parsed) ? parsed : [parsed];
  registerTemplates(customTemplates);
  return customTemplates;
}

const FLAG_ALIASES = {
  t: 'template',
  m: 'main',
  o: 'out',
  h: 'help',
};

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('-')) {
      args._.push(token);
      continue;
    }
    const raw = token.replace(/^-+/, '');
    const [name, inlineValue] = raw.includes('=') ? splitOnce(raw, '=') : [raw, undefined];
    const key = FLAG_ALIASES[name] || name;
    const next = argv[i + 1];
    if (inlineValue !== undefined) {
      args[key] = inlineValue;
    } else if (next === undefined || next.startsWith('--')) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function splitOnce(text, sep) {
  const at = text.indexOf(sep);
  return [text.slice(0, at), text.slice(at + 1)];
}

function unescapeNewlines(value) {
  return typeof value === 'string' ? value.replace(/\\n/g, '\n') : value;
}

function configFromArgs(args) {
  const config = {};
  const map = {
    template: 'template',
    theme: 'theme',
    main: 'mainText',
    mainText: 'mainText',
    sub: 'subText',
    subText: 'subText',
    highlight: 'highlightText',
    highlightText: 'highlightText',
    tag: 'tag',
    emoji: 'emoji',
    background: 'backgroundColor',
    backgroundColor: 'backgroundColor',
    textColor: 'textColor',
    emojiX: 'emojiX',
    emojiY: 'emojiY',
    emojiSize: 'emojiSize',
    width: 'width',
    height: 'height',
  };
  for (const [flag, field] of Object.entries(map)) {
    if (args[flag] !== undefined) config[field] = unescapeNewlines(args[flag]);
  }
  if (args['no-emoji'] || args.noEmoji) config.showEmoji = false;
  return config;
}

function findChrome() {
  const candidates = [];
  if (process.env.XHS_COVER_CHROME) candidates.push(process.env.XHS_COVER_CHROME);
  candidates.push(
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/microsoft-edge',
  );
  for (const cacheRoot of [
    path.join(os.homedir(), 'Library/Caches/ms-playwright'),
    path.join(os.homedir(), '.cache/ms-playwright'),
  ]) {
    if (!fs.existsSync(cacheRoot)) continue;
    const dirs = fs
      .readdirSync(cacheRoot)
      .filter((name) => name.startsWith('chromium'))
      .sort()
      .reverse();
    for (const dir of dirs) {
      candidates.push(
        path.join(cacheRoot, dir, 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
        path.join(cacheRoot, dir, 'chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
        path.join(cacheRoot, dir, 'chrome-linux/chrome'),
        path.join(cacheRoot, dir, 'chrome-mac-arm64/headless_shell'),
        path.join(cacheRoot, dir, 'chrome-linux/headless_shell'),
      );
    }
  }
  return candidates.find((bin) => bin && fs.existsSync(bin)) || null;
}

async function renderPNG(html, outPath, cfg) {
  const chrome = findChrome();
  if (!chrome) {
    throw new Error(
      'No Chrome/Chromium binary found. Install Chrome, or set XHS_COVER_CHROME to a Chromium executable, or run with --html to skip PNG rendering.',
    );
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'xhs-cover-'));
  const htmlPath = path.join(tmpDir, 'cover.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
  try {
    await execFileAsync(chrome, [
      '--headless=new',
      '--disable-gpu',
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
      '--default-background-color=00000000',
      `--window-size=${cfg.width},${cfg.height}`,
      '--virtual-time-budget=3000',
      `--screenshot=${path.resolve(outPath)}`,
      pathToFileURL(htmlPath).href,
    ]);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
  if (!fs.existsSync(outPath)) throw new Error(`Chrome did not produce ${outPath}`);
  return { chrome, outPath: path.resolve(outPath) };
}

async function renderOne(rawConfig, outPath, { htmlOnly = false } = {}) {
  const cfg = normalizeConfig(rawConfig);
  const html = buildCoverHTML(cfg);
  const resolved = path.resolve(outPath);
  if (htmlOnly || resolved.endsWith('.html')) {
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
    const target = resolved.endsWith('.html') ? resolved : resolved.replace(/\.png$/i, '.html');
    fs.writeFileSync(target, html, 'utf8');
    return { file: target, cfg };
  }
  await renderPNG(html, resolved, cfg);
  return { file: resolved, cfg };
}

function slugify(value, fallback) {
  const slug = String(value || '')
    .trim()
    .replace(/[\s\\/:*?"<>|]+/g, '-')
    .slice(0, 40);
  return slug || fallback;
}

async function runBatch(batchPath, args) {
  const entries = JSON.parse(fs.readFileSync(batchPath, 'utf8'));
  if (!Array.isArray(entries)) throw new Error('--batch expects a JSON array of cover configs');
  const outDir = path.resolve(args.outdir || 'covers');
  fs.mkdirSync(outDir, { recursive: true });
  const results = [];
  for (const [index, entry] of entries.entries()) {
    const name = entry.name || `${String(index + 1).padStart(2, '0')}-${slugify(entry.mainText?.split('\n')[0], 'cover')}`;
    const out = path.join(outDir, `${name}.png`);
    const { file } = await renderOne(entry, out, { htmlOnly: Boolean(args.html) });
    results.push(file);
    console.log(`rendered ${file}`);
  }
  return results;
}

function serveEditor(port) {
  const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css' };
  const outDir = path.resolve('covers');
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/custom-templates.json') {
      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(customTemplates));
      return;
    }
    if (req.method === 'POST' && url.pathname === '/render') {
      try {
        const body = await readBody(req);
        const config = normalizeConfig(JSON.parse(body));
        const name = `${TEMPLATES[config.template].key}-${config.theme}-${Date.now()}.png`;
        const { file } = await renderOne(config, path.join(outDir, name));
        res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ file }));
      } catch (error) {
        res.writeHead(500, { 'content-type': 'application/json' }).end(JSON.stringify({ error: String(error.message || error) }));
      }
      return;
    }
    const rel = url.pathname === '/' ? '/assets/editor.html' : url.pathname;
    const file = path.join(SKILL_ROOT, path.normalize(rel).replace(/^(\.\.[/\\])+/, ''));
    if (!file.startsWith(SKILL_ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end('not found');
      return;
    }
    res.writeHead(200, { 'content-type': mime[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  server.listen(port, () => {
    console.log(`小红书封面编辑器: http://localhost:${server.address().port}`);
    console.log(`拖拽表情调整位置，右下角手柄缩放，「保存 PNG」写入 ${outDir}。Ctrl+C 停止。`);
  });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
      if (data.length > 1e6) reject(new Error('payload too large'));
    });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function printHelp() {
  const templates = listTemplates()
    .map((t) => `  ${t.key.padEnd(18)} ${t.name.padEnd(6)} ${t.desc} · ${t.useCase}`)
    .join('\n');
  const themes = Object.entries(THEMES)
    .map(([key, t]) => `  ${key.padEnd(7)} ${t.name}  ${t.desc} · ${t.style}  [${t.colors.join(' ')}]`)
    .join('\n');
  console.log(`小红书封面生成器 (${CANVAS.width}x${CANVAS.height})

Templates:
${templates}

Themes:
${themes}

Flags:
  --template <key>       --theme <braun|melon|sunset|ocean>
  --main "line1\\nline2"  --sub <text>   --highlight <word>   --tag <word>
  --emoji <char>  --no-emoji  --emojiX <5-95>  --emojiY <5-95>  --emojiSize <40-220>
  --background <#hex>  --textColor <#hex>  --height <px>
  --out <file.png|file.html>   --html   --config <file.json>
  --batch <file.json> --outdir <dir>     --random   --editor [--port 5178]
  --template-file <file.json>            add custom templates (see references/design-system.md)
  --list                                 print the tables above and exit`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args['template-file'] || args.templateFile) loadTemplateFile(args['template-file'] || args.templateFile);
  if (args.help || args.list) return printHelp();
  if (args.editor) return serveEditor(Number(args.port) || 5178);

  if (args.batch) {
    await runBatch(path.resolve(String(args.batch)), args);
    return;
  }

  let config = {};
  if (args.config) config = JSON.parse(fs.readFileSync(path.resolve(String(args.config)), 'utf8'));
  if (args.random) {
    config = { ...config, ...randomSeed(args.template ?? config.template ?? 'thinking', args.theme ?? config.theme) };
  }
  config = { ...config, ...configFromArgs(args) };

  const templateKey = resolveTemplateKey(config.template);
  const out = args.out
    ? String(args.out)
    : path.join('covers', `${TEMPLATES[templateKey].key}-${resolveThemeKey(config.theme)}.png`);
  const { file, cfg } = await renderOne(config, out, { htmlOnly: Boolean(args.html) });
  console.log(`rendered ${file}  [${TEMPLATES[cfg.template].name} · ${THEMES[cfg.theme].name} · ${cfg.backgroundColor}]`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
