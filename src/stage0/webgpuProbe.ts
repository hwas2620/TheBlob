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
  queue: { submit(c: unknown[]): void; onSubmittedWorkDone(): Promise<void> };
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

const STORAGE = 0x80; // GPUBufferUsage.STORAGE
const N_DISPATCH = 2000;

/** 탐침이 끝나지 않는 기기에서도 속도 측정이 멈추지 않게 시간 제한을 둔다 */
export function webgpuProbe(timeoutMs = 15000): Promise<WebGpuProbe> {
  const timeout = new Promise<WebGpuProbe>((resolve) => setTimeout(() => resolve({ ok: false, error: `${timeoutMs / 1000}초 안에 끝나지 않았다` }), timeoutMs));
  return Promise.race([probe(), timeout]);
}

async function probe(): Promise<WebGpuProbe> {
  const gpu = (navigator as unknown as { gpu?: { requestAdapter(): Promise<AdapterL | null> } }).gpu;
  if (!gpu) return { ok: false, error: '이 브라우저에 navigator.gpu 가 없다' };
  let device: DeviceL | null = null;
  try {
    const adapter = await gpu.requestAdapter();
    if (!adapter) return { ok: false, error: '어댑터를 얻지 못했다' };
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
    const usPerDispatch = Math.min(await run(N_DISPATCH, false), await run(N_DISPATCH, false));
    const usPerPass = Math.min(await run(N_DISPATCH, true), await run(N_DISPATCH, true));
    bufs.forEach((b) => b.destroy());
    return { ok: true, adapter: name, usPerDispatch, usPerPass };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  } finally {
    if (device) device.destroy();
  }
}
