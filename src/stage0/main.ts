// 0단계 시험 페이지 — 게임과 분리해서 원형질체 코어(WebGL2)를 돌리고 시험한다
//
//   stage0.html                       돌려 보기 + 속도 측정 단추
//   stage0.html?run=1&N=384&spf=2[&tri=1]   돌려 보기의 처음 설정 (spf = 프레임당 스텝 수)
//   stage0.html?bench=1[&N=256,384,512,768] 열자마자 속도 측정(A3)을 시작한다. 주소 끝에 #bench 를 붙여도 같다
//   stage0.html?test=a0               A0 재생 시험 (멀티그리드를 numpy 와 대조)
//   stage0.html?test=parity           스텝 일치 시험 (규칙 1~7 을 numpy 와 대조)
//   stage0.html?test=a12&N=192&seed=1&cyc=2&steps=10000[&tri=1&variant=2]   A1·A2 긴 실행 (variant: tests.ts 의 VARIANTS 번호. 0 기준형)
//
// 시험 결과는 window.__stage0 에도 남긴다(헤드리스 러너가 읽는다).

import { Glx } from '../gpu/plasm/glx';
import { PlasmGPU } from '../gpu/plasm/PlasmGPU';
import { defaultParams } from '../gpu/plasm/params';
import { CELLS_PER_STEP, MAP_PX, runBench, STEPS_PER_PULSE, type BenchResult } from './bench';
import { REF_BASE } from './refData';
import { applyVariant, testA0, testA12, testNoise, testParity, VARIANTS } from './tests';

interface Stage0State {
  done: boolean;
  ok: boolean;
  result: unknown;
  error?: string;
}

declare global {
  interface Window {
    __stage0: Stage0State;
  }
}

const el = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;
const out = el<HTMLPreElement>('out');
const nav = el<HTMLDivElement>('nav');
const log = (line: string): void => {
  out.textContent += line + '\n';
};

/** 돌려 보기에 쓰는 계산 방식: 결과가 같은 것 중 가장 싼 것 */
const FAST = VARIANTS[3];
const GRIDS = [256, 384, 512];
const SPFS = [1, 2, 4, 8, 16];

/** 고르는 단추 한 줄. 누르면 pick 을 부르고 눌린 단추를 표시한다 */
function choices<T>(rowId: string, items: T[], label: (v: T) => string, initial: T, pick: (v: T) => void): void {
  const row = el<HTMLDivElement>(rowId);
  const buttons = items.map((v) => {
    const b = document.createElement('button');
    b.textContent = label(v);
    b.setAttribute('aria-pressed', String(v === initial));
    b.onclick = (): void => {
      buttons.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      pick(v);
    };
    row.append(b);
    return b;
  });
}

function tile(label: string, unit: string): (text: string) => void {
  const box = document.createElement('div');
  box.className = 'tile';
  const value = document.createElement('b');
  value.textContent = '–';
  const small = document.createElement('small');
  small.textContent = unit ? `${label} (${unit})` : label;
  box.append(value, small);
  el<HTMLDivElement>('tiles').append(box);
  return (text) => {
    value.textContent = text;
  };
}

function benchTable(bench: BenchResult): void {
  const rows = bench.rows.filter((r) => r.cycles === 2);
  const best = new Map<number, number>();
  for (const r of rows) best.set(r.N, Math.min(best.get(r.N) ?? Infinity, r.msPerStep));
  const table = document.createElement('table');
  const head = table.insertRow();
  for (const h of ['격자', '계산 방식', '드로콜', 'ms/스텝', '프레임당 스텝', '전진 px/s']) {
    const th = document.createElement('th');
    th.textContent = h;
    head.append(th);
  }
  for (const r of rows) {
    const tr = table.insertRow();
    if (r.msPerStep === best.get(r.N)) tr.className = 'best';
    for (const c of [`${r.N}²`, r.variant, String(r.drawCalls), r.msPerStep.toFixed(2), r.stepsPerFrame.toFixed(1), r.pxPerSec.toFixed(0)]) tr.insertCell().textContent = c;
  }
  const note = document.createElement('p');
  note.className = 'lead';
  note.textContent = '프레임당 스텝은 한 프레임에 4ms 를 쓴다고 볼 때의 값이고, 전진 속도는 게임 지도(1500px) 기준입니다. 주황색 줄이 격자마다 가장 빠른 방식입니다.';
  el<HTMLDivElement>('benchTable').replaceChildren(table, note);
}

