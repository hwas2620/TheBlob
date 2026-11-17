export const meta = {
  name: 'physarum-model-round3',
  description: '3차 연구: 통합 모델을 멀티그리드로 풀 수 있는지, 점 먹이와 관 연결, 격자 잠김과 몸 크기 눈금, 입자층의 쓸모를 시험하고 독립 검증 뒤 종합',
  phases: [
    { title: 'Experiment', detail: 'N1 통합+멀티그리드, N3 먹이·줄기·연결, N2 등방성·몸 크기, N4 입자층' },
    { title: 'Verify', detail: '실험마다 독립 반박 검증' },
    { title: 'Synthesize', detail: '권장 모델이 살아남았는지, 0단계로 가도 되는지 판단' },
  ],
}

const REPO = '/home/user/TheBlob/specs/plasmodium-core/research'
const R2 = REPO + '/round2'
const OUT = '/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research3'

const CTX = [
  '## 배경',
  '프로젝트: /home/user/TheBlob — 황색망사점균(Physarum polycephalum) 시뮬레이션 게임. WebGL2, 1500x1500 토러스 맵.',
  '연구 목표: 블롭이 실제 점균 원형질체처럼 보이고 움직이게 하는 시뮬레이션 모델을 찾는다. 재현할 특징:',
  ' (1) 부채꼴 전진면(앞쪽은 조밀한 시트) (2) 그 뒤의 분기 정맥망, 뒤로 갈수록 굵은 줄기로 합류 (3) 두께 맥동과 왕복 흐름',
  ' (4) 부피 보존, 점액 흔적과 기피 (5) 먹이를 찾아 연결하고 먹이 사이를 굵은 관으로 이음.',
  '',
  '## 지금까지의 결론 (반드시 먼저 읽을 것: ' + R2 + '/SYNTHESIS.md, 그리고 /home/user/TheBlob/specs/plasmodium-core/spec.md 의 "목표 모델"과 "미해결 문제")',
  '- 권장 모델 = E10(부피 보존 두께장 h + 나이 수축 + 두께 항복 전진면 + 간선 전도도 초선형 강화 + 결합 진동자 맥동). 코드: ' + R2 + '/E10-pulsation-front/e10.py (보고서 REPORT.md, 검증 verification.json, 검증자 지표 스크립트 verify/indep.py·verify/jacobi_check.py).',
  '- 그 압력 풀이는 지금까지 CPU 희소 직접 풀이뿐이다. GPU로 옮길 수 있는 풀이는 E9 의 멀티그리드(PᵀAP/1.5 과보정, nearest 보간, V(2,2), ω=0.8, 스텝당 1사이클 웜스타트)이고 순수 포아송 + 미리 정한 원반에서만 검증됐다. 코드: ' + R2 + '/E9-solver-feasibility/e9.py (REPORT.md, verification.json).',
  '- Jacobi 수십 회로는 안 된다는 증거가 셋 있다(유량 34~52% 차이, 굵은 정맥 1.8배 과대, 망 붕괴).',
  '- 검증에서 확인된 결함: 한 방향 이주는 먹이 구배가 있을 때만 / 맥동을 켜면 정맥이 조각남(네이티브 간선 그래프 최대 성분 40~51%) / 전진면과 정맥이 격자 방향(0°·45°)에 잠김 / 통합 모델은 N=192, 몸 길이 약 65셀에서만 돌았음 / 점 먹이와 먹이 사이 관은 미시험.',
  '- 다른 실험 코드: E1 ' + R2 + '/E1-front-sink-reinforcement/e1.py, E7 ' + R2 + '/E7-flux-driven-front/e7.py, E6 ' + R2 + '/E6-shuttle-flow-loops/e6.py, E2 ' + R2 + '/E2-jones-at-scale/jones3.py. 문헌 노트: ' + REPO + '/lit/*.md.',
  '',
  '## 채점에 대한 교훈',
  '- 공통 채점기 ' + REPO + '/common/eval_morph.py 의 렌더 기반 all_three 판정은 변별력이 없었다(폭주 중인 실행, 유량이 거의 없는 대조도 통과). 참고용으로만 쓴다.',
  '- 정맥 판정은 네이티브 간선 그래프로 한다: C>문턱인 간선의 최대 연결 성분 비율, 분기 노드·끝점·순환 수, Strahler 차수, 위치–log C 의 Spearman 상관(뒤가 굵으면 음수), 정맥 현 길이 중 격자 방향 ±7.5° 안의 비율(등방 기대 0.333). 검증자들이 쓴 스크립트(' + R2 + '/E10-pulsation-front/verify/indep.py, ' + R2 + '/E1-front-sink-reinforcement/verify/vgraph.py)를 복사해 써도 된다.',
  '- 모델 안의 정맥은 1셀 폭이다. 굵기는 전도도 C 와 렌더 규칙(폭 ∝ C^(1/4))으로만 드러난다. 렌더에서 잰 폭 비를 위계의 증거로 쓰지 마라.',
  '',
  '## 최종 구현 제약',
  'WebGL2 프래그먼트 셰이더 핑퐁 패스, RGBA32F 텍스처, 두께·정맥 격자 512² 또는 768², 프레임당 풀스크린 패스 약 60회 이내. CPU 리드백과 희소 직접 풀이는 쓸 수 없다. 국소 스텐실 연산과 밉 축소(전역 평균)만 가능하다.',
  '',
  '## 규칙',
  '- /home/user/TheBlob 저장소는 읽기 전용이다. 저장소 안의 어떤 파일도 만들거나 고치거나 커밋하지 마라. 저장소의 코드는 자기 출력 폴더로 복사해서 고친다.',
  '- 파일은 지정된 출력 폴더에만 쓴다(없으면 mkdir -p). 다른 실험 폴더는 읽기만 한다.',
  '- python3 에 numpy, scipy, scikit-image, numba, Pillow 가 있어야 한다. import 가 실패하면 pip install --user 로 설치한다.',
  '- 확인하지 못한 것은 확인하지 못했다고 쓴다. 실패한 결과도 그대로 보고한다. 과장하지 마라. 대표 실행을 가장 좋은 시드로 고르지 말고, 시드별 결과를 모두 적는다.',
  '- 세션이 사용량 한도로 예고 없이 끊길 수 있다. 시작 10분 안에 출력 폴더에 REPORT.md(가설, 계획, 식)를 만들고, 실행 배치가 끝날 때마다 결과 표와 해석을 덧붙여라. Write 도구가 거절되면 bash heredoc 으로 쓴다.',
].join('\n')

