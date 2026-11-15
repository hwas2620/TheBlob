{{COMMON}}
// 규칙 7 (2/2): 새로 젖는 셀은 공급 셀에서 min(h_fill, 0.5·h/받는 셀 수) 를 받고 θ 와 압력을 물려받는다
uniform sampler2D uA;
uniform sampler2D uB;
uniform sampler2D uPlan; // r: 젖을 셀, g: 공급 셀 방향 번호
layout(location = 0) out vec4 oA;
layout(location = 1) out vec4 oB;
const ivec2 ALL[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(1, 1), ivec2(1, -1), ivec2(-1, 0), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 1));
// 셀 d 를 공급 셀로 고른 이웃의 수. 방향 q 의 반대는 (q + 4) % 8
float takers(ivec2 d, ivec2 n) {
  float cnt = 0.0;
  for (int q = 0; q < 8; q++) {
    vec4 pl = texelFetch(uPlan, wr(d + ALL[q], n), 0);
    if (pl.r > 0.5 && int(pl.g + 0.5) == (q + 4) % 8) cnt += 1.0;
  }
  return cnt;
}
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  vec4 B = texelFetch(uB, c, 0);
  vec4 pl = texelFetch(uPlan, c, 0);
  if (A.g > 0.5) {
    float cnt = takers(c, n);
    if (cnt > 0.0) A.r -= cnt * min({{H_FILL}}, 0.5 * max(A.r, 0.0) / cnt);
  } else if (pl.r > 0.5) {
    ivec2 d = wr(c + ALL[int(pl.g + 0.5)], n);
    vec4 Ad = texelFetch(uA, d, 0);
    vec4 Bd = texelFetch(uB, d, 0);
    A = vec4(min({{H_FILL}}, 0.5 * max(Ad.r, 0.0) / takers(d, n)), 1.0, 0.0, 0.0);
    B = vec4(Bd.r, B.g, Bd.b, Bd.a);
  }
  oA = A;
  oB = B;
}
