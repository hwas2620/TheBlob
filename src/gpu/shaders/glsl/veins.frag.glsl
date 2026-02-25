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

    // 줌 레벨 계산
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));
    vec2 texel = ({{STEP}} * zoomFactor) / u_mapSize;

    // 3x3 블러: 에이전트 개별 트레일을 평활화하여 수송 채널만 남김
    float value = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            value += texture(u_trailMap, fract(trailUV + vec2(float(dx), float(dy)) * texel)).r;
        }
    }
    value /= 9.0;

    // 줌 아웃 시 임계값 조정
    float veinMin = {{VEIN_MIN}} / zoomFactor;
    float veinMax = {{VEIN_MAX}};

    if (value < veinMin) {
        fragColor = vec4(0.0);
        return;
    }

    // 능선 검출: 더 넓은 범위 (STEP*2) 이웃과 비교
    vec2 farTexel = texel * 2.0;
    float right = texture(u_trailMap, fract(trailUV + vec2(farTexel.x, 0.0))).r;
    float up    = texture(u_trailMap, fract(trailUV + vec2(0.0, farTexel.y))).r;
    float left  = texture(u_trailMap, fract(trailUV - vec2(farTexel.x, 0.0))).r;
    float down  = texture(u_trailMap, fract(trailUV - vec2(0.0, farTexel.y))).r;
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
    // 상대적 ridge: 고밀도에서 개별 에이전트 노이즈 억제
    float relRidge = ridge / max(value, 1.0);
    // smoothstep으로 약한 릿지 제거, 강한 릿지만 선명하게
    float ridgeStrength = smoothstep(0.2, 0.5, relRidge * {{RIDGE_SCALE}});

    // 맥동 효과 — 파라미터화된 진폭
    float pulsePeriod = 120.0;
    float pulsePhase = mod(u_time, pulsePeriod) / pulsePeriod * 2.0 * 3.14159;
    float pulseBase = {{PULSE_MIN}} + ({{PULSE_MAX}} - {{PULSE_MIN}}) * (0.5 + 0.5 * sin(pulsePhase));

    // 정맥 계층화: 주정맥/모세정맥 분리
    float majorT = smoothstep({{MAJOR_THRESHOLD}} * 0.7, {{MAJOR_THRESHOLD}} * 1.3, value);

    // 계층별 알파 — 주정맥은 전체 맥동, 모세정맥은 약한 맥동
    float majorPulse = pulseBase;
    float minorPulse = mix(1.0, pulseBase, 0.3);
    float layerAlpha = mix({{MINOR_ALPHA}}, {{MAJOR_ALPHA}}, majorT);
    float layerPulse = mix(minorPulse, majorPulse, majorT);

    float alpha = densityT * ridgeStrength * layerAlpha * layerPulse;

    // 계층별 색상 — 주정맥(밝고 크림) / 모세정맥(어둡고 황갈)
    vec3 majorColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{MAJOR_R}}, {{MAJOR_G}}, {{MAJOR_B}});
    vec3 minorColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{MINOR_R}}, {{MINOR_G}}, {{MINOR_B}});
    vec3 veinColor = mix(minorColor, majorColor, majorT);

    fragColor = vec4(veinColor, alpha);
}
