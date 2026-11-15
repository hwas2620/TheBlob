{{COMMON}}
// 감쇠 Jacobi 두 번을 한 패스로. 산술은 mg_jacobi 를 두 번 돌린 것과 같다.
// 텍셀 읽기가 약 150번으로 늘어나므로 그리는 영역이 작은 레벨에서만 쓴다(거기서는 드로콜 수가 비용이다).
uniform sampler2D uP; // r: p
uniform sampler2D uW; // rgba: E, N, NE, SE 간선 가중치
uniform sampler2D uS; // r: 우변
uniform sampler2D uM; // g: 차폐 항
{{MG_FN}}
out vec4 o;
// 첫 번째 스무딩 뒤의 값
float j1(ivec2 c, ivec2 n) {
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) return 0.0;
  float wsum, nbr;
  mgStencil(c, n, wsum, nbr);
  return (1.0 - {{MG_OMEGA}}) * texelFetch(uP, c, 0).r + {{MG_OMEGA}} * (texelFetch(uS, c, 0).r + nbr) / (M + wsum);
}
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uP, 0);
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
