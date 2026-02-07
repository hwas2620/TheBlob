// 트레일맵 기반 페로몬 필드 프래그먼트 셰이더

import pheromoneFieldTrailmapFragSrc from './glsl/pheromone_field_trailmap.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';

// 트레일맵 등고선 설정
const TRAILMAP_PHEROMONE = {
  MIN_THRESHOLD: 5,      // 최소 표시 임계값
  MAX_VALUE: 150,        // 정규화 기준 최대값
  LOW_COLOR: { r: 0, g: 80, b: 100 },   // 낮은 농도: 어두운 청록
  HIGH_COLOR: { r: 50, g: 200, b: 100 }, // 높은 농도: 밝은 녹색
  BASE_ALPHA: 0.3,
  LINE_WIDTH: 2.0,
  CONTOUR_COLOR: { r: 100, g: 255, b: 150 },
  CONTOUR_ALPHA: 0.6,
};

const P = TRAILMAP_PHEROMONE;

export const PHEROMONE_FIELD_TRAILMAP_FRAG = resolveShader(pheromoneFieldTrailmapFragSrc, {
  MIN_THRESHOLD: P.MIN_THRESHOLD.toFixed(1),
  MAX_VALUE: P.MAX_VALUE.toFixed(1),
  LOW_R: (P.LOW_COLOR.r / 255).toFixed(3),
  LOW_G: (P.LOW_COLOR.g / 255).toFixed(3),
  LOW_B: (P.LOW_COLOR.b / 255).toFixed(3),
  HIGH_R: (P.HIGH_COLOR.r / 255).toFixed(3),
  HIGH_G: (P.HIGH_COLOR.g / 255).toFixed(3),
  HIGH_B: (P.HIGH_COLOR.b / 255).toFixed(3),
  BASE_ALPHA: P.BASE_ALPHA.toFixed(2),
  LINE_WIDTH: P.LINE_WIDTH.toFixed(1),
  CONTOUR_R: (P.CONTOUR_COLOR.r / 255).toFixed(3),
  CONTOUR_G: (P.CONTOUR_COLOR.g / 255).toFixed(3),
  CONTOUR_B: (P.CONTOUR_COLOR.b / 255).toFixed(3),
  CONTOUR_ALPHA: P.CONTOUR_ALPHA.toFixed(2),
});
