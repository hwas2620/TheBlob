#version 300 es
precision highp float;

uniform sampler2D u_trailMap;
uniform sampler2D u_foodMap;
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
    vec2 texel = zoomFactor / u_mapSize;

    vec3 finalColor = vec3(0.0);
    float finalAlpha = 0.0;

    // ========================================
    // A. 자기 페로몬 등고선 (녹색 계열)
    // ========================================
    float sum = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            sum += texture(u_trailMap, fract(trailUV + offset)).r;
        }
    }
    float value = sum / 9.0;

    float minThreshold = {{MIN_THRESHOLD}} / zoomFactor;
    if (value >= minThreshold) {
        float maxValue = {{MAX_VALUE}};
        float intensity = clamp(value / maxValue, 0.0, 1.0);

        vec3 lowColor = vec3({{LOW_R}}, {{LOW_G}}, {{LOW_B}});
        vec3 highColor = vec3({{HIGH_R}}, {{HIGH_G}}, {{HIGH_B}});
        vec3 fieldColor = mix(lowColor, highColor, intensity);
        float baseAlpha = intensity * {{BASE_ALPHA}};

        // 등고선 (중앙차분 그래디언트)
        float valueR = texture(u_trailMap, fract(trailUV + vec2(texel.x, 0.0))).r;
        float valueU = texture(u_trailMap, fract(trailUV + vec2(0.0, texel.y))).r;
        float iR = clamp(valueR / maxValue, 0.0, 1.0);
        float iU = clamp(valueU / maxValue, 0.0, 1.0);
        vec2 grad = vec2(iR - intensity, iU - intensity);
        float gradLen = length(grad);

        float contourLine = 0.0;
        float levels[5] = float[5](0.1, 0.25, 0.4, 0.6, 0.8);
        for (int i = 0; i < 5; i++) {
            float dist = abs(intensity - levels[i]);
            float pixelDist = gradLen > 0.0001 ? dist / gradLen : 9999.0;
            float line = 1.0 - smoothstep(0.0, {{LINE_WIDTH}}, pixelDist);
            contourLine = max(contourLine, line);
        }

        vec3 contourRGB = vec3({{CONTOUR_R}}, {{CONTOUR_G}}, {{CONTOUR_B}});
        float contourAlpha = contourLine * {{CONTOUR_ALPHA}};

        finalColor = mix(fieldColor, contourRGB, contourLine * 0.5);
        finalAlpha = max(baseAlpha, contourAlpha);
    }

    // ========================================
    // B. 먹이 등고선 (주황색 계열, 별도 채널)
    // ========================================
    float foodSum = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            foodSum += texture(u_foodMap, fract(trailUV + offset)).r;
        }
    }
    float foodValue = foodSum / 9.0;

    float foodMinThreshold = {{FOOD_MIN_THRESHOLD}} / zoomFactor;
    if (foodValue >= foodMinThreshold) {
        float foodMaxValue = {{FOOD_MAX_VALUE}};
        float foodIntensity = clamp(foodValue / foodMaxValue, 0.0, 1.0);

        vec3 foodLowColor = vec3({{FOOD_LOW_R}}, {{FOOD_LOW_G}}, {{FOOD_LOW_B}});
        vec3 foodHighColor = vec3({{FOOD_HIGH_R}}, {{FOOD_HIGH_G}}, {{FOOD_HIGH_B}});
        vec3 foodFieldColor = mix(foodLowColor, foodHighColor, foodIntensity);
        float foodBaseAlpha = foodIntensity * {{FOOD_BASE_ALPHA}};

        // 등고선 (중앙차분 그래디언트)
        float foodR = texture(u_foodMap, fract(trailUV + vec2(texel.x, 0.0))).r;
        float foodU = texture(u_foodMap, fract(trailUV + vec2(0.0, texel.y))).r;
        float fIR = clamp(foodR / foodMaxValue, 0.0, 1.0);
        float fIU = clamp(foodU / foodMaxValue, 0.0, 1.0);
        vec2 foodGrad = vec2(fIR - foodIntensity, fIU - foodIntensity);
        float foodGradLen = length(foodGrad);

        float foodContourLine = 0.0;
        float foodLevels[5] = float[5]({{FOOD_LEVELS}});
        for (int i = 0; i < 5; i++) {
            float dist = abs(foodIntensity - foodLevels[i]);
            float pixelDist = foodGradLen > 0.0001 ? dist / foodGradLen : 9999.0;
            float line = 1.0 - smoothstep(0.0, {{FOOD_LINE_WIDTH}}, pixelDist);
            foodContourLine = max(foodContourLine, line);
        }

        vec3 foodContourRGB = vec3({{FOOD_CONTOUR_R}}, {{FOOD_CONTOUR_G}}, {{FOOD_CONTOUR_B}});
        vec3 foodFinal = mix(foodFieldColor, foodContourRGB, foodContourLine * 0.5);
        float foodFinalAlpha = max(foodBaseAlpha, foodContourLine * {{FOOD_CONTOUR_ALPHA}});

        // food를 trail 위에 합성
        finalColor = finalColor * (1.0 - foodFinalAlpha) + foodFinal * foodFinalAlpha;
        finalAlpha = max(finalAlpha, foodFinalAlpha);
    }

    if (finalAlpha < 0.001) {
        fragColor = vec4(0.0);
        return;
    }

    fragColor = vec4(finalColor, finalAlpha);
}
