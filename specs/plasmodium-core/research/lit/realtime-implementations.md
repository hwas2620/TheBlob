# 문헌 조사 노트 — realtime-implementations (실시간/그래픽스/오픈소스 구현)

작성: 2026-11-12. 대상: TheBlob `specs/plasmodium-core` (두께장 h + 진동자 + 점액 + 갇힌 Jones 입자 프로토타입).
같은 폴더의 `jones-extensions.md`, `vein-formation-models.md`, `continuum-channelization.md` 와 겹치지 않게, **실제로 돌아가는 구현의 코드·수치**에 집중했다. 이론(Tero/Hu–Cai/Almeida–Dilão 식, Jones 논문 수치)은 그 세 노트를 볼 것.

## 0. 접근 상태와 표기 (먼저 읽을 것)

- 이 세션의 네트워크는 `github.com`(git clone), `raw.githubusercontent.com`, `arxiv.org` 만 열렸다. WebFetch 는 `cargocollective.com`, `bleuje.com`, `developer.nvidia.com` 에서 ENOTFOUND, curl 은 `sagejenson.com`, `shadertoy.com`, `michaelfogleman.com`, `web.archive.org`, `export.arxiv.org` 등에서 프록시 403.
- 그래서 **1차 자료는 대부분 공개 저장소의 소스 코드**다. 블로그 글·Shadertoy·GPU Gems 본문은 못 읽었다(10절).
- 표기:
  - **[코드]** = 저장소를 clone 해서 해당 파일을 직접 읽고 식·상수를 옮김. 경로를 적었다.
  - **[저장소 문서]** = 저장소의 README/ADR/결과 JSON 에 저자가 적은 수치(자가 보고). 내가 재현하지 않았다.
  - **[본문]** = 원문(논문/글 원본)을 직접 읽음.
  - **[검색 요약]** = WebSearch 결과 요약만 봄. 원문 미확인.
  - **[기억]** = 원문을 못 열었고 기억에 의존. 신뢰도 낮음.
  - **[자체 수치 점검]** = 내가 이 조사 중 numpy 로 돌린 것. 문헌이 아니다.
  - **[추론]** = 내 해석.
- **실행하지 않았다**: 내려받은 저장소의 코드는 하나도 실행하지 않았다(읽기만). `davideciccarese/Physarum-polycephalum-simulation` 을 돌려 보려 했으나 세션의 권한 정책이 내려받은 스크립트 실행을 막았다. 그 저장소의 결과는 저장소에 들어 있는 PNG 를 눈으로 본 것이다.
- clone 위치: `/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research/dl_rt/repos/<owner>_<repo>/`
- 자체 점검 스크립트/결과: `/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research/work_rt/` (`poisson_cost_check.py`, `tracking_check.py`, `res_*.json`, `log_*.txt`)

---

## 1. 한 장 요약

1. **분기 정맥 위계 + 전진면을 실시간 GPU 셰이더로 구현한 공개 사례는 찾지 못했다.** GitHub 저장소 검색 20여 개 질의(physarum + solver/tero/conductivity/poiseuille/peristalsis/poroelastic/vein/webgl/webgpu 등)에서 나온 GPU 구현은 전부 Jones 입자 계열이다. Tero 계열 구현은 전부 CPU 그래프 풀이(직접 풀이 또는 CG)다.
2. 격자 위에서 "부채꼴 전진면 + 뒤의 굵기 위계 정맥 + 고리"에 가장 가까운 그림을 낸 공개 구현은 `davideciccarese/Physarum-polycephalum-simulation`(Python, 140×180 격자, 8-이웃 간선 Tero + 군체화 층)이다. 핵심 조건 세 가지: **(i) 매 스텝 희소 직접 풀이로 압력을 전역으로 푼다, (ii) 소스/싱크를 매 스텝 몇 개만 무작위로 뽑는다(소스 4, 싱크 2). 저자 문서: 수백 개 소스·싱크를 판 전체에 퍼뜨리는 diffuse 모드에서는 "모든 격자 간선이 작은 유량을 받아 아무것도 가지치기되지 않는다", (iii) μ = 1.5** (μ = 1 은 모든 간선 생존, μ = 2 는 간선 하나). 단, 부채꼴과 "판 → 정맥" 전환은 나이 기반 배수 규칙(현상론)으로 넣은 것이고, 저자 스스로 검증되지 않은 가정이라고 적었다.
3. **Jones 입자가 한 줄로 뭉치는 문제**에 대해 실시간 구현들이 쓰는 수단은 세 가지다: (a) 감지값에 따라 SO/SA/RA/이동거리를 바꾸는 **36 Points 식** `param = A + B·s^C`, (b) **준선형 침착** `deposit = sqrt(min(count, 100))·0.003`(Bleuje), (c) 종 간 반발 테이블(Fogleman). 그리고 이들은 **픽셀당 입자 0.35~6개**로 돈다(우리 게임은 전역 0.044개/px). 점유 규칙을 GPU 에서 결정적으로 구현한 사례(KarstenSiemer, `atomicMax`/WebGL2 `MAX` 블렌딩 claim)도 있고, 그 저자는 "규칙 없이는 Fig. 4 망이 2,000~8,000 스텝 안에 직선 몇 개로 수축한다"고 측정했다.
4. **포아송 비용**: 유체 데모들은 Jacobi 3~30회를 **1/2~1/8 해상도**에서 웜스타트로 돌린다(시각용, 수렴 아님). 몸 규모 모드까지 수렴시키려면 Jacobi 로는 부족하다 — 측정 사례 둘과 내 점검이 일치한다. 가변 계수(대비 50~500, 관 폭 3셀)·원판 마스크에서 **기하 멀티그리드 V(2,2) 는 256² 에서 3~4 사이클, 512² 에서 4~8 사이클에 유량 오차 10% 이하**이고, Jacobi 는 같은 정확도에 256² 에서 1만~2만 패스가 든다. V-사이클 1회 ≈ 미세 격자 패스 9.4회 분량의 픽셀 작업, 드로콜 45~82회. 주기 600프레임의 왕복 소스 추적: V-사이클 1회/프레임 → 유량 오차 0.4%, Jacobi 60회/프레임 → 51%. **단 관 폭 1셀·대비 500 이상에서는 단순 멀티그리드가 발산했고, V(1,1) 도 발산했다**(6.3).
5. **질량 보존 이류를 프래그먼트 셰이더 3×3 gather 로 하는 검증된 방법**: Moroz 의 reintegration tracking(식 4절). Flow-Lenia 가 이것으로 "질량 보존 + 친화도 기울기 유동" 생물체를 만든다(s = 0.65, n = 2, dt = 0.2).
6. **국소 명시 갱신만으로 위계 채널망을 실시간으로 만드는 검증된 계열은 수력 침식(virtual pipe 모델)**이다. 면 유량을 상태로 저장하고 관성으로 누적한다(`f ← max(0, f + dt·A·g·Δh/l)`). 1024² WebGL2 구현이 있다. 포아송 풀이 없이 유역 전체의 유량이 하류에 모인다는 점이 우리 실패 (a)의 원인(국소 압력의 침투 깊이 한계)과 정확히 대비된다.
7. **젖은 질감**: 높이 `1 − exp(−h)` → 중앙차분 법선 → Blinn–Phong 스펙큘러(지수 40~48) + 두께 기반 투과(Barré-Brisebois 근사, three.js 구현) + Beer–Lambert 흡수. 프레임당 1.7~2.3 ms(M3 Pro, 높이 사전 패스 r16float) 측정 사례가 있다.

---

## 2. Jones 를 넘어서는 GPU 입자 구현

### 2.1 Sage Jenson "36 Points" → Etienne Jacob (Bleuje) `interactive-physarum`, `physarum-36p` **[코드]**

- 서지: Sage Jenson (mxsage), "36 Points", sagejenson.com/36points (원본 미접근). Etienne Jacob, github.com/Bleuje/interactive-physarum (★228), github.com/Bleuje/physarum-36p. 라이선스 CC BY-NC-SA 3.0 — **코드·파라미터 표를 그대로 가져다 쓰면 안 된다**(비상업·동일조건). 식의 형태만 참고할 것.
- 읽은 파일: `bin/data/shaders/computeshader_move.glsl`, `computeshader_deposit.glsl`, `computeshader_diffusion.glsl`, `src/points_basematrix.h`, `src/ofApp.h`.
- 규칙(원문 주석 그대로): "Sage Jenson's approach is to control the original physarum simulation parameters of a particle based on some current sensed value at the particle's position."

