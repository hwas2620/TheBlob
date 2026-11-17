{{COMMON}}
// 규칙 6 (1/4): 마를 후보. 얇고(h < h_min) 유예가 지난 셀 가운데, 떼어 내도 주변이 끊기지 않거나 인접 관이 약한 셀.
// 한 스텝에는 2×2 색 하나만 마른다. 두께가 음수인 셀은 조건 없이 마른다
uniform sampler2D uA;   // 유량 갱신 뒤의 h, wet, age, sage
uniform sampler2D uAux; // b: 인접 최대 전도도 (강화 전 값)
uniform int uStep;
out vec4 o;
// 셀을 한 바퀴 도는 이웃 순서
const ivec2 RING[8] = ivec2[8](ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 0), ivec2(-1, 1), ivec2(0, 1), ivec2(1, 1));
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  bool wet = A.g > 0.5;
  bool dry = wet && A.r < {{H_MIN}} && A.b > {{GRACE}};
  if (dry) {
    float xb[8];
    for (int q = 0; q < 8; q++) xb[q] = texelFetch(uA, wr(c + RING[q], n), 0).g > 0.5 ? 0.0 : 1.0;
    // 연결수(Yokoi, 8연결): 1 이하면 떼어 내도 젖은 이웃들이 끊기지 않는다
    float nc = 0.0;
    for (int q = 0; q < 8; q += 2) nc += xb[q] - xb[q] * xb[q + 1] * xb[(q + 2) % 8];
    int colour = (c.x % 2) + 2 * (c.y % 2);
    dry = (nc <= 1.0 || texelFetch(uAux, c, 0).b < {{BRIDGE_BREAK}}) && colour == uStep % 4;
  }
  if (wet && A.r < 0.0) dry = true;
  o = vec4(dry ? 1.0 : 0.0);
}
