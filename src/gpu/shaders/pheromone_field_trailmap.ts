// 트레일맵 기반 페로몬 필드 프래그먼트 셰이더

import pheromoneFieldTrailmapFragSrc from './glsl/pheromone_field_trailmap.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';
import { FOOD_CONTOUR } from '../../config';

// 트레일맵 등고선 설정 (자기 페로몬 — 녹색 계열)
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
const F = FOOD_CONTOUR;

export const PHEROMONE_FIELD_TRAILMAP_FRAG = resolveShader(pheromoneFieldTrailmapFragSrc, {
  // 자기 페로몬 (녹색)
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
  // 먹이 (주황색)
  FOOD_MIN_THRESHOLD: F.MIN_THRESHOLD.toFixed(1),
  FOOD_MAX_VALUE: F.MAX_VALUE.toFixed(1),
  FOOD_LOW_R: (F.LOW_COLOR.r / 255).toFixed(3),
  FOOD_LOW_G: (F.LOW_COLOR.g / 255).toFixed(3),
  FOOD_LOW_B: (F.LOW_COLOR.b / 255).toFixed(3),
  FOOD_HIGH_R: (F.HIGH_COLOR.r / 255).toFixed(3),
  FOOD_HIGH_G: (F.HIGH_COLOR.g / 255).toFixed(3),
  FOOD_HIGH_B: (F.HIGH_COLOR.b / 255).toFixed(3),
  FOOD_BASE_ALPHA: F.BASE_ALPHA.toFixed(2),
  FOOD_LINE_WIDTH: F.LINE_WIDTH.toFixed(1),
  FOOD_CONTOUR_R: (F.CONTOUR_COLOR.r / 255).toFixed(3),
  FOOD_CONTOUR_G: (F.CONTOUR_COLOR.g / 255).toFixed(3),
  FOOD_CONTOUR_B: (F.CONTOUR_COLOR.b / 255).toFixed(3),
  FOOD_CONTOUR_ALPHA: F.CONTOUR_ALPHA.toFixed(2),
  FOOD_LEVELS: F.LEVELS.map(l => l.toFixed(2)).join(', '),
});
