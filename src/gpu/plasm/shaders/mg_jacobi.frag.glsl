{{COMMON}}
// 감쇠 Jacobi 한 번: p ← (1−ω)·p + ω·(S + ΣW·p_이웃)/D,  D = M + ΣW. 비활성 셀(M = 0)은 0
uniform sampler2D uP; // r: p
uniform sampler2D uW; // rgba: E, N, NE, SE 간선 가중치
uniform sampler2D uS; // r: 우변
uniform sampler2D uM; // g: 차폐 항
{{MG_FN}}
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) { o = vec4(0.0); return; }
  float wsum, nbr;
  mgStencil(c, textureSize(uP, 0), wsum, nbr);
  float p = texelFetch(uP, c, 0).r;
  o = vec4((1.0 - {{MG_OMEGA}}) * p + {{MG_OMEGA}} * (texelFetch(uS, c, 0).r + nbr) / (M + wsum));
}
