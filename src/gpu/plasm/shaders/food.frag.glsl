{{COMMON}}
// 규칙 8 (먹는 양): 텍셀 하나가 먹이 하나다. 원반 안의 젖은 셀 n 개가 단위 시간에 EAT 씩 먹는다
//   먹은 양 = min(EAT·n·dt, 남은 양),  셀 하나가 받는 두께 = GAIN·먹은 양/n
//   남은 양이 0 이 되면 그 먹이는 죽는다: 유인장의 세기가 e^(−(t − 떨어진 시각)/FADE) 로 줄고(1e-4 아래에서 멈춘다) 원반의 셀은 다시 늙는다
uniform sampler2D uA;       // h, wet, age, sage (젖은 마스크는 이 스텝의 시작 시점 것이다)
uniform sampler2D uB;       // r: θ (통계용)
uniform sampler2D uField;   // g: 먹이 원반의 번호 + 1
uniform sampler2D uFS;      // 먹이 상태: 남은 양, 유인장의 세기, 떨어진 스텝, 셀 하나가 받는 두께
uniform sampler2D uFoodPos; // rg: 원반을 훑는 창의 가운데 셀
uniform int uStep;
layout(location = 0) out vec4 oS;    // 새 먹이 상태
layout(location = 1) out vec4 oStat; // 원반의 젖은 셀 수, 두께의 합, 젖은 셀의 Σcos θ, Σsin θ
void main() {
  int k = int(gl_FragCoord.x);
  ivec2 n = textureSize(uA, 0);
  ivec2 ctr = ivec2(texelFetch(uFoodPos, ivec2(k, 0), 0).rg);
  float id = float(k + 1);
  float cnt = 0.0, sh = 0.0, sc = 0.0, ss = 0.0;
  for (int dy = -{{FOOD_WIN}}; dy <= {{FOOD_WIN}}; dy++) {
    for (int dx = -{{FOOD_WIN}}; dx <= {{FOOD_WIN}}; dx++) {
      ivec2 c = wr(ctr + ivec2(dx, dy), n);
      if (texelFetch(uField, c, 0).g == id) {
        vec4 A = texelFetch(uA, c, 0);
        sh += A.r;
        if (A.g > 0.5) {
          float th = texelFetch(uB, c, 0).r;
          cnt += 1.0;
          sc += cos(th);
          ss += sin(th);
        }
      }
    }
  }
  vec4 S = texelFetch(uFS, ivec2(k, 0), 0);
  float M = S.r, amp = S.g, sx = S.b, add = 0.0;
  if (M > 0.0 && cnt > 0.0) {
    float amt = min({{EAT}} * cnt * {{DT}}, M);
    float left = M - amt;
    // 남은 양에서 실제로 빠진 만큼만 두께로 준다 (float32 의 반올림으로 먹은 양과 준 양이 어긋나지 않게). 줄지 않는 먹이는 그대로
    add = {{GAIN}} * (M > {{FOOD_UNLIMITED}} ? amt : M - left) / cnt;
    M = left;
    if (M <= 1e-12) { M = 0.0; sx = float(uStep); }
  }
  if (M <= 0.0 && amp > 1e-4) amp = exp(-(float(uStep) - sx) * {{DT}} / {{FADE}});
  oS = vec4(M, amp, sx, add);
  oStat = vec4(cnt, sh, sc, ss);
}
