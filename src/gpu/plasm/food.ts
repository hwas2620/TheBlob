// 규칙 8 (먹이)의 정적 자료 — 먹이의 자리, 원반, 먹이별 유인장. numpy 기준 모델(ref_model.py)과 같은 식을 쓴다

import { foodWindow, FOOD_UNLIMITED, type PlasmParams } from './params';

export interface FoodGeometry {
  /** 먹이의 자리 (셀 좌표, 실수) */
  pos: [number, number][];
  /** 셀마다 그 셀이 든 먹이 원반의 번호 + 1 (0 = 원반 밖) */
  disc: Float32Array;
  /** 원반마다 셀 수 */
  discCells: number[];
  /** 먹이 패스가 원반을 훑는 창의 가운데 셀 */
  centre: [number, number][];
  /** 먹이별 유인장 c_k = amp·Σ(주기 상) exp(−r²/2σ²). 먹이 4개씩 RGBA 한 장에 끼워 넣는다 */
  fields: Float32Array[];
}

/** 먹이 상태 텍셀: 남은 양, 유인장의 세기, 다 떨어진 스텝(살아 있으면 −1), 이번 스텝에 셀 하나가 받는 두께 */
export interface FoodState {
  /** 남은 양. 줄지 않는 먹이는 Infinity */
  M: number;
  /** 유인장의 세기 (살아 있으면 1) */
  amp: number;
  /** 다 떨어진 스텝. 살아 있으면 −1 */
  stepExh: number;
}

/** 먹이 원반의 통계 (먹이 패스의 둘째 출력) */
export interface FoodStat {
  /** 원반 안의 젖은 셀 수 */
  wet: number;
  /** 원반 전체의 평균 두께 (마른 셀은 0) */
  hMean: number;
  /** 원반 안 젖은 셀의 위상의 원형 평균 (젖은 셀이 없으면 NaN) */
  phase: number;
}

export function foodGeometry(p: PlasmParams): FoodGeometry {
  const N = p.N;
  const c0 = N / 2 - 0.5;
  const half = N / 2;
  // 최소 상(minimum image). 파이썬의 (v + N/2) % N − N/2 와 같다
  const mimg = (v: number): number => ((((v + half) % N) + N) % N) - half;
  const win = foodWindow(p);
  const pos: [number, number][] = [];
  const centre: [number, number][] = [];
  const disc = new Float32Array(N * N);
  const discCells: number[] = [];
  const fields: Float32Array[] = [];
  for (let k = 0; k < p.foods.length; k++) {
    const f = p.foods[k];
    const fx = c0 + f.dist * Math.cos((f.angleDeg * Math.PI) / 180);
    const fy = c0 + f.dist * Math.sin((f.angleDeg * Math.PI) / 180);
    pos.push([fx, fy]);
    const cx = Math.round(fx);
    const cy = Math.round(fy);
    centre.push([((cx % N) + N) % N, ((cy % N) + N) % N]);
    if (k % 4 === 0) fields.push(new Float32Array(N * N * 4));
    const field = fields[fields.length - 1];
    let cells = 0;
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        const i = y * N + x;
        let g = 0;
        for (let sx = -N; sx <= N; sx += N) {
          for (let sy = -N; sy <= N; sy += N) {
            g += Math.exp(-((x - fx - sx) ** 2 + (y - fy - sy) ** 2) / (2 * p.foodSigma * p.foodSigma));
          }
        }
        field[i * 4 + (k % 4)] = p.foodAmp * g;
        if (Math.hypot(mimg(x - fx), mimg(y - fy)) < p.foodR) {
          if (disc[i] !== 0) throw new Error(`먹이 ${disc[i] - 1}번과 ${k}번의 원반이 겹친다`);
          if (Math.abs(mimg(x - cx)) > win || Math.abs(mimg(y - cy)) > win) throw new Error('먹이 원반이 훑는 창을 벗어난다');
          disc[i] = k + 1;
          cells++;
        }
      }
    }
    discCells.push(cells);
  }
  if (2 * win + 1 > N) throw new Error('먹이 원반이 격자보다 크다');
  return { pos, disc, discCells, centre, fields };
}

/** 처음의 먹이 상태 (RGBA 로 끼워 넣은 것) */
export function initialFoodState(p: PlasmParams): Float32Array {
  const out = new Float32Array(Math.max(1, p.foods.length) * 4);
  for (let k = 0; k < p.foods.length; k++) {
    out[k * 4] = p.foodM > 0 ? p.foodM : FOOD_UNLIMITED;
    out[k * 4 + 1] = 1;
    out[k * 4 + 2] = -1;
  }
  return out;
}

/** 먹이 상태를 텍셀 배열로 */
export function packFoodState(states: FoodState[]): Float32Array {
  const out = new Float32Array(Math.max(1, states.length) * 4);
  states.forEach((s, k) => {
    out[k * 4] = Number.isFinite(s.M) ? s.M : FOOD_UNLIMITED;
    out[k * 4 + 1] = s.amp;
    out[k * 4 + 2] = s.stepExh;
  });
  return out;
}

/** 텍셀 배열을 먹이 상태로 */
export function unpackFoodState(v: Float32Array, n: number): FoodState[] {
  const out: FoodState[] = [];
  for (let k = 0; k < n; k++) out.push({ M: v[k * 4] > FOOD_UNLIMITED / 10 ? Infinity : v[k * 4], amp: v[k * 4 + 1], stepExh: v[k * 4 + 2] });
  return out;
}
