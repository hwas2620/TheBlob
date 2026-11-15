{{COMMON}}
// 규칙 5 의 정규화용 축소 (첫 단, 8×8 블록): 활성 간선의 |Q|^γ 합과 개수. 같이 젖은 셀의 최소 두께와 최대 전도도
uniform sampler2D uW;
uniform sampler2D uP;
uniform sampler2D uA;
uniform sampler2D uC;
out vec4 o;
void main() {
  ivec2 C = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uW, 0);
  float sum = 0.0, cnt = 0.0, hmin = 1e30, cmax = 0.0;
  for (int dy = 0; dy < 8; dy++) {
    for (int dx = 0; dx < 8; dx++) {
      ivec2 c = 8 * C + ivec2(dx, dy);
      vec4 W = texelFetch(uW, c, 0);
      float p = texelFetch(uP, c, 0).r;
      vec4 dp = p - vec4(texelFetch(uP, wr(c + ivec2(1, 0), n), 0).r, texelFetch(uP, wr(c + ivec2(0, 1), n), 0).r,
                         texelFetch(uP, wr(c + ivec2(1, 1), n), 0).r, texelFetch(uP, wr(c + ivec2(1, -1), n), 0).r);
      vec4 act = vec4(greaterThan(W, vec4(0.0)));
      sum += dot(act, pow(abs(W * dp), vec4({{GAMMA}})));
      cnt += dot(act, vec4(1.0));
      vec4 A = texelFetch(uA, c, 0);
      if (A.g > 0.5) hmin = min(hmin, A.r);
      vec4 Cc = texelFetch(uC, c, 0);
      cmax = max(cmax, max(max(Cc.r, Cc.g), max(Cc.b, Cc.a)));
    }
  }
  o = vec4(sum, cnt, hmin, cmax);
}
