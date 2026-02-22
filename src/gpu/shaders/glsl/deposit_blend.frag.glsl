#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform sampler2D u_depositMap;

in vec2 v_uv;
out float fragColor;

void main() {
    float trail = texture(u_trailMap, v_uv).r;
    float deposit = texture(u_depositMap, v_uv).r;
    // 가산 블렌딩: 에이전트 밀집 영역에서 트레일 축적 + 먹이 신호 침투 허용
    // (max()는 블롭 내부에서 deposit을 완전히 무시 → 먹이 방향 신호 차단)
    fragColor = trail + deposit;
}
