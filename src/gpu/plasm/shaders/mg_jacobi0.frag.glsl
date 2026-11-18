{{COMMON}}
// 해가 0 인 상태에서 건 감쇠 Jacobi 첫 번: p ← ω·S/D. mg_jacobi 에 p = 0 을 넣은 것과 같은 값이다.
// 조대 레벨은 늘 0 에서 출발하므로, 해를 0 으로 지우는 패스 없이 이 패스로 시작한다 (p 를 읽지 않는다)
uniform sampler2D uW; // rgba: E, N, NE, SE 간선 가중치
uniform sampler2D uS; // r: 우변
uniform sampler2D uM; // g: 차폐 항
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uW, 0);
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) { o = vec4(0.0); return; }
  ivec2 w = wr(c + ivec2(-1, 0), n), s = wr(c + ivec2(0, -1), n), sw = wr(c + ivec2(-1, -1), n), nw = wr(c + ivec2(-1, 1), n);
  vec4 w0 = texelFetch(uW, c, 0);
  float wW = texelFetch(uW, w, 0).r, wS = texelFetch(uW, s, 0).g, wSW = texelFetch(uW, sw, 0).b, wNW = texelFetch(uW, nw, 0).a;
  float wsum = w0.r + wW + w0.g + wS + w0.b + wSW + w0.a + wNW;
  o = vec4({{MG_OMEGA}} * texelFetch(uS, c, 0).r / (M + wsum));
}
