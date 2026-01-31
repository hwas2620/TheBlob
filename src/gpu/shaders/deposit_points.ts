// 에이전트 분비 포인트 렌더링 셰이더 — .glsl에서 로드 (플레이스홀더 없음)

import depositPointsVertSrc from './glsl/deposit_points.vert.glsl?raw';
import depositPointsFragSrc from './glsl/deposit_points.frag.glsl?raw';

export const DEPOSIT_POINTS_VERT = depositPointsVertSrc;
export const DEPOSIT_POINTS_FRAG = depositPointsFragSrc;
