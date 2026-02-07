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

    // 줌 레벨 계산
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));

    // 트레일맵에서 값 읽기 (3x3 평균)
    float sum = 0.0;
    vec2 texel = zoomFactor / u_mapSize;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            sum += texture(u_trailMap, fract(trailUV + offset)).r;
        }
    }
    float value = sum / 9.0;

    // 최소 임계값 미만이면 투명
    float minThreshold = {{MIN_THRESHOLD}} / zoomFactor;
    if (value < minThreshold) {
        fragColor = vec4(0.0);
        return;
    }

    // 정규화 (0~maxValue → 0~1)
    float maxValue = {{MAX_VALUE}};
    float intensity = clamp(value / maxValue, 0.0, 1.0);

    // 그라데이션 색상 (연한 청록색 → 녹색)
    vec3 lowColor = vec3({{LOW_R}}, {{LOW_G}}, {{LOW_B}});
    vec3 highColor = vec3({{HIGH_R}}, {{HIGH_G}}, {{HIGH_B}});
    vec3 fieldColor = mix(lowColor, highColor, intensity);

    float baseAlpha = intensity * {{BASE_ALPHA}};

    // === 등고선 (중앙차분으로 그래디언트 계산) ===
    float valueR = texture(u_trailMap, fract(trailUV + vec2(texel.x, 0.0))).r;
    float valueU = texture(u_trailMap, fract(trailUV + vec2(0.0, texel.y))).r;
    float iR = clamp(valueR / maxValue, 0.0, 1.0);
    float iU = clamp(valueU / maxValue, 0.0, 1.0);
    vec2 grad = vec2(iR - intensity, iU - intensity);
    float gradLen = length(grad);

    // 등고선 레벨
    float contourColor = 0.0;
    float levels[5] = float[5](0.1, 0.25, 0.4, 0.6, 0.8);
    for (int i = 0; i < 5; i++) {
        float dist = abs(intensity - levels[i]);
        float pixelDist = gradLen > 0.0001 ? dist / gradLen : 9999.0;
        float line = 1.0 - smoothstep(0.0, {{LINE_WIDTH}}, pixelDist);
        contourColor = max(contourColor, line);
    }

    // 등고선 합성
    vec3 contourRGB = vec3({{CONTOUR_R}}, {{CONTOUR_G}}, {{CONTOUR_B}});
    float contourAlpha = contourColor * {{CONTOUR_ALPHA}};

    // 최종 색상
    vec3 finalColor = mix(fieldColor, contourRGB, contourColor * 0.5);
    float finalAlpha = max(baseAlpha, contourAlpha);

    fragColor = vec4(finalColor, finalAlpha);
}
