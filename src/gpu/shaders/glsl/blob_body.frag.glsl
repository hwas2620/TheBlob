#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform sampler2D u_occupancyMap;  // 밀집도 맵 (에이전트 수/셀)
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;
uniform bool u_isDormant;
uniform int u_viewMode;  // 0 = 페로몬, 1 = 밀집도

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    // === 밀집도 뷰 모드 ===
    if (u_viewMode == 1) {
        float density = texture(u_occupancyMap, trailUV).r;

        // 밀집도 히트맵 색상 (파랑 → 초록 → 노랑 → 빨강)
        vec3 color;
        if (density < 1.0) {
            // 빈 셀: 투명
            fragColor = vec4(0.0);
            return;
        } else if (density < 3.0) {
            // 저밀도: 파랑 → 초록
            float t = (density - 1.0) / 2.0;
            color = mix(vec3(0.0, 0.3, 0.8), vec3(0.0, 0.8, 0.2), t);
        } else if (density < 10.0) {
            // 중밀도: 초록 → 노랑
            float t = (density - 3.0) / 7.0;
            color = mix(vec3(0.0, 0.8, 0.2), vec3(1.0, 0.9, 0.0), t);
        } else {
            // 고밀도: 노랑 → 빨강
            float t = clamp((density - 10.0) / 20.0, 0.0, 1.0);
            color = mix(vec3(1.0, 0.9, 0.0), vec3(1.0, 0.1, 0.0), t);
        }

        float alpha = clamp(density / 5.0, 0.3, 0.95);
        fragColor = vec4(color, alpha);
        return;
    }

    // === 트레일맵 직접 렌더링 ===

    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));
    float sampleRadius = {{DILATE_RADIUS}} * zoomFactor;
    vec2 texel = sampleRadius / u_mapSize;

    float threshold = {{FADE_START}};
    float maxValue = {{MAX_VALUE}};

    float neighborSum = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            neighborSum += texture(u_trailMap, fract(trailUV + offset)).r;
        }
    }
    float avgVal = neighborSum / 9.0;

    float adjustedThreshold = threshold / zoomFactor;
    if (avgVal < adjustedThreshold) {
        fragColor = vec4(0.0);
        return;
    }

    // 본체 색상 (trail 강도에 비례한 색상/알파)
    float densityT = clamp((avgVal - adjustedThreshold) / (maxValue - adjustedThreshold), 0.0, 1.0);

    vec3 baseColor = u_isDormant
        ? vec3({{DORMANT_BASE_R}}, {{DORMANT_BASE_G}}, {{DORMANT_BASE_B}})
        : vec3({{ACTIVE_BASE_R}}, {{ACTIVE_BASE_G}}, {{ACTIVE_BASE_B}});
    vec3 darkColor = u_isDormant
        ? vec3({{DORMANT_DARK_R}}, {{DORMANT_DARK_G}}, {{DORMANT_DARK_B}})
        : vec3({{ACTIVE_DARK_R}}, {{ACTIVE_DARK_G}}, {{ACTIVE_DARK_B}});

    vec3 bodyColor = mix(darkColor, baseColor, sqrt(densityT));
    float alpha = smoothstep(adjustedThreshold, adjustedThreshold * 3.0, avgVal);
    fragColor = vec4(bodyColor, alpha);
}
