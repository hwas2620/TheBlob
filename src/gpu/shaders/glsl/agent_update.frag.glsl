#version 300 es
precision highp float;

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

    if (flags < 0.5) {
        fragColor = state;
        return;
    }

    vec2 randUV = fract(v_uv * 7.31 + vec2(u_frameIndex * 0.137, u_frameIndex * 0.293));
    vec4 rnd = texture(u_random, randUV);

    vec2 pos = vec2(x, y);
    float curTrail = texture(u_trailMap, mod(pos, u_mapSize) / u_mapSize).r;

    // === 원거리 탐색: 강한 페로몬/트레일 찾기 ===
    // 50px 거리에서 8방향 탐색
    float bestDist50 = 0.0;
    float bestAngle50 = angle;
    for (int i = 0; i < 8; i++) {
        float a = float(i) / 8.0 * 6.28318530718;
        vec2 searchPos = mod(pos + vec2(cos(a), sin(a)) * 50.0, u_mapSize);
        float trail = texture(u_trailMap, searchPos / u_mapSize).r;
        if (trail > bestDist50) {
            bestDist50 = trail;
            bestAngle50 = a;
        }
    }

    // 100px 거리에서도 탐색 (먹이 페로몬 감지용)
    float bestDist100 = 0.0;
    float bestAngle100 = angle;
    for (int i = 0; i < 8; i++) {
        float a = float(i) / 8.0 * 6.28318530718;
        vec2 searchPos = mod(pos + vec2(cos(a), sin(a)) * 100.0, u_mapSize);
        float trail = texture(u_trailMap, searchPos / u_mapSize).r;
        if (trail > bestDist100) {
            bestDist100 = trail;
            bestAngle100 = a;
        }
    }

    // === 강한 페로몬 방향으로 유인 (먹이 찾기) ===
    // 현재 위치보다 훨씬 강한 곳(2배 이상)이 있으면 그쪽으로 회전
    bool attracted = false;
    if (bestDist100 > curTrail * 2.0 && bestDist100 > 500.0) {
        // 먹이 페로몬 감지 (500 이상 = 강한 페로몬)
        float angleDiff = bestAngle100 - angle;
        angleDiff = angleDiff - round(angleDiff / 6.28318530718) * 6.28318530718;
        angle += angleDiff * 0.4;  // 40% 강도로 회전
        attracted = true;
    } else if (bestDist50 > curTrail * 1.5 && bestDist50 > 100.0) {
        // 근거리에서 더 강한 트레일 발견
        float angleDiff = bestAngle50 - angle;
        angleDiff = angleDiff - round(angleDiff / 6.28318530718) * 6.28318530718;
        angle += angleDiff * 0.25;
        attracted = true;
    }

    // === SENSE (Jeff Jones) ===
    float frontSense = senseTrail(pos, angle, u_sensorDistance);
    float leftSense  = senseTrail(pos, angle - u_sensorAngle, u_sensorDistance);
    float rightSense = senseTrail(pos, angle + u_sensorAngle, u_sensorDistance);

    // === ROTATE ===
    if (!attracted) {
        if (frontSense > leftSense && frontSense > rightSense) {
            // 앞이 최강 - 직진
        } else if (frontSense < leftSense && frontSense < rightSense) {
            // 앞이 최약 - 랜덤 좌우
            angle += (rnd.x > 0.5 ? 1.0 : -1.0) * u_turnSpeed;
        } else if (leftSense > rightSense) {
            angle -= u_turnSpeed;
        } else if (rightSense > leftSense) {
            angle += u_turnSpeed;
        }
    }

    // === 랜덤 지터 (탐험) ===
    angle += (rnd.y - 0.5) * 0.4;

    // === MOVE ===
    x = mod(x + cos(angle) * u_moveSpeed, u_mapSize.x);
    y = mod(y + sin(angle) * u_moveSpeed, u_mapSize.y);

    fragColor = vec4(x, y, angle, flags);
}
