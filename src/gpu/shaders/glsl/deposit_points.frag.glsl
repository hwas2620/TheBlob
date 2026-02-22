#version 300 es
precision highp float;

uniform float u_depositAmount;

flat in float v_flags; // 1.0=일반, 2.0=스카우트/먹이추적

out float fragColor;

void main() {
    // 개미 페로몬 모델: 스카우트/먹이추적 에이전트는 15배 강한 트레일
    // → 외부에 강력한 "고속도로" 형성, Jeff Jones가 자연스럽게 따라감
    float boost = v_flags > 1.5 ? 15.0 : 1.0;
    fragColor = u_depositAmount * boost;
}
