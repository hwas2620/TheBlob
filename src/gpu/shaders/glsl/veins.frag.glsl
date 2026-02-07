#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;
uniform bool u_isDormant;
uniform float u_time;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    float value = texture(u_trailMap, trailUV).r;

    // 줌 레벨 계산
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));

    // 줌 아웃 시 임계값 조정
    float veinMin = {{VEIN_MIN}} / zoomFactor;
    float veinMax = {{VEIN_MAX}};

    if (value < veinMin) {
        fragColor = vec4(0.0);
        return;
    }
    vec2 texel = ({{STEP}} * zoomFactor) / u_mapSize;
    float right = texture(u_trailMap, fract(trailUV + vec2(texel.x, 0.0))).r;
    float up    = texture(u_trailMap, fract(trailUV + vec2(0.0, texel.y))).r;
    float left  = texture(u_trailMap, fract(trailUV - vec2(texel.x, 0.0))).r;
    float down  = texture(u_trailMap, fract(trailUV - vec2(0.0, texel.y))).r;

    // 능선 검출: 현재 값이 이웃 평균보다 높은 곳 = 고밀도 경로 중심
    float avg = (right + left + up + down) * 0.25;
    float ridge = value - avg;

    // 아주 작은 음수도 허용 (확산으로 평평해진 영역 대응)
    if (ridge < -0.5) {
        fragColor = vec4(0.0);
        return;
    }
    // 작은 ridge는 0으로 클램프
    ridge = max(ridge, 0.0);

    // 밀도에 비례한 기본 강도 + 능선 강도
    float densityT = clamp((value - veinMin) / (veinMax - veinMin), 0.0, 1.0);
    float ridgeStrength = clamp(ridge * {{RIDGE_SCALE}}, 0.0, 1.0);

    // 맥동 효과 (60-180초 주기 → 평균 120초 = 2분)
    // 실제 Physarum의 cytoplasmic streaming 재현
    float pulsePeriod = 120.0; // 초
    float pulsePhase = mod(u_time, pulsePeriod) / pulsePeriod * 2.0 * 3.14159;
    float pulseIntensity = 0.85 + 0.15 * sin(pulsePhase); // 0.85~1.0 범위

    float alpha = densityT * ridgeStrength * {{MAX_ALPHA}} * pulseIntensity;

    vec3 veinColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{ACTIVE_R}}, {{ACTIVE_G}}, {{ACTIVE_B}});

    fragColor = vec4(veinColor, alpha);
}
