{{COMMON}}
// 규칙 2 와 3 의 준비: 쉬는 두께 h*, 압력 방정식의 우변과 차폐 항, 간선 가중치
//   h* = [h0·H·e^(−sage/τ_a)·(1 − (1 − h_fill/h0)·e^(−age/τ_f)) + min(β·√C_인접최대, cap)]·(1 + ε·cos(θ + ψ))
//   ψ  = 위상 무늬 (나): 크기가 일정한 기울기를 삼각 격자로 주고 방향을 돌리며 천천히 흘린다 (TRI_K = 0 이면 꺼짐)
//   H  = 규칙 8 의 저장 배율. 살아 있는 먹이 위의 젖은 셀에서 τ_H 로 H_MAX 를 향해 오른다.
//        RES_GATE 가 있으면 셀이 직전 스텝의 쉬는 두께(맥동을 뺀 값)의 그 비율 이상 차 있을 때만 오른다. 마른 셀과 갓 젖은 셀은 1
uniform sampler2D uA; // h, wet, age, sage
uniform sampler2D uB; // θ, slime, p, 직전 p
uniform sampler2D uC; // 켜진 간선의 전도도
uniform sampler2D uG; // 정적 간선 잡음
uniform float uT;     // 모델 시간
layout(location = 0) out vec4 oAux; // 우변, 차폐 항, 인접 최대 전도도, h*
layout(location = 1) out vec4 oW;   // 간선 가중치 W = G·(C + r)/L
#if {{FOOD_STORE}}
uniform sampler2D uH;     // r: 저장 배율 H, g: 직전 스텝의 쉬는 두께 (맥동을 뺀 값)
uniform sampler2D uField; // g: 먹이 원반의 번호 + 1
uniform sampler2D uFS;    // 먹이 상태. r: 남은 양
layout(location = 2) out vec4 oH;   // 새 H, 이번 스텝의 쉬는 두께 (맥동을 뺀 값)
#endif
float tri(float u) { return abs(mod(u + 0.5 * {{TRI_P}}, {{TRI_P}}) - 0.5 * {{TRI_P}}) - 0.25 * {{TRI_P}}; }
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  vec4 C0 = texelFetch(uC, c, 0);
  float cW = texelFetch(uC, wr(c + ivec2(-1, 0), n), 0).r, cS = texelFetch(uC, wr(c + ivec2(0, -1), n), 0).g;
  float cSW = texelFetch(uC, wr(c + ivec2(-1, -1), n), 0).b, cNW = texelFetch(uC, wr(c + ivec2(-1, 1), n), 0).a;
  float Cn = max(max(max(C0.r, C0.g), max(C0.b, C0.a)), max(max(cW, cS), max(cSW, cNW)));
#if {{FOOD_STORE}}
  vec2 D = texelFetch(uH, c, 0).rg;
  float H = (A.g > 0.5 && A.b > 0.0) ? D.r : 1.0;
  float id = texelFetch(uField, c, 0).g;
  bool grow = A.g > 0.5 && id > 0.5 && texelFetch(uFS, ivec2(int(id) - 1, 0), 0).r > 0.0;
#if {{RES_GATE_ON}}
  grow = grow && A.r >= {{RES_GATE}} * D.g;
#endif
  if (grow) H += {{DT}} * ({{H_MAX}} - H) / {{TAU_H}};
  float hs = {{H0}} * H * exp(-A.a / {{TAU_A}}) * (1.0 - (1.0 - {{H_FILL}} / {{H0}}) * exp(-A.b / {{TAU_F}}));
#else
  float hs = {{H0}} * exp(-A.a / {{TAU_A}}) * (1.0 - (1.0 - {{H_FILL}} / {{H0}}) * exp(-A.b / {{TAU_F}}));
#endif
  float tube = min({{BETA}} * sqrt(Cn), {{CAP}});
  float psi = {{TRI_K}} * (cos({{TRI_OMEGA}} * uT) * tri(float(c.x) - {{TRI_V}} * uT) + sin({{TRI_OMEGA}} * uT) * tri(float(c.y) - 0.618 * {{TRI_V}} * uT));
  float hstar = (hs + tube) * (1.0 + {{EPS}} * cos(texelFetch(uB, c, 0).r + psi));
  oAux = vec4(A.g * (A.r - hstar) / {{DT}}, A.g * {{INV_KAPPA_DT}}, Cn, hstar);
  oW = vec4(greaterThan(C0, vec4(0.0))) * texelFetch(uG, c, 0) * (C0 + {{R_BASE}}) * vec4(1.0, 1.0, 0.7071067811865476, 0.7071067811865476);
#if {{FOOD_STORE}}
  oH = vec4(H, hs + tube, 0.0, 0.0);
#endif
}
