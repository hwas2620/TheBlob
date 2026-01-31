#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    // 블록 영역 평균 (5x5 샘플링으로 근사)
    float step_ = {{SAMPLE_STEP}};
    float sum = 0.0;
    for (int dy = -2; dy <= 2; dy++) {
        for (int dx = -2; dx <= 2; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * step_ / u_mapSize;
            sum += texture(u_trailMap, fract(trailUV + offset)).r;
        }
    }
    float avgDensity = sum / 25.0;

    if (avgDensity <= {{THRESHOLD}}) {
        fragColor = vec4(0.0);
        return;
    }

    float intensity = clamp((avgDensity - {{THRESHOLD}}) / {{INTENSITY_RANGE}}, 0.0, 1.0);

    // 블록 내 상대 좌표 (0~1)
    vec2 blockStart = floor(screenPos / {{BLOCK_SIZE}}) * {{BLOCK_SIZE}};
    vec2 localPos = (screenPos - blockStart) / {{BLOCK_SIZE}};

    // 간격 마진 (0~0.1 = 간격, 0.1~0.9 = 타일, 0.9~1.0 = 간격)
    float margin = 0.08;
    vec2 tilePos = (localPos - margin) / (1.0 - 2.0 * margin);

    // 타일 범위 밖이면 투명
    if (tilePos.x < 0.0 || tilePos.x > 1.0 || tilePos.y < 0.0 || tilePos.y > 1.0) {
        fragColor = vec4(0.0);
        return;
    }

    // 타일 내부에서 가장자리까지의 거리
    vec2 edgeDist = min(tilePos, 1.0 - tilePos);
    float minEdgeDist = min(edgeDist.x, edgeDist.y);

    // 유리판 효과: 전체 채우기 + 가장자리 더 밝게
    float baseFill = 0.3; // 기본 투명도
    float edgeHighlight = smoothstep(0.0, 0.25, minEdgeDist); // 가장자리가 더 밝음

    float totalGlow = baseFill + (1.0 - edgeHighlight) * 0.4;

    float alpha = intensity * totalGlow * {{ALPHA_MULTIPLIER}};

    fragColor = vec4({{COLOR_R}}, {{COLOR_G}}, {{COLOR_B}}, alpha);
}
