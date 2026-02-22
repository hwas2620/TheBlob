#version 300 es
precision highp float;

// ============================================================
// Jeff Jones 2010 + 점균 행동 확장
//
// 기반: SENSE → ROTATE → ATTEMPT MOVE (논문 원본)
// 확장1: 연결성 탐색 (고립 에이전트 → 트레일 복귀 or 탐험)
// 확장2: 의사족 탐험 (경계 에이전트 → pseudopod 뻗기)
// 확장3: 장거리 먹이 감지 (확장 센서 8방향 스캔)
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
uniform float u_occupancyThreshold;

// 연결성 탐색
uniform float u_isolationThreshold;  // 이 트레일 미만 → 고립
uniform float u_searchDistance;      // 고립 시 탐색 거리
uniform float u_recoveryTrailMin;    // 복귀 목표 최소 트레일
uniform float u_jitterStrength;      // 탐험 지터 강도

// 장거리 먹이 감지
uniform float u_longSensorDist;      // 확장 센서 거리

in vec2 v_uv;
out vec4 fragColor;

// 센서 위치의 페로몬 읽기 (토러스 래핑 — GL_REPEAT)
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
    float curTrail = texture(u_trailMap, pos / u_mapSize).r;
    float origAngle = angle; // 센서 방향 계산용 원본 각도 보존

    // 에이전트별 고유 파라미터 변이 (결정질 격자 패턴 방지)
    // 모든 에이전트가 동일한 센서 거리/각도 → 균일 간격 → 벌집 격자 형성
    // 변이를 주면 각 에이전트의 평형 간격이 달라져 불규칙 네트워크 생성
    float agentSeed1 = fract(sin(float(agentIdx) * 12.9898) * 43758.5453);
    float agentSeed2 = fract(sin(float(agentIdx) * 78.233) * 43758.5453);
    float mySensorDist = u_sensorDistance * (0.5 + agentSeed1 * 1.0);   // 50%-150% (4.5~13.5px)
    float mySensorAngle = u_sensorAngle * (0.6 + agentSeed2 * 0.8);    // 60%-140% (13.5°~31.5°)

    // ===========================================
    // 1. SENSE + ROTATE (Jeff Jones 논문 원본)
    // ===========================================
    float frontSense = senseTrail(pos, angle, mySensorDist);
    float leftSense  = senseTrail(pos, angle - mySensorAngle, mySensorDist);
    float rightSense = senseTrail(pos, angle + mySensorAngle, mySensorDist);

    // 센서 노이즈: 미세 대칭 파괴 (동일 값에서의 무한 진동 방지)
    frontSense += (rnd.x - 0.5) * 0.5;
    leftSense += (rnd.y - 0.5) * 0.5;
    rightSense += (rnd.z - 0.5) * 0.5;

    if (frontSense > leftSense && frontSense > rightSense) {
        // 전방 최강 → 직진
    } else if (frontSense < leftSense && frontSense < rightSense) {
        angle += (rnd.x > 0.5 ? 1.0 : -1.0) * u_turnSpeed;
    } else if (leftSense > rightSense) {
        angle -= u_turnSpeed;
    } else if (rightSense > leftSense) {
        angle += u_turnSpeed;
    }

    // ===========================================
    // 2. 연결성 탐색 (고립 에이전트 → 복귀 or 탐험)
    // ===========================================
    if (curTrail < u_isolationThreshold) {
        // 8방향 탐색: 가장 강한 트레일 찾기
        float bestTrail = 0.0;
        float bestAngle = angle;
        bool found = false;

        for (int i = 0; i < 8; i++) {
            float a = float(i) / 8.0 * 6.28318;
            vec2 searchPos = mod(pos + vec2(cos(a), sin(a)) * u_searchDistance, u_mapSize);
            float trail = texture(u_trailMap, searchPos / u_mapSize).r;
            if (trail > bestTrail && trail > u_recoveryTrailMin) {
                bestTrail = trail;
                bestAngle = a;
                found = true;
            }
        }

        if (found) {
            // 트레일 발견 → 그쪽으로 회전 (본체와 재연결)
            float angleDiff = bestAngle - angle;
            angleDiff -= round(angleDiff / 6.28318) * 6.28318;
            float strength = curTrail < 2.0 ? 0.7 : 0.5;
            angle += angleDiff * strength;
            angle += (rnd.z - 0.5) * 0.06; // 복귀 중 소폭 지터
        } else {
            // 트레일 없음 → 탐험 (강한 랜덤 회전)
            angle += (rnd.z - 0.5) * u_jitterStrength * 2.0;
        }
    }

    // ===========================================
    // 3. 의사족 탐험 (pseudopod — 경계 에이전트 동적 행동)
    //    실제 점균은 경계에서 의사족을 뻗어 먹이를 찾음
    // ===========================================
    float maxSense = max(frontSense, max(leftSense, rightSense));
    float minSense = min(frontSense, min(leftSense, rightSense));
    float senseRange = maxSense - minSense;

    // (a) 경계 지터: 센서 값 차이가 큰 에이전트 = 네트워크 가장자리
    //     차이가 클수록 강한 요동 → 경계가 살아있듯 흔들림
    if (senseRange > 1.0 && curTrail > 0.5) {
        float edgeFactor = min(1.0, senseRange / (curTrail + 1.0));
        angle += (rnd.w - 0.5) * u_jitterStrength * edgeFactor;
    }

    // (b) 의사족 탐험: 경계 에이전트의 일부가 랜덤 방향 탐험
    //     트레일이 약할수록 탐험 확률 ↑ (최대 5%)
    //     범위 확대: curTrail < 150 (경계 외곽 에이전트 포함)
    if (curTrail > 0.5 && curTrail < 150.0) {
        float exploreChance = 0.05 * (1.0 - curTrail / 150.0);
        float eRand = fract(sin(float(agentIdx) + u_frameIndex * 0.731) * 43758.5453);
        if (eRand < exploreChance) {
            float eAngle = fract(sin(float(agentIdx) * 12.9898 + u_frameIndex * 78.233) * 43758.5453);
            angle += (eAngle - 0.5) * 3.14159; // ±90° 방향 변경
        }
    }

    // (c) 의사족 추종: 경계 에이전트가 외부 트레일(의사족/스카우트 경로)을 감지하면 따라감
    //     Jeff Jones는 항상 가장 강한 방향(=블롭 내부)으로 45° 회전
    //     → 외부 트레일(의사족)은 절대 이길 수 없음
    //     → 이 섹션에서 Jeff Jones를 override하여 외부 추종
    //     → 양성 피드백: 추종자 증가 → 트레일 강화 → 더 많은 추종자 → 의사족 성장
    bool isFollower = false;
    if (curTrail > 5.0 && curTrail < 190.0) {
        // origAngle 기준 3방향 센서 재계산 (Jeff Jones가 angle을 이미 바꿨으므로)
        float oF = senseTrail(pos, origAngle, mySensorDist);
        float oL = senseTrail(pos, origAngle - mySensorAngle, mySensorDist);
        float oR = senseTrail(pos, origAngle + mySensorAngle, mySensorDist);

        // 가장 약한 센서 방향 = 블롭 외부/의사족 방향
        float weakVal = min(oF, min(oL, oR));
        float weakAngle = origAngle; // 기본값: 전방
        if (weakVal == oL) weakAngle = origAngle - mySensorAngle;
        else if (weakVal == oR) weakAngle = origAngle + mySensorAngle;

        // 의사족 트레일 존재 확인: 약하지만 0이 아닌 트레일 (5~curTrail*0.6)
        // → 누군가 탐험 중인 경로가 있다는 뜻 (스카우트 15x deposit = 75)
        if (weakVal > 5.0 && weakVal < curTrail * 0.6) {
            // 추종 확률: 의사족이 강할수록 ↑ (최대 40%)
            float followChance = 0.40 * weakVal / max(curTrail * 0.6, 1.0);
            float fRand = fract(sin(float(agentIdx) * 3.7159 + u_frameIndex * 1.337) * 43758.5453);
            if (fRand < followChance) {
                // 의사족 방향으로 강하게 회전 (Jeff Jones override)
                float angleDiff = weakAngle - angle;
                angleDiff -= round(angleDiff / 6.28318) * 6.28318;
                angle += angleDiff * 0.85;
                isFollower = true; // 추종자도 강화 deposit → 양성 피드백
            }
        }
    }

    // ===========================================
    // 4. 장거리 먹이 감지 (확장 센서 8방향 스캔)
    // ===========================================
    float bestLong = 0.0;
    float bestLongAngle = angle;
    for (int i = 0; i < 8; i++) {
        float a = float(i) / 8.0 * 6.28318;
        vec2 searchPos = mod(pos + vec2(cos(a), sin(a)) * u_longSensorDist, u_mapSize);
        float trail = texture(u_trailMap, searchPos / u_mapSize).r;
        if (trail > bestLong) {
            bestLong = trail;
            bestLongAngle = a;
        }
    }
    // 먹이 페로몬(150~270)이 현재 위치보다 확실히 강할 때 유인
    // 가산 비교: 블롭 내부(200)에선 발동 안 됨, 경계(~60 이하)에서만 작동
    if (bestLong > curTrail + 20.0 && bestLong > 30.0) {
        float angleDiff = bestLongAngle - angle;
        angleDiff -= round(angleDiff / 6.28318) * 6.28318;
        float pullStrength = min(0.4, (bestLong - curTrail) / 200.0);
        angle += angleDiff * pullStrength;
    }

    // ===========================================
    // 5. 스카우트 파견 + 내부 압력
    //    Jeff Jones는 매 프레임 45° 내부 회전 → 미세 보정으론 극복 불가
    //    → 스카우트: 경계 에이전트의 8%가 Jeff Jones를 완전 override
    //       30프레임 동안 외부로 직진하며 트레일을 남김 (의사족 씨앗)
    //    → 비스카우트: 부드러운 외부 압력 (생동감)
    // ===========================================
    float localDensity = texture(u_occupancyMap, pos / u_mapSize).r;
    vec2 pressureDir = vec2(0.0);
    float pMag = 0.0;

    if (localDensity > 0.5) {
        float pDist = 15.0;
        float dN = texture(u_occupancyMap, mod(pos + vec2(0.0, pDist), u_mapSize) / u_mapSize).r;
        float dS = texture(u_occupancyMap, mod(pos + vec2(0.0, -pDist), u_mapSize) / u_mapSize).r;
        float dE = texture(u_occupancyMap, mod(pos + vec2(pDist, 0.0), u_mapSize) / u_mapSize).r;
        float dW = texture(u_occupancyMap, mod(pos + vec2(-pDist, 0.0), u_mapSize) / u_mapSize).r;
        pressureDir = vec2(dW - dE, dS - dN);
        pMag = length(pressureDir);
    }

    // 스카우트: 25%의 에이전트가 120프레임(~2초) 동안 외부 탐험
    // 더 많은 스카우트 + 더 긴 탐험 → 먹이까지 도달 가능 (120px 이동)
    // 트리거 조건 3가지 (OR):
    //   (a) pMag > 0.3: 밀도 그래디언트가 강한 곳 (블롭 경계)
    //   (b) curTrail < 160: 이미 블롭 외부
    //   (c) senseRange > 20: 트레일 구배가 있는 곳 (경계 근처)
    float scoutPhase = floor(u_frameIndex / 120.0);
    float scoutHash = fract(sin(float(agentIdx) * 127.1 + scoutPhase * 311.7) * 43758.5453);
    bool isScout = scoutHash < 0.25 && curTrail > 1.0
                   && (pMag > 0.3 || curTrail < 160.0 || senseRange > 20.0);

    if (isScout) {
        bool foodDetected = bestLong > curTrail + 20.0 && bestLong > 30.0;
        if (pMag > 0.3) {
            // (a) 밀도 그래디언트로 외부 방향 + 에이전트별 고유 편차 (격자 방지)
            float baseAngle = atan(pressureDir.y, pressureDir.x);
            float personalOffset = (fract(sin(float(agentIdx) * 73.13 + scoutPhase * 17.31) * 43758.5453) - 0.5) * 2.5;
            angle = baseAngle + personalOffset;
        } else if (senseRange > 30.0 && !foodDetected) {
            // (c) 트레일 구배 기반: 가장 약한 센서 = 외부 방향
            float minS = min(frontSense, min(leftSense, rightSense));
            float outAngle = origAngle;
            if (minS == leftSense) outAngle = origAngle - mySensorAngle;
            else if (minS == rightSense) outAngle = origAngle + mySensorAngle;
            float personalOffset2 = (fract(sin(float(agentIdx) * 53.71 + scoutPhase * 29.17) * 43758.5453) - 0.5) * 1.5;
            angle = outAngle + personalOffset2;
        } else if (!foodDetected) {
            // (b) 외부: 현재 방향 유지 (Jeff Jones 무시, 직진)
            angle = origAngle;
        }
        // 먹이 감지 시: section 4가 설정한 방향 유지
    } else if (localDensity > 1.0 && pMag > 0.1) {
        // 비스카우트: 부드러운 외부 압력 (경계 생동감)
        float pAngle = atan(pressureDir.y, pressureDir.x);
        float aDiff = pAngle - angle;
        aDiff -= round(aDiff / 6.28318) * 6.28318;
        float pWeight = smoothstep(1.0, 5.0, localDensity) * 0.15;
        angle += aDiff * pWeight;
    }

    // ===========================================
    // 6. ATTEMPT MOVE (셀 점유 확인)
    // ===========================================
    vec2 newPos = mod(pos + vec2(cos(angle), sin(angle)) * u_moveSpeed, u_mapSize);
    float targetOccupancy = texture(u_occupancyMap, newPos / u_mapSize).r;

    if (targetOccupancy < u_occupancyThreshold) {
        x = newPos.x;
        y = newPos.y;
    } else {
        angle = rnd.y * 6.28318;
    }

    // 개미 페로몬 모델: 스카우트/추종자/먹이추적 에이전트는 flags=2 → 15배 강한 트레일
    // → 외부에 강력한 "고속도로" 형성 → Jeff Jones가 자연스럽게 따라감
    // → 추종자도 강화 deposit → 양성 피드백 루프 (의사족 자기 강화)
    float finalFlags = 1.0;
    if (isScout) finalFlags = 2.0;
    if (isFollower) finalFlags = 2.0;
    if (bestLong > curTrail + 20.0 && bestLong > 30.0) finalFlags = 2.0;

    fragColor = vec4(x, y, angle, finalFlags);
}
