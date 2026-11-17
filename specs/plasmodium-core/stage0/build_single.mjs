// 시험 페이지를 파일 하나짜리 HTML 로 만든다 (스크립트를 안에 넣는다). 서버 없이 브라우저에서 바로 열 수 있다.
//   node specs/plasmodium-core/stage0/build_single.mjs <출력 폴더>
// numpy 기준 자료가 필요한 시험 모드(?test=…)는 이 파일에서 돌지 않는다. 돌려 보기와 속도 측정만 된다.
import { build } from 'vite';
import fs from 'node:fs';
import path from 'node:path';

const out = path.resolve(process.argv[2] ?? 'dist-single');
const tmp = path.join(out, 'tmp');
await build({
  configFile: false,
  base: './',
  logLevel: 'warn',
  publicDir: false,
  build: { outDir: tmp, emptyOutDir: true, modulePreload: false, rollupOptions: { input: 'stage0.html' } },
});
let html = fs.readFileSync(path.join(tmp, 'stage0.html'), 'utf8');
const m = html.match(/<script type="module"[^>]*src="\.\/(assets\/[^"]+)"><\/script>/);
if (!m) throw new Error('스크립트 태그를 찾지 못했다');
const js = fs.readFileSync(path.join(tmp, m[1]), 'utf8');
if (/import\s*["'(]|from\s*["']\.\//.test(js)) throw new Error('묶음이 다른 파일을 불러온다 (한 파일로 묶이지 않았다)');
html = html.replace(m[0], () => `<script type="module">\n${js.replace(/<\/script/g, '<\\/script')}\n</script>`);
const file = path.join(out, 'theblob-stage0.html');
fs.writeFileSync(file, html);
fs.rmSync(tmp, { recursive: true });
console.log(file, `${(html.length / 1024).toFixed(0)} KB`);
