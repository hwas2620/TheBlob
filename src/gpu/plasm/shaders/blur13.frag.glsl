{{COMMON}}
// 한 방향 가우스 흐림 (감김). 핵은 scipy.ndimage.gaussian_filter(σ, truncate=3) 와 같다
uniform sampler2D uSrc;
uniform ivec2 uDir;
uniform int uCh; // 읽을 채널 (0 = r, 1 = g)
out vec4 o;
const float K[{{BLUR_TAPS}}] = float[{{BLUR_TAPS}}]({{BLUR_KERNEL}});
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy);
  ivec2 n = textureSize(uSrc, 0);
  float s = 0.0;
  for (int i = -{{BLUR_RADIUS}}; i <= {{BLUR_RADIUS}}; i++) {
    vec4 t = texelFetch(uSrc, wr(c + i * uDir, n), 0);
    s += K[i + {{BLUR_RADIUS}}] * (uCh == 1 ? t.g : t.r);
  }
  o = vec4(s);
}
