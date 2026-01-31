#version 300 es
precision highp float;

uniform sampler2D u_agentState;
uniform vec2 u_mapSize;
uniform vec2 u_viewportSize;
uniform vec2 u_camera;
uniform int u_agentCount;
uniform int u_texWidth;
uniform int u_instanceOffset;  // 인스턴스별 오프셋 (0~8)

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

    // 인스턴스 오프셋 계산 (3x3 그리드: -1, 0, +1)
    int ox = u_instanceOffset % 3 - 1;  // -1, 0, 1
    int oy = u_instanceOffset / 3 - 1;  // -1, 0, 1

    // 월드 좌표 → 스크린 좌표
    vec2 worldPos = state.xy;
    vec2 screenPos = worldPos - u_camera;

    // 토러스 래핑: [0, mapSize) 범위로 정규화
    screenPos.x = screenPos.x - u_mapSize.x * floor(screenPos.x / u_mapSize.x);
    screenPos.y = screenPos.y - u_mapSize.y * floor(screenPos.y / u_mapSize.y);

    // 인스턴스 오프셋 적용 (맵 반복 위치)
    screenPos.x += float(ox) * u_mapSize.x;
    screenPos.y += float(oy) * u_mapSize.y;

    // 뷰포트 밖이면 클리핑
    if (screenPos.x < 0.0 || screenPos.x >= u_viewportSize.x ||
        screenPos.y < 0.0 || screenPos.y >= u_viewportSize.y) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
        gl_PointSize = 0.0;
        return;
    }

    // 스크린 좌표 → 클립 좌표
    vec2 clipPos = (screenPos / u_viewportSize) * 2.0 - 1.0;
    gl_Position = vec4(clipPos.x, -clipPos.y, 0.0, 1.0);
    gl_PointSize = 1.0;
}
