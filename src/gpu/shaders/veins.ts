// 정맥(vein) 프래그먼트 셰이더 — .glsl + 플레이스홀더 치환

import veinsFragSrc from './glsl/veins.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';
import { VEINS } from '../../config';

const V = VEINS;

export const VEINS_FRAG = resolveShader(veinsFragSrc, {
  VEIN_MIN: V.MIN.toFixed(1),
  VEIN_MAX: V.MAX.toFixed(1),
  STEP: V.STEP.toFixed(1),
  MAX_ALPHA: V.MAX_ALPHA.toFixed(1),
  RIDGE_SCALE: V.RIDGE_SCALE.toFixed(1),
  ACTIVE_R: V.ACTIVE_COLOR.r.toFixed(3),
  ACTIVE_G: V.ACTIVE_COLOR.g.toFixed(3),
  ACTIVE_B: V.ACTIVE_COLOR.b.toFixed(3),
  DORMANT_R: V.DORMANT_COLOR.r.toFixed(3),
  DORMANT_G: V.DORMANT_COLOR.g.toFixed(3),
  DORMANT_B: V.DORMANT_COLOR.b.toFixed(3),
});
