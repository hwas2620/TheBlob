{{COMMON}}
// 간선 켜기: 양 끝이 젖은 간선만 남긴다. 새로 켜진 간선(저장된 전도도가 0)은 초기 전도도를 받는다
uniform sampler2D uA;     // h, wet, age, sage
uniform sampler2D uC;     // 간선 전도도 E, N, NE, SE
uniform sampler2D uCinit; // 새 간선의 전도도
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 act = texelFetch(uA, c, 0).g * vec4(
    texelFetch(uA, wr(c + ivec2(1, 0), n), 0).g, texelFetch(uA, wr(c + ivec2(0, 1), n), 0).g,
    texelFetch(uA, wr(c + ivec2(1, 1), n), 0).g, texelFetch(uA, wr(c + ivec2(1, -1), n), 0).g);
  vec4 C = texelFetch(uC, c, 0);
  o = act * mix(C, texelFetch(uCinit, c, 0), vec4(equal(C, vec4(0.0))));
}
