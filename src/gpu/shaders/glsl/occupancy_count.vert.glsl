#version 300 es
precision highp float;

// Occupancy Map 렌더링: 에이전트 위치를 점으로 렌더링하여 셀당 에이전트 수 계산
// 가산 블렌딩으로 중첩 시 합산됨

uniform sampler2D u_agentState;
uniform vec2 u_mapSize;
uniform int u_agentCount;
uniform int u_texWidth;

void main() {
    int agentIdx = gl_VertexID;

    if (agentIdx >= u_agentCount) {
        gl_Position = vec4(-9999.0, -9999.0, 0.0, 1.0);
        gl_PointSize = 0.0;
        return;
    }

    // 에이전트 텍스처에서 위치 읽기
    int tx = agentIdx % u_texWidth;
    int ty = agentIdx / u_texWidth;
    vec4 state = texelFetch(u_agentState, ivec2(tx, ty), 0);

    float x = state.x;
    float y = state.y;
    float flags = state.w;

    // 비활성 에이전트는 화면 밖으로
    if (flags < 0.5) {
        gl_Position = vec4(-9999.0, -9999.0, 0.0, 1.0);
        gl_PointSize = 0.0;
        return;
    }

    // 맵 좌표 → 클립 좌표 [-1, 1]
    vec2 ndc = (vec2(x, y) / u_mapSize) * 2.0 - 1.0;
    gl_Position = vec4(ndc, 0.0, 1.0);
    gl_PointSize = 1.0;
}
