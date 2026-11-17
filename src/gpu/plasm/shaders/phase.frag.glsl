{{COMMON}}
// 규칙 1 (부분 스텝 한 번): dθ/dt = ω·(1 + D_OMEGA·(1 − e^(−sage/τ_a))) + D_θ·Σ w·sin(θ_j − θ_i)
// 결합 가중치는 축 이웃 4/6, 대각 이웃 1/6. 마른 셀의 θ 는 0
uniform sampler2D uA; // h, wet, age, sage
uniform sampler2D uB; // θ, slime, p, 직전 p
out vec4 o;
const float TWO_PI = 6.283185307179586;
const ivec2 NB[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(-1, 0), ivec2(0, -1), ivec2(1, 1), ivec2(1, -1), ivec2(-1, 1), ivec2(-1, -1));
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uA, 0);
  vec4 A = texelFetch(uA, c, 0);
  vec4 B = texelFetch(uB, c, 0);
  if (A.g < 0.5) { o = vec4(0.0, B.g, B.b, B.a); return; }
  float coup = 0.0;
  for (int q = 0; q < 8; q++) {
    ivec2 j = wr(c + NB[q], n);
    if (texelFetch(uA, j, 0).g > 0.5) coup += (q < 4 ? 0.6666666666666666 : 0.16666666666666666) * sin(texelFetch(uB, j, 0).r - B.r);
  }
  float om = {{OMEGA0}} * (1.0 + {{D_OMEGA}} * (1.0 - exp(-A.a / {{TAU_A}})));
  float th = B.r + {{DTS}} * (om + {{D_THETA}} * coup);
  o = vec4(th - TWO_PI * floor(th / TWO_PI), B.g, B.b, B.a);
}