const EXPS = [
  {
    key: 'N1-integrated-multigrid', verify: true,
    h: 'E10 통합 모델의 차폐 포아송(p/(κ·dt) + Σ W(p_i−p_j) = (h−h*)/dt)을 E9 의 멀티그리드(PᵀAP/1.5, V(2,2), 스텝당 1~2사이클 웜스타트)로 풀어도 희소 직접 풀이와 같은 형태(이주, 시트 전진면, 뒤가 굵은 정맥, 맥동)가 나오고 두께가 음수가 되지 않는다.',
    todo: [
      'e10.py 와 e9.py 를 출력 폴더로 복사한다. E9 의 멀티그리드를 E10 의 연산자에 맞게 옮긴다: 차폐 항(대각 1/(κ·dt)), 젖은 셀만 미지수(마른 셀은 분리), 매 스텝 바뀌는 젖은 집합(새로 젖은 셀의 웜스타트 값), 고립 조각. 조대 연산자는 PᵀAP/1.5 로 매 스텝 다시 만든다. 구현이 국소 스텐실 연산만으로 되는지(GPU 로 옮길 수 있는지) 확인한다.',
      '정적 점검: E10 대표 설정(먹이 구배, 결합 진동자, eps 0.1, 주기 4)을 직접 풀이로 돌리며 몇 시점의 상태를 저장하고, 그 상태에서 멀티그리드 사이클 수별 잔차와 유량 오차(직접 풀이 대비 L2, 전체 간선과 C>100 간선 따로)를 잰다. 같은 상태에서 Jacobi 40/160 회와 비교한다.',
      '동적 점검(핵심): 같은 시드에서 (a) 직접 풀이 (b) 멀티그리드 1사이클/스텝 (c) 2사이클/스텝으로 끝까지 돌린다. 시드 3개. 10~20스텝마다 그 시점 상태에서 직접 풀이를 따로 풀어 유량 오차를 기록한다(버스트를 놓치지 않게 성기게 재지 마라). 최소 두께, 총 부피 오차, 이동 거리, 위치–log C Spearman, 네이티브 간선 그래프 최대 성분, 정맥 총유량/순유량, 최대 전도도를 직접 풀이 실행과 비교한다.',
      '음수 두께 대책: 근사 유량으로 h 를 옮길 때 음수가 나오면 양수 보존 유출 제한(셀의 총 유출이 h/dt 를 넘지 않게 유출 간선을 같은 비율로 줄임)을 넣는다. 이때 강화에 제한 전 유량을 쓸지 제한 후 유량을 쓸지 둘 다 시험하고, 압력–두께 관계가 얼마나 깨지는지 잰다(E8 검증에서 정맥 셀의 56~60% 가 깨졌다).',
      '격자 크기: N=192 에서 통과하면 N=256 과 384 이상(가능하면 512)에서 몸도 그만큼 크게(초기 원반·부피를 키우거나 실행을 길게) 해서 반복한다. 직접 풀이 기준선이 5분을 넘으면 기준선 없이 자체 지표와 성긴 유량 오차만 잰다. float32 로도 1회 돌린다.',
      '주기당 스텝 수(40, 80, 120)와 스텝당 사이클 수의 곱이 같은 예산에서 어느 쪽이 나은지 1~2쌍 비교한다. 자동 Q0 정규화가 근사 풀이의 전도도 폭주를 막는지(막되 조용히 틀린 형태가 되는지)도 본다.',
      '통과 기준: 유량 오차 중앙값 ≤ 0.15(최댓값도 보고), 음수 두께 0, 형태 지표가 직접 풀이의 시드 간 편차 안. 실패하면 어디서 깨지는지(자유 경계, 고립 조각, 진동하는 우변, 전도도 대비)를 분리해 보고한다. 스텝당 드로콜 수와 격자 풀스크린 환산 패스 수를 코드 구성에서 센다.',
    ],
  },
  {
    key: 'N3-food-trunk-connect', verify: true,
    h: '점 먹이를 늙지 않는 저장소(부피 주입 포함)로 두면 저장소에서 전진면으로 이어지는 연결된 줄기가 생기고(E1 의 점 소스 조건이 통합 모델 안에서 재현됨), 몸이 닿은 먹이 둘 사이 경로가 굵은 관으로 남는다. E10 에서 뒤쪽 정맥이 굵어진 원인은 관 부피항에 곱한 맥동이다.',
    todo: [
      'e10.py 를 출력 폴더로 복사한다. 먹이장을 토러스에서 주기적인 점원(가우스 봉우리 1~3개, 초기 몸에서 30~60셀 거리, 방향은 격자 축이 아닌 각도 포함)으로 바꾼다. 선형 구배는 쓰지 않는다. 직접 풀이를 써도 된다.',
      '굵기 구배의 원인 분리(먼저, 3~4회): pulse_tube 0/1, 균일 위상 + 구배, 결합 진동자 + 구배를 같은 시드로 비교해 위치–log C Spearman 과 나이 구간별 C 중앙값을 낸다. "오래돼서 굵다"와 "상류라서 굵다"를 구분할 지표(간선의 평균 순유량과 C 의 관계, 줄기 쪽으로 유량이 모이는지)를 함께 낸다.',
      '먹이 도달: 전용 규칙 없이(항복 문턱의 −y_c·c 항만으로) 몸이 점 먹이에 닿는지, 시드 3개 이상과 먹이 방향 0°/27°/45° 에서 확인한다. 먹이가 없는 쪽 전진면이 줄어드는지도 본다.',
      '저장소 규칙: 먹이 위 셀은 늙지 않는다(쉬는 두께 유지). 변형으로 먹이 위에서 부피를 일정 속도로 주입(먹이 양이 유한해 다 먹으면 끝남)한다. 측정: 저장소–전진면 사이 네이티브 간선 그래프의 연결(최대 성분), 저장소에서 나가는 간선의 순유량과 전도도, Strahler 차수, 줄기가 저장소로 모이는지.',
      '먹이 둘 이상: 몸이 두 먹이에 모두 닿은 뒤 두 먹이 사이 최대 전도도 경로(최소 저항 경로)의 C 중앙값이 전체 정맥 C 중앙값의 몇 배인지, 50주기 이상 유지되는지 잰다. 먹이를 다 먹은 뒤 그 관이 어떻게 되는지도 본다.',
      '조각난 정맥 대책 1~2개: 예) 마름 규칙에서 굵은 관 셀은 늦게 마르게 함, 막다른 끝부터 후퇴, 저장소 연결. 대책 유무로 최대 성분과 끝점/분기 노드 비를 비교한다.',
      '먹이 위에 머무를 때 몸이 말라 흩어지지 않는지(모든 먹이에 닿은 뒤 100주기) 확인한다.',
      '통과 기준: 네이티브 최대 성분 ≥ 0.8 과 먹이 사이 경로 C ≥ 전체 중앙값의 10배가 시드 3개 중 2개 이상. 모든 지표는 네이티브 간선 그래프로 낸다.',
    ],
  },
  {
    key: 'N2-isotropy-scale', verify: true,
    h: '젖음 규칙과 강화 신호의 격자 이방성을 고치면(등방 곡률 추정, 대각 이웃의 전진 속도 보정, 공간 상관 항복 잡음, 강화 신호에 스텐실 가중 반영) 전진면과 정맥의 격자 잠김이 사라지고, 몸 크기에 맞춘 눈금 규칙으로 몸 길이를 2~4배 키워도 맥동 위상 지연(0.5~2바퀴)과 시트 전진면·정맥이 유지된다.',
    todo: [
      'e10.py 를 출력 폴더로 복사한다. 먼저 기준선의 잠김을 잰다: 먹이 구배(또는 점 먹이) 방향 0°/27°/45° 에서 정맥 현 길이의 격자 방향 ±7.5° 비율, 전진 가장자리의 직선성(가장자리 위치의 표준편차), 초기 무구배 퍼짐의 대각/축 도달 거리비(E7 검증에서 1.12). 직접 풀이를 써도 된다.',
      '원인 후보를 하나씩 바꿔 본다(한 번에 하나, 그다음 조합): (i) 젖음 문턱의 곡률항을 8이웃 개수 대신 반지름 2~3 원형 커널의 젖은 비율로, (ii) 대각 이웃이 축 이웃과 같은 조건으로 젖어 대각 전진이 √2 배 빠른 문제를 거리 가중이나 확률 1/√2 로 보정, (iii) 항복 잡음을 상관 길이 3~6셀의 공간 상관 잡음으로 바꾸고 세기 스윕, (iv) 강화 신호에 실제 간선 유량(스텐실 가중과 길이 포함)을 쓰는지 점검하고 고침, (v) 젖음 공여를 최대 h 이웃 하나가 아니라 원형 커널 가중 평균으로.',
      '각 변형에서 세 방향 모두 잠김 지표를 낸다. 통과 기준: 격자 방향 비율 ≤ 0.45, 27° 방향에서 정맥이 45°·0° 빗살이 되지 않음(그림으로도 확인), 이주 방향 오차 ≤ 5°.',
      '몸 크기 눈금: 몸 길이 약 65/130/(가능하면 260)셀이 되도록 초기 부피와 격자를 키운다(N=192/384, 실행 시간이 허락하면 그 이상). 눈금 후보를 시험한다: D_θ ∝ L², τ_a ∝ L, 관 적응 시간, 주기. 실제 점균은 몸 길이에 연동파 약 한 파장이 걸린다. 측정: 늙은 셀과 젊은 셀의 위상차(바퀴), 정맥 총유량/순유량, 젖음 위상 잠금 R, 시트 폭과 정맥 간격이 몸 크기에 따라 어떻게 변하는지, 전진 속도.',
      '등방화한 규칙으로 무구배 실행을 시드 5개 돌려 엽 수, 가장 큰 엽의 부피 비율, 줄기가 가운데로 모이는지를 적는다(한 방향 이주가 안 되는 것은 결함으로 치지 않는다. 형태만 기록).',
      'GPU 비용: 채택한 변형마다 추가 패스 수와 텍스처 조회 수를 적는다(반지름 3 커널은 조회 약 29회).',
    ],
  },
  {
    key: 'N4-particle-layer', verify: false,
    h: 'Jones 입자는 칸당 1개 제한 + 젖은 영역 가둠 아래에서 창발한 몸(E10 의 젖은 마스크) 위에서도 그물 질감을 유지하고 몸을 따라온다. E2 의 세 주장(칸당 1개 제한이 필요조건 / 가둠이 필요 / 게임의 현재 trail 규칙에서는 제한을 켜도 수축)은 새 시드에서 재현된다.',
    todo: [
      'E2 보고(' + R2 + '/E2-jones-at-scale/REPORT.md, result.json)는 독립 검증이 없다. jones3.py 를 출력 폴더로 복사해 세 주장을 새 시드로 각 1~2회 다시 돌린다(512², 8000스텝 이내). 보고와 다르면 그대로 적는다.',
      'E10 대표 설정을 직접 풀이로 돌리며 젖은 마스크와 두께 h 를 촘촘히(예: 2스텝마다) 저장한다. 그 시계열을 몸으로 써서 입자를 돌린다: 젖은 셀에만 존재, 새로 젖은 셀에 확률로 주입, 마른 셀의 입자는 삭제 또는 재배치. 격자 배율(두께 격자 1셀 = 입자 격자 몇 px)을 정해 밝힌다.',
      '측정: 입자 그물이 앞쪽 시트에 생기는지, 몸을 따라오는지, 뒤쪽(1셀 폭 정맥과 마른 흔적)에서 입자가 어떻게 되는지, 그물코 크기, 1만 스텝 지속성, 몸 밖 입자 비율. 입자 감지값에 전도도 C 를 더하면(자기 trail + α·C) 입자가 정맥에 달라붙어 정맥을 굵고 자연스럽게 보이게 하는지도 1~2회 본다.',
      '결론: 입자층을 (a) 구조 부품 (b) 시트 질감·흐름 표시층 (c) 버림 중 어느 쪽으로 권하는지와 근거. 게임의 입자 10만 개를 쓰려면 몸 면적이 얼마여야 하는지 계산한다.',
      '이 실험은 독립 검증 없이 보고만 싣는다. 그만큼 확인하지 못한 것을 분명히 적는다.',
    ],
  },
]

