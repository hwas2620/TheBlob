// 0단계 시험 페이지 — 게임과 분리해서 원형질체 코어(WebGL2)를 돌리고 시험한다
//
//   stage0.html                       돌려 보기 + 속도 측정 단추
//   stage0.html?run=1&N=384&spf=2[&tri=1]   돌려 보기의 처음 설정 (spf = 프레임당 스텝 수)
//   stage0.html?bench=1[&N=256,384,512,768] 열자마자 속도 측정(A3)을 시작한다. 주소 끝에 #bench 를 붙여도 같다
//                                     (&block=2&blocks=1 을 붙이면 드로콜 수만 볼 만큼 짧게 잰다)
//   stage0.html?test=a0               A0 재생 시험 (멀티그리드를 numpy 와 대조)
//   stage0.html?test=parity           스텝 일치 시험 (규칙 1~7 을 numpy 와 대조)
//   stage0.html?test=a12&N=192&seed=1&cyc=2&steps=10000[&tri=1&variant=2&sync=1]   A1·A2 긴 실행 (variant: tests.ts 의 VARIANTS 번호. 0 기준형)
//                                     (&dt=0.2&period=8&sub=8&tag=dt2p8 처럼 설정을 덮어쓸 수 있다)
//
// 시험 결과는 window.__stage0 에도 남긴다(헤드리스 러너가 읽는다).

import { Glx } from '../gpu/plasm/glx';
import { PlasmGPU } from '../gpu/plasm/PlasmGPU';
import { defaultParams } from '../gpu/plasm/params';
import { benchSummary, bestHeld, CELLS_PER_STEP, heldLabel, MAP_PX, runBench, STEPS_PER_PULSE, type BenchResult } from './bench';
import { countingGl } from './glCount';
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
/**
 * 한 스텝이 가는 모델 시간을 늘린 후보 설정: dt 와 맥동 주기를 함께 2배로 (6차 실험 V1).
 * 스텝당 전진이 기준의 약 FAST_DT_GAIN 배다(유인원에 닿는 시각으로 잰 값. 무게중심으로 재면 더 작다). 기본 설정은 아니다
 */
const FAST_DT = { dt: 0.2, period: 8, substeps: 8 };
const FAST_DT_GAIN = 1.7;

/** 고르는 단추 한 줄. 누르면 pick 을 부르고 눌린 단추를 표시한다. 만든 단추들을 돌려준다 */
function choices<T>(rowId: string, items: T[], label: (v: T) => string, initial: T, pick: (v: T) => void): HTMLButtonElement[] {
  const row = el<HTMLDivElement>(rowId);
  const buttons = items.map((v) => {
    const b = document.createElement('button');
    b.textContent = label(v);
    b.setAttribute('aria-pressed', String(v === initial));
    b.onclick = (): void => {
      buttons.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      try {
        pick(v);
      } catch (e) {
        fail(e); // 큰 격자에서 메모리가 모자라면 여기로 온다
      }
    };
    row.append(b);
    return b;
  });
  return buttons;
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
  for (const h of ['격자', '계산 방식', '패스', 'ms/스텝', '풀이 한 번', '프레임당 스텝', '전진 px/s']) {
    const th = document.createElement('th');
    th.textContent = h;
    head.append(th);
  }
  for (const r of rows) {
    const tr = table.insertRow();
    if (r.msPerStep === best.get(r.N)) tr.className = 'best';
    for (const c of [`${r.N}²`, r.variant, String(r.passes), r.msPerStep.toFixed(2), r.msSolve.toFixed(2), r.stepsPerFrame.toFixed(1), r.pxPerSec.toFixed(0)]) tr.insertCell().textContent = c;
  }
  const note = document.createElement('p');
  note.className = 'lead';
  note.textContent = '패스는 드로콜에 타깃을 지우는 횟수를 더한 수입니다. 프레임당 스텝은 한 프레임에 4ms 를 쓴다고 볼 때의 값이고, 전진 속도는 게임 지도(1500px) 기준입니다. 주황색 줄이 격자마다 가장 빠른 방식입니다.';
  const parts: HTMLElement[] = [];
  const loop = bench.frameLoop;
  if (loop && loop.rows.length > 0) {
    // 게임과 같은 꼴의 루프에서 잰 값. 게임에서 쓸 수 있는 속도는 이쪽이다
    const held = bestHeld(loop);
    const lt = document.createElement('table');
    lt.className = 'loop';
    const lh = lt.insertRow();
    for (const h of ['프레임당 스텝', '프레임 간격 ms', '초당 프레임', '초당 스텝', '전진 px/s']) {
      const th = document.createElement('th');
      th.textContent = h;
      lh.append(th);
    }
    for (const r of loop.rows) {
      const tr = lt.insertRow();
      if (r === held) tr.className = 'best';
      for (const c of [String(r.spf), r.msMean.toFixed(1), (1000 / r.msMean).toFixed(0), r.stepsPerSec.toFixed(0), (CELLS_PER_STEP * r.stepsPerSec * (MAP_PX / loop.N)).toFixed(0)]) tr.insertCell().textContent = c;
    }
    const ln = document.createElement('p');
    ln.className = 'lead';
    ln.textContent = `프레임 루프 (${loop.N}², 가장 빠른 계산 방식): 게임처럼 화면 갱신마다 스텝을 돌리며 잰 값입니다. 주황색 줄이 ${heldLabel(loop)}을 지키면서 가장 빠른 설정입니다.${held ? '' : ' (지킨 설정이 없습니다)'} 아래 표는 일을 몰아서 시켰을 때의 스텝당 시간입니다.`;
    parts.push(lt, ln);
  }
  el<HTMLDivElement>('benchTable').replaceChildren(...parts, table, note);
}

