#version 300 es
precision highp float;

uniform float u_depositAmount;

out float fragColor;

void main() {
    fragColor = u_depositAmount;
}
