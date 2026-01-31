#version 300 es
precision highp float;

// ============================================================
// Jeff Jones 알고리즘 (2010 논문) + 충돌 감지
// "Characteristics of Pattern Formation and Evolution in
//  Approximations of Physarum Transport Networks"
//
// 핵심: "at most one particle in each grid square"
// GPU 근사: 밀도 기반 회피 (높은 페로몬 = 밀집 = 이동 실패)
// ============================================================

uniform sampler2D u_agentState;
uniform sampler2D u_trailMap;
uniform sampler2D u_random;

uniform int u_agentCount;
uniform int u_texWidth;
uniform vec2 u_mapSize;
uniform float u_sensorAngle;
uniform float u_sensorDistance;
uniform float u_turnSpeed;
uniform float u_moveSpeed;
uniform float u_frameIndex;

in vec2 v_uv;
out vec4 fragColor;

// 센서 위치의 페로몬 밀도 읽기
float senseTrail(vec2 pos, float angle, float dist) {
    vec2 sensorPos = pos + vec2(cos(angle), sin(angle)) * dist;
    vec2 uv = mod(sensorPos, u_mapSize) / u_mapSize;
    return texture(u_trailMap, uv).r;
}

void main() {
    ivec2 texCoord = ivec2(gl_FragCoord.xy);
    int agentIdx = texCoord.y * u_texWidth + texCoord.x;

    if (agentIdx >= u_agentCount) {
        fragColor = vec4(0.0);
        return;
    }

    vec4 state = texelFetch(u_agentState, texCoord, 0);
    float x = state.x;
    float y = state.y;
    float angle = state.z;
    float flags = state.w;

    // 비활성 에이전트는 그대로 유지
    if (flags < 0.5) {
        fragColor = state;
        return;
    }

    // 랜덤 시드
    vec2 randUV = fract(v_uv * 7.31 + vec2(u_frameIndex * 0.137, u_frameIndex * 0.293));
    vec4 rnd = texture(u_random, randUV);

    vec2 pos = vec2(x, y);

    // 현재 위치의 페로몬 (밀도 체크용)
    float currentTrail = texture(u_trailMap, pos / u_mapSize).r;

    // === SENSE ===
    float frontSense = senseTrail(pos, angle, u_sensorDistance);
    float leftSense  = senseTrail(pos, angle - u_sensorAngle, u_sensorDistance);
    float rightSense = senseTrail(pos, angle + u_sensorAngle, u_sensorDistance);

    // === COLLISION DETECTION (밀도 기반) ===
    // 현재 위치가 과밀(페로몬 > 임계값)이면 → 낮은 방향으로 탈출
    float densityThreshold = 50.0;
    bool isOvercrowded = currentTrail > densityThreshold;

    if (isOvercrowded) {
        // 과밀 상태: 페로몬이 가장 낮은 방향으로 회전 (탈출)
        if (frontSense <= leftSense && frontSense <= rightSense) {
            // 앞이 가장 낮음 → 직진 (탈출)
        } else if (leftSense < rightSense) {
            // 왼쪽이 더 낮음 → 좌회전
            angle -= u_turnSpeed;
        } else {
            // 오른쪽이 더 낮음 → 우회전
            angle += u_turnSpeed;
        }
    } else {
        // === ROTATE (일반 Jeff Jones) ===
        if (frontSense > leftSense && frontSense > rightSense) {
            // Case 1: 전방이 가장 강함 → 직진
        } else if (frontSense < leftSense && frontSense < rightSense) {
            // Case 2: 전방이 가장 약함 → 랜덤 좌/우
            angle += (rnd.x > 0.5 ? 1.0 : -1.0) * u_turnSpeed;
        } else if (leftSense > rightSense) {
            // Case 3: 좌측이 더 강함 → 좌회전
            angle -= u_turnSpeed;
        } else if (rightSense > leftSense) {
            // Case 4: 우측이 더 강함 → 우회전
            angle += u_turnSpeed;
        }
        // Case 5: 모두 동일 → 직진
    }

    // === MOVE ===
    vec2 newPos = mod(pos + vec2(cos(angle), sin(angle)) * u_moveSpeed, u_mapSize);

    // 목표 위치의 밀도 체크 (충돌 감지)
    float targetTrail = texture(u_trailMap, newPos / u_mapSize).r;

    // 과밀 상태면 무조건 이동 (탈출), 아니면 충돌 감지
    if (isOvercrowded || targetTrail < densityThreshold * 1.5) {
        x = newPos.x;
        y = newPos.y;
    } else {
        // 이동 실패: 랜덤 회전
        angle += (rnd.z - 0.5) * 3.14159;
    }

    fragColor = vec4(x, y, angle, flags);
}