async function main(): Promise<void> {
  window.__stage0 = { done: false, ok: false, result: null };
  const q = new URLSearchParams(location.search);

  // 캔버스 하나에는 WebGL2 컨텍스트만 만든다. 글자는 DOM 에 쓴다
  const canvas = el<HTMLCanvasElement>('view');
  const glReal = canvas.getContext('webgl2', { antialias: false, alpha: false, preserveDrawingBuffer: true });
  if (!glReal) {
    log('이 브라우저는 WebGL2 를 지원하지 않습니다.');
    window.__stage0 = { done: true, ok: false, result: null, error: 'no webgl2' };
    return;
  }
  // count=1 이면 GL 호출을 세는 껍데기를 씌운다 (느려지므로 호출 수를 볼 때만)
  const counting = q.get('count') === '1' ? countingGl(glReal) : null;
  const gl = counting ? counting.gl : glReal;
  const caps = Glx.caps(gl);
  log(`GPU: ${caps.renderer}`);
  log(`float 렌더 타깃 ${caps.colorBufferFloat ? '지원' : '미지원'} · 다중 타깃 ${caps.maxDrawBuffers} · 타이머 질의 ${caps.timerQuery ? '지원' : '미지원'}`);
  if (!caps.colorBufferFloat) {
    log('이 기기의 GPU 는 실수(float) 텍스처에 그리는 기능(EXT_color_buffer_float)이 없어 코어를 돌릴 수 없습니다. 위의 GPU 이름을 알려 주세요.');
    window.__stage0 = { done: true, ok: false, result: { caps }, error: 'no float targets' };
    return;
  }
  const glx = new Glx(gl);
  let raf = 0;
  // 복원을 요청하지 않는다(preventDefault 를 부르지 않는다). 복원되면 이전 텍스처와 프로그램이 모두 죽은 객체라
  // 오류 없이 빈 값만 나온다. 잃으면 멈추고 새로 열게 한다
  canvas.addEventListener('webglcontextlost', () => {
    glx.markLost();
    cancelAnimationFrame(raf);
    log('GPU 컨텍스트를 잃었습니다(메모리 부족, 드라이버 재시작, 탭이 오래 뒤에 있었을 때 생깁니다). 페이지를 새로 열어 주세요. 되풀이되면 더 작은 격자로 해 보세요.');
    window.__stage0 = { done: true, ok: false, result: { caps }, error: 'context lost' };
  });
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
    // dt, period, eps, sub 를 주면 기본 설정을 덮어쓴다 (tag 는 그 설정의 이름)
    const over: { dt?: number; period?: number; eps?: number; substeps?: number } = {};
    if (q.has('dt')) over.dt = num('dt', 0.1);
    if (q.has('period')) over.period = num('period', 4);
    if (q.has('eps')) over.eps = num('eps', 0.1);
    if (q.has('sub')) over.substeps = num('sub', 4);
    const a12 = await testA12(
      glx,
      { N: num('N', 192), seed: num('seed', 1), cycles: num('cyc', 2), steps: num('steps', 10000), tri: q.get('tri') === '1', checkEvery: num('check', 50), variant: num('variant', 0), syncBounds: q.get('sync') === '1', over, tag: q.get('tag') ?? undefined },
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
  let fastDt = q.get('fast') === '1';
  let sim: PlasmGPU | null = null;

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
    const s = new PlasmGPU(glx, defaultParams({ N: gridN, seed: 1, triK: tri ? (2 * Math.PI) / 100 : 0, ...(fastDt ? FAST_DT : {}) }));
    applyVariant(s, FAST);
    sim = s;
    const gain = fastDt ? FAST_DT_GAIN : 1;
    let frames = 0, steps = 0, draws0 = glx.drawCalls, t0 = performance.now();
    const frame = (): void => {
      if (sim !== s || glx.lost()) return;
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
        setPx((CELLS_PER_STEP * gain * sps * (MAP_PX / s.N)).toFixed(1));
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

  // 격자와 무늬 단추는 시뮬레이션을 새로 만든다(앞의 GL 자원을 지운다). 속도를 재는 동안에는 잠근다
  const rebuilders = [
    ...choices('gridRow', GRIDS, (n) => `${n}²`, gridN, (n) => {
      gridN = n;
      startRun();
    }),
    ...choices('triRow', [false, true], (on) => (on ? '삼각 격자' : '끔'), tri, (on) => {
      tri = on;
      startRun();
    }),
    ...choices('dtRow', [false, true], (on) => (on ? '2배 (시험 중)' : '기본'), fastDt, (on) => {
      fastDt = on;
      startRun();
    }),
  ];
  choices('spfRow', SPFS, String, spf, (n) => {
    spf = n;
  });

  const benchStart = el<HTMLButtonElement>('benchStart');
  const benchCopy = el<HTMLButtonElement>('benchCopy');
  const benchText = el<HTMLTextAreaElement>('benchText');
  // 글 상자를 누르면 전부 선택된다. 복사 단추가 막힌 곳(앱 안의 미리 보기 등)에서는 그대로 Ctrl/⌘+C 를 누르면 된다
  benchText.onfocus = (): void => benchText.select();
  benchCopy.onclick = (): void => {
    const failed = (): void => {
      benchText.focus();
      benchText.select();
      benchCopy.textContent = '복사가 막혔습니다 — 글 상자가 선택돼 있으니 Ctrl/⌘+C 를 눌러 주세요';
    };
    if (!navigator.clipboard) failed();
    else navigator.clipboard.writeText(benchText.value).then(() => (benchCopy.textContent = '복사했습니다'), failed);
  };
  const startBench = async (sizes: number[]): Promise<void> => {
    benchStart.disabled = true;
    benchStart.textContent = '재는 중…';
    rebuilders.forEach((b) => (b.disabled = true));
    cancelAnimationFrame(raf);
    sim = null;
    try {
      const opt = (k: string): number | undefined => (q.has(k) && Number.isFinite(num(k, NaN)) ? num(k, NaN) : undefined);
      const bench = await runBench(glx, caps.renderer, sizes, log, { block: opt('block'), blocks: opt('blocks'), glCounts: counting?.counts, view: (s) => s.view(canvas.width, canvas.height) });
      log(`드로콜 하나의 고정 비용 약 ${bench.usPerTinyDraw.toFixed(1)}µs · 전체 ${bench.seconds.toFixed(0)}초`);
      // 요약(사람이 읽는 줄)과 전체 JSON 을 한 글 상자에 넣는다
      // 붙여 넣기 쉽게 수는 소수 셋째 자리까지만 적는다
      benchText.value = `${benchSummary(bench)}\n\n${JSON.stringify(bench, (_k, v: unknown) => (typeof v === 'number' ? Math.round(v * 1000) / 1000 : v))}`;
      benchText.hidden = false;
      benchTable(bench);
      benchCopy.hidden = false;
      benchCopy.textContent = '결과 복사';
      if (bench.errors.length > 0) log(`끝까지 재지 못한 격자: ${bench.errors.join(' / ')} — 나머지 결과는 글 상자에 있습니다.`);
      log('\n끝났습니다. "결과 복사" 단추를 누르거나, 글 상자를 눌러(전부 선택됩니다) 복사해서 대화창에 붙여 주세요.');
      window.__stage0 = { done: true, ok: true, result: { caps, bench } };
    } finally {
      benchStart.disabled = false;
      benchStart.textContent = '다시 재기';
      rebuilders.forEach((b) => (b.disabled = false));
      if (!glx.lost()) {
        try {
          startRun();
        } catch (e) {
          fail(e);
        }
      }
    }
  };
  benchStart.onclick = (): void => {
    void startBench([256, 384, 512, 768]).catch(fail);
  };

  // 시험 모드 링크는 numpy 기준 자료가 함께 올라가 있을 때만 보인다 (파일로 연 페이지에는 없다)
  if (location.protocol.startsWith('http')) {
    fetch(`${REF_BASE}manifest.json`).then(
      (r) => {
        if (r.ok) nav.innerHTML = '개발용 시험: ' + ['?test=a0', '?test=parity', '?test=a12&N=192&steps=2000'].map((s) => `<a href="stage0.html${s}">${s}</a>`).join(' · ');
      },
      () => undefined,
    );
  }

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
