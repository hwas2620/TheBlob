#!/usr/bin/env node
// 0단계 디버그 페이지를 헤드리스 Chromium 으로 돌리고 결과를 모은다.
//
//   npm run build
//   node specs/plasmodium-core/stage0/run_stage0.cjs <이름> "<쿼리>" [제한 시간(초)]
//   예) node specs/plasmodium-core/stage0/run_stage0.cjs a0 "test=a0"
//
// dist/ 를 작은 정적 서버로 띄우고 stage0.html?<쿼리> 를 연 뒤 window.__stage0.done 을 기다린다.
// 결과 JSON 은 results/<이름>.json, 화면 갈무리는 screenshots/stage0-<이름>.png 에 쓴다.
// 페이지가 보내는 상태 덤프(POST /__dump/<실행>/<파일>. 관문 B 의 ?test=b&dump=1)는 STAGE0_DUMP 폴더(기본 dumps/)에 그대로 쓴다.
// 이 컨테이너의 Chromium 은 소프트웨어 렌더러(SwiftShader)라서 시간 수치는 참고용이다.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..', '..');
// STAGE0_DIST 로 다른 빌드 폴더를 가리킬 수 있다 (긴 실행이 dist/ 를 쓰는 동안 개발용 빌드를 따로 시험할 때)
const DIST = process.env.STAGE0_DIST ? path.resolve(process.env.STAGE0_DIST) : path.join(ROOT, 'dist');
// 덤프는 크다(192² 한 장 3MB). 저장소에 넣지 않는다(.gitignore). metrics/gpu2run.py 가 numpy 실행과 같은 꼴로 바꾼 뒤 지운다
const DUMP = process.env.STAGE0_DUMP ? path.resolve(process.env.STAGE0_DUMP) : path.join(__dirname, 'dumps');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.gz': 'application/octet-stream', '.svg': 'image/svg+xml' };

function serve() {
  const server = http.createServer((req, res) => {
    let rel;
    try {
      rel = decodeURIComponent(req.url.split('?')[0]);
    } catch {
      rel = '\0';
    }
    if (rel.includes('\0')) {
      res.writeHead(400);
      res.end('bad path');
      return;
    }
    if (req.method === 'POST' && rel.startsWith('/__dump/')) {
      const file = path.join(DUMP, rel.slice('/__dump/'.length));
      if (!file.startsWith(DUMP + path.sep)) {
        res.writeHead(400);
        res.end('bad path');
        return;
      }
      fs.mkdirSync(path.dirname(file), { recursive: true });
      const out = fs.createWriteStream(file);
      req.pipe(out);
      out.on('finish', () => {
        res.writeHead(200);
        res.end('ok');
      });
      out.on('error', (e) => {
        res.writeHead(500);
        res.end(String(e));
      });
      return;
    }
    const file = path.join(DIST, rel === '/' ? 'index.html' : rel);
    if (!file.startsWith(DIST) || !fs.existsSync(file)) {
      res.writeHead(404);
      res.end('not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

(async () => {
  const [name, query = '', timeoutSec = '600'] = process.argv.slice(2);
  if (!name) {
    console.error('usage: run_stage0.cjs <이름> "<쿼리>" [제한 시간(초)]');
    process.exit(2);
  }
  if (!fs.existsSync(path.join(DIST, 'stage0.html'))) {
    console.error('dist/stage0.html 이 없다. 먼저 npm run build');
    process.exit(2);
  }
  const server = await serve();
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') console.log(`[브라우저 ${m.type()}] ${m.text()}`);
  });
  page.on('pageerror', (e) => console.log(`[브라우저 오류] ${e.message}`));
  const t0 = Date.now();
  // 'commit' 까지만 기다린다. 큰 격자의 기준형은 첫 100스텝이 30초를 넘어 load 이벤트가 늦게 온다
  await page.goto(`http://127.0.0.1:${port}/stage0.html?${query}`, { waitUntil: 'commit' });
  await page.waitForFunction(() => document.getElementById('out') !== null, null, { timeout: 0 });
  let state = null;
  let printed = 0;
  const deadline = t0 + Number(timeoutSec) * 1000;
  for (;;) {
    const text = await page.evaluate(() => document.getElementById('out').textContent);
    if (text.length > printed) {
      process.stdout.write(text.slice(printed));
      printed = text.length;
    }
    state = await page.evaluate(() => window.__stage0);
    if (state && state.done) break;
    if (Date.now() > deadline) {
      console.log('\n제한 시간 초과');
      break;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  // 끝났다는 표시와 마지막 글 사이에 적힌 줄을 마저 찍는다
  const rest = await page.evaluate(() => document.getElementById('out').textContent);
  if (rest.length > printed) process.stdout.write(rest.slice(printed));
  // 속도 측정이면 글 상자의 요약(사용자가 복사해 붙이는 것의 앞부분)도 찍는다
  const summary = await page.evaluate(() => {
    const t = document.getElementById('benchText');
    return t && t.value ? t.value.split('\n\n{')[0] : '';
  });
  if (summary) console.log(`\n── 글 상자의 요약 ──\n${summary}`);
  const outDir = path.join(__dirname, 'results');
  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(path.join(ROOT, 'screenshots'), { recursive: true });
  fs.writeFileSync(path.join(outDir, `${name}.json`), JSON.stringify({ name, query, seconds: (Date.now() - t0) / 1000, ...state }, null, 1));
  await page.screenshot({ path: path.join(ROOT, 'screenshots', `stage0-${name}.png`), timeout: 120000 }).catch((e) => console.log(`(화면 갈무리 실패: ${e.message.split('\n')[0]})`));
  await browser.close();
  server.close();
  console.log(`\n${name}: ${state && state.done ? (state.ok ? '통과' : '실패') : '끝나지 않음'} (${((Date.now() - t0) / 1000).toFixed(1)}초)`);
  process.exit(state && state.done && state.ok ? 0 : 1);
})();