const EXP_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['supports', 'partial', 'refutes', 'inconclusive'] },
    headline: { type: 'string', description: '결과 한두 문장' },
    model_rules: { type: 'string', description: '실제로 구현하거나 바꾼 식/규칙. 재구현 가능할 만큼 구체적으로, 2500자 이내' },
    runs_summary: { type: 'string', description: '무엇을 몇 번, 어떤 파라미터로 돌렸는지와 각 결과(시드별). 2000자 이내' },
    pass_criteria_result: { type: 'string', description: '임무에 적힌 통과 기준 각각에 대해 통과/불통과와 수치' },
    best_run_dir: { type: 'string' },
    best_metrics: { type: 'object', description: '네이티브 간선 그래프 지표와 직접 정의한 지표' },
    images: { type: 'array', items: { type: 'string' }, description: '대표 PNG 절대경로 (최대 6장)' },
    mass_conserved: { type: 'string', description: '오차 수치와 최소 두께, 해당 없으면 "해당 없음"' },
    gpu_feasibility: { type: 'object', properties: {
      est_drawcalls_per_step: { type: 'number' }, est_fullscreen_passes_per_step: { type: 'number' }, notes: { type: 'string' },
    }, required: ['notes'] },
    failure_modes: { type: 'array', items: { type: 'string' } },
    limitations: { type: 'array', items: { type: 'string' } },
    next_steps: { type: 'array', items: { type: 'string' } },
    reproduce_command: { type: 'string' },
    report_path: { type: 'string' },
  },
  required: ['verdict', 'headline', 'model_rules', 'runs_summary', 'pass_criteria_result', 'best_run_dir', 'best_metrics', 'images', 'gpu_feasibility', 'failure_modes', 'limitations', 'reproduce_command', 'report_path'],
}