```
s  = clamp( trail(pos + SB2·dir + (0, SB1)) · SF, 1e-9, 1 )        // 입자 위치(또는 약간 앞)의 trail
sensor distance = SD0 + SDA · pow(s, SDE) · 250                     // 250 = PIXEL_SCALE_FACTOR
sensor angle    = SA0 + SAA · pow(s, SAE)
rotation angle  = RA0 + RAA · pow(s, RAE)
move distance   = MD0 + MDA · pow(s, MDE) · 250
```
  이후 감지 3점·회전은 Jones 와 같다(F 최대 → 직진, F 최소 → 무작위 ±RA, 아니면 큰 쪽).
- 침착(Bleuje 고유): 입자가 픽셀 카운터를 `atomicAdd(1)` 하고, 픽셀 패스에서
  `addedDeposit = sqrt(min(count, 100)) · depositFactor`, `depositFactor = 0.003`. **침착이 입자 수의 제곱근**이다.
- 확산·감쇠: 3×3 평균 후 `× DECAY_FACTOR = 0.75`.
- 재배치: 입자마다 진행 변수 `curA += 0.0010`, 한 바퀴(1000 스텝)마다 무작위 위치로 리스폰.
- 규모: 격자 **1280×736, 입자 512·512·22 = 5,767,168개(픽셀당 6.1개)**, 60 fps 목표, compute shader(GL 4.4).
- 파라미터 예(행 = `SD0, SDE, SDA, SA0, SAE, SAA, RA0, RAE, RAA, MD0, MDE, MDA, SB1, SB2, SF`):
  - "pure_multiscale": `0, 4, 0.3 | 0.1, 51.32, 20 | 0.41, 4, 0 | 0.1, 6, 0.1 | 0, 0 | 22`
  - "star_network": `3, 10.17, 0.4 | 1.03, 2.3, 2 | 1.42, 20, 0.75 | 0.83, 1.56, 0.11 | 1.07, 0 | 13`
  - "vertebrata": `17.92, –, 0 | 0.52, –, 0 | 0.18, –, 0 | 0.1, 6.05, 0.17 | 0, 0 | 18`
  (24행 전체는 `src/points_basematrix.h`. 원본 36 Points 는 21개 파라미터 중 14개를 쓴다고 주석에 있다.)
- 무엇을 재현하나: 망·점·벌집·줄무늬 등 다양한 정상 패턴. 점균의 몸·성장·굵기 위계는 다루지 않는다(저자: "It's not meant to be scientific").
- 2차 확인 **[저장소 문서]**: KarstenSiemer 저장소의 `docs/knowledge-base/variants.md` 가 Jenson 의 cargocollective 글(2026-11-08 열람)을 요약: GTX 1070 에서 **500만~1000만 입자** 실시간, 충돌 단계 없음. "Jenson notes that collisions approximate conservation of matter and are needed for exact Physarum mimicry, but preferred the patterns without them."
- 시사점 **[추론]**:
  - 식의 효과는 **밀도 의존 분산**이다. 예컨대 "pure_multiscale" 은 s → 1 인 조밀한 곳에서 센서 거리 → 75 px, 이동 거리 → 25 px 가 되어 입자가 굵은 관 밖으로 튀어나가 멀리서 다시 감지한다. s 가 작은 곳에서는 고전 Jones 로 돌아간다. 하드 점유 제한(우리 실패 (c): 흩어짐) 대신 쓸 수 있는 **부드러운 자기제한**이다.
  - `sqrt(count)` 침착도 같은 역할: 한 관에 입자가 2배 몰려도 trail 은 1.41배만 는다. 양의 되먹임 이득이 1 미만으로 떨어지는 지점이 생겨 "굵은 관 하나"로의 폭주가 완화된다.
  - 우리 하이브리드에서 `D = trail/(trail+T0)` 포화는 **입자가 보는 감지값에는 걸려 있지 않다**(hybrid.py 는 `sf = tr + …` 로 원 trail 을 감지). 감지값을 포화시키거나(sqrt, tanh) 36 Points 식으로 RA/SO 를 trail 에 묶는 실험이 가장 싸다.

### 2.2 Michael Fogleman `physarum` (Go, CPU) **[코드]**

- github.com/fogleman/physarum (★930, MIT). 읽은 파일: `pkg/physarum/config.go`, `model.go`, `run.go`, `cmd/viewer/main.go`.
- 종(species)마다 trail 격자를 따로 두고, 감지값을 **종 간 인력/반발 테이블**로 합친다: `sensed_c = Σ_i table[c][i]·trail_i`, 대각 ≈ N(+1, 0.25), 비대각 ≈ N(−1, 0.25).
- 무작위 설정 범위: SA 0~120°, SD 0~64, RA 0~120°, step 0.2~2, deposit 5, decay(유지 비율) 0.1. 침착 후 box blur 반경 1 × 2패스.
- 규모: 정지 화상 1024² 에 2²² 입자(픽셀당 4개), 뷰어 512² 에 2²⁰(픽셀당 4개).
- 시사점 **[추론]**: 반발하는 두 번째 종은 망을 벌려 놓는 수단이다. 우리 모델에서는 점액 s 가 이미 "반발 장" 역할을 할 수 있다(`−b·s`). 다만 s 는 몸 밖에만 쌓이므로 몸 안의 관을 벌리지는 못한다. 몸 안에서 관 사이를 벌리려면 trail 의 넓은 블러를 빼는 **측방 억제**(`sensed = trail − k·blur_R(trail)`)가 같은 효과를 낸다 — 문헌 근거 없는 내 제안.

### 2.3 Amanda Ghassaei `gpu-io` physarum 예제 (WebGL1/2 프래그먼트 셰이더) **[코드]**

- github.com/amandaghassaei/gpu-io, `examples/physarum/index.js`. "All simulation steps are computed on the GPU via a series of WebGL fragment shaders."
- 프리셋 공통: `decayFactor 0.9, depositAmount 4, particleDensity 0.35`(픽셀당 0.35개). 프리셋별 `(sensorDistance, sensorAngle°, stepSize, rotationAngle°)`: Fibers (18, 5.5, 2, 45) / (14, 70, 1.5, −25) / (7.5, 90, 2, −45) / (18, 90, 2, −16) / (26, 5.5, 1.5, −70). 음의 회전각(= trail 에서 멀어지는 쪽으로 회전)이 여러 프리셋에 쓰인다.
- 시사점: WebGL 프래그먼트 경로에서 실제로 쓰이는 밀도 하한이 0.35/px 정도다.

### 2.4 Karsten Siemer `physarum-slime-mold` (WebGPU + WebGL2 폴백, 점유 규칙·성장·젤 렌더) **[코드][저장소 문서]**

- github.com/KarstenSiemer/physarum-slime-mold (MIT, 2026-11-12 커밋). 읽은 파일: `docs/adr/0003, 0008, 0025, 0027, 0028`, `docs/knowledge-base/{gpu-techniques-and-extensions,variants}.md`, `src/engine/shaders/render.wgsl`.
- **점유 규칙의 GPU 구현 (ADR 0008)**: 2패스 claim. 패스 A 에서 각 입자가 목표 셀에 고유 키를 `atomicMax(claims[target], key)`(키 = 입자 id 의 전단사 해시, 스텝마다 치환), **WebGL2 에서는 `MAX` 블렌딩**으로 같은 일을 한다. 목표 셀은 스텝 시작 시 비어 있어야 한다. 패스 B 에서 승자만 이동·침착. 막힌 입자는 침착 없음 + 무작위 새 방향. 근거 문헌: Yang, Andelfinger, Cai & Knoll, SIGSIM-PADS '18 (doi 10.1145/3200921.3200940; 본문 미확인).
  - 저자 조사: "No public GPU Physarum implements Jones' occupancy rule (GitHub code and web search, 2026-11-08)."
- **점유 규칙이 없을 때 측정 (ADR 0008)**: "Jones' attraction networks need the rule. Without it, agents pile up and the Fig. 4 network contracts into a few straight lines that wrap around the edges, usually within 2,000 to 8,000 steps (measured on 2026-11-09 on WebGPU and WebGL2 and in two CPU ports). Jones ties new branches to the random turns of blocked agents (p. 135)."
  - 충돌 없는 기본 장면에서 한 셀에 한 종의 입자가 **최대 29,083개**(WebGPU, 600 스텝) 쌓인다(ADR 0003).
