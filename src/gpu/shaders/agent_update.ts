// 에이전트 업데이트 프래그먼트 셰이더 — Jeff Jones 2010 논문 원본
// 직접 유인(Direct Attraction) 없음, 순수 센서 기반 알고리즘

import agentUpdateFragSrc from './glsl/agent_update.frag.glsl?raw';

// 플레이스홀더 없음 — 모든 파라미터는 uniform으로 전달
export const AGENT_UPDATE_FRAG = agentUpdateFragSrc;
