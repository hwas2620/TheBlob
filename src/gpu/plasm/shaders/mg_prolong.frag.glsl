{{COMMON}}
// 보간: 활성 셀에 조대 보정을 더한다 (조각 상수)
uniform sampler2D uP; // 미세 p
uniform sampler2D uE; // 조대 p (보정)
uniform sampler2D uM; // 미세 차폐 항 (g)
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  float p = texelFetch(uP, c, 0).r;
  o = vec4(texelFetch(uM, c, 0).g > 0.0 ? p + texelFetch(uE, c / 2, 0).r : p);
}
