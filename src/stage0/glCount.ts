// GL 함수 호출을 이름별로 세는 껍데기. 스텝당 GL 호출 수를 재는 데 쓴다(주소에 count=1).
// 호출마다 Proxy 를 거치므로 느리다. 이 껍데기를 쓴 실행의 시간 수치는 믿지 않는다.

export interface CountingGl {
  gl: WebGL2RenderingContext;
  counts: Map<string, number>;
}

export function countingGl(real: WebGL2RenderingContext): CountingGl {
  const counts = new Map<string, number>();
  const wrapped = new Map<PropertyKey, unknown>();
  const gl = new Proxy(real, {
    get(target, prop): unknown {
      // 상수와 접근자(canvas 등)는 진짜 컨텍스트를 수신자로 읽어야 한다
      const v: unknown = Reflect.get(target, prop, target);
      if (typeof v !== 'function') return v;
      let f = wrapped.get(prop);
      if (!f) {
        const name = String(prop);
        f = (...args: unknown[]): unknown => {
          counts.set(name, (counts.get(name) ?? 0) + 1);
          return (v as (...a: unknown[]) => unknown).apply(target, args);
        };
        wrapped.set(prop, f);
      }
      return f;
    },
  });
  return { gl, counts };
}

export function totalCalls(counts: Map<string, number>): number {
  let s = 0;
  for (const v of counts.values()) s += v;
  return s;
}
