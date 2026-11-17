{{COMMON}}
// "보간 + 뒤 스무딩 두 번"을 한 패스로: 보정한 p̃ = p + (활성이면 조대 보정) 에 Jacobi 를 두 번 건다.
// 산술은 mg_prolong 뒤 mg_jacobi 두 번과 같다. 텍셀 읽기가 많아(약 300번) 그리는 영역이 작은 레벨에서만 쓴다.
uniform sampler2D uP; // 미세 p (보정 전)
uniform sampler2D uE; // 조대 p (보정)
uniform sampler2D uW;
uniform sampler2D uS;
uniform sampler2D uM;
out vec4 o;
float pc(ivec2 q) { return texelFetch(uP, q, 0).r + (texelFetch(uM, q, 0).g > 0.0 ? texelFetch(uE, q / 2, 0).r : 0.0); }
// 보정한 p̃ 에 건 첫 번째 스무딩 뒤의 값
float j1(ivec2 c, ivec2 n) {
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) return 0.0;
  ivec2 e = wr(c + ivec2(1, 0), n), w = wr(c + ivec2(-1, 0), n), nn = wr(c + ivec2(0, 1), n), s = wr(c + ivec2(0, -1), n);
  ivec2 ne = wr(c + ivec2(1, 1), n), sw = wr(c + ivec2(-1, -1), n), se = wr(c + ivec2(1, -1), n), nw = wr(c + ivec2(-1, 1), n);
  vec4 w0 = texelFetch(uW, c, 0);
  float wW = texelFetch(uW, w, 0).r, wS = texelFetch(uW, s, 0).g, wSW = texelFetch(uW, sw, 0).b, wNW = texelFetch(uW, nw, 0).a;
  float wsum = w0.r + wW + w0.g + wS + w0.b + wSW + w0.a + wNW;
  float nbr = w0.r * pc(e) + wW * pc(w) + w0.g * pc(nn) + wS * pc(s) + w0.b * pc(ne) + wSW * pc(sw) + w0.a * pc(se) + wNW * pc(nw);
  return (1.0 - {{MG_OMEGA}}) * pc(c) + {{MG_OMEGA}} * (texelFetch(uS, c, 0).r + nbr) / (M + wsum);
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
