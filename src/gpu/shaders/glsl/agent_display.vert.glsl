#version 300 es
precision highp float;

uniform sampler2D u_agentState;
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;
uniform int u_agentCount;
uniform int u_texWidth;

void main() {
    int agentIdx = gl_VertexID;
    if (agentIdx >= u_agentCount) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0); // 화면 밖
        gl_PointSize = 0.0;
        return;
    }

    int tx = agentIdx % u_texWidth;
    int ty = agentIdx / u_texWidth;
    vec4 state = texelFetch(u_agentState, ivec2(tx, ty), 0);

    // 비활성 에이전트 스킵
    if (state.w < 0.5) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
        gl_PointSize = 0.0;
        return;
    }

    // 월드 좌표 → 스크린 좌표 (블롭 본체와 동일한 변환)
    vec2 worldPos = state.xy;
    vec2 screenPos = worldPos - u_camera;

    // 토러스 래핑: mod로 [0, mapSize) 범위로 정규화
    screenPos.x = mod(screenPos.x, u_mapSize.x);
    screenPos.y = mod(screenPos.y, u_mapSize.y);

    // 스크린 좌표 → 클립 좌표 (블롭 본체와 동일)
    vec2 clipPos = (screenPos / u_viewportSize) * 2.0 - 1.0;
    gl_Position = vec4(clipPos.x, -clipPos.y, 0.0, 1.0);
    gl_PointSize = 1.0;
}
