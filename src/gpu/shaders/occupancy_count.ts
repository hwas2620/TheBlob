// Occupancy Map 렌더링 셰이더
// 에이전트 위치를 GL_POINTS로 렌더링하여 셀당 에이전트 수 계산

import occupancyCountVertSrc from './glsl/occupancy_count.vert.glsl?raw';
import occupancyCountFragSrc from './glsl/occupancy_count.frag.glsl?raw';

export const OCCUPANCY_COUNT_VERT = occupancyCountVertSrc;
export const OCCUPANCY_COUNT_FRAG = occupancyCountFragSrc;