- **규칙이 있어도 망은 계속 거칠어진다 (ADR 0027)**: Jones Fig. 4(Transport network, 200×200)의 lacuna 수, 스텝 99 / 512 / 1,740 / 4,151 에서 논문 그림 56 / 23 / 12 / 8, 구현 WebGPU 50.4 / 24.5 / 12.0 / 6.7 ± 0.6, WebGL2 50.9 / 26.1 / 11.1 / 6.6 ± 0.9. Fig. 5(Minimizing network)는 스텝 670 / 4,072 / 31,190 에서 논문 18 / 6 / 1, 구현 22.2 / 7.4 / 2.0 ± 0.4 — 3만 스텝이면 고리 1~2개로 수축한다.
- **성장 규칙을 넣어도 '가는 정맥의 부채'는 안 나왔다 (ADR 0024, 0025)**: 2026-11-11 의 소유자 비교 기록 — "agents barely react to food, a Maze started from one point never reaches the other food, tubes do not thicken, and the margin never looks like a tree crown." Jones 2011 성장·수축을 구현한 뒤에도 앱 설명문에서 "a fan of fine veins" 라는 문구를 "that the app does not draw" 라는 이유로 뺐다(ADR 0025 항목 28). 우리 (b)·(d) 와 같은 음성 결과를 독립 구현이 보고한 것이다.
- **성장·수축 (ADR 0025)**: Jones 2011 규칙(9×9 창에 1~10개면 분열, 5×5 창에 0~20개면 생존, 3 스텝마다). GPU 에서 새 입자 슬롯을 찾는 방법으로 **fan-in 4 의 히스토그램 피라미드(최대 13 레벨)**를 채택 — WebGL2 에서는 레벨마다 프래그먼트 패스로 만든다.
- **WebGL2 침착 (ADR 0003)**: 입자를 1픽셀 점으로 그려 카운트 텍스처에 가산 블렌딩. `EXT_float_blend` 가 있으면 RGBA32F(셀당 2²⁴ 까지 정확), 없으면 스텐실 8비트 + carry 로 우회.
- **성능 [저장소 문서]** (M3 Pro, Chromium): 440만 입자 장면의 한 스텝이 WebGPU 3.7 ms, **WebGL2 21~24 ms**(원인 미조사라고 적혀 있음). 200×200 Jones 장면 스텝 1.2~1.4 ms.
- 시사점: (1) 우리 (c) "점유 제한 → 흩어짐"은 규칙 자체보다 **규칙의 세부**(막히면 침착 안 함 + 무작위 방향, 인구 %p, 동기 claim) 문제일 수 있다 — 이 구현은 같은 규칙으로 Jones Fig. 4 를 수치까지 재현했다. (2) 그래도 Jones 망은 고정점이 없으면 단조롭게 거칠어진다(56 → 8). 굵기 위계가 유지되는 구조가 아니다. (3) 10만 입자면 WebGL2 입자 경로 비용은 문제가 안 된다(440만에 21 ms → 10만이면 대략 0.5 ms; 선형 외삽, 미측정).

### 2.5 MCPM / Polyphorm / PolyPhy — `jones-extensions.md` 8.1 참조

- 추가로 확인한 것 **[코드]**: `PolyPhyHub/PolyPhy` `src/polyphy/core/common.py` 기본값 — `N_AGENTS_DEFAULT = 1000000, sense_angle = 1.5, steering_rate = 0.5, sampling_exponent = 2.0, deposit_attenuation = 0.9, trace_attenuation = 0.96`. Taichi 로 GPU 실행. 몸·굵기 위계는 없다.

### 2.6 픽셀당 입자 수 비교 **[코드]**

| 구현 | 격자 | 입자 | 픽셀당 |
|---|---|---|---|
| Bleuje interactive-physarum | 1280×736 | 5.77 M | 6.1 |
| Fogleman (정지 화상 / 뷰어) | 1024² / 512² | 4.19 M / 1.05 M | 4 / 4 |
| KarstenSiemer "Three strains" | 1536×960 | 4.4 M | 3.0 |
| gpu-io physarum | 화면 크기 | 0.35 × 픽셀 수 | 0.35 |
| Jenson (2차) | 미확인 | 5~10 M | 미확인 |
| TheBlob 현재 | 1500² | 0.1 M | 0.044 (몸이 300² 를 덮으면 몸 안 1.1) |

**[추론]** 입자 trail 만으로 굵기가 다른 관을 표현하려면 가는 관에도 통계적으로 충분한 입자가 있어야 한다. 10만 입자로는 "굵은 간선 몇 개"가 한계이고, 가는 지선까지의 위계는 입자가 아니라 **장(field)**에서 나와야 할 가능성이 높다.

---

## 3. Tero / 전도도 적응을 격자에서 구현한 저장소

### 3.1 `davideciccarese/Physarum-polycephalum-simulation` (Python, 2026-10) **[저장소 문서][코드 일부]** — 우리 과제에 가장 가까운 공개 구현

- github.com/davideciccarese/Physarum-polycephalum-simulation (MIT, ★0, 단일 파일 `physarum_sim.py` 1,383줄, numpy/scipy). 읽은 것: `README.md`, `docs/model_documentation.md` 전체, `physarum_sim.py` 의 `Config`(60~200행). 본 것: `assets/scenario_A_step02500.png`, `scenario_C_step02500.png`. **실행은 못 했다**(0절).
- 격자: H×W = 140×180, 모든 셀이 노드, 8-이웃 쌍이 잠재 관(약 10만 개). 양쪽 셀이 점유되면 간선 활성.
- Tero 코어(문서 원문 표기):
  - `L p = I`, `L_ii = Σ_j D_ij / l_ij`, `L_ij = −D_ij / l_ij`, `Q_ij = (D_ij / l_ij)(p_i − p_j)`
  - `dD_ij/dt = alpha |Q_ij / Q0|^mu − gamma D_ij`, 지수 적분: `D(t+dt) = D e^(−gamma dt) + alpha |Q/Q0|^mu (1 − e^(−gamma dt)) / gamma`, `[D_floor, D_max]` 로 자름.
  - 기본값: `alpha = 1, mu = 1.5, gamma = 0.1, Q0 = 1, D_init = 0.2 (±5% 잡음), D_floor = 1e-4, D_max = 1e3, prune_threshold = 0.05, dt = 0.5`.
  - 풀이: 희소 LU(`splu`) 직접 풀이. 큰 격자용으로 Jacobi 전처리 CG 옵션. 연결 성분마다 게이지 1개.
- **소스/싱크 배정(저자 확장)**:
  - 소스 가중 `s_i = B_i (eps_s + S_i)`(먹는 셀 = 강한 소스, 기존 셀 = 약한 소스, eps_s = 0.1).
  - 싱크 가중 `k_i = front_i (c0 + S_i + w_A a_i^3) + w_d S_i max(0, 1 − B_i / B_ref)`(전진면 셀 = 싱크, c0 = 0.1, w_A = 2).
  - 성분의 총 전류 `I0_c = q_flow × Σ s`.
  - **sampled 모드(기본)**: 스텝마다 소스 셀 `n_sources = 4`개, 싱크 셀 `n_sinks = 2`개를 가중 확률로 뽑아 각각 `I0_c / n` 을 주입/회수.
  - **diffuse 모드**: `I_i = I0_c (s_i / Σs − k_i / Σk)`.
  - 저자 문서 원문: "The sampled mode is the one that produces sparse trunks: with hundreds of sources and sinks spread over a sheet, the diffuse mode gives every lattice edge a small flux and nothing is ever pruned."
- μ 의 효과(저자 문서): "mu = 1 keeps every lattice edge alive, and mu above 1 is what prunes the lattice into a vein network with a main trunk and secondary branches (mu = 2 leaves a single trunk)". 시나리오 B 비교(50×64, 1,000 스텝): μ = 2 에서 관 1,155개, μ = 1 에서 2,236개.
- **부채꼴 + 정맥 전환(저자 확장, 현상론)**:
  - 군체화: 빈 이웃 셀 j 의 군체화율 `lambda_j = k_col (eps + S_j^eta + lam_grad g_j) min(1, B_donor,max / B_ref)`, 확률 `1 − exp(−lambda_j dt)`; `k_col = 1.5, eta = 2, eps_explore = 0.005, lam_grad = 20`. 새 셀로 `b_colonize = 0.05` 를 가장 부유한 이웃에서 옮김(보존).
  - 유량에 따른 바이오매스 수송: `dB_i = −f_c kappa_T I_i dt`, `kappa_T = 0.5`, 소스당 상한 `f_max = 0.5`.
  - 판 퍼짐: `consolidate_age = 50` 스텝보다 어린 셀끼리만 `dB_i = D_B dt Σ_j (B_j − B_i) / l_ij²`, `D_B = 0.1`.
  - **정맥으로의 응집**: 나이 > 50 이고 `D ≥ tube_D = 1.0` 인 인접 간선이 없는 셀은 스텝당 `consolidate_rate·dt = 0.04·0.5` 비율로 바이오매스를 `b_sheet = 0.03` 까지 배수. 나이 > `retract_age = 200` 이고 관이 없으면 완전히 버림(scar, 200 스텝 재군체화 금지). 배수된 바이오매스는 전도도에 비례해 정맥 셀로.