function expPrompt(e) {
  return [
    CTX, '',
    '## 당신의 임무: 수치 실험 — ' + e.key,
    '가설: ' + e.h, '',
    '할 일:',
    e.todo.map((t, i) => (i + 1) + '. ' + t).join('\n'), '',
    '## 실험 규칙',
    '- 출력 폴더: ' + OUT + '/' + e.key + ' (없으면 만든다). 여기에만 쓴다.',
    '- 계산 자원: 코어 4개를 다른 에이전트 1명과 나눠 쓴다. 동시에 프로세스 2개 이하, NUMBA_NUM_THREADS=2 / OMP_NUM_THREADS=2 / OPENBLAS_NUM_THREADS=2. 한 번의 실행은 5분 이내, 전체 계산 시간은 40분 안팎.',
    '- 작게 시작해 빨리 반복한다. 가설이 틀렸다는 결론도 유효한 결과다. 할 일이 예산을 넘으면 위에서부터 차례로 하고, 못 한 항목은 못 했다고 적는다.',
    '- 구조를 손으로 그려 넣지 마라. 초기 조건과 잡음은 보고서에 밝힌다. 좋아 보이는 임계값이나 시드만 골라 보고하지 마라.',
    '- 실행마다 runs/<이름>/ 에 저장: 상태 배열(h, wet, age, 간선 C 등 .npy), snapshot_*.png(시간 순, 긴 변 1024px 이하, 최소 3시점), params.json, metrics.json.',
    '- 이미지는 몽타주를 만들어 Read 로 직접 열어 눈으로 확인한다(꼭 필요한 것만 연다).',
    '- REPORT.md 최종본: 가설, 구현한 식, 실행 목록과 시드별 결과 표, 통과 기준별 판정, 대표 이미지 경로, 실패한 시도, GPU 비용, 재현 명령, 한계.',
    '- verdict: 가설대로면 supports, 일부만이면 partial, 충분히 시험했는데 안 되면 refutes, 시험이 부족하면 inconclusive.',
  ].join('\n')
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    claim_refuted: { type: 'boolean', description: '실험 담당자의 verdict 가 지지되지 않으면 true' },
    corrected_verdict: { type: 'string', enum: ['supports', 'partial', 'refutes', 'inconclusive'] },
    reproduced: { type: 'string', enum: ['yes', 'no', 'partially', 'not_attempted'] },
    pass_criteria_recheck: { type: 'string', description: '통과 기준 각각을 직접 다시 잰 결과' },
    emergent_not_handplaced: { type: 'boolean' },
    lattice_artifact_suspected: { type: 'boolean' },
    realism_score_0_10: { type: 'number', description: '실제 점균 원형질체와 닮은 정도. 0=전혀, 10=사진과 구별 어려움' },
    independent_metrics: { type: 'object' },
    issues: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string', description: '900자 이내' },
  },
  required: ['claim_refuted', 'corrected_verdict', 'reproduced', 'pass_criteria_recheck', 'emergent_not_handplaced', 'lattice_artifact_suspected', 'realism_score_0_10', 'issues', 'summary'],
}

