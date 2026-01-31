#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;
uniform bool u_isDormant;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    float value = texture(u_trailMap, trailUV).r;

    float threshold = {{FADE_START}};
    float maxValue = {{MAX_VALUE}};

    // ── 3x3 이웃 평균 → 고립 점 무시, 밀집 영역만 막 형성 ──
    vec2 texel = {{DILATE_RADIUS}} / u_mapSize;
    float neighborSum = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            neighborSum += texture(u_trailMap, fract(trailUV + offset)).r;
        }
    }
    float avgVal = neighborSum / 9.0;

    // 본체 판정: 이웃 평균 기준 (에이전트 밀집도)
    float bodyThreshold = 25.0;  // 본체: 에이전트가 많이 모인 곳

    // 최소 임계값 미만이면 투명
    if (avgVal < threshold) {
        fragColor = vec4(0.0);
        return;
    }

    if (avgVal >= bodyThreshold) {
        // ── 본체: 에이전트가 밀집한 활성 영역 ──
        // 선명한 경계를 위해 가파른 smoothstep
        float alpha = smoothstep(bodyThreshold * 0.95, bodyThreshold * 1.1, avgVal);
        float densityT = clamp((value - bodyThreshold) / (maxValue - bodyThreshold), 0.0, 1.0);

        vec3 baseColor = u_isDormant
            ? vec3({{DORMANT_BASE_R}}, {{DORMANT_BASE_G}}, {{DORMANT_BASE_B}})
            : vec3({{ACTIVE_BASE_R}}, {{ACTIVE_BASE_G}}, {{ACTIVE_BASE_B}});
        vec3 darkColor = u_isDormant
            ? vec3({{DORMANT_DARK_R}}, {{DORMANT_DARK_G}}, {{DORMANT_DARK_B}})
            : vec3({{ACTIVE_DARK_R}}, {{ACTIVE_DARK_G}}, {{ACTIVE_DARK_B}});

        vec3 bodyColor = mix(darkColor, baseColor, sqrt(densityT));
        fragColor = vec4(bodyColor, alpha);
    } else {
        // ── 점액 흔적: 에이전트가 지나갔지만 떠난 영역 ──
        // 매우 얇고 투명한 막
        float trailAlpha = smoothstep(threshold, bodyThreshold * 0.6, avgVal) * 0.06;
        vec3 trailColor = u_isDormant
            ? vec3(0.20, 0.16, 0.10)  // 휴면: 어두운 갈색
            : vec3(0.45, 0.40, 0.15);  // 활성: 연한 갈색

        fragColor = vec4(trailColor, trailAlpha);
    }
}
