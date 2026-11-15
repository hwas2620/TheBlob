{{COMMON}}
// 축소 (다음 단): 블록 안에서 r·g 는 더하고 b 는 최소, a 는 최대
uniform sampler2D uSrc;
uniform int uBlock;
out vec4 o;
void main() {
  ivec2 C = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uSrc, 0);
  float s = 0.0, t = 0.0, mn = 1e30, mx = -1e30;
  for (int dy = 0; dy < uBlock; dy++) {
    for (int dx = 0; dx < uBlock; dx++) {
      ivec2 q = uBlock * C + ivec2(dx, dy);
      if (q.x < n.x && q.y < n.y) {
        vec4 v = texelFetch(uSrc, q, 0);
        s += v.r; t += v.g; mn = min(mn, v.b); mx = max(mx, v.a);
      }
    }
  }
  o = vec4(s, t, mn, mx);
}
