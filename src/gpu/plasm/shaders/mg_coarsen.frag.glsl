{{COMMON}}
// 조대 연산자: 간선 가중치는 집합체 사이를 건너는 미세 간선의 합에 1/scale 을 곱하고, 차폐 항은 자식 넷의 합 그대로
uniform sampler2D uWf; // 미세 가중치
uniform sampler2D uMf; // 미세 차폐 항 (g)
layout(location = 0) out vec4 oW;
layout(location = 1) out vec4 oM;
void main() {
  ivec2 C = ivec2(gl_FragCoord.xy);
  ivec2 nf = textureSize(uWf, 0);
  int i = 2 * C.x, j = 2 * C.y, i1 = i + 1, j1 = j + 1, j2 = (j + 2) % nf.y;
  vec4 a = texelFetch(uWf, ivec2(i1, j), 0);   // (j, i1)
  vec4 b = texelFetch(uWf, ivec2(i1, j1), 0);  // (j1, i1)
  vec4 d = texelFetch(uWf, ivec2(i, j1), 0);   // (j1, i)
  float e = texelFetch(uWf, ivec2(i, j2), 0).a; // (j2, i) 의 SE 간선
  oW = {{MG_COARSE_F}} * vec4(a.r + b.r + a.b + b.a, d.g + b.g + d.b + e, b.b, a.a);
  float m = texelFetch(uMf, ivec2(i, j), 0).g + texelFetch(uMf, ivec2(i1, j), 0).g + texelFetch(uMf, ivec2(i, j1), 0).g + texelFetch(uMf, ivec2(i1, j1), 0).g;
  oM = vec4(0.0, m, 0.0, 0.0);
}
