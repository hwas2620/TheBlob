// 셰이더 템플릿 치환 유틸리티
// .glsl 파일의 {{VAR}} 플레이스홀더를 실제 값으로 치환

export function resolveShader(
  src: string,
  vars: Record<string, string | number>,
): string {
  return src.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    const val = vars[key];
    if (val === undefined) {
      console.warn(`[shader] unresolved placeholder: ${match}`);
      return match;
    }
    return String(val);
  });
}