- 결과(저장소 그림을 본 것): 시나리오 A/C 최종 상태에서 전도도 폭으로 그린 망이 **굵은 간선(진한 갈색) → 가는 지선 → 고리**의 위계를 보이고, 활성 영역은 채워진 판이다. 메트릭 패널: 시나리오 A step 2500 에서 area 5060, tubes 5355, meanD 14.97; C 에서 area 8094, tubes 8686, meanD 27.75. 선형 풀이 잔차 ~1e-14.
- 성능 **[저장소 문서]**: 140×180, 2,500 스텝에 60~90 초(노트북) — 스텝당 24~36 ms, 실시간 아님.
- 한계(저자 본인 기술): 군체화·응집 규칙은 실측 근거가 없다("the consolidation rules are a phenomenological substitute for the dewetting-like contraction of the real sheet"). 흐름은 스텝 내 정상류이고 왕복하지 않는다. 격자 아티팩트(축 정렬 간선)가 있다. 관에 저장되는 부피가 없다.
- **우리 문제에 주는 시사점**:
  - 실패 (a)에 대한 두 번째 독립 진단: 우리 연속체 프로토타입의 유량은 **몸 전체에 퍼진 연속 소스/싱크**(진동 위상)에서 나온다. 이 구현의 저자는 전역 타원 풀이를 쓰고도 diffuse 배정에서는 가지치기가 안 된다고 보고한다. 즉 타원형 압력만으로는 부족하고 **소스/싱크의 시공간 집중**(매 스텝 몇 점, 시간 평균은 넓게)이 필요할 수 있다. `continuum-channelization.md` 7절의 자체 점검은 "중심 소스 → 전선 띠 싱크"라는 이미 집중된 기하를 썼으므로 이 조건과 모순되지 않는다.
  - **[추론]** 무작위로 뽑힌 소수의 소스–싱크 쌍은 Tero 2010 의 "매 반복 무작위 먹이 쌍"과 같은 장치이고, 고리가 남는 이유도 같다(요동하는 부하; `vein-formation-models.md` 6절). GPU 에서는 소스/싱크 텍스처에 **프레임마다 다른 희소 잡음 마스크**를 곱하는 것으로 흉내 낼 수 있다.
  - 부채꼴은 이 구현에서도 **창발이 아니라 "어린 셀만 확산" 규칙**에서 나온다. "앞은 판, 뒤는 관"을 나이(= 전진면 통과 후 경과 시간) 장으로 가르는 것은 싸고 확실한 현상론적 대안이다.

### 3.2 브라우저 Tero 그래프 구현들 **[코드]**

- `santapong/physarum`(TypeScript): Delaunay/완전 그래프. 접지된 라플라시안을 **CG, tol 1e-6, 최대 200회, 초기값 0**(웜스타트 없음)으로 풂. `D ← D + Δt·(|Q|^μ/(1+|Q|^μ) − D)`.
- `brainlessmold/physarum`(TypeScript): Tero 2010 그대로, `f(Q) = Q^g/(1+Q^g)`. README 의 구현 경고 두 가지(원문):
  - "**Fix the current, not the pressure.** If you pin the pressures at both ends, the total flux decays together with the conductivities and the whole network quietly fades to zero."
  - "with a single pair per step, peripheral tubes die off between visits. That is what `pairsPerStep` is for — it averages several pairs per step, making adaptation slower than the pair sampling, and the network stays connected."
  - 36개 도시 망 비용(총 길이/MST) 2.04 (논문 1.75, 실제 철도 1.80)라고 자가 보고.
- `robert-30/physarum-maze`, `CyanTachyon/PhysarumFlow`: 그래프 Tero 재현(자세히 읽지 않음).
- 공통점: 전부 노드 수십~수천의 CPU 풀이. **격자 전체(10⁵~10⁶ 셀)를 GPU 반복법으로 푸는 Tero 구현은 찾지 못했다.**

### 3.3 그래프로 정맥만 따로 만드는 그래픽스 관용 기법 (spec 의 방식 D 변형) **[검색 요약 — 본문 미확인]**

- Runions, Fuhrer, Lane, Federl, Rolland-Lagan, Prusinkiewicz, "Modeling and visualization of leaf venation patterns", ACM TOG 24(3), 2005, pp. 702–711 (space colonization). 초록 수준에서 확인한 것: 잎맥이 잎 안에 박힌 호르몬(옥신) 소스를 향해 자라고, 소스 분포는 맥이 가까워지면 바뀌며, 맥 연결 그래프를 유지해 **맥 굵기를 정하고**, 규칙에 따라 열린(나무형) 패턴과 닫힌(고리 있는) 패턴이 모두 나온다.
- 세부 규칙(소스 제거 거리, 굵기 합산 지수 등)은 원문을 못 읽어 적지 않는다.
- 시사점 **[추론]**: 전진면 띠에 소스 점을 뿌리고 뒤에서 맥이 따라 자라게 하면 "앞은 촘촘하고 가늘게, 뒤는 굵게 합류"가 구성상 보장된다. 노드 수천 개의 CPU 그래프라 비용이 작고, 결과를 선분으로 D 텍스처에 그려 넣으면 장 모델과 결합할 수 있다. 물리적 창발은 아니지만 0단계 (d) 가 계속 실패할 때의 확실한 대안이다.

---

## 4. 질량 보존 이류를 프래그먼트 셰이더로: Reintegration Tracking

### 4.1 Mykhailo Moroz, "Reintegration tracking" (2020-08-31) **[본문]**

- 원문: michaelmoroz.github.io/Reintegration-Tracking/ — 사이트는 못 열었고, 같은 글의 원본 마크다운을 저장소 `michaelmoroz/michaelmoroz.github.io` 의 `_posts/2020-8-31-Reintegration-Tracking.md` 에서 읽었다.
- 상태: 셀마다 입자 하나(질량 M, 셀 내 위치 X, 속도 V). 갱신은 **이웃 3×3 gather**:

```
M_i(t+1) = Σ_j K_i(X_j + Δt V_j) m_j
X_i(t+1) = (1/M_i) Σ_j K_i(…) (X_j + Δt V_j) m_j
V_i(t+1) = (1/M_i) Σ_j K_i(…) V_j m_j
```
  K 를 0/1 대신 **분포의 셀 내 적분**으로 바꾼 것이 reintegration:
  `M = ∫∫_Ω ρ(X) dX`, `C = (1/M) ∫∫_Ω X ρ(X) dX`, ρ = 입자 위치 중심의 균일 축정렬 상자(반변 `diffusion_radius`).
```glsl
vec3 overlap(vec2 x, vec2 p, float diffusion_radius) {
    vec4 aabb0 = vec4(p - 0.5, p + 0.5);                                   // cell box
    vec4 aabb1 = vec4(x - diffusion_radius, x + diffusion_radius);         // particle box
    vec4 aabbX = vec4(max(aabb0.xy, aabb1.xy), min(aabb0.zw, aabb1.zw));   // overlap box
    vec2 center = 0.5*(aabbX.xy + aabbX.zw);
    vec2 size = max(aabbX.zw - aabbX.xy, 0.);
    float m = size.x*size.y/(4.0*diffusion_radius*diffusion_radius);       // relative area
    return vec3(center, m);
}
```
- 성질(원문): 분포 지름 < 1 px 이면 입자처럼, > 1 px 이면 수치 확산이 있는 일반 이류처럼 거동("The distribution diameter oscillates between 0.75 and 1.25"). 입자 위치를 셀 중심에 고정하고 반경 0.5 면 정확히 전진 오일러 이류. 속도는 셀당 1 px/스텝 이하로 제한해야 3×3 으로 충분. 반경 0.55~0.6 + SPH 커널 폭 1.5 px 로 유체를 만든다.
- 압력(상태방정식, 원문): 기체 `P = kρ`; Cole `P = k((ρ/ρ0)^γ − 1)`, γ = 7; 저자가 주로 쓴 것 `P_i = k ρ_i (ρ_i − ρ0)`.
- 저자가 든 응용 목록에 "Slime molds (shadertoy WtBcDG)"가 있다 — 셰이더 자체는 못 읽었다.

### 4.2 Flow-Lenia (Plantec et al., arXiv:2212.07906) **[본문]**

- 질량 보존 CA. 식 (5)–(7) 원문 표기:
  - 유동 `F_i^t = (1 − α^t) ∇U_i^t − α^t ∇A_Σ^t`, `α^t(p) = [(A_Σ^t(p)/θ_A)^n]_0^1` (U = 친화도 지도, A_Σ = 채널 합 질량. 질량이 임계 θ_A 에 가까우면 농도 기울기 반대 방향 확산이 지배).
  - `A_i^{t+dt}(p) = Σ_{p'} A_i^t(p') I_i(p', p)`, `I_i(p', p) = ∫_{Ω(p)} D(p''_i, s)`, `p''_i = p' + dt·F_i^t(p')`, D = 변 2s 의 균일 정사각 분포.
  - 값: `s = 0.65, n = 2, dt = 0.2`. s 를 "온도"라 부르며, s 에 따라 Turing 형 ↔ 평형 상이 바뀌고 경계에서 가장 역동적이라고 보고.
  - 성능: JAX, 128², 커널 10개에서 스텝당 255 µs (Tesla T4).
