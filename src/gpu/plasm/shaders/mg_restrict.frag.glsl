{{COMMON}}
// 제한: 조대 셀의 우변 = 자식 넷의 잔차 합
uniform sampler2D uR;
out vec4 o;
void main() {
  ivec2 f = 2 * ivec2(gl_FragCoord.xy);
  o = vec4(texelFetch(uR, f, 0).r + texelFetch(uR, f + ivec2(1, 0), 0).r + texelFetch(uR, f + ivec2(0, 1), 0).r + texelFetch(uR, f + ivec2(1, 1), 0).r);
}
