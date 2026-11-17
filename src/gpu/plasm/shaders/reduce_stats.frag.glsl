{{COMMON}}
// 상태 통계의 축소 (첫 단, 8×8 블록): 부피 합, 젖은 셀 수, 젖은 셀의 최소 두께, 음수 두께 셀이 있는지(1/0)
uniform sampler2D uA;
out vec4 o;
void main() {
  ivec2 C = ivec2(gl_FragCoord.xy);
  float vol = 0.0, area = 0.0, hmin = 1e30, neg = 0.0;
  for (int dy = 0; dy < 8; dy++) {
    for (int dx = 0; dx < 8; dx++) {
      vec4 A = texelFetch(uA, 8 * C + ivec2(dx, dy), 0);
      vol += A.r;
      if (A.g > 0.5) { area += 1.0; hmin = min(hmin, A.r); if (A.r < 0.0) neg = 1.0; }
    }
  }
  o = vec4(vol, area, hmin, neg);
}