- 무엇을 보여 주나: 질량이 보존되는 덩어리가 스스로 움직이고(방향 운동), 장애물을 지나고, 화학주성을 한다. 점균 모델은 아니다.
- **시사점**: 우리 `h` 갱신(flux-form, 면 유량 제한 `clip(q, ±0.2h/dt)`)과 목적이 같지만, reintegration 은 (i) 3×3 gather 한 패스로 끝나고, (ii) 상류 판정·유출 제한이 필요 없으며(분포 적분이 1 이라 "가진 것보다 많이 내보낼 수 없다"), (iii) 셀 내 위치를 저장하면 수치 확산이 작아 **가는 관이 번지지 않는다**. 가는 정맥을 `h` 의 융기로 표현하려면 수치 확산이 작은 이류가 필요하므로 후보로 둘 만하다. 비용: 셀당 5개 float(M, X, V) → RGBA32F 1장 + 추가 1채널, 또는 X 를 생략(= 셀 중심 고정, 반경으로 확산 조절)하면 RGBA 1장.
- Flow-Lenia 의 α 항은 "임계 질량을 넘으면 퍼진다" — 우리 탄성벽 `κ(h − h*)` 와 같은 역할을 **친화도(끌림)와 가중 혼합**으로 구현한 것이다. 끌림 항 `∇U` 를 넣으면 몸이 원반으로 퍼지지 않고 응집 구조를 유지한다는 것이 이 모델의 요점이다(우리 실패 (d)와 관련된 방향 — 단 부채꼴이 나온다는 보고는 없다).

---

## 5. 국소 갱신만으로 위계 채널망이 나오는 실시간 사례: 수력 침식 (virtual pipe 모델)

- 서지: Mei, Decaudin, Hu, "Fast Hydraulic Erosion Simulation and Visualization on GPU", Pacific Graphics 2007, pp. 47–56 **[검색 요약 — 본문 미확인]**. Št'ava et al., "Interactive Terrain Modeling Using Hydraulic Erosion", SCA 2008 **[미확인]**.
- 읽은 구현 **[코드]**: `LanLou123/Webgl-Erosion`(WebGL2, 시뮬 해상도 **1024²**), `src/shaders/flow-frag.glsl`, `alterwaterhight-frag.glsl`, `sediment-frag.glsl`, `src/main.ts`.
- 상태: 지형 높이 b, 수심 d, **네 방향 유출 유량 f = (f_T, f_R, f_B, f_L)**(텍스처 1장), 속도 v, 부유 퇴적물 s.
- 식(코드 그대로):
```
Δh_dir = (b + d)_self − (b + d)_neighbor
f_dir ← max(0, f_dir + Δt · A · g · Δh_dir / l)          // 유량에 관성: 이전 값에 누적
K = min(1, d · l² / (Δt · Σ f_dir));  f_dir ← K · f_dir   // 가진 물보다 많이 못 내보냄
d ← max(0, d + Δt (Σ f_in − Σ f_out) / l²)
v = ((f_L→self − f_self→L + f_self→R − f_R→self), (…y…)) / 2
C = Kc · slope · |v|                                       // 운반 용량 (slope = max(0.1, sinα))
if C > s:  b −= Ks (C − s);  s += Ks (C − s)               // 침식
else:      b += Kd (s − C);  s −= Kd (s − C)               // 퇴적
s 는 v 로 세미-라그랑주 이류, d 는 증발로 감소
```
  기본값: `Δt = 0.05, l(pipelen) = 0.8, A(pipeArea) = 0.6, g = 0.80, Kc = 0.06~0.10, Ks = 0.020~0.036, Kd = 0.006~0.013, 증발 0.003~0.005`.
- 무엇을 재현하나: 비가 고르게 내리면 물이 모여 **수지상 하천망(본류–지류 위계)**이 지형에 새겨진다. 압력 풀이 없음, 패스당 4-이웃 참조.
- 왜 국소 갱신으로 되는가 **[추론]**: (1) 유량이 상태 변수이고 관성으로 누적되므로 정보가 확산(√t)이 아니라 **파동(∝ t)**으로 퍼진다. (2) 물은 고정된 지형 경사를 따라 실제로 흘러 내려가 모이므로 하류 유량 = 상류 유역 전체의 강우 적분이 된다. (3) 유량이 큰 곳이 더 깎이고 깎인 곳이 더 많은 물을 모은다(초선형 되먹임). `continuum-channelization.md` 5절 (가)의 "유량 = 하류 전체의 부피 변화율 적분"을 포아송 풀이 없이 얻는 구조다.
- **우리 문제에 주는 시사점 [추론, 미검증]**:
  - 우리 프로토타입은 `q = −M h ∇p` (과감쇠 Darcy, 유량이 압력의 즉시 함수)이고 p 가 h 의 국소 함수라 전체가 확산형이다. **면 유량을 상태로 두고 `q ← (1 − γ dt) q − dt·M h ∇p` 로 누적**하면 전신 방정식(감쇠 파동)이 되어 압력이 `c = √(κ h M)` 로 전파된다. CFL 한계에서 c ≈ 0.5 셀/스텝이면 600 스텝(진동 한 주기)에 300 셀 — 몸 크기 규모다. 확산형의 침투 깊이 수 셀(`continuum-channelization.md`)과 비교하면 타원 풀이 없이 몸 규모 유량을 얻는 유일한 국소 경로다.
  - 단 감쇠가 작으면 유량이 전도도가 아니라 관성으로 정해져 "전도도 적응 → 유량 재분배" 되먹임이 약해진다. 침식 모델에서 채널화는 전도도가 아니라 **바닥 높이(= 통로의 기하)**를 깎는 것으로 일어난다. 대응시키면: 유속이 큰 곳의 **겔 벽을 깎아 h 의 수용량(= 목표 두께 h*)을 키우는** 규칙. `h*` 를 장으로 두고 `∂h*/∂t = Ks·(Kc|v| − …)` 꼴로 올리는 것은 `continuum-channelization.md` 8절 제안 8(침식형 대안)의 실시간판이다.
  - 이것은 문헌에 있는 점균 모델이 아니다. 실험으로 확인해야 한다.

---

## 6. WebGL2 에서 (가변 계수) 포아송 방정식

### 6.1 유체 데모들이 실제로 쓰는 설정 **[코드]**

| 구현 | 압력 격자 | 반복 | 초기값(웜스타트) | 비고 |
|---|---|---|---|---|
| PavelDoGreat/WebGL-Fluid-Simulation (`script.js`) | `SIM_RESOLUTION: 128` (짧은 변 128), 염료만 1024 | Jacobi `PRESSURE_ITERATIONS: 20` | 이전 프레임 압력 × `PRESSURE: 0.8` | `pressure = (L + R + B + T − divergence) · 0.25` |
| amandaghassaei/gpu-io fluid | 화면의 1/8 (`VELOCITY_SCALE_FACTOR = 8`) | Jacobi `NUM_JACOBI_STEPS = 3` | 이전 프레임 그대로 | `(n + s + e + w + α·d)·β`, α = −1, β = 0.25 |
| haxiomic/GPU-Fluid-Experiments (`GPUFluid.hx`, `Main.hx`) | 화면의 1/2 ~ 1/5 | Jacobi 18~30 (기본 18) | 이전 프레임 그대로 | 품질 프리셋별 (1/2, 30) / (1/4, 20) / (1/4, 18) |
| GPU Gems 1 ch. 38 (Harris 2004) | — | Jacobi 40~80 권장 **[기억, 미확인]** | 0 **[기억]** | 원문 못 엶 |

- 공통 패턴: **(1) 압력은 저해상도에서, (2) 이전 프레임 해를 초기값으로(감쇠 0.8~1.0), (3) 반복 3~30회.** 이것은 "눈에 그럴듯한 비압축성"용이고 수렴한 해가 아니다.

### 6.2 수렴을 측정한 사례 **[저장소 문서 — 자가 보고, 상수 계수]**

- `abho7/fluid-sim`(WebGPU compute, Intel gen-12lp 내장 GPU, 주기 경계, f32). `results/gpu-verify.json` 의 포아송 잔차(초기 1 대비):
  - Jacobi: 20 스윕 0.110 / 40 → 0.078 / 80 → 0.057 / 320 → 0.031
  - Red-black GS: 20 → 0.0102 / 80 → 0.0019 / 320 → 2.5e-4
  - 멀티그리드 V-사이클(pre 2, post 2, 최조 격자 8 에서 40 스윕, full-weighting 2×2 평균 + bilinear): **1 사이클(5.33 스윕 상당) → 0.0064, 2 사이클 → 2.8e-4**
  - `results/bench.json`: 목표 max|div| ≤ 1e-3 에 red-black 은 64² 에서 160 스윕, 128² 에서 640 스윕, **256²·512² 에서는 1,280 스윕으로도 실패**. 멀티그리드는 64²~512² 전부 1 사이클로 달성. `interactive.gpuRows` 항목: 512² 19.2 ms, 1024² 42.4 ms, 2048² 211.7 ms (내장 GPU. 이 값이 정확히 무엇의 시간인지는 측정 코드를 읽지 않아 확인하지 못했다).
  - README 의 f32 한계: "The multigrid residual plateaus near 1e-7".
