// WebGPU 탐침 — 같은 기기에서 계산 디스패치 하나가 드는 고정 비용을 잰다
//
// WebGL2 에서는 패스마다 타깃을 바꿔야 해서 패스 하나에 십수 µs 가 든다(멀티그리드는 스텝당 100패스쯤이다).
// WebGPU 의 계산 패스는 타깃 전환 없이 디스패치를 잇달아 넣을 수 있다. 그 차이가 얼마나 되는지만 본다.
// 64×64 격자의 9점 스텐실을 버퍼 둘 사이에서 번갈아 n 번 돌린다(작업량은 무시할 만하다).
// 타입 선언 패키지를 들이지 않으려고 쓰는 메서드만 최소한으로 적었다.

type Dict = Record<string, unknown>;
interface BufferL {
  destroy(): void;
}
interface PassL {
  setPipeline(p: unknown): void;
  setBindGroup(i: number, g: unknown): void;
  dispatchWorkgroups(x: number, y?: number): void;
  end(): void;
}
interface EncoderL {
  beginComputePass(): PassL;
  finish(): unknown;
}
interface DeviceL {
  createBuffer(d: Dict): BufferL;
  createShaderModule(d: Dict): unknown;
  createComputePipelineAsync(d: Dict): Promise<{ getBindGroupLayout(i: number): unknown }>;
  createBindGroup(d: Dict): unknown;
  createCommandEncoder(): EncoderL;
  queue: { submit(c: unknown[]): void; onSubmittedWorkDone(): Promise<void>; writeBuffer(b: BufferL, offset: number, data: ArrayBufferView): void };
  destroy(): void;
}
interface AdapterL {
  requestDevice(): Promise<DeviceL>;
  info?: { vendor?: string; architecture?: string; description?: string };
}

export interface WebGpuProbe {
  ok: boolean;
  adapter?: string;
  /** 계산 패스 하나 안에서 잇달아 넣은 디스패치 하나의 시간(µs) */
  usPerDispatch?: number;
  /** 디스패치마다 계산 패스를 따로 열었을 때의 시간(µs) */
  usPerPass?: number;
  /**
   * 압력 풀이 한 번을 흉내 낸 것의 시간(ms). 격자 solveN² 에 레벨을 6² 까지 두고, 실제 풀이와 같은 순서로
   * (조대 연산자, V(2,2) 사이클 2번) 9점 스텐실 디스패치를 solveDispatches 번 넣는다. 산술은 실제 풀이가 아니고 일의 양과 꼴만 같다.
   * Full 은 레벨 전체를, Rect 는 몸 주변(레벨 0 에서 104×104 셀)만 디스패치한다
   */
  solveFullMs?: number;
  solveRectMs?: number;
  /** 몸 주변만의 풀이 흉내를 쉬지 않고 0.8초쯤 돌렸을 때의 한 번의 시간(ms). 기기가 클럭을 올린 뒤의 값이다 */
  solveRectSustainedMs?: number;
  solveN?: number;
  solveDispatches?: number;
  error?: string;
}

const WGSL = `
@group(0) @binding(0) var<storage, read> src: array<f32>;
@group(0) @binding(1) var<storage, read_write> dst: array<f32>;
const N: u32 = 64u;
@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
  let x = id.x;
  let y = id.y;
  if (x >= N || y >= N) { return; }
  let xm = (x + N - 1u) % N;
  let xp = (x + 1u) % N;
  let ym = (y + N - 1u) % N;
  let yp = (y + 1u) % N;
  let s = src[y * N + xm] + src[y * N + xp] + src[ym * N + x] + src[yp * N + x]
        + src[ym * N + xm] + src[ym * N + xp] + src[yp * N + xm] + src[yp * N + xp];
  dst[y * N + x] = 0.2 * src[y * N + x] + 0.1 * s;
}`;

