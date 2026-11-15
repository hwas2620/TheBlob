{{COMMON}}
// 규칙 6 (4/4): 마르는 셀은 비우고 점액 흔적을 남긴다. 남는 셀은 마르는 이웃들의 몫을 받는다
uniform sampler2D uA;
uniform sampler2D uB;
uniform sampler2D uD; // 마르는 셀, gh, ge
layout(location = 0) out vec4 oA;
layout(location = 1) out vec4 oB;
const ivec2 NB[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(1, 1), ivec2(1, -1), ivec2(-1, 0), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 1));
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  vec4 B = texelFetch(uB, c, 0);
  if (texelFetch(uD, c, 0).r > 0.5) {
    oA = vec4(0.0);
    oB = vec4(0.0, 1.0, 0.0, 0.0); // slime = 1, 압력은 지운다
    return;
  }
  if (A.g > 0.5) {
    float hpos = max(A.r, 0.0), add = 0.0;
    for (int q = 0; q < 8; q++) {
      vec4 D = texelFetch(uD, wr(c + NB[q], n), 0);
      add += D.g * hpos + D.b;
    }
    A.r += add;
  }
  oA = A;
  oB = B;
}