const VFOCUS = {
  'N1-integrated-multigrid': '집중할 점: (a) 유량 오차를 담당자보다 촘촘히(매 5~10스텝) 재서 버스트가 있는지 본다. (b) 멀티그리드 실행의 형태가 직접 풀이와 같다는 주장을 새 시드로 확인한다. 자동 Q0 정규화 때문에 폭주 대신 조용히 틀린 형태가 나오는지 본다(정맥 위치의 겹침, Spearman, 최대 성분을 직접 풀이 실행과 비교). (c) 구현이 정말 국소 스텐실만 쓰는지, 전역 연산(연결 성분 라벨링, 정렬, 직접 풀이 호출)이 숨어 있지 않은지 코드로 확인한다. (d) 음수 두께 대책이 압력–두께 관계를 얼마나 깨는지 다시 잰다. (e) 패스 수 계산이 코드와 맞는지.',
  'N3-food-trunk-connect': '집중할 점: (a) 먹이 도달과 관 연결이 전용 규칙 없이 나온 것인지 코드로 확인한다(먹이 쪽으로 부피를 직접 옮기거나 경로를 심는 코드가 없는지). (b) 먹이 사이 경로의 굵기를 네이티브 간선 그래프의 최소 저항 경로로 직접 다시 잰다. 먹이 위치를 바꾼 새 시드 1회. (c) 최대 성분 ≥ 0.8 이 문턱(C>4, C>10, C>30)에 따라 유지되는지. (d) 굵기 구배 원인 분리의 대조가 한 쌍뿐이면 시드 편차 안인지 확인한다.',
  'N2-isotropy-scale': '집중할 점: (a) 담당자가 재지 않은 방향(예: 13°, 34°)으로 먹이를 놓고 잠김 지표를 직접 잰다. 정맥 방향 히스토그램을 그려 0°/45°/90° 봉우리가 남는지 본다. (b) 등방화가 다른 성질(시트 전진면, 뒤가 굵은 정맥, 맥동, 부피 보존)을 망가뜨리지 않았는지 기준선과 비교한다. (c) 몸 크기 눈금 규칙이 한 크기에 맞춘 조정이 아닌지, 담당자가 돌리지 않은 크기 1개로 확인한다.',
}

