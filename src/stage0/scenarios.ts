// 관문 B 의 시나리오 — numpy 기준 실행(specs/plasmodium-core/stage0/ref/export_ref.py 의 GB + SCN)과 같은 설정

import { foodParams, type FoodSpot, type PlasmParams } from '../gpu/plasm/params';

export interface Scenario {
  /** 격자 한 변 */
  N: number;
  /** 길이 (모델 시간) */
  T: number;
  /** 기본 설정(관문 A 의 굶은 이주 + 위상 무늬 (나))을 덮어쓰는 값 */
  over: Partial<PlasmParams>;
  /** 모든 먹이에 닿으면 멈춘다 (도달 시각만 잰다) */
  stopOnTouch?: boolean;
  /** 처음에 깔아 두는 점액 흔적: 'half' = 가운데의 왼쪽 절반, 'all' = 사방 (처음 원반 밖) */
  slime0?: 'half' | 'all';
  what: string;
}

/** 대칭 먹이 셋 */
export const FOOD3: FoodSpot[] = [{ angleDeg: 20, dist: 40 }, { angleDeg: 140, dist: 40 }, { angleDeg: 260, dist: 40 }];
const ASYM3: FoodSpot[] = [{ angleDeg: 0, dist: 35 }, { angleDeg: 100, dist: 45 }, { angleDeg: 200, dist: 40 }];
const FOOD4: FoodSpot[] = [{ angleDeg: 10, dist: 45 }, { angleDeg: 100, dist: 75 }, { angleDeg: 215, dist: 60 }, { angleDeg: 300, dist: 40 }];
const dir = (angleDeg: number): Scenario => ({ N: 192, T: 500, over: { foods: [{ angleDeg, dist: 70 }] }, stopOnTouch: true, what: `유인원 하나를 ${angleDeg}° 방향 70셀에 (닿는 시각)` });

export const SCENARIOS: Record<string, Scenario> = {
  mig: { N: 192, T: 400, over: {}, what: '굶은 이주: 유인원 하나 (27°, 70셀)' },
  dir0: dir(0),
  dir13: dir(13),
  dir27: dir(27),
  dir34: dir(34),
  dir45: dir(45),
  food3: { N: 192, T: 480, over: foodParams(FOOD3), what: '대칭 먹이 셋 (20°/140°/260°, 거리 40)' },
  asym3: { N: 192, T: 480, over: foodParams(ASYM3), what: '비대칭 먹이 셋 (0°/100°/200°, 거리 35/45/40)' },
  food4: { N: 256, T: 700, over: { ...foodParams(FOOD4, { eat: 0.02 }), triP: 128, mgCycles: 3 }, what: '긴 배치 먹이 넷 (거리 40~75, 256², 3사이클)' },
  long: { N: 192, T: 2000, over: {}, what: '지속: 굶은 이주를 500주기' },
  mig2x: { N: 384, T: 400, over: { rInit: 24 }, what: '굶은 이주, 몸 길이 2배 (384², 처음 원반의 반지름 24)' },
  slimehalf: { N: 192, T: 200, over: { foods: [] }, slime0: 'half', what: '점액: 몸 둘레의 왼쪽 절반이 흔적 (유인원 없음)' },
  slimeall: { N: 192, T: 200, over: { foods: [] }, slime0: 'all', what: '점액: 사방이 흔적 (유인원 없음)' },
  mig256: { N: 256, T: 400, over: { triP: 128 }, what: '굶은 이주, 256² (무늬의 주기 128)' },
  food3_256: { N: 256, T: 480, over: { ...foodParams(FOOD3), triP: 128 }, what: '대칭 먹이 셋, 256² (무늬의 주기 128)' },
};
