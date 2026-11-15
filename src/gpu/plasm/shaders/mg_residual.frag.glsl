{{COMMON}}
// 잔차 R = S − (D·p − ΣW·p_이웃). 비활성 셀은 0
uniform sampler2D uP;
uniform sampler2D uW;
uniform sampler2D uS;
uniform sampler2D uM;
{{MG_FN}}
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  float M = texelFetch(uM, c, 0).g;
  if (M <= 0.0) { o = vec4(0.0); return; }
  float wsum, nbr;
  mgStencil(c, textureSize(uP, 0), wsum, nbr);
  o = vec4(texelFetch(uS, c, 0).r - ((M + wsum) * texelFetch(uP, c, 0).r - nbr));
}