function verifyPrompt(e, res) {
  const positive = res.verdict === 'supports' || res.verdict === 'partial'
  return [
    CTX, '',
    '## 당신의 임무: 독립 반박 검증 — ' + e.key,
    '가설: ' + e.h, '',
    '실험 담당자의 보고:',
    '- verdict: ' + res.verdict,
    '- headline: ' + res.headline,
    '- 구현한 규칙: ' + res.model_rules,
    '- 실행 요약: ' + res.runs_summary,
    '- 통과 기준 판정: ' + res.pass_criteria_result,
    '- 대표 실행 폴더: ' + res.best_run_dir,
    '- 대표 이미지: ' + (res.images || []).join(', '),
    '- 보고한 지표: ' + JSON.stringify(res.best_metrics || {}),
    '- 보고서: ' + res.report_path,
    '- 재현 명령: ' + res.reproduce_command,
    '- 실험 폴더: ' + OUT + '/' + e.key, '',
    '당신은 실험 담당자와 독립인 심사자다. 담당자의 결론을 그대로 받아들이지 말고 반박을 시도하라. 확신이 없으면 claim_refuted=true.',
    '1. 그림을 직접 본다: 대표 PNG 를 Read 로 연다(3~5장). 흔한 함정: 격자 축·대각선에 정렬된 직선 정맥, 한 시점에만 보이는 과도 상태, 문턱을 바꾸면 사라지는 구조, 가장 좋은 시드만 보여 주기.',
    '2. 수치를 다시 잰다: 저장된 상태 배열에서 네이티브 간선 그래프 지표를 직접 계산한다. 담당자 스크립트를 그대로 믿지 말고 따로 짠다.',
    '3. 코드를 읽는다: 보고된 식과 코드가 일치하는지, 구조가 손으로 심어졌는지, 보존량이 실제로 보존되는지.',
    '4. 대표 실행을 다른 난수 시드로 직접 다시 돌린다(계산 합계 10분 이내, 프로세스 1개, 결과는 실험 폴더 아래 verify/ 에만 저장).',
    positive
      ? '5. 통과 기준 각각을 직접 다시 판정한다. GPU 비용 주장이 코드와 맞는지 본다.'
      : '5. 담당자는 부정적/불확정 결론을 냈다. 실패가 구현 버그, 잘못된 파라미터 범위, 너무 짧은 실행 탓은 아닌지 보고, 가장 의심되는 원인 하나를 5분 이내 계산으로 직접 시험한다.',
    VFOCUS[e.key] || '',
    '실험 폴더의 기존 파일은 고치지 않는다. 검증 보고는 verify/REPORT.md 에도 남긴다.',
  ].join('\n')
}

