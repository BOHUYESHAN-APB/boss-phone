// BOSS PHONE 设计文档集 → 汇总 PDF 导出脚本
// 用法: npm run export  (node export.mjs)
// 原理: markdown-it 合并各文档 -> HTML; mermaid 在浏览器内渲染成 SVG;
//       本机 Chrome 无头打印为单份 PDF; 目录页码用 CSS target-counter(Chrome 117+)
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import MarkdownIt from 'markdown-it';
import anchor from 'markdown-it-anchor';
import puppeteer from 'puppeteer-core';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const OUT_DIR = path.join(ROOT, 'docs', 'pdf');
const TMP_DIR = path.join(HERE, '_out');

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find((p) => fs.existsSync(p));

if (!CHROME) {
  console.error('未找到 Chrome/Edge，无法导出 PDF');
  process.exit(1);
}

const DOCS = [
  { file: 'docs/BOSS_PHONE_PRD.md',            title: '产品需求文档 (PRD)',             prefix: 'prd' },
  { file: 'docs/BOSS_PHONE_DESIGN_OVERVIEW.md', title: '总体技术设计',                    prefix: 'ov' },
  { file: 'docs/BOSS_PHONE_DESIGN_PROTOCOL.md', title: '通讯协议规范',                    prefix: 'proto' },
  { file: 'docs/BOSS_PHONE_DESIGN_FIRMWARE.md', title: '板端固件设计',                    prefix: 'fw' },
  { file: 'docs/BOSS_PHONE_DESIGN_HUB.md',      title: 'PC 总机房设计',                   prefix: 'hub' },
  { file: 'docs/BOSS_PHONE_DESIGN_PLUGIN.md',   title: 'CLI 插件桥设计',                  prefix: 'plugin' },
  { file: 'docs/BOSS_PHONE_DESIGN_ANDROID.md',  title: '安卓 App 设计',                   prefix: 'android' },
  { file: 'docs/BOSS_PHONE_DESIGN_DEPLOYMENT.md', title: '部署与运维指南',                prefix: 'deploy' },
  { file: 'docs/BOSS_PHONE_DESIGN_TEST.md',     title: '测试与验收方案',                  prefix: 'test' },
  { file: 'docs/BOSS_PHONE_DESIGN_SECURITY.md', title: '安全设计',                        prefix: 'sec' },
];

// ---------- markdown 渲染 ----------
function slugify(s, prefix) {
  const slug = s
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^\p{L}\p{N}\-_]/gu, '')
    .slice(0, 60);
  return `${prefix}-${slug || 'sec'}`;
}

function renderDoc(content, prefix) {
  const md = new MarkdownIt({ html: true, linkify: true, breaks: false });
  md.use(anchor, { slugify: (s) => slugify(s, prefix), tabIndex: false });
  const defaultFence = md.renderer.rules.fence;
  md.renderer.rules.fence = (tokens, idx, options, env, slf) => {
    const t = tokens[idx];
    const info = t.info.trim();
    if (info === 'mermaid') {
      // 用独立类名 + data-src 存源码，避免 mermaid 自动渲染(startOnLoad)污染内容，
      // 渲染完全由浏览器端 evaluate 手动控制。
      return `<div class="mermaid-block" data-src="${md.utils.escapeHtml(t.content)}"></div>`;
    }
    if (info === 'svg') {
      // 原始 SVG 代码块 → 直接输出为 HTML，让浏览器渲染成图片（不再显示为代码）。
      return `<div class="svg-wrap">${t.content}</div>`;
    }
    return defaultFence(tokens, idx, options, env, slf);
  };
  const tokens = md.parse(content, {});
  const html = md.renderer.render(tokens, {}, {});
  // 收集标题用于目录
  const toc = [];
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type === 'heading_open') {
      const level = Number(tokens[i].tag.slice(1));
      const id = tokens[i].attrGet('id');
      const text = tokens[i + 1]?.content ?? '';
      toc.push({ level, id, text });
    }
  }
  return { html, toc };
}