- `in-c0/cuda-lab`(CUDA, RTX 2080) README: "**Jacobi is a smoother, not a solver.** … removing 76% of grid-scale mode k=64 in 20 sweeps but 0.6% of domain-scale mode k=1 in 320." "640 Jacobi sweeps, at 14.6× the cost, still cannot match 4 V-cycles." Red-black GS 는 "2× convergence exactly cancelled by stride-2 access halving effective bandwidth".
- 프래그먼트 셰이더에서 red-black 은 색마다 전체 화면 패스가 필요하므로(체커보드 discard 를 써도 드로콜 2회) 패스 수 기준 이득이 없다 — 아래 자체 점검에서도 확인.

### 6.3 [자체 수치 점검] 가변 계수 + 몸 마스크에서의 비용

문헌·저장소 수치는 전부 상수 계수다. 우리 문제(관/비관 전도도 대비, 몸 밖은 무유량)에 대해 직접 쟀다.

- 설정(`poisson_cost_check.py`): N² 주기 격자, 몸 = 반지름 0.4N 원판(밖은 면 전도도 0, 미지수 제외). 셀 전도도 C = r_bg (배경) 또는 1 (관; 중심에서 뻗는 폭 3셀 분기 랜덤워크). 면 전도도 = 조화 평균. `Σ_f c_f (p_i − p_nb) = b_i`, b = 중심 작은 원판 소스 − 전선 띠(0.80R~0.95R) 싱크. 기준해 = scipy 희소 직접 풀이. 지표 = **면 유량의 상대 L2 오차** `‖q − q*‖/‖q*‖` (압력이 아니라 유량 — 적응식이 쓰는 양). 초기값 0(콜드 스타트).
- 멀티그리드: 셀 중심 2× 조대화, 평활 = 감쇠 Jacobi(ω = 0.8) pre 2 + post 2, 잔차 제한 = 2×2 합, 최조 격자 8² 에서 40 스윕, **조대 면 전도도 = 조대 면에 걸친 미세 면 2개의 산술 평균**, 보간 = 상수(nearest) 또는 bilinear.

**(1) 콜드 스타트에서 유량 오차가 기준 이하로 내려가는 데 드는 비용** (`v2/res_*.json`). Jacobi 는 전체 화면 패스 수, MG 는 V-사이클 수(보간 nearest). 관 폭 3셀, 관 면적 = 몸의 10~15%.

| 격자 | 대비 (1/r_bg) | Jacobi 패스: 오차 ≤ 0.5 / 0.3 / 0.1 | MG 사이클: ≤ 0.5 / 0.3 / 0.1 / 0.03 | MG 1·2·3·5 사이클 뒤 오차 |
|---|---|---|---|---|
| 256² | 50 | 2,560 / 5,120 / 10,240 | 1 / 1 / 3 / 5 | 0.25 / 0.11 / 0.066 / 0.029 |
| 256² | 500 | 5,120 / 10,240 / 20,480 | 1 / 2 / 4 / 8 | 0.32 / 0.17 / 0.12 / 0.064 |
| 512² | 50 | 10,240 / 20,480 / 20,480 초과(그 시점 0.28) | 1 / 2 / 4 / 8 | 0.38 / 0.20 / 0.13 / 0.061 |
| 512² | 500 | 20,480 / 미달(20,480 에서 0.39) | 1 / 3 / 8 / 21 | 0.49 / 0.33 / 0.24 / 0.15 |

- Jacobi 패스 수는 격자 변의 제곱에 비례한다(256² → 512² 에서 4배). 대비 50 기준으로 750² 로 외삽하면 유량 오차 50% 에 약 2.2만 패스, 30% 에 4.4만 패스 — 프레임당 20회면 **18~37초**(1500² 면 그 4배, 1~2.5분). 즉 Jacobi + 웜스타트의 압력장은 변화에 수십 초 늦게 따라온다. 소스·전도도·몸 모양이 그보다 천천히 변하는 **정적(DC) 성분에는 쓸 수 있지만**, 주기 10초 안팎의 맥동 성분은 따라가지 못한다((3) 참조). (128² 에서는 0.5 / 0.3 / 0.1 에 640 / 2,560 / 5,120 패스; `res_128.json`, 이 실행만 관 면적 14.7% 의 초기 판.)
- Red-black GS 는 128² 에서 Jacobi 와 **패스 수 기준으로 똑같았다**(스윕당 2패스라 2배 수렴이 상쇄. 640 패스에서 둘 다 0.50).
- V-사이클 1회의 비용: 미세 격자 패스 9.3~9.4회 분량의 픽셀 작업, 드로콜 75회(256², 6레벨) / 82회(512², 7레벨). 최조 격자 스윕을 40 → 10 으로 줄이거나 4² 까지 조대화하면 드로콜 45~50회, 수렴은 같다(`mg_variants.py`).
- MG 의 점근 수렴률은 사이클당 약 0.7 로 교과서 값(0.1 안팎)보다 훨씬 나쁘다. 처음 2~3 사이클이 빠르고 그 뒤가 느리다. 계수 도약 + 단순(산술 평균) 조대화의 한계다.

**(2) MG 가 깨지는 조건 — 반드시 알고 쓸 것**

| 변형 (256², 대비 50, 폭 3) | 결과 |
|---|---|
| V(2,2), ω = 0.8 (기준) | 오차 0.31 → 0.14 → 0.080 → 0.052, 점근 0.71/사이클 |
| V(3,3), ω = 0.8 | 0.23 → 0.097 → 0.055, 점근 0.66 |
| **V(1,1), ω = 0.8** | **발산**(점근 1.3~1.6) |
| V(1,1), ω = 1.0 | 수렴하지만 느림(0.89) |
| V(1,1), ω = 0.67 | 발산 |
| V(1,0) | 발산 |
| V(2,2), ω = 1.0 | 0.28 → 0.15 → 0.10, 점근 0.90 |
| 조대 보정에 감쇠 θ = 0.7 / 0.5 | 훨씬 나빠짐(레벨마다 곱해져 전역 모드가 0.7⁶ 로 줄어듦). 쓰지 말 것 |
| 조대 전도도를 직렬–병렬(조화형)로 계산 | **발산**(128²). 조대 연산자가 너무 약해져 과보정 |

| 관 폭 1셀 (256², 관 면적 3%) | Jacobi | MG nearest | MG bilinear |
|---|---|---|---|
| 대비 500 | 40,960 패스에서 0.12 | **발산** | 6 사이클 0.5, 12 사이클 0.29, 30 사이클 0.11 |
| 대비 5,000 | 40,960 패스에서 0.66 | **발산** | 30 사이클에서 0.60 |

- **폭 1셀의 고대비 관은 단순 기하 멀티그리드를 깨뜨린다.** 조대 격자가 관을 표현하지 못하기 때문이다. 대책(택1 이상): (i) 관 폭을 3셀 이상으로 정칙화(`continuum-channelization.md` 6절 조건 6 — 어차피 필요), (ii) 전도도 대비를 포화 법칙으로 50~500 이내로 제한, (iii) 압력을 관 폭이 3셀 이상이 되는 해상도에서만 푼다. 연산자 의존 보간(Dendy 식 black-box MG)이나 MG 전처리 CG 는 셰이더 구현 사례를 찾지 못했다.
- 폭 3셀에서도 bilinear 보간이 nearest 보다 나은 경우는 없었다(대비 500 에서 오히려 나쁨: 256² 첫 사이클 1.11 대 0.32). 마른 셀 경계를 넘어 번지기 때문으로 보인다. **nearest(2×2 복제) 보간 + 2×2 합 제한**을 쓸 것.

**(3) 웜스타트로 진동 소스를 따라갈 수 있는가** (`tracking_check.py`, 256², 대비 50, 폭 3)

소스 `b(t) = b_dc + b_ac·cos(2πt/T)`, b_ac = 몸의 왼쪽 절반 ↔ 오른쪽 절반 왕복(shuttle), T = 600 프레임(60 fps 에서 10초). 매 프레임 이전 해에서 시작. 둘째 주기 동안의 RMS 상대 유량 오차:

| 프레임당 작업 | 미세 패스 상당 | RMS 유량 오차 |
|---|---|---|
| Jacobi 5회 | 5 | 0.61 |
| Jacobi 20회 | 20 | 0.54 |
| Jacobi 60회 | 60 | 0.51 |
| **V-사이클 1회** | 9.4 | **0.0037** |
| V-사이클 1회를 4프레임마다 | 2.3 | 0.021 |

