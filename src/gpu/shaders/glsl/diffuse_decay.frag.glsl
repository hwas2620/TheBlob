#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform vec2 u_texelSize;    // vec2(1.0/width, 1.0/height)
uniform float u_decayFactor; // 0.9 (활성) 또는 0.98 (휴면)

in vec2 v_uv;
out float fragColor;

void main() {
    float sum = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * u_texelSize;
            // fract()로 토러스 래핑 (GL_REPEAT과 동일 효과)
            vec2 sampleUV = fract(v_uv + offset);
            sum += texture(u_trailMap, sampleUV).r;
        }
    }
    fragColor = (sum / 9.0) * u_decayFactor;
}
