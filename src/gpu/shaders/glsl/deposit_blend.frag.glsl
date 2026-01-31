#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform sampler2D u_depositMap;

in vec2 v_uv;
out float fragColor;

void main() {
    float trail = texture(u_trailMap, v_uv).r;
    float deposit = texture(u_depositMap, v_uv).r;
    fragColor = min(255.0, trail + deposit);
}
