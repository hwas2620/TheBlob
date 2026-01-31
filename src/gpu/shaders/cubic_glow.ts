// 큐빅 글로우 프래그먼트 셰이더 — .glsl + 플레이스홀더 치환

import cubicGlowFragSrc from './glsl/cubic_glow.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';
import { CUBIC_GLOW } from '../../config';

const C = CUBIC_GLOW;

export const CUBIC_GLOW_FRAG = resolveShader(cubicGlowFragSrc, {
  SAMPLE_STEP: C.SAMPLE_STEP.toFixed(1),
  THRESHOLD: C.THRESHOLD.toFixed(1),
  INTENSITY_RANGE: C.INTENSITY_RANGE.toFixed(1),
  BLOCK_SIZE: C.BLOCK_SIZE.toFixed(1),
  BLOCK_HALF: (C.BLOCK_SIZE / 2).toFixed(1),
  ALPHA_MULTIPLIER: C.ALPHA_MULTIPLIER.toFixed(1),
  COLOR_R: C.COLOR.r.toFixed(3),
  COLOR_G: C.COLOR.g.toFixed(3),
  COLOR_B: C.COLOR.b.toFixed(3),
});