async function main(): Promise<void> {
  window.__stage0 = { done: false, ok: false, result: null };
  const q = new URLSearchParams(location.search);

  // 캔버스 하나에는 WebGL2 컨텍스트만 만든다. 글자는 DOM 에 쓴다
  const canvas = el<HTMLCanvasElement>('view');
  const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, preserveDrawingBuffer: true });
  if (!gl) {
    log('이 브라우저는 WebGL2 를 지원하지 않습니다.');
    window.__stage0 = { done: true, ok: false, result: null, error: 'no webgl2' };
    return;
  }
  const caps = Glx.caps(gl);
  log(`GPU: ${caps.renderer}`);
  log(`float 렌더 타깃 ${caps.colorBufferFloat ? '지원' : '미지원'} · 다중 타깃 ${caps.maxDrawBuffers} · 타이머 질의 ${caps.timerQuery ? '지원' : '미지원'}`);
  if (!caps.colorBufferFloat) {
    log('이 기기의 GPU 는 실수(float) 텍스처에 그리는 기능(EXT_color_buffer_float)이 없어 코어를 돌릴 수 없습니다. 위의 GPU 이름을 알려 주세요.');
    window.__stage0 = { done: true, ok: false, result: { caps }, error: 'no float targets' };
    return;
  }
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    log('GPU 컨텍스트를 잃었습니다(메모리 부족일 수 있습니다). 페이지를 새로 열고 더 작은 격자로 해 보세요.');
    window.__stage0 = { done: true, ok: false, result: { caps }, error: 'context lost' };
  });
  const glx = new Glx(gl);
  const num = (k: string, d: number): number => (q.has(k) ? Number(q.get(k)) : d);

  // ── 시험 모드 (numpy 기준 자료가 필요하다) ──
  const test = q.get('test');
  if (test === 'a0') {
    const noise = testNoise(log);
    const a0 = await testA0(glx, log);
    window.__stage0 = { done: true, ok: noise.pass && a0.pass, result: { caps, noise, a0 } };
    return;
  }
  if (test === 'parity') {
    const parity = [];
    for (const v of VARIANTS) parity.push(await testParity(glx, log, v));
    window.__stage0 = { done: true, ok: parity.every((p) => p.pass), result: { caps, parity } };
    return;
  }
  if (test === 'a12') {
    const a12 = await testA12(
      glx,
      { N: num('N', 192), seed: num('seed', 1), cycles: num('cyc', 2), steps: num('steps', 10000), tri: q.get('tri') === '1', checkEvery: num('check', 50), variant: num('variant', 0) },
      log,
      (sim) => sim.view(canvas.width, canvas.height),
    );
    window.__stage0 = { done: true, ok: !a12.nan && a12.stepsDone === a12.steps, result: { caps, a12 } };
    return;
  }

  // ── 돌려 보기 + 속도 측정 ──
  let gridN = num('N', 384);
  if (q.get('bench') === '1' || !GRIDS.includes(gridN)) gridN = 384;
  let spf = SPFS.includes(num('spf', 2)) ? num('spf', 2) : 2;
  let tri = q.get('tri') === '1';
  let sim: PlasmGPU | null = null;
  let raf = 0;

  el('controls').hidden = false;
  el('tiles').hidden = false;
  el('benchBox').hidden = false;
  const setFps = tile('화면 갱신', '초당 프레임');
  const setSps = tile('계산 속도', '초당 스텝');
  const setPx = tile('전진 속도', '게임 지도 기준 px/s');
  const setPulse = tile('맥동 주기', '초');
  const setDraws = tile('스텝당 드로콜', '');
  const setTime = tile('모델 시간', '');

  const startRun = (): void => {
    cancelAnimationFrame(raf);
    glx.reset();
    const s = new PlasmGPU(glx, defaultParams({ N: gridN, seed: 1, triK: tri ? (2 * Math.PI) / 100 : 0 }));
    applyVariant(s, FAST);
    sim = s;
    let frames = 0, steps = 0, draws0 = glx.drawCalls, t0 = performance.now();
    const frame = (): void => {
      if (sim !== s) return;
      for (let i = 0; i < spf; i++) s.stepOnce();
      s.view(canvas.width, canvas.height);
      frames++;
      steps += spf;
      const now = performance.now();
      if (now - t0 >= 500) {
        const sec = (now - t0) / 1000;
        const sps = steps / sec;
        setFps((frames / sec).toFixed(0));
        setSps(sps.toFixed(0));
        setPx((CELLS_PER_STEP * sps * (MAP_PX / s.N)).toFixed(1));
        setPulse((STEPS_PER_PULSE / sps).toFixed(2));
        setDraws(((glx.drawCalls - draws0 - frames) / steps).toFixed(0));
        setTime((s.step * s.params.dt).toFixed(0));
        frames = 0;
        steps = 0;
        draws0 = glx.drawCalls;
        t0 = now;
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
  };

  choices('gridRow', GRIDS, (n) => `${n}²`, gridN, (n) => {
    gridN = n;
    startRun();
  });
  choices('spfRow', SPFS, String, spf, (n) => {
    spf = n;
  });
  choices('triRow', [false, true], (on) => (on ? '삼각 격자' : '끔'), tri, (on) => {
    tri = on;
    startRun();
  });

  const benchStart = el<HTMLButtonElement>('benchStart');
  const benchCopy = el<HTMLButtonElement>('benchCopy');
  let benchJson = '';
  benchCopy.onclick = (): void => {
    navigator.clipboard.writeText(benchJson).then(
      () => (benchCopy.textContent = '복사했습니다'),
      () => (benchCopy.textContent = '복사가 막혔습니다 — 아래 글자를 직접 골라 복사해 주세요'),
    );
  };
  const startBench = async (sizes: number[]): Promise<void> => {
    benchStart.disabled = true;
    benchStart.textContent = '재는 중…';
    cancelAnimationFrame(raf);
    sim = null;
    try {
      const bench = await runBench(glx, caps.renderer, sizes, log);
      log(`드로콜 하나의 고정 비용 약 ${bench.usPerTinyDraw.toFixed(1)}µs · 전체 ${bench.seconds.toFixed(0)}초`);
      benchJson = JSON.stringify(bench);
      benchTable(bench);
      benchCopy.hidden = false;
      benchCopy.textContent = '결과 복사';
      log('\n끝났습니다. "결과 복사" 단추를 누르거나 아래 JSON 을 그대로 복사해 대화창에 붙여 주세요.\n');
      log(benchJson);
      window.__stage0 = { done: true, ok: true, result: { caps, bench } };
    } finally {
      benchStart.disabled = false;
      benchStart.textContent = '다시 재기';
      startRun();
    }
  };
  benchStart.onclick = (): void => {
    void startBench([256, 384, 512, 768]).catch(fail);
  };

  // 시험 모드 링크는 numpy 기준 자료가 함께 올라가 있을 때만 보인다
  fetch(`${REF_BASE}manifest.json`).then(
    (r) => {
      if (r.ok) nav.innerHTML = '개발용 시험: ' + ['?test=a0', '?test=parity', '?test=a12&N=192&steps=2000'].map((s) => `<a href="stage0.html${s}">${s}</a>`).join(' · ');
    },
    () => undefined,
  );

  if (q.get('bench') === '1' || location.hash === '#bench') {
    await startBench((q.get('N') ?? '256,384,512,768').split(',').map(Number));
    return;
  }
  startRun();
  window.__stage0 = { done: true, ok: true, result: { caps } };
}

function fail(e: unknown): void {
  const msg = e instanceof Error ? e.message : String(e);
  log(`오류: ${msg}`);
  window.__stage0 = { done: true, ok: false, result: null, error: msg };
}

main().catch(fail);
