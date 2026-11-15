// 0단계 디버그 페이지 — 게임과 분리해서 원형질체 코어(WebGL2)를 돌리고 시험한다
//
//   stage0.html              보기
//   stage0.html?test=a0      A0 재생 시험 (멀티그리드를 numpy 와 대조)
//   stage0.html?test=parity  스텝 일치 시험 (규칙 1~7 을 numpy 와 대조)
//   stage0.html?test=a12&N=192&seed=1&cyc=2&steps=10000[&tri=1&variant=2]   A1·A2 긴 실행 (variant: tests.ts 의 VARIANTS 번호. 0 기준형)
//   stage0.html?run=1&N=384[&spf=2&tri=1]   그냥 돌려 보기 (spf = 프레임당 스텝 수)
//   stage0.html?bench=1[&N=256,384,512,768] A3 벤치마크 (스텝당 시간과 드로콜 수)
//
// 시험 결과는 window.__stage0 에도 남긴다(헤드리스 러너가 읽는다).

import { Glx } from '../gpu/plasm/glx';
import { PlasmGPU } from '../gpu/plasm/PlasmGPU';
import { defaultParams } from '../gpu/plasm/params';
import { runBench } from './bench';
import { testA0, testA12, testNoise, testParity, VARIANTS } from './tests';

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

const out = document.getElementById('out') as HTMLPreElement;
const nav = document.getElementById('nav') as HTMLDivElement;
const log = (line: string): void => {
  out.textContent += line + '\n';
};

async function main(): Promise<void> {
  window.__stage0 = { done: false, ok: false, result: null };
  const q = new URLSearchParams(location.search);
  nav.innerHTML = ['', '?run=1&N=384', '?bench=1', '?test=a0', '?test=parity'].map((s) => `<a href="stage0.html${s}">${s || '보기'}</a>`).join(' · ');

  // 캔버스 하나에는 WebGL2 컨텍스트만 만든다. 글자는 DOM 에 쓴다
  const canvas = document.getElementById('view') as HTMLCanvasElement;
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
    log('float 렌더 타깃(EXT_color_buffer_float)이 없어 돌릴 수 없습니다.');
    window.__stage0 = { done: true, ok: false, result: { caps }, error: 'no float targets' };
    return;
  }
  const glx = new Glx(gl);
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
  const num = (k: string, d: number): number => (q.has(k) ? Number(q.get(k)) : d);
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
  if (q.get('bench') === '1') {
    const sizes = (q.get('N') ?? '256,384,512,768').split(',').map(Number);
    log('벤치마크를 돌립니다. 끝날 때까지 이 탭을 앞에 두세요.');
    const bench = await runBench(glx, caps.renderer, sizes, log);
    log(`드로콜 하나의 고정 비용 약 ${bench.usPerTinyDraw.toFixed(1)}µs · 전체 ${bench.seconds.toFixed(0)}초`);
    const json = JSON.stringify(bench);
    const copy = document.createElement('button');
    copy.textContent = '결과 복사';
    copy.onclick = (): void => {
      navigator.clipboard.writeText(json).then(
        () => (copy.textContent = '복사했습니다'),
        () => (copy.textContent = '복사 실패 — 아래 글자를 직접 골라 복사해 주세요'),
      );
    };
    nav.after(copy);
    log('\n끝났습니다. 위의 "결과 복사" 단추를 누르거나 아래 JSON 을 그대로 복사해 붙여 주세요.\n');
    log(json);
    window.__stage0 = { done: true, ok: true, result: { caps, bench } };
    return;
  }
  if (q.get('run') === '1') {
    const sim = new PlasmGPU(glx, defaultParams({ N: num('N', 384), seed: num('seed', 1), mgCycles: num('cyc', 2), triK: q.get('tri') === '1' ? (2 * Math.PI) / 100 : 0 }));
    const spf = num('spf', 1);
    const status = document.createElement('div');
    nav.after(status);
    const frame = (): void => {
      for (let i = 0; i < spf; i++) sim.stepOnce();
      sim.view(canvas.width, canvas.height);
      if (sim.step % 60 < spf) status.textContent = `스텝 ${sim.step} · 모델 시간 ${(sim.step * sim.params.dt).toFixed(0)}`;
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
    window.__stage0 = { done: true, ok: true, result: { caps } };
    return;
  }
  log('위의 링크에서 시험을 고르세요.');
  window.__stage0 = { done: true, ok: true, result: { caps } };
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  log(`오류: ${msg}`);
  window.__stage0 = { done: true, ok: false, result: null, error: msg };
});
