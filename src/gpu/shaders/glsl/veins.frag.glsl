#version 300 es
precision highp float;

uniform sampler2D u_trailMap;      // 확산 맵 (본체 마스킹 + Hessian ridge 입력)
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

    // 1. 본체 마스킹: 확산 맵 기준 veinMin 미만 제거
    float bodyValue = texture(u_trailMap, trailUV).r;
    float veinMin = {{VEIN_MIN}};
    if (bodyValue < veinMin) {
        fragColor = vec4(0.0);
        return;
    }

    // 2. 줌 레벨 계산
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));

    // 3. Hessian ridge detection (확산 맵에서 — 점 노이즈 원천 제거)
    float h = {{HESSIAN_STEP}} * zoomFactor;
    vec2 dxH = vec2(h / u_mapSize.x, 0.0);
    vec2 dyH = vec2(0.0, h / u_mapSize.y);

    // 9 texture fetches: center + 상하좌우 4 + 대각 4
    // GL_REPEAT 래핑으로 토러스 경계 자동 처리 (fract 불필요)
    float c  = texture(u_trailMap, trailUV).r;
    float l  = texture(u_trailMap, trailUV - dxH).r;
    float r  = texture(u_trailMap, trailUV + dxH).r;
    float up = texture(u_trailMap, trailUV + dyH).r;
    float dn = texture(u_trailMap, trailUV - dyH).r;
    float tr = texture(u_trailMap, trailUV + dxH + dyH).r;
    float tl = texture(u_trailMap, trailUV - dxH + dyH).r;
    float br = texture(u_trailMap, trailUV + dxH - dyH).r;
    float bl = texture(u_trailMap, trailUV - dxH - dyH).r;

    // Hessian 행렬 요소
    float h2 = h * h;
    float Hxx = (l + r - 2.0 * c) / h2;
    float Hyy = (up + dn - 2.0 * c) / h2;
    float Hxy = (tr + bl - tl - br) / (4.0 * h2);

    // 고유값: lambda2 = 0.5*trace - sqrt(discriminant)
    float traceH = Hxx + Hyy;
    float det = Hxx * Hyy - Hxy * Hxy;
    float disc = max(traceH * traceH * 0.25 - det, 0.0);
    float sqrtDisc = sqrt(disc);
    float lambda2 = 0.5 * traceH - sqrtDisc;

    // ridgeness: 큰 음의 고유값 = 능선 (감수 반영: lambda2 직접 사용)
    float ridgeness = max(-lambda2, 0.0);

    // 정규화: 밀도 비례 스케일링
    float normalizedRidge = ridgeness / max(c, 1.0);

    // 강도 매핑
    float intensity = smoothstep({{RIDGE_THRESHOLD}}, {{RIDGE_SATURATE}}, normalizedRidge);

    if (intensity < 0.01) {
        fragColor = vec4(0.0);
        return;
    }

    // 4. 맥동 효과
    float pulsePeriod = 120.0;
    float pulsePhase = mod(u_time, pulsePeriod) / pulsePeriod * 2.0 * 3.14159;
    float pulseBase = {{PULSE_MIN}} + ({{PULSE_MAX}} - {{PULSE_MIN}}) * (0.5 + 0.5 * sin(pulsePhase));

    // 5. 정맥 계층화: 확산 맵 기반 주정맥/모세정맥
    float majorT = smoothstep({{MAJOR_THRESHOLD}} * 0.7, {{MAJOR_THRESHOLD}} * 1.3, bodyValue);
    float majorPulse = pulseBase;
    float minorPulse = mix(1.0, pulseBase, 0.3);
    float layerAlpha = mix({{MINOR_ALPHA}}, {{MAJOR_ALPHA}}, majorT);
    float layerPulse = mix(minorPulse, majorPulse, majorT);

    float alpha = intensity * layerAlpha * layerPulse;

    // 6. 계층별 색상 — 주정맥/모세정맥
    vec3 majorColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{MAJOR_R}}, {{MAJOR_G}}, {{MAJOR_B}});
    vec3 minorColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{MINOR_R}}, {{MINOR_G}}, {{MINOR_B}});
    vec3 veinColor = mix(minorColor, majorColor, majorT);

    fragColor = vec4(veinColor, alpha);
}
