{{COMMON}}
// "잔차 + 제한"을 한 패스로: 조대 셀의 우변 = 자식 넷의 잔차 합. 산술은 mg_residual 뒤 mg_restrict 와 같다
uniform sampler2D uP; // 미세 p
uniform sampler2D uW; // 미세 가중치
uniform sampler2D uS; // 미세 우변 (r)
uniform sampler2D uM; // 미세 차폐 항 (g)
{{MG_FN}}
out vec4 o;
float residual(ivec2 c, ivec2 n) {
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) return 0.0;
  float wsum, nbr;
  mgStencil(c, n, wsum, nbr);
  return texelFetch(uS, c, 0).r - ((M + wsum) * texelFetch(uP, c, 0).r - nbr);
}
void main() {
  ivec2 f = 2 * ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uP, 0);
  o = vec4(residual(f, n) + residual(f + ivec2(1, 0), n) + residual(f + ivec2(0, 1), n) + residual(f + ivec2(1, 1), n));
}
