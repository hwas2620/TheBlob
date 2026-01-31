// 페로몬 필드 프래그먼트 셰이더 — .glsl + 플레이스홀더 치환

import pheromoneFieldFragSrc from './glsl/pheromone_field.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';
import { PHEROMONE } from '../../config';

const P = PHEROMONE;
const cc = P.CONTOUR_COLOR;

export const PHEROMONE_FIELD_FRAG = resolveShader(pheromoneFieldFragSrc, {
  FADE_START_RATIO: (0.75).toFixed(2),  // distSq 기준 75% → 거리 기준 ~87%에서 감쇠 시작
  FIELD_RADIUS: P.FIELD_RADIUS.toFixed(1),
  SOFTENING: P.SOFTENING.toFixed(1),
  MIN_THRESHOLD: P.MIN_THRESHOLD.toFixed(2),
  NORMALIZATION: P.NORMALIZATION.toFixed(1),
  COLOR_R: (P.COLOR.r / 255).toFixed(3),
  COLOR_G: (P.COLOR.g / 255).toFixed(3),
  COLOR_B: (P.COLOR.b / 255).toFixed(3),
  COLOR_A: (P.COLOR.a / 255).toFixed(3),
  CONTOUR_COUNT: P.CONTOUR_LEVELS.length,
  CONTOUR_LEVELS: P.CONTOUR_LEVELS.map(l => l.toFixed(2)).join(', '),
  CONTOUR_R: (cc.r / 255).toFixed(3),
  CONTOUR_G: (cc.g / 255).toFixed(3),
  CONTOUR_B: (cc.b / 255).toFixed(3),
  CONTOUR_A: cc.a.toFixed(2),
  LINE_WIDTH_PX: P.CONTOUR_LINE_WIDTH_PX.toFixed(1),
});
