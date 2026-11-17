{{COMMON}}
// 규칙 4: 유량 Q_e = W_e·(p_i − p_j) 로 두께를 갱신한다. 간선마다 차이를 먼저 내므로 한 셀에서 나간 양이 이웃에 그대로 들어간다
uniform sampler2D uA; // h, wet, age, sage
uniform sampler2D uB; // θ, slime, p, 직전 p
uniform sampler2D uW; // 간선 가중치
uniform sampler2D uP; // 이번 스텝의 해
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
  oA = vec4(A.r - {{DT}} * div, A.g, A.g * (A.b + {{DT}}), A.g * (A.a + {{DT}}));
  oB = vec4(B.r, B.g, p, B.b);
}
