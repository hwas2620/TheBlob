{{COMMON}}
// 규칙 5: dC/dt = rate·((|Q|/Q0)^γ − C),  Q0 = Q0_AUTO·(활성 간선의 |Q|^γ 평균)^(1/γ)
uniform sampler2D uC;   // 켜진 간선의 전도도
uniform sampler2D uW;
uniform sampler2D uP;
uniform sampler2D uRed; // 1×1: (|Q|^γ 합, 활성 간선 수, ·, ·)
out vec4 o;
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uC, 0);
  vec4 C = texelFetch(uC, c, 0);
  vec4 W = texelFetch(uW, c, 0);
  float p = texelFetch(uP, c, 0).r;
  vec4 dp = p - vec4(texelFetch(uP, wr(c + ivec2(1, 0), n), 0).r, texelFetch(uP, wr(c + ivec2(0, 1), n), 0).r,
                     texelFetch(uP, wr(c + ivec2(1, 1), n), 0).r, texelFetch(uP, wr(c + ivec2(1, -1), n), 0).r);
  vec4 tot = texelFetch(uRed, ivec2(0), 0);
  float Q0 = tot.g > 0.0 ? max({{Q0_FLOOR}}, {{Q0_AUTO}} * pow(tot.r / tot.g, 1.0 / {{GAMMA}})) : {{Q0_FLOOR}};
  vec4 f = pow(abs(W * dp) / Q0, vec4({{GAMMA}}));
  o = vec4(greaterThan(W, vec4(0.0))) * clamp(C + {{DT}} * {{RATE}} * (f - C), 0.0, {{C_MAX}});
}
