// Склейка build/*.html в один сайт dist/ для GitHub Pages.
//
//   dist/index.html      — оболочка со вкладками (скрипт обфусцирован)
//   dist/a/<hash>.bin    — приложения: минифицированы, логика обфусцирована,
//                          сжаты gzip и замаскированы; грузятся по требованию
//   dist/img/            — картинки атласа
//
// node tools/bundle.mjs          — полная сборка
// node tools/bundle.mjs --fast   — без обфускации и минификации (для отладки)
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import JavaScriptObfuscator from 'javascript-obfuscator';
import { minify } from 'html-minifier-terser';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BUILD = path.join(ROOT, 'build');
const FAST = process.argv.includes('--fast');
const DIST = path.join(ROOT, FAST ? 'dist-fast' : 'dist');
const rd = (...p) => fs.readFileSync(path.join(...p), 'utf8');

// Ссылки артефактов Claude → переходы внутри сайта
const LINKS = {
  'https://claude.ai/artifact/ThYN3MvgSKqpgR8yRx12sm': 'zz:atlas',
  'https://claude.ai/artifact/AmASUy51PbjhvngTJCasdg': 'zz:rules',
  'https://claude.ai/artifact/3pfFpJ5XBXeQC9YmwMiw4u': 'zz:sheet',
  'https://claude.ai/artifact/LuRvpFgFFgWDr8cUcjThuF': 'zz:stats',
  'https://claude.ai/artifact/35kvTHF2td82eAeYxc2ueK': 'zz:skills',
};

const ATLAS_DATA_END = ';d.byId=Object.fromEntries(d.nodes.map(n=>[n.id,n]));d.imgs=new Set(d.imgs);return d})();';

const APPS = [
  {
    id: 'atlas', file: 'atlas.html', tab: 'Атлас', title: 'Атлас Зазеркалья',
    // переход по ключу: id карточки или pN — абзац выпусков
    hook: "window.__zzNav=function(k){var m=/^p(\\d+)$/.exec(k||'');if(m){select(null);parJump=+m[1];tab='txt';txtQ='';render()}else if(byId[k])go(k)};",
  },
  {
    id: 'rules', file: 'rules.html', tab: 'Свод правил', title: 'Свод правил Зазеркалья',
    hook: 'window.__zzNav=function(k){if(k&&byId[k])show(k)};',
    // переходы на лист и атлас есть во вкладках сайта
    css: '.ext{display:none!important}',
  },
  { id: 'sheet', file: 'sheet.html', tab: 'Лист путника', title: 'Лист путника' },
  // solo: на вкладке есть кнопка «Скрыть шапку» (ссылка ?solo для игроков)
  { id: 'stats', file: 'stats.html', tab: 'Тест характеристик', title: 'Тест характеристик', solo: true },
  { id: 'skills', file: 'skills.html', tab: 'Тест навыков', title: 'Тест навыков', solo: true },
  {
    id: 'camp', file: 'campaign.html', tab: 'Кампания', title: 'Кампания: поиск «пацаноида»',
    hook: 'window.__zzNav=function(k){if(k&&byId[k])show(k)};',
    css: '.ext{display:none!important}',
  },
];

// Каркас, в который Claude оборачивает артефакты, — чтобы страницы выглядели так же.
const SKELETON_CSS = ':root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#faf9f5;color:#141413}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}';

const OBF = {
  compact: true,
  simplify: true,
  target: 'browser',
  identifierNamesGenerator: 'hexadecimal',
  renameGlobals: false,            // верхнеуровневые имена нужны мосту и обработчикам
  stringArray: true,
  stringArrayThreshold: 1,
  stringArrayEncoding: ['base64'],
  stringArrayRotate: true,
  stringArrayShuffle: true,
  stringArrayIndexShift: true,
  stringArrayWrappersCount: 1,
  splitStrings: false,
  controlFlowFlattening: false,
  deadCodeInjection: false,
  selfDefending: false,
  debugProtection: false,
  transformObjectKeys: false,
  numbersToExpressions: false,
  unicodeEscapeSequence: false,
  sourceMap: false,
};

function obfuscate(code, extra = {}) {
  if (FAST) return code;
  let out = JavaScriptObfuscator.obfuscate(code, { ...OBF, ...extra }).getObfuscatedCode();
  return out.replace(/<\/(script)/gi, '<\\/$1');
}

const MINIFY = {
  collapseWhitespace: true,
  conservativeCollapse: true,
  removeComments: true,
  minifyCSS: { level: 1 },
  minifyJS: false,
  caseSensitive: true,
  keepClosingSlash: true,
  decodeEntities: false,
};

