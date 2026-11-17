{{COMMON}}
// 축소 (다음 단): 블록 안에서 채널별 최소
uniform sampler2D uSrc;
uniform int uBlock;
out vec4 o;
void main() {
  ivec2 C = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uSrc, 0);
  vec4 b = vec4(1e9);
  for (int dy = 0; dy < uBlock; dy++) {
    for (int dx = 0; dx < uBlock; dx++) {
      ivec2 q = uBlock * C + ivec2(dx, dy);
      if (q.x < n.x && q.y < n.y) b = min(b, texelFetch(uSrc, q, 0));
    }
  }
  o = b;
}
