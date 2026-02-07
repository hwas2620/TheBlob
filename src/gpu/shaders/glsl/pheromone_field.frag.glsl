#version 300 es
precision highp float;

uniform sampler2D u_attractors; // 어트랙터 데이터 텍스처 (64x1 RGBA32F)
uniform int u_attractorCount;
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;

in vec2 v_uv;
out vec4 fragColor;

// 필드 세기 계산 (함수로 추출하여 수동 그래디언트에 재사용)
float computeField(vec2 wPos, float fieldRadiusSq, float soft) {
    float fadeStart = fieldRadiusSq * {{FADE_START_RATIO}};
    float total = 0.0;
    for (int i = 0; i < 64; i++) {
        if (i >= u_attractorCount) break;
        vec4 att = texelFetch(u_attractors, ivec2(i, 0), 0);
        vec2 delta = att.xy - wPos;
        delta = delta - round(delta / u_mapSize) * u_mapSize;
        float distSq = dot(delta, delta);
        if (distSq > fieldRadiusSq) continue;
        // 부드러운 경계 감쇠 (하드 컷오프 → smoothstep)
        float falloff = 1.0 - smoothstep(fadeStart, fieldRadiusSq, distSq);
        total += att.z * soft / (distSq + soft) * falloff;
    }
    return total;
}

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);

    float fieldRadius = {{FIELD_RADIUS}};
    float fieldRadiusSq = fieldRadius * fieldRadius;
    float softening = {{SOFTENING}};
    float norm = {{NORMALIZATION}};

    float totalField = computeField(worldPos, fieldRadiusSq, softening);

    if (totalField < {{MIN_THRESHOLD}}) {
        fragColor = vec4(0.0);
        return;
    }

    float intensity = totalField / (totalField + norm);

    // 그라데이션 색상 (초록색 글로우)
    vec4 baseColor = vec4(
        {{COLOR_R}} * intensity,
        {{COLOR_G}} * intensity,
        {{COLOR_B}} * intensity,
        {{COLOR_A}} * intensity
    );

    // === 수동 그래디언트 (하드웨어 dFdx/dFdy 대신 중앙차분) ===
    float fieldR = computeField(mod(worldPos + vec2(1.0, 0.0), u_mapSize), fieldRadiusSq, softening);
    float fieldU = computeField(mod(worldPos + vec2(0.0, 1.0), u_mapSize), fieldRadiusSq, softening);
    float iR = fieldR / (fieldR + norm);
    float iU = fieldU / (fieldU + norm);
    vec2 grad = vec2(iR - intensity, iU - intensity);
    float gradLen = length(grad);

    // === 등고선 (signed distance field 방식, 픽셀 단위) ===
    float contourColor = 0.0;
    float levels[{{CONTOUR_COUNT}}] = float[{{CONTOUR_COUNT}}]({{CONTOUR_LEVELS}});
    for (int i = 0; i < {{CONTOUR_COUNT}}; i++) {
        float dist = abs(intensity - levels[i]);
        float pixelDist = gradLen > 0.0001 ? dist / gradLen : 9999.0;
        float line = 1.0 - smoothstep(0.0, {{LINE_WIDTH_PX}}, pixelDist);
        contourColor = max(contourColor, line);
    }

    // 등고선 합성
    vec4 contour = vec4({{CONTOUR_R}}, {{CONTOUR_G}}, {{CONTOUR_B}}, {{CONTOUR_A}}) * contourColor;

    fragColor = baseColor + contour * (1.0 - baseColor.a);
}
