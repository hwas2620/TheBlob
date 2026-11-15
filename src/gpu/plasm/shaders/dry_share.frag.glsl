{{COMMON}}
// 규칙 6 (3/4): 마르는 셀이 부피(음수면 부족분)를 남는 이웃에게 두께에 비례해 나눌 몫
//   gh = h / Σ(남는 이웃의 양의 두께),  이웃의 두께 합이 0 이면 ge = h / (남는 이웃 수)
uniform sampler2D uA;
uniform sampler2D uD; // r: 마르는 셀
out vec4 o;
const ivec2 NB[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(1, 1), ivec2(1, -1), ivec2(-1, 0), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 1));
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  if (texelFetch(uD, c, 0).r < 0.5) { o = vec4(0.0); return; }
  float ns = 0.0, sh = 0.0;
  for (int q = 0; q < 8; q++) {
    ivec2 j = wr(c + NB[q], n);
    vec4 Aj = texelFetch(uA, j, 0);
    if (Aj.g > 0.5 && texelFetch(uD, j, 0).r < 0.5) { ns += 1.0; sh += max(Aj.r, 0.0); }
  }
  float h = texelFetch(uA, c, 0).r;
  o = vec4(1.0, sh > 0.0 ? h / max(sh, 1e-30) : 0.0, sh > 0.0 ? 0.0 : h / max(ns, 1.0), 0.0);
}