- Jacobi 는 프레임당 60회를 써도 몸 규모 왕복 모드를 절반밖에 못 따라간다(가장 느린 모드의 완화 시간이 진동 주기보다 길다). **웜스타트 Jacobi 는 정적인(DC) 소스에만 쓸 수 있다.**
- V-사이클은 4프레임에 한 번만 돌려도 2% 다. 프레임당 드로콜 예산이 빠듯하면 사이클을 여러 프레임에 나눠 돌리는 것이 가능하다는 뜻이다.
- 재지 않은 것: 512² 이상·대비 500 에서의 추적 오차, 전도도 C 가 프레임마다 바뀔 때, 몸 마스크가 움직일 때. f32/half-float 정밀도 영향(numpy float64 로 돌렸다; `abho7/fluid-sim` 은 f32 에서 잔차가 1e-7 에서 멈춘다고 보고).

**(4) WebGL2 구현 메모 [추론]**
- 레벨별 텍스처: `p`(핑퐁 2장, R32F 또는 R16F), `rhs`(R), 면 전도도 `(c_x, c_y)`(RG). 조대 전도도는 C 가 바뀔 때만 다시 만든다(레벨당 1패스, 2탭 평균). 대각합은 평활 셰이더에서 4탭으로 즉석 계산.
- 한 사이클의 패스 순서(레벨 k → k+1): 평활 ×2 → 잔차+제한(한 셰이더로 합칠 수 있다: 조대 픽셀에서 미세 2×2 의 잔차를 직접 계산하면 16탭 정도, 드로콜 1회 절약) → … → 보간+가산(nearest, 1패스) → 평활 ×2.
- 드로콜 수가 진짜 비용이다. 750² 에서 7레벨 V(2,2) ≈ 45~80 드로콜. WebGL2 에서 FBO 전환을 포함한 드로콜당 CPU 비용은 **이 조사에서 측정하지 못했다** — 0단계에서 가장 먼저 실측할 항목.
- **압력이 부정확해도 질량 보존은 깨지지 않는다**: h 갱신이 flux-form 이면 어떤 p 를 넣어도 총량이 보존된다. 따라서 압력을 1/2~1/4 해상도(375²~188²)에서 풀고 bilinear 로 올려 미세 격자의 `q = −C_fine ∇p` 에 쓰는 구성이 가능하다(유체 데모들의 저해상도 압력과 같은 발상). 오차는 "유량 분배의 정확도"에만 들어간다.
- 참고(본문 미확인, 검색 요약): 프래그먼트 셰이더 멀티그리드의 고전은 Goodnight et al. 2003 ("A multigrid solver for boundary value problems using programmable graphics hardware"), Bolz et al. SIGGRAPH 2003 ("Sparse matrix solvers on the GPU: conjugate gradients and multigrid"). WebGL 판 예제 페이지가 ibiblio.org/e-notes/webgl/gpu/mg/ 에 있다(가중 Jacobi 평활, 5레벨 V-사이클이라고 요약됨).
- 주의: 첫 실행 묶음(`res_256.json`, `log_512.txt`, `log_track_256.txt`)은 관 생성기가 몸의 40~86% 를 관으로 덮어 버린 설정이라 버렸다. 위 표는 관 면적을 10~15% 로 고친 `v2/` 결과다. 버린 묶음의 추적 결과(Jacobi 0.61 / 0.55 / 0.52, MG 0.0059 / 0.032)는 `v2` 와 같은 결론이다.

---

## 7. 젖은 질감 렌더링 (높이맵 기반)

### 7.1 실제 구현 A — KarstenSiemer "gel" 스타일 **[코드]** (`src/engine/shaders/render.wgsl`, WebGL2 판도 같은 식)

```
height(p) = 1 − exp(−max(heightFiltered(p), 0))               // 포화하는 높이. heightFiltered = (trail − black)·exposure 의 4탭 평균
d  = max(scale, 0.75)                                          // 차분 간격(셀)
gx = height(p + (d,0)) − height(p − (d,0));  gy = 같은 식 y
n  = normalize(vec3(−gx, −gy, 0.35·d))                         // 0.35 = 릴리프 세기
l  = normalize(vec3(−0.45, −0.6, 0.65))                        // 왼쪽 위 광원
diffuse = max(dot(n, l), 0)
spec    = pow(max(dot(n, normalize(l + vec3(0,0,1))), 0), 48)  // Blinn–Phong, 시선 = 수직
lit     = albedo·(0.25 + 0.9·diffuse) + 0.6·spec·h
color   = mix(base, lit, smoothstep(0.02, 0.35, h))            // 가장자리 알파
```
- 최적화와 측정 **[저장소 문서]** (ADR 0009): 높이를 프레임당 한 번 격자 해상도 `r16float` 텍스처에 써 두고(값이 trail 의 아핀 함수라 하드웨어 bilinear 로 충분) 조명 패스에서 5점만 읽는다. M3 Pro 에서 젤 프레임 7.4~9.3 ms → **1.7~2.3 ms** (glow 스타일 1.3~1.8 ms).
- 같은 저장소의 "paper" 스타일은 Beer–Lambert: `base · exp(−absorb · exposure)`.
- 같은 저장소 조사 노트: "Relief: normals from central differences, Phong specular (SuboptimalEng/slime-sim-webgpu)" — 릴리프 방식은 여러 구현이 공유한다.

### 7.2 실제 구현 B — three.js `SubsurfaceScatteringShader` **[코드]** (`examples/jsm/shaders/SubsurfaceScatteringShader.js`)

- 주석의 출처: Barré-Brisebois & Bouchard, GDC 2011, "Approximating Translucency for a Fast, Cheap and Convincing Subsurface Scattering Look" (슬라이드 원문 미확인).
```glsl
vec3 thickness = thicknessColor * texture2D(thicknessMap, uv).r;
vec3 scatteringHalf = normalize(directLight.direction + (geometryNormal * thicknessDistortion));
float scatteringDot = pow(saturate(dot(geometryViewDir, -scatteringHalf)), thicknessPower) * thicknessScale;
vec3 scatteringIllu = (scatteringDot + thicknessAmbient) * thickness;
reflectedLight.directDiffuse += scatteringIllu * thicknessAttenuation * directLight.color;
```
  기본값: `thicknessDistortion 0.1, thicknessAmbient 0.0, thicknessAttenuation 0.1, thicknessPower 2.0, thicknessScale 10.0`. 여기서 thicknessMap 은 "얇을수록 밝은" 지도(투과량)다.
- 2D 평면 점균에 옮기는 법 **[추론]**: 시선 V = (0,0,1) 고정, 광원을 화면 뒤쪽 비스듬히(역광) 두면 `dot(V, −normalize(L + N·distortion))` 이 법선 기울기에 따라 변한다. 투과량 = `exp(−σ·h)`(Beer–Lambert)를 thickness 로 쓰면 얇은 전진면 가장자리는 밝게 비치고 굵은 정맥은 불투명하고 진해진다.

### 7.3 조합 제안 (h, D, s 가 있을 때) **[추론 — 위 두 구현의 식을 조합]**

1. 높이 사전 패스: `H = 1 − exp(−k_h·h)` + 정맥 융기 `k_D·D`. 격자 해상도 R16F, LINEAR 필터.
2. 법선: 중앙차분(4탭), 줌에 따라 간격 `d = max(셀/픽셀, 0.75)`.
3. 몸 색: 흡수 `T = exp(−σ_rgb·h)`(파장별 σ 로 얇은 곳은 연노랑, 두꺼운 곳은 진한 황토), `color = mix(substrate, pigment, 1 − T)`.
4. 표면: Blinn–Phong 지수 40~48 스펙큘러 × Schlick 프레넬(F0 ≈ 0.02~0.04, 물 막) **[프레넬 수치는 기억]**. 맥동(`A sin φ`)이 H 에 들어가 있으면 하이라이트가 저절로 일렁인다.
5. 투과: 7.2 식에 thickness = T.
6. 점액 흔적 s: 기질에 약한 스펙큘러만 있는 얇은 막(높이 기여 0.02~0.05)으로.
- 비용 추정: 사전 패스 1 + 본 패스 1, 본 패스 텍스처 읽기 5~6회. 7.1 의 측정(1.7~2.3 ms, 통합 GPU 급)과 같은 구조.
- 못 읽은 참고 자료(검색 요약만): Oat, "Rendering Gooey Materials with Multiple Layers", SIGGRAPH 2006 course; Jensen, Legakis, Dorsey, "Rendering of Wet Materials", EGWR 1999; GPU Gems 1 ch. 16 wrap lighting `max(0, (N·L + w)/(1 + w))` **[기억]**.

---

