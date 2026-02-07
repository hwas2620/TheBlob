#version 300 es
precision highp float;

// ============================================================
// Jeff Jones 알고리즘 (2010 논문) + 셀 기반 충돌 감지
// "Characteristics of Pattern Formation and Evolution in
//  Approximations of Physarum Transport Networks"
//
// 핵심: "at most one particle in each grid square"
// GPU 구현: Occupancy Map으로 셀당 에이전트 수 추적
// ============================================================

uniform sampler2D u_agentState;
uniform sampler2D u_trailMap;
uniform sampler2D u_random;
uniform sampler2D u_occupancyMap;

uniform int u_agentCount;
uniform int u_texWidth;
uniform vec2 u_mapSize;
uniform float u_sensorAngle;
uniform float u_sensorDistance;
uniform float u_turnSpeed;
uniform float u_moveSpeed;
uniform float u_frameIndex;
uniform float u_occupancyThreshold;  // 셀당 최대 에이전트 수

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

    // === SENSE (페로몬) ===
    float frontSense = senseTrail(pos, angle, u_sensorDistance);
    float leftSense  = senseTrail(pos, angle - u_sensorAngle, u_sensorDistance);
    float rightSense = senseTrail(pos, angle + u_sensorAngle, u_sensorDistance);

    // === SENSE (밀도) - 물처럼 퍼지기 위해 밀집 지역 회피 ===
    float sensorDist = u_sensorDistance * 2.0;  // 밀도는 더 멀리 감지
    vec2 frontPos = mod(pos + vec2(cos(angle), sin(angle)) * sensorDist, u_mapSize);
    vec2 leftPos  = mod(pos + vec2(cos(angle - u_sensorAngle), sin(angle - u_sensorAngle)) * sensorDist, u_mapSize);
    vec2 rightPos = mod(pos + vec2(cos(angle + u_sensorAngle), sin(angle + u_sensorAngle)) * sensorDist, u_mapSize);

    float frontDensity = texture(u_occupancyMap, frontPos / u_mapSize).r;
    float leftDensity  = texture(u_occupancyMap, leftPos / u_mapSize).r;
    float rightDensity = texture(u_occupancyMap, rightPos / u_mapSize).r;
    float currentDensity = texture(u_occupancyMap, pos / u_mapSize).r;

    // === ROTATE ===
    // 밀도가 높으면 무조건 회피, 아니면 페로몬 추적

    // 현재 위치 밀도가 높으면 → 강제로 낮은 밀도 방향으로
    if (currentDensity > 1.0) {
        // 밀집: 가장 낮은 밀도 방향으로 회전
        if (frontDensity <= leftDensity && frontDensity <= rightDensity) {
            // 전방이 가장 비어있음 → 직진
        } else if (leftDensity < rightDensity) {
            angle -= u_turnSpeed;
        } else if (rightDensity < leftDensity) {
            angle += u_turnSpeed;
        } else {
            // 모두 비슷 → 강한 랜덤 회전
            angle += (rnd.x - 0.5) * 3.14159;
        }
    } else {
        // 여유: Jeff Jones 페로몬 추적
        if (frontSense > leftSense && frontSense > rightSense) {
            // 직진
        } else if (frontSense < leftSense && frontSense < rightSense) {
            angle += (rnd.x > 0.5 ? 1.0 : -1.0) * u_turnSpeed;
        } else if (leftSense > rightSense) {
            angle -= u_turnSpeed;
        } else if (rightSense > leftSense) {
            angle += u_turnSpeed;
        } else {
            // 페로몬 없음 → 랜덤 탐색
            angle += (rnd.x - 0.5) * u_turnSpeed;
        }
    }

    // === MOVE ===
    // 밀도 그래디언트로 회전 방향이 결정되었으므로, 항상 이동
    vec2 direction = vec2(cos(angle), sin(angle));
    vec2 newPos = mod(pos + direction * u_moveSpeed, u_mapSize);
    x = newPos.x;
    y = newPos.y;

    fragColor = vec4(x, y, angle, flags);
}
