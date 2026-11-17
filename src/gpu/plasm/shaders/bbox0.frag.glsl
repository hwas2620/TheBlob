{{COMMON}}
// 몸의 경계 상자 (첫 단, 8×8 블록): 젖은 셀의 (최소 x, 최소 y, −최대 x, −최대 y). 네 채널 모두 최소를 취하면 된다
uniform sampler2D uA;
out vec4 o;
void main() {
  ivec2 C = ivec2(gl_FragCoord.xy);
  vec4 b = vec4(1e9);
  for (int dy = 0; dy < 8; dy++) {
    for (int dx = 0; dx < 8; dx++) {
      ivec2 c = 8 * C + ivec2(dx, dy);
      if (texelFetch(uA, c, 0).g > 0.5) b = min(b, vec4(float(c.x), float(c.y), -float(c.x), -float(c.y)));
    }
  }
  o = b;
}
