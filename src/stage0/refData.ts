// numpy 기준 자료 불러오기 — public/stage0/ref/ 의 manifest.json 과 float32 .bin.gz

export interface RefField {
  name: string;
  ch: number;
  offset: number;
}

export interface RefFile {
  file: string;
  tag: string;
  kind: 'state' | 'solver' | 'foodstate' | 'food6state' | 'foodfadestate';
  N: number;
  step: number;
  t: number;
  seed: number;
  fields: RefField[];
  floats: number;
  /** 풀이 재생용: 직접 풀이 대비 numpy 멀티그리드 1·2·3사이클의 유량 오차 */
  flux_err?: number[];
  flux_err_p0?: number;
  wet?: number;
  nc?: number;
  /** 먹이가 있는 상태(foodstate): 먹이마다 남은 양(−1 = 줄지 않음), 유인장의 세기, 다 떨어진 시각(null = 살아 있음) */
  fM?: number[];
  famp?: number[];
  t_exh?: (number | null)[];
}

export interface RefManifest {
  files: RefFile[];
}

export const REF_BASE = './stage0/ref/';

export async function loadManifest(base = REF_BASE): Promise<RefManifest> {
  const res = await fetch(base + 'manifest.json');
  if (!res.ok) throw new Error(`기준 자료 목록을 읽지 못했다: ${res.status}`);
  return (await res.json()) as RefManifest;
}

/** 필드 이름 → 채널별 평면(N·N) 배열 */
export type RefArrays = Map<string, Float32Array[]>;

export async function loadRef(f: RefFile, base = REF_BASE): Promise<RefArrays> {
  const res = await fetch(base + f.file);
  if (!res.ok) throw new Error(`기준 자료를 읽지 못했다: ${f.file} (${res.status})`);
  let buf = await res.arrayBuffer();
  const head = new Uint8Array(buf, 0, 2);
  // 서버가 이미 풀어서 주는 경우가 있어 gzip 머리표를 보고 판단한다
  if (head[0] === 0x1f && head[1] === 0x8b) {
    const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    buf = await new Response(stream).arrayBuffer();
  }
  const all = new Float32Array(buf);
  if (all.length !== f.floats) throw new Error(`${f.file}: 길이가 다르다 (${all.length} ≠ ${f.floats})`);
  const n = f.N * f.N;
  const out: RefArrays = new Map();
  for (const fld of f.fields) {
    const planes: Float32Array[] = [];
    for (let c = 0; c < fld.ch; c++) planes.push(all.subarray(fld.offset + c * n, fld.offset + (c + 1) * n));
    out.set(fld.name, planes);
  }
  return out;
}

/** 채널별 평면을 RGBA(또는 RG) 로 끼워 넣는다. 모자라는 채널은 0 */
export function interleave(planes: (Float32Array | null)[], n: number, channels: number): Float32Array {
  const out = new Float32Array(n * channels);
  for (let c = 0; c < channels; c++) {
    const p = planes[c];
    if (!p) continue;
    for (let i = 0; i < n; i++) out[i * channels + c] = p[i];
  }
  return out;
}
