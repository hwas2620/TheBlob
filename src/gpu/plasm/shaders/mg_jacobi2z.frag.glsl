{{COMMON}}
// 해가 0 인 상태에서 건 감쇠 Jacobi 두 번을 한 패스로. mg_jacobi0 뒤 mg_jacobi 한 번과 같은 값이다 (p 를 읽지 않는다)
uniform sampler2D uW;
uniform sampler2D uS;
uniform sampler2D uM;
out vec4 o;
// 셀 q 의 가중치 합
float wsumAt(ivec2 q, ivec2 n) {
  ivec2 w = wr(q + ivec2(-1, 0), n), s = wr(q + ivec2(0, -1), n), sw = wr(q + ivec2(-1, -1), n), nw = wr(q + ivec2(-1, 1), n);
  vec4 w0 = texelFetch(uW, q, 0);
  float wW = texelFetch(uW, w, 0).r, wS = texelFetch(uW, s, 0).g, wSW = texelFetch(uW, sw, 0).b, wNW = texelFetch(uW, nw, 0).a;
  return w0.r + wW + w0.g + wS + w0.b + wSW + w0.a + wNW;
}
// 첫 번째 스무딩 뒤의 값 (0 에서 출발)
float j1(ivec2 q, ivec2 n) {
  float M = texelFetch(uM, q, 0).g;
  if (M <= 0.0) return 0.0;
  return {{MG_OMEGA}} * texelFetch(uS, q, 0).r / (M + wsumAt(q, n));
}
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uW, 0);
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) { o = vec4(0.0); return; }
  ivec2 e = wr(c + ivec2(1, 0), n), w = wr(c + ivec2(-1, 0), n), nn = wr(c + ivec2(0, 1), n), s = wr(c + ivec2(0, -1), n);
  ivec2 ne = wr(c + ivec2(1, 1), n), sw = wr(c + ivec2(-1, -1), n), se = wr(c + ivec2(1, -1), n), nw = wr(c + ivec2(-1, 1), n);
  vec4 w0 = texelFetch(uW, c, 0);
  float wW = texelFetch(uW, w, 0).r, wS = texelFetch(uW, s, 0).g, wSW = texelFetch(uW, sw, 0).b, wNW = texelFetch(uW, nw, 0).a;
  float wsum = w0.r + wW + w0.g + wS + w0.b + wSW + w0.a + wNW;
  float nbr = w0.r * j1(e, n) + wW * j1(w, n) + w0.g * j1(nn, n) + wS * j1(s, n) + w0.b * j1(ne, n) + wSW * j1(sw, n) + w0.a * j1(se, n) + wNW * j1(nw, n);
  o = vec4((1.0 - {{MG_OMEGA}}) * j1(c, n) + {{MG_OMEGA}} * (texelFetch(uS, c, 0).r + nbr) / (M + wsum));
}
