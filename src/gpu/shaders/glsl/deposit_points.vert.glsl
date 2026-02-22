#version 300 es
precision highp float;

uniform sampler2D u_agentState;
uniform vec2 u_mapSize;
uniform int u_agentCount;
uniform int u_texWidth;

flat out float v_flags; // 개미 모델: flags>1.5이면 강화 디파짓

void main() {
    int agentIdx = gl_VertexID;
    if (agentIdx >= u_agentCount) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0); // 화면 밖
        gl_PointSize = 0.0;
        v_flags = 0.0;
        return;
    }

    int tx = agentIdx % u_texWidth;
    int ty = agentIdx / u_texWidth;
    vec4 state = texelFetch(u_agentState, ivec2(tx, ty), 0);

    // 비활성 에이전트 스킵
    if (state.w < 0.5) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
        gl_PointSize = 0.0;
        v_flags = 0.0;
        return;
    }

    v_flags = state.w; // flags: 1.0=일반, 2.0=스카우트/먹이추적

    // 월드 좌표 → 클립 좌표 [-1, 1]
    vec2 clipPos = (state.xy / u_mapSize) * 2.0 - 1.0;
    gl_Position = vec4(clipPos, 0.0, 1.0);
    gl_PointSize = 1.0;
}
