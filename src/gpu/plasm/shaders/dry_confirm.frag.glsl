{{COMMON}}
// 규칙 6 (2/4): 남는 젖은 이웃이 하나도 없는 후보는 마르지 않는다 (부피를 넘길 곳이 없다)
uniform sampler2D uA;
uniform sampler2D uD; // r: 후보
out vec4 o;
const ivec2 NB[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(1, 1), ivec2(1, -1), ivec2(-1, 0), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 1));
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  float keep = 0.0;
  if (texelFetch(uD, c, 0).r > 0.5) {
    for (int q = 0; q < 8; q++) {
      ivec2 j = wr(c + NB[q], n);
      if (texelFetch(uA, j, 0).g > 0.5 && texelFetch(uD, j, 0).r < 0.5) keep = 1.0;
    }
  }
  o = vec4(keep);
}
