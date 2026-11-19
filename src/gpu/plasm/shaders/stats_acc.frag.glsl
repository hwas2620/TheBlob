{{COMMON}}
// 시험용 누적 (판정 도구의 입력): 구간 동안 간선의 유량 Q 와 |Q| 와 전도도 C 의 합, 셀의 두께의 합·최대·최소.
// 스텝마다 강화 뒤, 마름 앞에서 한 번 그린다 (numpy 기준 모델의 "rolling statistics" 자리). 게임에서는 돌지 않는다
uniform sampler2D uA;    // 유량 갱신 뒤의 h, wet (젖은 마스크는 스텝 시작 시점의 것)
uniform sampler2D uW;    // 간선 가중치
uniform sampler2D uP;    // 이번 스텝의 해
uniform sampler2D uC;    // 강화 뒤의 전도도
uniform sampler2D uAccQ; // ΣQ (E, N, NE, SE)
uniform sampler2D uAccG; // Σ|Q|
uniform sampler2D uAccC; // ΣC
uniform sampler2D uAccH; // Σh, 최대 h, 최소 h, 구간 내내 젖어 있었는가
uniform float uKeepFlow;  // 0 이면 유량·전도도 구간을 새로 시작한다
uniform float uKeepThick; // 0 이면 두께 구간을 새로 시작한다
layout(location = 0) out vec4 oQ;
layout(location = 1) out vec4 oG;
layout(location = 2) out vec4 oC;
layout(location = 3) out vec4 oH;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  float p = texelFetch(uP, c, 0).r;
  vec4 dp = p - vec4(texelFetch(uP, wr(c + ivec2(1, 0), n), 0).r, texelFetch(uP, wr(c + ivec2(0, 1), n), 0).r,
                     texelFetch(uP, wr(c + ivec2(1, 1), n), 0).r, texelFetch(uP, wr(c + ivec2(1, -1), n), 0).r);
  vec4 Q = texelFetch(uW, c, 0) * dp;
  oQ = uKeepFlow * texelFetch(uAccQ, c, 0) + Q;
  oG = uKeepFlow * texelFetch(uAccG, c, 0) + abs(Q);
  oC = uKeepFlow * texelFetch(uAccC, c, 0) + texelFetch(uC, c, 0);
  vec4 H = uKeepThick > 0.5 ? texelFetch(uAccH, c, 0) : vec4(0.0, -1e30, 1e30, 1.0);
  oH = vec4(H.r + A.r, max(H.g, A.r), min(H.b, A.r), H.a * (A.g > 0.5 ? 1.0 : 0.0));
}