// 레벨 하나의 가중 Jacobi 를 흉내 낸 스텐실: 압력 9번, 간선 가중치 5번을 읽는다 (실제 스무딩 패스와 같은 읽기 수)
const WGSL_LEVEL = `
struct Lv { n: u32, x0: u32, y0: u32, pad: u32 };
@group(0) @binding(0) var<storage, read> src: array<f32>;
@group(0) @binding(1) var<storage, read_write> dst: array<f32>;
@group(0) @binding(2) var<storage, read> wts: array<vec4<f32>>;
@group(0) @binding(3) var<uniform> lv: Lv;
@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
  let n = lv.n;
  let x = id.x + lv.x0;
  let y = id.y + lv.y0;
  if (x >= n || y >= n) { return; }
  let xm = (x + n - 1u) % n;
  let xp = (x + 1u) % n;
  let ym = (y + n - 1u) % n;
  let yp = (y + 1u) % n;
  let w0 = wts[y * n + x];
  let wW = wts[y * n + xm].x;
  let wS = wts[ym * n + x].y;
  let wSW = wts[ym * n + xm].z;
  let wNW = wts[yp * n + xm].w;
  let s = w0.x * src[y * n + xp] + w0.y * src[yp * n + x] + w0.z * src[yp * n + xp] + w0.w * src[ym * n + xp]
        + wW * src[y * n + xm] + wS * src[ym * n + x] + wSW * src[ym * n + xm] + wNW * src[yp * n + xm];
  let m = 1.0 + w0.x + w0.y + w0.z + w0.w + wW + wS + wSW + wNW;
  dst[y * n + x] = 0.2 * src[y * n + x] + 0.8 * s / m;
}`;

const STORAGE = 0x80; // GPUBufferUsage.STORAGE
const UNIFORM = 0x40;
const COPY_DST = 0x08;
const N_DISPATCH = 2000;
const SOLVE_N = 384;
const SOLVE_RECT = 104; // "몸 주변만"에서 레벨 0 에 그리는 영역의 한 변(셀)

/** 압력 풀이 한 번의 디스패치를 흉내 낸다 (레벨 0 … 6², 조대 연산자 + V(2,2) 두 번) */
async function solveLike(dev: DeviceL, out: WebGpuProbe): Promise<void> {
  const sizes: number[] = [];
  for (let n = SOLVE_N; n >= 6; n >>= 1) sizes.push(n);
  const L = sizes.length;
  const pipeline = await dev.createComputePipelineAsync({ layout: 'auto', compute: { module: dev.createShaderModule({ code: WGSL_LEVEL }), entryPoint: 'main' } });
  const layout = pipeline.getBindGroupLayout(0);
  const bufs: BufferL[] = [];
  const mk = (size: number, usage: number): BufferL => {
    const b = dev.createBuffer({ size, usage });
    bufs.push(b);
    return b;
  };
  // 레벨마다: 압력 두 장(번갈아 쓴다), 가중치 한 장, 영역을 적은 유니폼 둘(전체 / 몸 주변)
  const groups: unknown[][][] = []; // [레벨][전체 0 | 몸 주변 1][짝수 0 | 홀수 1]
  const counts: number[][] = []; // [레벨][전체 | 몸 주변] 한 변의 작업 묶음 수
  sizes.forEach((n, l) => {
    const p = [mk(n * n * 4, STORAGE), mk(n * n * 4, STORAGE)];
    const w = mk(n * n * 16, STORAGE);
    const rect = Math.min(n, Math.max(8, Math.ceil(SOLVE_RECT / (1 << l))));
    const off = Math.floor((n - rect) / 2);
    const uni = [[n, 0, 0, 0], [n, off, off, 0]].map((v) => {
      const u = mk(16, UNIFORM | COPY_DST);
      dev.queue.writeBuffer(u, 0, new Uint32Array(v));
      return u;
    });
    groups.push(uni.map((u) => [0, 1].map((i) => dev.createBindGroup({
      layout,
      entries: [
        { binding: 0, resource: { buffer: p[i] } },
        { binding: 1, resource: { buffer: p[1 - i] } },
        { binding: 2, resource: { buffer: w } },
        { binding: 3, resource: { buffer: u } },
      ],
    }))));
    counts.push([Math.ceil(n / 8), Math.ceil(rect / 8)]);
  });
  let dispatches = 0;
  const run = async (mode: number, solves: number): Promise<number> => {
    const flip = sizes.map(() => 0);
    const t0 = performance.now();
    const enc = dev.createCommandEncoder();
    const pass = enc.beginComputePass();
    pass.setPipeline(pipeline);
    let n = 0;
    const sweep = (l: number): void => {
      pass.setBindGroup(0, groups[l][mode][flip[l]]);
      pass.dispatchWorkgroups(counts[l][mode], counts[l][mode]);
      flip[l] = 1 - flip[l];
      n++;
    };
    for (let s = 0; s < solves; s++) {
      for (let l = 1; l < L; l++) sweep(l); // 조대 연산자
      for (let c = 0; c < 2; c++) {
        for (let l = 0; l < L - 1; l++) {
          sweep(l);
          sweep(l); // 앞 스무딩 두 번
          sweep(l + 1); // 잔차 + 제한
        }
        for (let i = 0; i < 4; i++) sweep(L - 1);
        for (let l = L - 2; l >= 0; l--) {
          sweep(l); // 보간 + 뒤 스무딩
          sweep(l);
        }
      }
    }
    pass.end();
    dev.queue.submit([enc.finish()]);
    await dev.queue.onSubmittedWorkDone();
    dispatches = n / solves;
    return (performance.now() - t0) / solves;
  };
  try {
    await run(1, 1); // 데운다
    out.solveN = SOLVE_N;
    out.solveRectMs = Math.min(await run(1, 20), await run(1, 20));
    out.solveDispatches = dispatches;
    await run(0, 1);
    out.solveFullMs = Math.min(await run(0, 5), await run(0, 5));
    // 쉬지 않고: 20번씩 묶어 잇달아 넣는다
    const t0 = performance.now();
    let solves = 0;
    while (performance.now() - t0 < 800) {
      await run(1, 20);
      solves += 20;
    }
    out.solveRectSustainedMs = (performance.now() - t0) / solves;
  } finally {
    bufs.forEach((b) => b.destroy());
  }
}

