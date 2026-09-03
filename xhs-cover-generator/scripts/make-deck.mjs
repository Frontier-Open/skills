#!/usr/bin/env node
// CLI for the Xiaohongshu carousel generator: one deck JSON -> N PNGs.
//
//   node make-deck.mjs --sample --outdir ./out
//   node make-deck.mjs --deck my-deck.json --outdir ./out --theme mint
//   node make-deck.mjs --deck my-deck.json --page 3 --out page3.png
//   node make-deck.mjs --deck my-deck.json --html preview.html
//   node make-deck.mjs --themes
//
// Chrome lookup order: $XHS_COVER_CHROME, installed Chrome/Edge/Chromium, Playwright cache.

import { execFile } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { buildDeckPreviewHTML, buildPageHTML, listDeckThemes, normalizeDeck } from './deck.js';

const execFileAsync = promisify(execFile);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(HERE, '..');
const SAMPLE = path.join(SKILL_ROOT, 'assets/deck-xhs-post.sample.json');

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('-')) { args._.push(token); continue; }
    const raw = token.replace(/^-+/, '');
    const eq = raw.indexOf('=');
    const [name, inline] = eq === -1 ? [raw, undefined] : [raw.slice(0, eq), raw.slice(eq + 1)];
    const next = argv[i + 1];
    if (inline !== undefined) args[name] = inline;
    else if (next === undefined || next.startsWith('--')) args[name] = true;
    else { args[name] = next; i += 1; }
  }
  return args;
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
    const dirs = fs.readdirSync(cacheRoot).filter((n) => n.startsWith('chromium')).sort().reverse();
    for (const dir of dirs) {
      candidates.push(
        path.join(cacheRoot, dir, 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
        path.join(cacheRoot, dir, 'chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
        path.join(cacheRoot, dir, 'chrome-linux/chrome'),
      );
    }
  }
  return candidates.find((bin) => bin && fs.existsSync(bin)) || null;
}

async function shoot(chrome, html, outPath, width, height) {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'xhs-deck-'));
  const htmlPath = path.join(tmpDir, 'page.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
  try {
    await execFileAsync(chrome, [
      '--headless=new',
      '--disable-gpu',
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
      `--window-size=${width},${height}`,
      '--virtual-time-budget=4000',
      `--screenshot=${path.resolve(outPath)}`,
      pathToFileURL(htmlPath).href,
    ]);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
  if (!fs.existsSync(outPath)) throw new Error(`Chrome did not produce ${outPath}`);
}

function loadDeck(args) {
  const file = args.sample === true ? SAMPLE : args.deck || args._[0];
  if (!file) throw new Error('need --deck <file.json> or --sample');
  const raw = JSON.parse(fs.readFileSync(path.resolve(String(file)), 'utf8'));
  if (args.theme && args.theme !== true) raw.theme = args.theme;
  if (args.size && args.size !== true) {
    const [w, h] = String(args.size).toLowerCase().split('x').map(Number);
    if (w && h) { raw.width = w; raw.height = h; }
  }
  return normalizeDeck(raw);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.themes) {
    for (const t of listDeckThemes()) console.log(`${t.key.padEnd(8)} ${t.name}`);
    return;
  }
  if (args.help) {
    console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 12).join('\n').replace(/^\/\/ ?/gm, ''));
    return;
  }

  const deck = loadDeck(args);

  if (args.html) {
    const target = path.resolve(args.html === true ? 'deck-preview.html' : args.html);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, buildDeckPreviewHTML(deck), 'utf8');
    console.log(`wrote ${target}`);
    return;
  }

  const chrome = findChrome();
  if (!chrome) throw new Error('No Chrome/Chromium found. Set XHS_COVER_CHROME, or use --html.');

  if (args.page) {
    const index = Number(args.page) - 1;
    const out = path.resolve(args.out && args.out !== true ? args.out : `page-${args.page}.png`);
    await shoot(chrome, buildPageHTML(deck, index), out, deck.width, deck.height);
    console.log(`rendered ${out}`);
    return;
  }

  const outDir = path.resolve(args.outdir && args.outdir !== true ? args.outdir : 'deck');
  fs.mkdirSync(outDir, { recursive: true });
  const files = [];
  for (let i = 0; i < deck.pages.length; i += 1) {
    const label = deck.pages[i].name ? `-${deck.pages[i].name.replace(/[\s/\\:*?"<>|]+/g, '-')}` : '';
    const out = path.join(outDir, `${String(i + 1).padStart(2, '0')}${label}.png`);
    await shoot(chrome, buildPageHTML(deck, i), out, deck.width, deck.height);
    files.push(out);
    console.log(`rendered ${out}`);
  }
  console.log(`\n${files.length} pages -> ${outDir}`);
}

main().catch((error) => {
  console.error(String(error.message || error));
  process.exit(1);
});