// ---------- 组装 HTML ----------
function buildHtml(docs) {
  const body = [];
  const tocRows = [];
  docs.forEach((doc, di) => {
    const { html, toc } = renderDoc(fs.readFileSync(path.join(ROOT, doc.file), 'utf8'), doc.prefix);
    tocRows.push(`<li class="toc-doc"><a href="#${doc.prefix}-doc">${di + 1}. ${doc.title}</a></li>`);
    for (const h of toc) {
      if (h.level <= 2) {
        tocRows.push(`<li class="toc-h${h.level}"><a href="#${h.id}">${h.text}</a></li>`);
      }
    }
    body.push(`<section class="doc" id="${doc.prefix}-doc">\n${html}\n</section>`);
  });

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>BOSS PHONE 设计文档集</title>
<style>
  @page { size: A4; margin: 16mm 14mm 16mm 14mm; }
  * { box-sizing: border-box; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
    color: #1b1b2f; font-size: 12.5px; line-height: 1.7; margin: 0;
  }
  code, pre, .mermaid { font-family: Consolas, "Courier New", monospace; }
  h1 { font-size: 21px; margin: 0 0 10px; padding-bottom: 8px; border-bottom: 2px solid #7c5cfc; page-break-after: avoid; }
  h2 { font-size: 17px; margin: 22px 0 8px; color: #4a3aa8; border-left: 4px solid #7c5cfc; padding-left: 8px; page-break-after: avoid; }
  h3 { font-size: 14.5px; margin: 18px 0 6px; page-break-after: avoid; }
  h4 { font-size: 13px; margin: 14px 0 4px; }
  p { margin: 6px 0; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 11px; page-break-inside: auto; }
  th, td { border: 1px solid #c9c9df; padding: 4px 6px; text-align: left; vertical-align: top; }
  th { background: #ece7fb; font-weight: 700; }
  tr { page-break-inside: avoid; }
  pre {
    background: #f4f4fa; border: 1px solid #e2e2ef; border-radius: 6px;
    padding: 8px 10px; font-size: 11px; overflow: hidden; white-space: pre-wrap; word-break: break-word;
  }
  blockquote { border-left: 3px solid #bcbcd4; margin: 8px 0; padding: 2px 12px; color: #5b5b78; background: #f8f8fc; }
  hr { border: none; border-top: 1px solid #e2e2ef; margin: 16px 0; }
  .mermaid-block { display: flex; justify-content: center; margin: 10px 0; page-break-inside: avoid; }
  .mermaid-block svg, .mermaid-block .mermaid svg { max-width: 100%; height: auto; }
  .mermaid-error { color: #e5484d; border: 1px dashed #e5484d; padding: 6px; font-size: 11px; white-space: pre-wrap; }
  svg.svg-block { max-width: 100%; height: auto; margin: 8px auto; display: block; }
  .svg-wrap { display: flex; justify-content: center; margin: 10px 0; page-break-inside: avoid; }
  .svg-wrap svg { max-width: 100%; height: auto; }

  /* 封面 */
  .cover { text-align: center; padding: 60mm 0 0; page-break-after: always; }
  .cover .kicker { font-size: 13px; letter-spacing: 4px; color: #7c5cfc; font-weight: 700; }
  .cover h1 { font-size: 34px; border: none; margin: 14px 0 4px; }
  .cover .sub { font-size: 15px; color: #5b5b78; margin-bottom: 40px; }
  .cover .meta { font-size: 12px; color: #8a8aa8; line-height: 2; }

  /* 目录 */
  .toc-page { page-break-after: always; }
  .toc-page h2 { border: none; font-size: 20px; color: #1b1b2f; margin: 0 0 14px; }
  .toc-page ol { list-style: none; margin: 0; padding: 0; }
  .toc-page li { margin: 2px 0; }
  .toc-page a { text-decoration: none; color: #1b1b2f; display: block; }
  .toc-page .toc-doc a { font-weight: 700; font-size: 13.5px; margin-top: 10px; }
  .toc-page .toc-h2 a { padding-left: 18px; font-size: 12px; color: #4a4a68; }
  .toc-page a::after { content: target-counter(attr(href), page); float: right; color: #8a8aa8; }
  .toc-page .toc-doc a::after { color: #7c5cfc; font-weight: 700; }

  /* 文档章节 */
  .doc { page-break-before: always; }
  .doc:first-of-type { page-break-before: auto; }
</style>
</head>
<body>
  <section class="cover">
    <div class="kicker">BOSS PHONE</div>
    <h1>领导电话 · 设计文档集</h1>
    <div class="sub">远程指挥 AI Agent 的"领导手机" —— 设计文档合集</div>
    <div class="meta">
      硬件平台 FoloToy AI Passport (ESP32-C3)<br>
      配套 PC 总机房 · CLI 插件桥 · 安卓富终端<br>
      ${new Date().toISOString().slice(0, 10)} · 共 ${docs.length} 篇
    </div>
  </section>
  <section class="toc-page">
    <h2>目录</h2>
    <ol>
      ${tocRows.join('\n')}
    </ol>
  </section>
  ${body.join('\n')}
  <script>window.mermaid = { startOnLoad: false };</script>
  <script src="/tools/pdf-export/node_modules/mermaid/dist/mermaid.min.js"></script>
</body>
</html>`;
}

// ---------- 本地静态服务 ----------
const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.ttf': 'font/ttf',
  '.wasm': 'application/wasm', '.map': 'application/json',
};
function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
      if (urlPath.endsWith('/')) urlPath += 'index.html';
      const file = path.normalize(path.join(ROOT, urlPath));
      if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
      fs.readFile(file, (err, data) => {
        if (err) { res.writeHead(404).end('not found'); return; }
        const ext = path.extname(file).toLowerCase();
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

// ---------- 主流程 ----------
async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.mkdirSync(TMP_DIR, { recursive: true });
  const html = buildHtml(DOCS);
  const htmlPath = path.join(TMP_DIR, 'index.html');
  fs.writeFileSync(htmlPath, html, 'utf8');

  const server = await startServer();
  const port = server.address().port;
  const url = `http://127.0.0.1:${port}/tools/pdf-export/_out/index.html`;
  console.log('打开:', url);

  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  page.on('console', (m) => { if (m.type() === 'error') console.log('[browser]', m.text().slice(0, 300)); });
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 90000 });

  await page.evaluate(async () => {
    const m = window.mermaid;
    m.initialize({ startOnLoad: false, securityLevel: 'loose', theme: 'default' });
    const nodes = Array.from(document.querySelectorAll('.mermaid-block'));
    for (const el of nodes) {
      try {
        const id = 'mmd' + Math.random().toString(36).slice(2, 10);
        const { svg } = await m.render(id, el.dataset.src || '');
        el.innerHTML = svg;
      } catch (e) {
        el.classList.add('mermaid-error');
        el.dataset.err = String(e && e.message ? e.message : e);
        el.textContent = el.dataset.src || '';
      }
    }
  });
  const errs = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.mermaid-error')).map((el, i) => ({
      i,
      err: el.dataset.err || '?',
      src: (el.dataset.src || '').slice(0, 150),
    }))
  );
  console.log('mermaid 失败数量:', errs.length);
  for (const e of errs) console.log(`  [${e.i}] ${e.err} :: ${e.src}`);
  if (errs.length) {
    fs.writeFileSync(
      path.join(TMP_DIR, 'mermaid-errors.json'),
      JSON.stringify(
        await page.evaluate(() =>
          Array.from(document.querySelectorAll('.mermaid-error')).map((el, i) => ({
            i,
            err: el.dataset.err || '?',
            src: el.dataset.src || '',
          }))
        ),
        null,
        2
      ),
      'utf8'
    );
    console.log('失败源码已写入: _out/mermaid-errors.json');
  }

  const outPdf = path.join(OUT_DIR, 'BOSS_PHONE_设计文档集.pdf');
  await page.pdf({
    path: outPdf,
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="font-size:8px;color:#8a8aa8;width:100%;text-align:center;">BOSS PHONE 设计文档集 · 第 <span class="pageNumber"></span> / <span class="totalPages"></span> 页</div>',
    margin: { top: '18mm', bottom: '18mm', left: '14mm', right: '14mm' },
  });

  await browser.close();
  server.close();
  console.log('已导出:', outPdf);
}

main().catch((e) => { console.error(e); process.exit(1); });
