// 0단계 디버그 페이지 — 게임과 분리해서 원형질체 코어(WebGL2)를 돌리고 시험한다
//
//   stage0.html              보기
//   stage0.html?test=a0      A0 재생 시험 (멀티그리드를 numpy 와 대조)
//
// 시험 결과는 window.__stage0 에도 남긴다(헤드리스 러너가 읽는다).

import { Glx } from '../gpu/plasm/glx';
import { testA0, testNoise } from './tests';

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
  nav.innerHTML = ['', '?test=a0'].map((s) => `<a href="stage0.html${s}">${s || '보기'}</a>`).join(' · ');

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
  log('위의 링크에서 시험을 고르세요.');
  window.__stage0 = { done: true, ok: true, result: { caps } };
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  log(`오류: ${msg}`);
  window.__stage0 = { done: true, ok: false, result: null, error: msg };
});
