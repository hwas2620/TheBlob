#version 300 es
precision highp float;

// 각 점이 1.0을 출력 → 가산 블렌딩으로 셀당 에이전트 수 합산
out float fragColor;

void main() {
    fragColor = 1.0;
}