async function runGroup(group) {
  return pipeline(
    group,
    e => agent(expPrompt(e), { label: 'exp:' + e.key, phase: 'Experiment', schema: EXP_SCHEMA }),
    async (res, e) => {
      if (!res) return { e, res: null, ver: null }
      if (!e.verify) return { e, res, ver: null }
      const ver = await agent(verifyPrompt(e, res), { label: 'verify:' + e.key, phase: 'Verify', schema: VERIFY_SCHEMA })
      return { e, res, ver }
    },
  )
}

phase('Experiment')
log('우선순위 순서로 돈다: 먼저 N1(통합 + 멀티그리드)과 N3(먹이·줄기·연결), 그다음 N2(등방성·몸 크기)와 N4(입자층).')
const g1 = await runGroup(EXPS.slice(0, 2))
log('1조 완료: ' + g1.filter(x => x && x.res).length + '/2 실험, ' + g1.filter(x => x && x.ver).length + '/2 검증')
const g2 = await runGroup(EXPS.slice(2, 4))
log('2조 완료: ' + g2.filter(x => x && x.res).length + '/2 실험. N4 는 독립 검증 없이 담당자 보고만 싣는다(예산 우선순위).')

const all = EXPS.map((e, i) => {
  const r = (i < 2 ? g1[i] : g2[i - 2]) || { res: null, ver: null }
  return { key: e.key, hypothesis: e.h, dir: OUT + '/' + e.key, result: r.res || null, verification: r.ver || null }
})

