{{COMMON}}
// 규칙 4: 유량 Q_e = W_e·(p_i − p_j) 로 두께를 갱신한다. 간선마다 차이를 먼저 내므로 한 셀에서 나간 양이 이웃에 그대로 들어간다
// 규칙 8: 먹이 원반의 젖은 셀은 이번 스텝에 먹은 만큼 두꺼워지고, 살아 있는 먹이 위에서는 늙지 않는다 (sage 가 멈춘다)
uniform sampler2D uA; // h, wet, age, sage
uniform sampler2D uB; // θ, slime, p, 직전 p
uniform sampler2D uW; // 간선 가중치
uniform sampler2D uP; // 이번 스텝의 해
#if {{FOOD_ACTIVE}}
uniform sampler2D uField; // g: 먹이 원반의 번호 + 1
uniform sampler2D uFS;    // 이번 스텝에 먹은 뒤의 먹이 상태. r: 남은 양, a: 셀 하나가 받는 두께
#endif
layout(location = 0) out vec4 oA;
layout(location = 1) out vec4 oB;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  vec4 B = texelFetch(uB, c, 0);
  ivec2 e = wr(c + ivec2(1, 0), n), w = wr(c + ivec2(-1, 0), n), nn = wr(c + ivec2(0, 1), n), s = wr(c + ivec2(0, -1), n);
  ivec2 ne = wr(c + ivec2(1, 1), n), sw = wr(c + ivec2(-1, -1), n), se = wr(c + ivec2(1, -1), n), nw = wr(c + ivec2(-1, 1), n);
  float p = texelFetch(uP, c, 0).r;
  vec4 w0 = texelFetch(uW, c, 0);
  float div = w0.r * (p - texelFetch(uP, e, 0).r) + texelFetch(uW, w, 0).r * (p - texelFetch(uP, w, 0).r)
            + w0.g * (p - texelFetch(uP, nn, 0).r) + texelFetch(uW, s, 0).g * (p - texelFetch(uP, s, 0).r)
            + w0.b * (p - texelFetch(uP, ne, 0).r) + texelFetch(uW, sw, 0).b * (p - texelFetch(uP, sw, 0).r)
            + w0.a * (p - texelFetch(uP, se, 0).r) + texelFetch(uW, nw, 0).a * (p - texelFetch(uP, nw, 0).r);
#if {{FOOD_ACTIVE}}
  float add = 0.0, live = 0.0;
  float id = texelFetch(uField, c, 0).g;
  if (id > 0.5) {
    vec4 S = texelFetch(uFS, ivec2(int(id) - 1, 0), 0);
    add = S.a;
    if (S.r > 0.0) live = {{RESERVOIR}};
  }
  oA = vec4(A.r - {{DT}} * div + A.g * add, A.g, A.g * (A.b + {{DT}}), A.g * (A.a + {{DT}} * (1.0 - live)));
#else
  oA = vec4(A.r - {{DT}} * div, A.g, A.g * (A.b + {{DT}}), A.g * (A.a + {{DT}}));
#endif
  oB = vec4(B.r, B.g, p, B.b);
}