## 8. 우리 실패 (a)~(d)에 대한 시사점 (이 노트의 범위에서)

| 실패 | 구현 사례가 말해 주는 것 | 근거 |
|---|---|---|
| (a) Tero 식을 연속 격자에 올리면 얼룩 | 격자 간선 Tero 로 위계 정맥이 나온 구현은 **전역 직접 풀이 + 스텝당 소스 4·싱크 2 무작위 추출 + μ = 1.5** 였다. 넓게 퍼진 소스/싱크(diffuse)로는 그 저자도 가지치기가 안 됐다. "전류 고정, 압력 고정 아님"도 구현자들의 공통 경고. | 3.1, 3.2 [저장소 문서] |
| (b) 갇힌 Jones 입자가 직선 관 하나로 | 충돌 없는 Jones 는 GPU 구현에서도 "직선 몇 개"로 수축한다(2,000~8,000 스텝, 셀당 최대 2.9만 입자 적체). 예술 구현들은 36 Points 식(밀도 의존 파라미터), sqrt 침착, 리스폰(1000 스텝마다), 높은 입자 밀도(0.35~6/px)로 이를 피한다. | 2.1, 2.4 [코드][저장소 문서] |
| (c) 셀당 1개 제한 → 흩어짐 | 동기 claim 방식 점유 규칙으로 Jones Fig. 4 의 lacuna 수가 재현된 GPU 구현이 있다. 규칙 = 막히면 **침착 없음 + 무작위 방향**, 스텝 시작 시 빈 셀만 목표. 단 그 망도 56 → 8 lacuna 로 계속 거칠어진다. | 2.4 [저장소 문서] |
| (d) 몸이 원반, 부채꼴 없음 | 부채꼴을 낸 유일한 격자 구현은 창발이 아니라 **나이 장**(어린 셀만 판으로 퍼지고, 늙은 무관 셀은 배수)으로 만들었다. 실시간 셰이더에서 창발적 부채꼴을 보인 사례는 찾지 못했다. | 3.1 [저장소 문서] |

---

## 9. 실험 제안 (우선순위 순)

1. **감지값 포화 / 36 Points 식**을 갇힌 Jones 입자에 적용: (i) 감지를 `sqrt(trail)` 또는 `trail/(trail+T0)` 로, (ii) 침착을 `sqrt(count)` 로, (iii) `RA = RA0 + RAA·s^RAE`, `SO = SO0 + SOA·s^SOE` (s = 정규화 trail). 지표: 관 수, 관 폭 분포, 한 줄로 수렴하기까지의 스텝 수. 160² 프로토타입에서 몇 분이면 된다.
2. **희소 무작위 소스/싱크**: 타원 압력 판(`continuum-channelization.md` 7절의 `scalar_channel_check.py`)에서 소스/싱크를 (A) 넓은 연속 분포, (B) 프레임마다 다른 점 2~6개(시간 평균은 A 와 같게)로 바꿔 비교. 3.1 의 "diffuse 는 가지치기 안 됨" 주장을 직접 확인. μ = 1.0 / 1.5 / 2.0.
3. **멀티그리드 V-사이클을 WebGL2 로**: 6.3 의 설정(V(2,2), ω = 0.8, 산술 평균 조대화, nearest 보간, 2×2 합 제한, 4² 에서 8 스윕)을 그대로 구현해 375²·750² 에서 사이클당 ms 를 실측. 예상 드로콜 45~80회/사이클. V(1,1) 로 줄이지 말 것(발산). 프레임당 1 사이클 또는 4프레임당 1 사이클 + 웜스타트로 충분한지, 관 폭·대비를 바꿔 가며 6.3 표와 대조. half-float(R16F)에서 수렴이 유지되는지도 확인.
4. **나이 장으로 판/정맥 구분**: `age` 텍스처(전진면이 지나간 뒤 경과 프레임). 어린 영역은 이동도 높고 균일(판), 늙은 영역은 `D` 가 낮은 곳의 h 를 관 쪽으로 배수. 3.1 의 `consolidate_age = 50, rate = 0.04, retract_age = 200` 비율(전진 속도 대비)을 출발점으로.
5. **유량 관성(virtual pipe)**: 면 유량을 RGBA 텍스처로 저장, `q ← (1 − γdt)q − dt·M h ∇p`. γ 를 스윕해 압력이 몸 전체에 닿는지(진동 한 주기 안에 반대편 h 가 반응하는지) 측정. 그 위에 "유속이 큰 곳의 h* 를 키우는" 침식형 규칙.
6. **reintegration tracking 으로 h 이류**: 현재 flux-form 과 수치 확산 비교(폭 3셀 융기가 1,000 스텝 뒤 얼마나 번지는지), 질량 오차.
7. **점유 규칙 재시험**: KarstenSiemer 방식 그대로(막히면 침착 없음 + 무작위 방향, 동기 claim, 인구 = 몸 면적의 3~15%). 우리 (c)가 구현 세부 문제였는지 확인.
8. **렌더**: 7.3 조합을 정적 h/D 스냅숏(프로토타입 출력 PNG → 텍스처)에 먼저 적용해 룩을 정한다. 시뮬과 독립적으로 진행 가능.

---

## 10. 접근하지 못한 것

- cargocollective.com/sagejenson/physarum, sagejenson.com/36points (Jenson 원문) — 호스트 차단. Bleuje 의 코드 주석과 KarstenSiemer 의 2차 요약으로 대체.
- bleuje.com/physarum-explanation (Bleuje 해설 글) — 호스트 차단. 저장소 코드로 대체.
- shadertoy.com 전체 (Moroz "Slime molds" WtBcDG, "Paint streams", cornusammonis/flockaroo 의 mip 기반 압력 풀이 등) — 차단. mip 피라미드로 포아송을 1~수 패스에 근사하는 Shadertoy 기법은 **확인하지 못했다**.
- developer.nvidia.com GPU Gems 1 ch. 38 (Harris), ch. 16 — 차단. "Jacobi 40~80회", wrap lighting 식은 기억이다.
- Mei et al. 2007, Št'ava et al. 2008 (침식 원 논문) — 미확인. 식은 WebGL 구현 코드에서 옮겼다.
- Barré-Brisebois & Bouchard GDC 2011 슬라이드 — 미확인. three.js 구현으로 대체.
- Yang et al. SIGSIM-PADS '18 (GPU 에이전트 충돌 claim) — 미확인.
- Krüger & Westermann 2003 (프래그먼트 셰이더 CG), Farbman et al. 2011 "Convolution Pyramids" — 찾아보지 못했다.
- Runions et al. 2005 (space colonization 잎맥) 본문 — 미확인. 초록 수준만.
- Goodnight et al. 2003, Bolz et al. 2003 (프래그먼트 셰이더 멀티그리드/CG), ibiblio e-notes WebGL multigrid 페이지 — 검색 요약만.
- `davideciccarese/Physarum-polycephalum-simulation` 실행 — 권한 정책으로 차단. diffuse vs sampled, μ 비교는 저자 문서의 주장일 뿐 내가 확인하지 못했다.
- GitHub 코드 검색(파일 내용 검색)은 쓰지 못했다(저장소 메타데이터 검색만). 별 0~수 개짜리 저장소에 관련 구현이 더 있을 수 있다.

## 11. 접근한 URL / 파일

- https://github.com/Bleuje/interactive-physarum , https://github.com/Bleuje/physarum-36p
- https://github.com/fogleman/physarum
- https://github.com/amandaghassaei/gpu-io (examples/physarum, examples/fluid)
- https://github.com/KarstenSiemer/physarum-slime-mold
- https://github.com/PolyPhyHub/PolyPhy
- https://github.com/davideciccarese/Physarum-polycephalum-simulation
- https://github.com/santapong/physarum , https://github.com/brainlessmold/physarum
- https://github.com/michaelmoroz/michaelmoroz.github.io (`_posts/2020-8-31-Reintegration-Tracking.md`)
- https://arxiv.org/abs/2212.07906 (Flow-Lenia)
- https://github.com/LanLou123/Webgl-Erosion
- https://github.com/PavelDoGreat/WebGL-Fluid-Simulation , https://github.com/haxiomic/GPU-Fluid-Experiments
- https://github.com/abho7/fluid-sim , https://github.com/in-c0/cuda-lab
- https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/shaders/SubsurfaceScatteringShader.js
- clone 만 하고 자세히 읽지 않은 것: SebLague/Slime-Simulation, nicoptere/physarum, DenizBicer/Physarum, CreativeCodingLab/Polyphorm, MattKulka/mycelia, SuboptimalEng/slime-sim-webgpu, Barbelot/Unity-ReintegrationTrackingFluid, ctkrug/erosion, tunabrain/incremental-fluids, mharrys/fluids-2d, thenumbernine/poisson-gpu-js, robert-30/physarum-maze, CyanTachyon/PhysarumFlow
