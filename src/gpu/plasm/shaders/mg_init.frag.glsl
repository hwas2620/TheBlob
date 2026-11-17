{{COMMON}}
// 웜스타트: 직전 두 스텝의 해를 외삽한다. p0 = p + k·(p − 직전 p)
uniform sampler2D uA;
uniform sampler2D uB;
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  vec4 B = texelFetch(uB, c, 0);
  o = vec4(texelFetch(uA, c, 0).g > 0.5 ? B.b + {{MG_EXTRAP}} * (B.b - B.a) : 0.0);
}
