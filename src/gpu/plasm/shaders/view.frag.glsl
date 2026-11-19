{{COMMON}}
// 확인용 표시: 점액 흔적, 몸(두께), 정맥(전도도^(1/4))
uniform sampler2D uA;
uniform sampler2D uB;
uniform sampler2D uC;
uniform sampler2D uField; // g: 먹이 원반의 번호 + 1
uniform sampler2D uFS;    // 먹이 상태. r: 남은 양
uniform vec2 uCanvas;
out vec4 o;
void main() {
  ivec2 n = textureSize(uA, 0);
  ivec2 c = clamp(ivec2(gl_FragCoord.xy / uCanvas * vec2(n)), ivec2(0), n - 1);
  vec4 A = texelFetch(uA, c, 0);
  vec4 C = texelFetch(uC, c, 0);
  float cW = texelFetch(uC, wr(c + ivec2(-1, 0), n), 0).r, cS = texelFetch(uC, wr(c + ivec2(0, -1), n), 0).g;
  float cSW = texelFetch(uC, wr(c + ivec2(-1, -1), n), 0).b, cNW = texelFetch(uC, wr(c + ivec2(-1, 1), n), 0).a;
  float cn = max(max(max(C.r, C.g), max(C.b, C.a)), max(max(cW, cS), max(cSW, cNW)));
  vec3 col = mix(vec3(0.04, 0.07, 0.06), vec3(0.20, 0.16, 0.12), clamp(texelFetch(uB, c, 0).g, 0.0, 1.0));
  if (A.g > 0.5) {
    col = mix(vec3(0.16, 0.13, 0.03), vec3(0.84, 0.73, 0.16), clamp(A.r / 1.3, 0.0, 1.0));
    col = mix(col, vec3(1.0, 0.47, 0.16), clamp((pow(cn, 0.25) - 1.5) / 2.5, 0.0, 1.0));
  }
#if {{FOOD_N}} > 0
  // 먹이 원반: 살아 있으면 푸른빛, 다 먹혔으면 잿빛을 얹는다
  float id = texelFetch(uField, c, 0).g;
  if (id > 0.5) col = mix(col, texelFetch(uFS, ivec2(int(id) - 1, 0), 0).r > 0.0 ? vec3(0.24, 0.86, 1.0) : vec3(0.5), 0.35);
#endif
  o = vec4(col, 1.0);
}
