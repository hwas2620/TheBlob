{{COMMON}}
// 규칙 7 (1/2): 마른 셀이 젖을지 판정하고 부피를 줄 이웃을 고른다
//   마른 셀이 보는 두께 P = max(축 이웃 4개의 h, 대각 4방향의 보간값)
//   P > hy0·(1 + σ_y·η) + λ·gain·(f_ref − f) + y_s·slime − y_c·c  이면 젖는다 (f = 젖은 마스크의 가우스 흐림)
//   공급 셀은 8이웃 가운데 가장 두꺼운 셀 (E, N, NE, SE, W, S, SW, NW 순서에서 처음으로 더 큰 것)
uniform sampler2D uA;     // 마름 뒤의 h, wet, age, sage
uniform sampler2D uB;     // g: slime
uniform sampler2D uF;     // r: 젖은 마스크의 흐림
uniform sampler2D uField; // r: 항복 잡음 η, g: 유인장 c
out vec4 o;
const ivec2 ALL[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(1, 1), ivec2(1, -1), ivec2(-1, 0), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 1));
const float NONE = -1e30;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  if (texelFetch(uA, c, 0).g > 0.5) { o = vec4(0.0); return; }
  float hz[8], wz[8];
  float pmax = NONE;
  int arg = 0;
  for (int q = 0; q < 8; q++) {
    vec4 t = texelFetch(uA, wr(c + ALL[q], n), 0);
    wz[q] = t.g > 0.5 ? 1.0 : 0.0;
    hz[q] = wz[q] * t.r;
    float v = t.g > 0.5 ? t.r : NONE;
    if (v > pmax) { pmax = v; arg = q; }
  }
  // 축 이웃: E(0), N(1), W(4), S(5)
  float ptest = max(max(wz[0] > 0.0 ? hz[0] : NONE, wz[1] > 0.0 ? hz[1] : NONE), max(wz[4] > 0.0 ? hz[4] : NONE, wz[5] > 0.0 ? hz[5] : NONE));
  // 대각 방향: 대각 이웃 D 와 그 사분면의 축 이웃 둘(X, Y)을 젖은 셀만으로 보간한다
  const ivec3 DIAG[4] = ivec3[4](ivec3(2, 0, 1), ivec3(3, 0, 5), ivec3(7, 4, 1), ivec3(6, 4, 5));
  for (int k = 0; k < 4; k++) {
    int d = DIAG[k].x, x = DIAG[k].y, y = DIAG[k].z;
    if (wz[d] > 0.0) {
      float den = {{WET_WA}} * (wz[x] + wz[y]) + {{WET_WD}} * wz[d];
      ptest = max(ptest, ({{WET_WA}} * (hz[x] + hz[y]) + {{WET_WD}} * hz[d]) / max(den, 1e-30));
    }
  }
  vec4 fld = texelFetch(uField, c, 0);
  float yld = {{HY0}} * (1.0 + {{Y_SIGMA}} * fld.r) + {{CURV_K}} * ({{CURV_REF}} - texelFetch(uF, c, 0).r) + {{Y_S}} * texelFetch(uB, c, 0).g - {{Y_C}} * fld.g;
  o = vec4(ptest > yld ? 1.0 : 0.0, float(arg), 0.0, 0.0);
}