/** 탐침이 끝나지 않는 기기에서도 속도 측정이 멈추지 않게 시간 제한을 둔다. 그때까지 잰 값은 남긴다 */
export function webgpuProbe(timeoutMs = 25000): Promise<WebGpuProbe> {
  const out: WebGpuProbe = { ok: false };
  const timeout = new Promise<WebGpuProbe>((resolve) => setTimeout(() => resolve({ ...out, error: `${timeoutMs / 1000}초 안에 끝나지 않았다` }), timeoutMs));
  return Promise.race([probe(out), timeout]);
}

async function probe(out: WebGpuProbe): Promise<WebGpuProbe> {
  const gpu = (navigator as unknown as { gpu?: { requestAdapter(): Promise<AdapterL | null> } }).gpu;
  if (!gpu) return { ...out, error: '이 브라우저에 navigator.gpu 가 없다' };
  let device: DeviceL | null = null;
  try {
    const adapter = await gpu.requestAdapter();
    if (!adapter) return { ...out, error: '어댑터를 얻지 못했다' };
    device = await adapter.requestDevice();
    const dev = device;
    const info = adapter.info;
    const name = info ? [info.vendor, info.architecture, info.description].filter(Boolean).join(' ') || '이름 없음' : '이름 없음';
    const bufs = [0, 1].map(() => dev.createBuffer({ size: 64 * 64 * 4, usage: STORAGE }));
    const pipeline = await dev.createComputePipelineAsync({ layout: 'auto', compute: { module: dev.createShaderModule({ code: WGSL }), entryPoint: 'main' } });
    const groups = [0, 1].map((i) =>
      dev.createBindGroup({
        layout: pipeline.getBindGroupLayout(0),
        entries: [
          { binding: 0, resource: { buffer: bufs[i] } },
          { binding: 1, resource: { buffer: bufs[1 - i] } },
        ],
      }),
    );
    const run = async (n: number, separate: boolean): Promise<number> => {
      const t0 = performance.now();
      const enc = dev.createCommandEncoder();
      let pass = separate ? null : enc.beginComputePass();
      for (let i = 0; i < n; i++) {
        if (separate) pass = enc.beginComputePass();
        pass!.setPipeline(pipeline);
        pass!.setBindGroup(0, groups[i & 1]);
        pass!.dispatchWorkgroups(8, 8);
        if (separate) pass!.end();
      }
      if (!separate) pass!.end();
      dev.queue.submit([enc.finish()]);
      await dev.queue.onSubmittedWorkDone();
      return ((performance.now() - t0) / n) * 1000;
    };
    await run(64, false); // 파이프라인과 버퍼를 데운다
    out.adapter = name;
    out.usPerDispatch = Math.min(await run(N_DISPATCH, false), await run(N_DISPATCH, false));
    out.usPerPass = Math.min(await run(N_DISPATCH, true), await run(N_DISPATCH, true));
    out.ok = true;
    bufs.forEach((b) => b.destroy());
    await solveLike(dev, out);
    return out;
  } catch (e) {
    return { ...out, error: e instanceof Error ? e.message : String(e) };
  } finally {
    if (device) device.destroy();
  }
}
