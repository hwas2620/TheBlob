#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform sampler2D u_depositMap;

in vec2 v_uv;
out float fragColor;

void main() {
    float trail = texture(u_trailMap, v_uv).r;
    float deposit = texture(u_depositMap, v_uv).r;
    // 논문: "fixing concentration at food sources" = 최댓값 유지
    fragColor = max(trail, deposit);
}
