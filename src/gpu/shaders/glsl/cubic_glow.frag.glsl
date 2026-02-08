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

    // 타일 마진 체크를 먼저 수행 (텍스처 읽기 전에 빈 영역 스킵)
    vec2 blockStart = floor(screenPos / {{BLOCK_SIZE}}) * {{BLOCK_SIZE}};
    vec2 localPos = (screenPos - blockStart) / {{BLOCK_SIZE}};

    float margin = 0.08;
    vec2 tilePos = (localPos - margin) / (1.0 - 2.0 * margin);

    // 타일 범위 밖이면 즉시 투명 (텍스처 읽기 스킵)
    if (tilePos.x < 0.0 || tilePos.x > 1.0 || tilePos.y < 0.0 || tilePos.y > 1.0) {
        fragColor = vec4(0.0);
        return;
    }

    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    // 조기 종료: 중앙 샘플로 빈 영역 빠르게 감지
    float centerVal = texture(u_trailMap, trailUV).r;
    if (centerVal < {{THRESHOLD}} * 0.5) {
        fragColor = vec4(0.0);
        return;
    }

    // 줌 레벨에 따른 동적 샘플링
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));

    // 9포인트 샘플링 (중앙 + 십자 + 대각선) - 25개에서 9개로 축소
    float step_ = {{SAMPLE_STEP}} * zoomFactor;
    vec2 texelStep = step_ / u_mapSize;

    float sum = centerVal;
    // 십자 (4개)
    sum += texture(u_trailMap, fract(trailUV + vec2( texelStep.x,  0.0))).r;
    sum += texture(u_trailMap, fract(trailUV + vec2(-texelStep.x,  0.0))).r;
    sum += texture(u_trailMap, fract(trailUV + vec2( 0.0,  texelStep.y))).r;
    sum += texture(u_trailMap, fract(trailUV + vec2( 0.0, -texelStep.y))).r;
    // 대각선 (4개, 2배 간격)
    vec2 diagStep = texelStep * 2.0;
    sum += texture(u_trailMap, fract(trailUV + vec2( diagStep.x,  diagStep.y))).r;
    sum += texture(u_trailMap, fract(trailUV + vec2(-diagStep.x,  diagStep.y))).r;
    sum += texture(u_trailMap, fract(trailUV + vec2( diagStep.x, -diagStep.y))).r;
    sum += texture(u_trailMap, fract(trailUV + vec2(-diagStep.x, -diagStep.y))).r;

    float avgDensity = sum / 9.0;

    if (avgDensity <= {{THRESHOLD}}) {
        fragColor = vec4(0.0);
        return;
    }

    float intensity = clamp((avgDensity - {{THRESHOLD}}) / {{INTENSITY_RANGE}}, 0.0, 1.0);

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
