// 정맥(vein) 프래그먼트 셰이더 — .glsl + 플레이스홀더 치환

import veinsFragSrc from './glsl/veins.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';
import { VEINS } from '../../config';

const V = VEINS;

export const VEINS_FRAG = resolveShader(veinsFragSrc, {
  VEIN_MIN: V.MIN.toFixed(1),
  VEIN_MAX: V.MAX.toFixed(1),
  HESSIAN_STEP: V.HESSIAN_STEP.toFixed(1),
  RIDGE_THRESHOLD: V.RIDGE_THRESHOLD.toFixed(3),
  RIDGE_SATURATE: V.RIDGE_SATURATE.toFixed(3),
  // 계층화
  MAJOR_THRESHOLD: V.MAJOR_THRESHOLD.toFixed(1),
  MAJOR_ALPHA: V.MAJOR_ALPHA.toFixed(2),
  MINOR_ALPHA: V.MINOR_ALPHA.toFixed(2),
  // 맥동
  PULSE_MIN: V.PULSE_MIN.toFixed(2),
  PULSE_MAX: V.PULSE_MAX.toFixed(2),
  // 색상 — 주정맥
  MAJOR_R: V.MAJOR_COLOR.r.toFixed(3),
  MAJOR_G: V.MAJOR_COLOR.g.toFixed(3),
  MAJOR_B: V.MAJOR_COLOR.b.toFixed(3),
  // 색상 — 모세정맥
  MINOR_R: V.MINOR_COLOR.r.toFixed(3),
  MINOR_G: V.MINOR_COLOR.g.toFixed(3),
  MINOR_B: V.MINOR_COLOR.b.toFixed(3),
  // 색상 — 휴면
  DORMANT_R: V.DORMANT_COLOR.r.toFixed(3),
  DORMANT_G: V.DORMANT_COLOR.g.toFixed(3),
  DORMANT_B: V.DORMANT_COLOR.b.toFixed(3),
});