async function buildApp(app) {
  let html = rd(BUILD, app.file);
  for (const [from, to] of Object.entries(LINKS)) html = html.split(from).join(to);
  const left = html.match(/https:\/\/claude\.ai\/[^"'`\s)]*/g);
  if (left) throw new Error(`${app.id}: остались ссылки на claude.ai: ${[...new Set(left)].join(', ')}`);

  // Встроенные скрипты: данные оставляем как есть, логику обфусцируем.
  const scripts = [];
  html = html.replace(/<script>([\s\S]*?)<\/script>/g, (m, code) => {
    const parts = [];
    if (code.includes('const NODES=')) {
      parts.push(code);                                     // данные атласа
    } else {
      const i = code.indexOf('const ATLAS_DATA=');
      if (i >= 0) {                                         // данные атласа внутри свода правил
        const j = code.indexOf(ATLAS_DATA_END, i);
        if (j < 0) throw new Error('rules: не найден конец ATLAS_DATA');
        const end = j + ATLAS_DATA_END.length;
        parts.push(code.slice(i, end));
        code = code.slice(0, i) + code.slice(end);
      }
      parts.push(obfuscate(code));
    }
    scripts.push(parts.map(c => `<script>${c}</script>`).join(''));
    return `<!--ZZSCRIPT${scripts.length - 1}-->`;
  });

  const bridge = obfuscate(rd(ROOT, 'tools', 'bridge.js').replace('%APP%', app.id));
  const hook = app.hook ? obfuscate(app.hook) : '';
  let page = '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    + `<style>${SKELETON_CSS}${app.css || ''}</style><script>${bridge}</script></head><body>\n`
    + html + (hook ? `\n<script>${hook}</script>` : '') + '\n</body></html>';

  if (!FAST) page = await minify(page, { ...MINIFY, ignoreCustomComments: [/^ZZSCRIPT\d+$/] });
  page = page.replace(/<!--ZZSCRIPT(\d+)-->/g, (m, n) => scripts[+n]);
  return page;
}

function mask(buf, key) {
  const out = Buffer.from(buf);
  for (let i = 0; i < out.length; i++) out[i] ^= key[i % key.length];
  return out;
}

async function main() {
  fs.rmSync(DIST, { recursive: true, force: true });
  fs.mkdirSync(path.join(DIST, 'a'), { recursive: true });
  const key = [...crypto.randomBytes(24)];
  const manifest = {};

  for (const app of APPS) {
    const t0 = Date.now();
    const page = await buildApp(app);
    const gz = zlib.gzipSync(Buffer.from(page, 'utf8'), { level: 9 });
    const bin = mask(gz, key);
    const name = `a/${crypto.createHash('sha256').update(bin).digest('hex').slice(0, 12)}.bin`;
    fs.writeFileSync(path.join(DIST, name), bin);
    manifest[app.id] = { f: name, t: app.title, ...(app.solo ? { s: 1 } : {}) };
    console.log(`${app.id.padEnd(7)} ${(page.length / 1024).toFixed(0).padStart(5)} КБ → ${(bin.length / 1024).toFixed(0).padStart(4)} КБ  ${name}  ${Date.now() - t0} мс`);
  }

  const mark = '<svg viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="16" cy="13.5" rx="9" ry="11" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.6"/><path d="M11.8 9.5q1.6-3.2 5.2-3.6" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round"/><path d="M16 24.5v4.5M11 30h10" fill="none" stroke="var(--accent)" stroke-width="2.6" stroke-linecap="round"/></svg>';
  const icon = 'data:image/svg+xml,' + encodeURIComponent(mark
    .replace(' aria-hidden="true"', ' xmlns="http://www.w3.org/2000/svg"')
    .replaceAll('var(--accent-soft)', '#ece9fb').replaceAll('var(--accent)', '#5b4bb7'));
  const tabs = APPS.map(a => `<a href="#${a.id}" data-app="${a.id}">${a.tab}</a>`).join('');
  const loader = obfuscate(rd(ROOT, 'tools', 'shell', 'loader.js')
    .replace('%MANIFEST%', JSON.stringify(manifest))
    .replace('%KEY%', JSON.stringify(key)));
  let index = rd(ROOT, 'tools', 'shell', 'index.html')
    .replace('%ICON%', icon).replace('%MARK%', mark).replace('%TABS%', tabs);
  index = index.replace('<script>%LOADER%</script>', '<!--ZZLOADER-->');
  if (!FAST) index = await minify(index, { ...MINIFY, ignoreCustomComments: [/^ZZLOADER$/] });
  index = index.replace('<!--ZZLOADER-->', () => `<script>${loader}</script>`);
  if (!index.includes(loader)) throw new Error('index: не удалось вставить загрузчик');
  fs.writeFileSync(path.join(DIST, 'index.html'), index);

  fs.cpSync(path.join(ROOT, 'src', 'atlas', 'img'), path.join(DIST, 'img'), { recursive: true });
  fs.mkdirSync(path.join(DIST, 'map'), { recursive: true });
  for (const f of fs.readdirSync(path.join(ROOT, 'src', 'atlas', 'map')))
    if (!f.endsWith('.txt')) fs.copyFileSync(path.join(ROOT, 'src', 'atlas', 'map', f), path.join(DIST, 'map', f));
  fs.writeFileSync(path.join(DIST, '.nojekyll'), '');
  console.log(`index   ${(index.length / 1024).toFixed(0).padStart(5)} КБ;  картинок: ${fs.readdirSync(path.join(DIST, 'img')).length}  → ${path.relative(ROOT, DIST)}/`);
}

main().catch(e => { console.error(e); process.exit(1); });