phase('Synthesize')
const SYN_SCHEMA = {
  type: 'object',
  properties: {
    model_survives: { type: 'string', enum: ['yes', 'with_changes', 'no'], description: '권장 모델(E10 + 멀티그리드)이 구현 경로로 살아남았는가' },
    go_to_stage0: { type: 'boolean', description: '브라우저 프로토타입(0단계)으로 넘어가도 되는가' },
    reasons: { type: 'string', description: '판단 근거. 1200자 이내' },
    model_changes: { type: 'array', items: { type: 'string' }, description: 'spec 의 목표 모델에서 바꿔야 할 규칙·값' },
    stage0_criteria_changes: { type: 'array', items: { type: 'string' } },
    rejected_claims: { type: 'array', items: { type: 'string' }, description: '검증에서 반박됐거나 근거가 약해 채택하지 않는 주장' },
    open_risks: { type: 'array', items: { type: 'string' } },
    next_experiments: { type: 'array', items: { type: 'string' } },
    synthesis_path: { type: 'string' },
  },
  required: ['model_survives', 'go_to_stage0', 'reasons', 'model_changes', 'stage0_criteria_changes', 'rejected_claims', 'open_risks', 'synthesis_path'],
}
const compact = all.map(d => ({
  key: d.key, hypothesis: d.hypothesis, dir: d.dir,
  result: d.result ? { verdict: d.result.verdict, headline: d.result.headline, pass: d.result.pass_criteria_result, runs: d.result.runs_summary, rules: d.result.model_rules, gpu: d.result.gpu_feasibility, failures: d.result.failure_modes, limitations: d.result.limitations, report: d.result.report_path, images: d.result.images } : null,
  verification: d.verification,
}))
const synthesis = await agent([
  CTX, '',
  '## 당신의 임무: 3차 실험 종합과 누락 점검',
  '아래는 3차 실험 4건과 독립 검증 결과다. 담당자 자기 평가보다 검증자 판정을 우선하라. 검증자가 반박한 주장은 채택하지 마라. 검증이 없는 실험(N4, 또는 검증이 실패한 것)은 "미검증"으로 표시한다.',
  JSON.stringify(compact), '',
  '할 일:',
  '1. 각 실험의 REPORT.md 와 검증 보고(verify/REPORT.md)를 직접 읽고 대표 이미지를 몇 장 연다.',
  '2. 권장 모델(E10 + E9 멀티그리드)이 구현 경로로 살아남았는지 판단한다. N1 이 실패했으면 대안(방식 D: 정맥만 그래프로 풀기, 풀이 빈도 낮추기, 다른 풀이)을 평가한다.',
  '3. spec.md 의 목표 모델 규칙 1~7 과 값 가운데 바꿔야 할 것을 구체적으로 적는다(등방 젖음 규칙, 먹이 저장소, 유출 제한, 눈금 규칙 등). 근거가 검증된 것만.',
  '4. spec.md 의 0단계 통과 기준(관문 A, B)에서 고칠 것을 적는다.',
  '5. 누락 점검: 돌리지 않은 시험, 서로 모순되는 결과, 2차 결론과 어긋나는 점, 결합했을 때 깨질 수 있는 가정.',
  '6. 0단계(브라우저 프로토타입)로 넘어가도 되는지, 아니면 numpy 실험이 더 필요한지 판단하고 이유를 적는다. 연구를 끝없이 늘리지 말고, 브라우저에서만 확인할 수 있는 것과 numpy 로 먼저 닫아야 하는 것을 구분한다.',
  '7. ' + OUT + '/SYNTHESIS3.md 에 전체 종합을 쓴다(없으면 폴더를 만든다. Write 가 거절되면 bash heredoc). 직접 확인한 것과 못 한 것을 구분해 적는다.',
].join('\n'), { label: 'synthesize', phase: 'Synthesize', schema: SYN_SCHEMA })

return { experiments: all, synthesis }
