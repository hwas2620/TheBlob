# 문헌 노트 — Jones 입자 모델의 후속 연구와 확장 (jones-extensions)

작성 범위: Jeff Jones의 다중 에이전트(입자) 점균 모델 2009~2016 후속 논문, 그리고 다른 저자의 입자 모델 확장.
목적: TheBlob `specs/plasmodium-core` 프로토타입의 실패 (a)~(d)를 설명하거나 뒤집을 수 있는 규칙·조건·수치를 뽑는다.

표기: **[본문]** = 원문 본문을 직접 읽고 확인. **[초록]** = 초록/검색 스니펫만 봄. **[2차]** = 다른 논문이 요약·재인용한 내용. **[기억]** = 기억에만 의존(신뢰도 낮음). **[추론]** = 문헌에 직접 없고 이 노트 작성자가 유도한 것.

---

## 0. 접근 상태

이 세션에서 열 수 있었던 호스트는 사실상 `arxiv.org` 하나였다. `uwe-repository.worktribe.com`, `ics-websites.science.uu.nl`, `link.springer.com`, `direct.mit.edu`, `pmc.ncbi.nlm.nih.gov`, `www.actaphys.uj.edu.pl`, `cargocollective.com`, `export.arxiv.org` 는 모두 네트워크 정책으로 막혀 있었다.

본문을 읽은 것 (전부 arXiv PDF → pdftotext):

| 약칭 | 서지 | URL |
|---|---|---|
| IJUC10 | Jones, "The Emergence and Dynamical Evolution of Complex Transport Networks from Simple Low-Level Behaviours", Int. J. Unconventional Computing 6(2):125–144, 2010 | https://arxiv.org/pdf/1503.06579 |
| PRPM09 | Adamatzky & Jones, "Programmable reconfiguration of Physarum machines" (2009 arXiv; 학술지 권호는 확인 못 함) | https://arxiv.org/pdf/0901.4556 |
| ROAD09 | Adamatzky & Jones, "Road planning with slime mould: if Physarum built motorways it would route M6/M74 through Newcastle" (2009 arXiv) | https://arxiv.org/pdf/0912.3967 |
| ADD10 | Jones & Adamatzky, "Towards Physarum Binary Adders" (2010 arXiv) | https://arxiv.org/pdf/1005.2303 |
| AMOE12 | Jones & Adamatzky, "Emergence of Self-Organized Amoeboid Movement in a Multi-Agent Approximation of Physarum polycephalum", Bioinspiration & Biomimetics 7:016009, 2012 | https://arxiv.org/pdf/1212.0023 |
| ENG12 | Tsuda, Jones & Adamatzky, "Towards Physarum Engines", Applied Bionics and Biomechanics 9(3):221–240, 2012 | https://arxiv.org/pdf/1212.0536 |
| TSP13 | Jones & Adamatzky, "Computation of the Travelling Salesman Problem by a Shrinking Blob", Natural Computing 13(1):1–16, 2014 | https://arxiv.org/pdf/1303.4969 |
| VOR13 | Jones & Adamatzky, "Slime Mould Inspired Generalised Voronoi Diagrams with Repulsive Fields" (IJBC in press로 표기) | https://arxiv.org/pdf/1503.06973 |
| MECH15 | Jones, "Mechanisms Inducing Parallel Computation in a Model of Physarum polycephalum Transport Networks", Parallel Processing Letters 25(1):1540004, 2015 | https://arxiv.org/pdf/1511.05869 |
| APP15 | Jones, "Applications of Multi-Agent Slime Mould Computing" (IJPEDS 투고본, 2015) | https://arxiv.org/pdf/1511.05774 |
| SHAPE15 | Jones, Mayne & Adamatzky, "Representation of Shape Mediated by Environmental Stimuli in Physarum polycephalum and a Multi-agent Model" (2015) | https://arxiv.org/pdf/1511.05862 |
| GUIDE15 | Jones, "Automated Guidance of Collective Movement in a Multi-Agent Model of Physarum polycephalum" (2015) | https://arxiv.org/pdf/1511.07654 |
| ENV15 | Jones, "Exploiting Environmental Computation in a Multi-Agent Model of Slime Mould" (2015, 짧은 초록형 논문) | https://arxiv.org/pdf/1511.07647 |
| MCPM | Elek, Burchett, Prochaska, Forbes, "Monte Carlo Physarum Machine: Characteristics of Pattern Formation in Continuous Stochastic Transport Networks" (2022) | https://arxiv.org/pdf/2204.01256 |
| RPG24 | Reginato, Proverbio & Giordano, "Bottom-up robust modeling for the foraging behavior of Physarum polycephalum" (2024 preprint) | https://arxiv.org/pdf/2412.19790 |
| ALM21 | de Almeida, "Formation and Optimisation of Vein Networks in Physarum" (MSc thesis, IST Lisboa, 2021; arXiv 2023) | https://arxiv.org/pdf/2305.12244 |
| HSU21 | Hsu, Schaposnik Massolo & Schaposnik, "The Power of Many: A Physarum Swarm Steiner Tree Algorithm" (2021) — Gunji CELL 모델 규칙을 재서술 | https://arxiv.org/pdf/2110.08233 |

못 읽은 핵심 1차 문헌 (12절 참조): Jones 2010 Artificial Life, Jones 2011 Natural Computing ("Influences on…"), Tsuda & Jones 2011 BioSystems, Jones 2015 Springer 단행본, Baumgarten–Jones–Hauser 2015.
다만 위 arXiv 논문들은 같은 저자가 같은 모델을 매번 부록에 다시 적어 두었으므로, 규칙과 수치는 저자 본인의 서술로 확인했다.

그림은 일부만 PDF 쪽을 이미지로 렌더해 직접 봤다: MECH15 Fig. 5·6·7·8·16·17, ROAD09 Fig. 5, AMOE12 Fig. 3·4, IJUC10 Fig. 9·15, APP15 Fig. 3, SHAPE15 Fig. 5. 아래에서 **[그림]** 으로 표시한 것은 그 이미지를 보고 내가 적은 관찰이다(해상도가 낮아 정량값은 아니다). 나머지 그림은 캡션과 본문 서술로만 판단했다.

---

## 1. 기본 모델 (Jones) — 규칙 원문

출처: IJUC10 2절, AMOE12 Methods, TSP13 부록 7, SHAPE15 부록 7 **[본문]**.

- 격자: 2D 픽셀 격자. 같은 격자에 입자 위치와 "chemoattractant"(= trail) 농도를 저장.
- 입자: 한 픽셀 차지, 방향 0–360° 연속. 전방 센서 3개 FL, F, FR. 센서 각 SA, 센서 거리 SO(픽셀), 센서 폭 SW(1px), 회전각 RA, 보폭 SS(1px), 침착량 depT.
- 한 스케줄러 스텝 = 모든 입자의 감각+운동. **입자 갱신 순서는 매 스텝 무작위** ("iteration of the particle population is performed randomly to avoid any artifacts from sequential ordering").

Motor stage (IJUC10 Fig. 2 원문):
```
- Attempt move forwards in current direction
- If (moved forwards successfully)
      Deposit trail in new location
- Else
      Choose random new orientation
```
Sensory stage (IJUC10 Fig. 2 원문):
```
- Sample trail map values
- if (F > FL) && (F > FR)      -> Stay facing same direction
- Else if (F < FL) && (F < FR) -> Rotate randomly left or right by RA
- Else if (FL < FR)            -> Rotate right by RA
- Else if (FR < FL)            -> Rotate left by RA
- Else                         -> Continue facing same direction
```
(AMOE12/ENG12 판에서는 둘째 분기가 "Rotate by RA towards larger of FL and FR" 로 적혀 있다.)

핵심 세부 규칙:
- **셀당 입자 1개.** "Each lattice site may only store a single particle and—critically—particles deposit chemoattractant into the lattice only in the event of a successful forwards movement." 막히면 이동 포기 + 무작위 새 방향.
- 확산: 매 스텝 3×3 평균 필터 × (1 − damp). damp 값은 논문마다 0.1(IJUC10), 0.07(AMOE12, ENG12), 0.05(TSP13: "multiplying the mean kernel value by 0.95"), 0.01(PRPM09: "degraded at every scheduler step by 0.01"). 커널 5×5(VOR13 "typically 5×5"), 7×7(ROAD09, ADD10)도 쓰임.
- "The SO distance is measured in pixels and a minimum distance of 3 pixels is required for strong local coupling to occur. The coupling effect increases as SO increases."
- 경계 처리(비주기): 센서가 화면 밖이면 임의로 우회전시켜 모서리 고착(adhesion)을 없앤다 (IJUC10).
- 해석: 입자 위치 = 겔 구조(전체 패턴), 입자 이동 = 졸 흐름, trail = "hypothetical flux of sol". 움직인 입자만 침착하므로 trail 지도는 곧 **유량 지도**다.

IJUC10 Table 1 기본값: 200×200, %p = 5, SA 15°, SO 15px, RA 45°, SW 1px, depT 5, damp 0.1, node weight 0.01~0.1.
다른 논문에서 "표준" 망 형성 예: 200×200, %p 15(= 6000 입자), SA 22.5°, RA 45°, SO 9 (APP15 Fig. 2, MECH15 Fig. 2; ALM21이 Jones 2010 Artificial Life 그림을 옮긴 캡션도 같은 값).

---

## 2. 파라미터별 형태

### 2.1 SA 대 RA — 가장 중요한 스위치

PRPM09 **[본문]** (α = 회전각 RA, β = 센서 각 SA):
> "There is significant interplay between the sensor arm angle (β) and the rotation angle (α) parameters. When the two parameters are equal (for example, both 45 degrees), the effect on network formation is to contract the initial network that emerges. If α < β the contraction behaviour is increased. If, however, α > β then spontaneous branching will appear during the network formation. The branching occurs because the larger rotation angle places an agent's sensory apparatus outside the zone of the trail that the agent was following. The α/β parameters can be used to tune the network behaviour towards minimisation or towards high connectivity."

정리:

| 조건 | 거동 | 출처 |
|---|---|---|
| RA > SA | 자발적 분기(sprouting)·스트리밍, 위상이 계속 바뀌는 동적 망 | PRPM09, IJUC10 |
| RA = SA | 초기 망이 수축 (minimising) | PRPM09 |
| RA < SA | 수축이 더 강해짐 | PRPM09 |

구체 값 **[본문]**:
- SA 15°, RA 45°, SO 15 (IJUC10): 분기·스트리밍이 계속되어 "never settles into equilibrium". "With a sensor offset distance (SO) of 15 pixels, the threshold value for the emergence of the streaming behaviour was a SA of 15 degrees. At angles greater than this, the stable regime returned."
- SA 45°, RA 45°, SO 15 (IJUC10): 고리가 닫히며 정적 평형(주기 경계에서 벌집형)으로 간다. 분기 없음.
- SA 22.5°, RA 45°, SO 9 (MECH15 4.1): "the networks continuously form branching paths from existing edges and reconfigure their structure over time".
- SA 60°, RA 60° (MECH15): "minimising networks where the number of cycles and edges are reduced over time".
- SA 90°, RA 45° (MECH15): "networks disassembling to form discrete island patterns" — 응집된 덩어리(blob) 모드. AMOE12의 아메바 덩어리가 이 값(SA 90, RA 45, SO 15)이다.
- SA 30°, RA 45°, SO 5 (ROAD09): "the relatively narrow sensor angle stimulates branching transport networks" — 수지상 foraging에 사용.
- 전체 지도(APP15 4절): "At low SA and RA values the patterns are reticulate and adaptive, constantly changing their topology. As SA and RA increase the networks undergo minimisation, reducing the number of edges. Further increases result in labyrinthine patterns and the formation of circular minimal configurations." 지도 그림 조건: 720×720, 입자 181,440개(= 35%), SO 3, t = 400, SA·RA 각 0~180°.
- 전환은 가역적이다 (IJUC10): 안정 상태에서 SA를 15°로 낮추면 스트리밍이 다시 생기고, 45°로 되돌리면 "any sprouting branches gradually shrunk back to be absorbed within the main mass of the network".

MECH15 Fig. 5 **[그림]** (입자 6000개 = 15%, 200×200 주기 경계, 자극 없음):
- SA 22.5°/RA 45°: t = 100에서 그물눈 수십 개의 촘촘한 망. t = 1000, 2000, 5000에서도 그물눈 20개 안팎의 망이 유지된다(그물눈 지름 대략 25~40px). 경로 굵기는 전체가 거의 같다.
- SA 60°/RA 60°: t = 100 미로형 → t = 500 그물눈 10여 개 → t = 3000 5개 안팎 → t = 9000 큰 그물눈 2~3개와 굵은 경로. 조대화가 진행될수록 남은 경로가 눈에 띄게 굵어진다(입자 수가 고정이므로).
- SA 90°/RA 45°: t = 100 짧은 조각 → t = 4000 서로 떨어진 원형 점(섬) 20여 개.

APP15 Fig. 3 **[그림]** (35% 밀도, SO 3, t = 400): SA·RA가 0°나 180° 근처인 가장자리는 무늬 없는 잡음이고, 안쪽은 구멍 뚫린 시트(벌집형 빈자리)와 미로형 줄무늬가 영역을 나눠 차지한다. 이 밀도에서는 가는 선형 망이 아니라 "빈자리 무늬를 가진 시트"가 기본형이다. 경계 각도의 정확한 값은 그림에서 읽을 수 없었다.

분기 기제(IJUC10 3.1): 경로 가장자리의 경계 흐름에서 입자 충돌로 방향이 무작위화될 때, 그 방향이 흐름에 대략 90°이면(강한 trail 신호 범위 밖) 작은 입자 줄기가 빈 공간으로 "explore" 한다. 줄기는 양방향으로 밀려갔다 돌아오고, 틈을 거의 건너면 반대편 경로에서도 가지가 나와 연결된다. 연결되면 고리가 생기고 그 고리는 다시 닫힌다.

**주의 — MCPM과의 겉보기 불일치.** MCPM은 "the sensing angle should be larger than the mutation (i.e. turning) angle. We typically use twice the value" 라고 쓴다. MCPM은 분기를 결정론적 오버슈트가 아니라 확률적 분기(Pmut)로 얻으므로 서로 모순은 아니다(8.1절).

### 2.2 SO (스케일 파라미터)

- MECH15 4.2: "Larger sensor offset distance (SO, in pixels) results in thicker network paths, faster network evolution, and coarse-grained networks ... Decreasing the SO parameter results in more fine-grained graphs with more edges and cycles". 예: 노드 100개 위에서 5000 스텝 후 SO 15는 여러 노드 사이를 지나는 매우 성긴 망, SO 10은 굵고 고리 적음, SO 5는 데이터 점을 지나는 촘촘한 망.
- SHAPE15: "The SO parameter acts as a scaling parameter, small values result in fine-grained networks whereas larger values result in coarse-grained networks." 큰 SO는 큰 덩어리 안에 "vacancy islands"를 만든다. 큰 덩어리가 필요하면 **각 입자가 매 스텝 SO를 범위(표의 1–19)에서 무작위로 뽑아** 이를 없앤다.
- IJUC10: 아주 작은 SO는 "only local networks". 안정 벌집의 변 길이는 SO 15에서 117px와 43px(비 2.72:1, 각 120°). 즉 안정 망의 그물눈은 SO의 약 3~8배 **[본문 수치, 배수 환산은 추론]**.
- 임계 각(MECH15 5.6): 가운데 노드를 낀 두 경로의 각이 임계값보다 작아지면 두 흐름이 합쳐져 노드에서 지퍼처럼 떨어지고 Steiner 점이 생긴다. 임계 각은 SO와 영양 농도에 의존한다(SO가 클수록 빨리 합쳐짐, 농도가 높을수록 노드에 붙어 있음). 값은 본문에 수치로 주어지지 않았다.

### 2.3 %p (입자 밀도) 와 점유 규칙

- 망 영역: %p 2%(자극 있는 경우, ALM21이 옮긴 Jones 2010 캡션 **[2차]**), 5%(IJUC10), 15%(APP15 Fig. 2). 필라멘트 방법의 최종 망은 "~3-5% of image area" (IJUC10 4.3).
- 시트 영역: "A very large population size (>40% of the image area) is required for the plasmodial shrinkage method ... This network takes the form of a large sheet with holes. The holes close up" (IJUC10 4.3).
- 진동 실험: 90% 점유 (ENG12).
- 고정 인구에서 비주기 경계로 두면 망은 원으로 수축하고, 그때 입자 분포는 "an almost solid mass of agents" 이다. trail에는 고리만 보이는데 "only those agents that are free to move (those at the periphery) will deposit trail" 이기 때문이다 (IJUC10 Fig. 6).
- 경로의 "벽"은 여러 겹의 입자로 되어 있고, 안쪽 층은 막혀서 침착하지 못하고 바깥 층만 흐른다 (IJUC10 Fig. 8). 즉 **경로 굵기는 그 단면의 입자 수로 정해지고, 유량은 경계층이 담당한다.**
- MCPM은 점유 제한을 아예 없앴다: "We therefore allow agents to move freely without enforcing any limit on their number in each grid cell." (대신 확률적 분기로 과응집을 막는다.)

---

## 3. 망이 유지되는 조건 / 한 줄(또는 덩어리)로 수축하는 조건

IJUC10 **[본문]**:

1. **확산이 있어야 수축이 일어난다.** "If no diffusion of trail occurs, networks of trails will still form but no network minimisation or reconfiguration occurs."
2. **고리가 닫히는 이유.** 고리 안쪽 입자는 바깥쪽보다 짧은 거리를 돈다 → 안쪽 유량·침착이 더 많다 → 입자가 안쪽으로 끌린다 → 고리가 더 작아진다(양성 되먹임). 바깥쪽은 스포크 경로들로 끊겨 있다는 점도 더해진다.
3. **고정점이 없으면 반드시 무너진다.** 비주기 경계 + 자극 없음 → 고리 닫힘 → 한 고리 → 원형 덩어리(Fig. 6). 노드 자극을 제거하면 "the tree collapses as the minimal surface is found" (Fig. 13).
4. **고정점(노드)이 있으면** 망은 노드에 "snagged" 되어 Steiner 최소 트리 근사로 수축한다. 노드가 2개면 최단 직선 하나다(ALM21이 옮긴 Jones 2010 캡션 **[2차]**: "In the case of two stimuli sources, the optimisation process converges to the shortest path connecting them").
5. **노드 인력의 세기 창(window).** "If the attraction of agents to the node sources is too strong then the loop structures will not be minimised. If the attraction to the node points is too weak the network will 'tear' and lose contact with one or more nodes."
6. **고리가 남는 경우.** (i) SA < RA foraging 모드: "The pattern of the network at the 'core' remains relatively stable and the outer connections are continuously remodelled" (노드가 많을 때, 1000 스텝 간격 스냅샷). (ii) 확산 감쇠가 너무 강함: "Too strong diffusion damping also generates foraging dynamic network". (iii) 노드가 많고 초기 망이 불균일할 때 생기는 비최소 고리. (iv) 영양 농도가 높을 때: 낮은 농도에서는 Steiner/MST, 높은 농도에서는 RNG·Gabriel 그래프(VOR13 5.5, MECH15 5.9 — 고농도 배경에서 최종 망에 고리 여러 개, 저농도에서는 "more tree-like with only a small inner cycle"). (v) von Neumann 법칙: 고리를 둘러싼 노드 수가 수축을 막는 지점에서 최소화가 멈춘다(MECH15 5.6).
7. **안정 평형의 전제.** "The stability of the network (with a 45 degree sensor angle) is ensured by the fact that the number of agent particles remains constant."
8. 수축 일반: "smaller cells in minimising networks tend to shrink, whilst larger cells tend to grow" (VOR13). 비누막과 같은 T1/T2 과정, Plateau 각, von Neumann 법칙을 따른다(MECH15, APP15).

MCPM의 관찰 **[본문]**: Jones 방식(최대값 추종, "Max-PM")은 "overly condensed pathways and only moderately connected networks" 를 만들고, "optimizing the network by erasing smaller filaments, rounding off loops" 한다. 우주 거대구조 맞춤에서 Max-PM은 데이터 점의 32%를 놓쳤고 MCPM은 0.072%를 놓쳤다.

---

## 4. 영양원 노드의 고정 효과 — projection 수치

노드는 매 스텝 trail 격자에 값을 투사(projection)하는 고정 확산원이다. trail과 같은 채널을 쓴다("Both data projection stimuli and agent particle trails were represented by the same chemo-attractant").

| 논문 | 투사 | 덮였을 때 억제 | 침착 depT | 확산 |
|---|---|---|---|---|
| IJUC10 | node weight 0.01~0.1, 매 스텝 trail map에 복사 | 없음 (소비하지 않음) | 5 | 3×3, damp 0.1 |
| PRPM09 | 가중 파라미터로 조절 | "damping the food stimulus projection to 1% of the food value if the site is occupied by an agent" | 5 | 3×3, 0.01 감쇠 |
| ROAD09 | weight 0.01(영양 풍부·foraging) / 0.5(고농도) | "multiplying it by 0.001 if there is a particle within a 3 × 3 neighbourhood" | — | 7×7, damp 0.1 / 0.01 |
| ADD10 | 20 × 255 | "multiplying it by 10^-3 if there was a particle within a 9×9 neighbourhood" | — | 7×7, damp 10^-4 |
| TSP13 | 3×3 창에 스텝당 1.275 | 3×3 안에 입자가 있으면 0.01275 (1/100) | 5 | 3×3, ×0.95 |
| SHAPE15 | proj_a = 12.75 / 127 / 2.55 / 5 (실험별) | — | 5 (일부 15, 0.01) | Dw 3 또는 5, Dd 0.05~0.1 |

- 단위 메모 **[추론]**: 투사값들이 weight × 255(픽셀 밝기)로 보인다. 0.005 × 255 = 1.275(TSP13), 0.01 × 255 = 2.55, 0.05 × 255 = 12.75, 0.5 × 255 = 127.5(SHAPE15의 2.55 / 12.75 / 127), ADD10은 "20 multiplied by the chemoattractant pixel value (255)"라고 명시한다. 그렇다면 ROAD09·IJUC10의 weight 0.01~0.1은 스텝당 2.55~25.5 단위이고 침착 5와 같은 자릿수다. MECH15의 "background nutrient concentration 0.01 / 0.001"이 같은 환산을 따르는지는 본문에 없다.
- SHAPE15: 침착값은 투사값보다 작게 둔다("This value is less than the attractant projection value proj_a, causing the particles to be attracted to projection sites"). 단 표의 일부 열(proj 2.55, Dept 5)은 이 문장과 맞지 않으므로 절대적 규칙으로 보면 안 된다.
- 억제의 역할(TSP13): "Suppression of projection from covered sites was necessary to ensure a uniform concentration within the blob at internal data points. Uncovering of the data points by the shrinking blob acted to increase concentration at exposed nodes, causing the blob to be anchored by the nodes." 즉 **덩어리 안에 묻힌 노드는 고정점 구실을 하지 않고, 가장자리에 드러난 노드만 고정한다.**
- 억제의 또 다른 역할(MECH15 5.4, 5.7, 5.8): 덮인 먹이의 기울기가 사라져야 다음 먹이의 기울기가 보인다. 농도가 다른 먹이가 여럿이면 강한 쪽으로 먼저 위족을 뻗고, 그 기울기가 삼켜져 억제된 뒤에야 다음으로 간다.
- 회피(빛·기피물질): 해당 영역에서 **센서가 읽는 값에 가중치를 곱한다**(Ld 0~1, 기본 0.2; 기피물질 Rd 0~−1, 기본 −0.2; SHAPE15 표에서는 Ld 0.9, 창 Lw 3). 경계에서 입자가 노출되지 않은 쪽으로 끌리고, 그 이동이 빈자리와 침착을 만들어 더 끌어당긴다(AMOE12 Fig. 6).

---

## 5. 입자 수 적응 (growth / shrink) — 정확한 규칙

일반형 (SHAPE15 부록 7.5 원문 **[본문]**):
> "Growth of the population was implemented as follows: If there were between Gmin and Gmax particles in a local neighbourhood (window size given by Gw) of a particle, and the particle had moved forward successfully, a new particle was created if there was a space available at a randomly selected empty location in the immediate 3 × 3 neighbourhood surrounding the particle."
> "Shrinkage of the population was implemented as follows: If there were between Smin and Smax particles in a local neighbourhood (window size given by Sw) of a particle the particle survived, otherwise it was deleted. Deletion of a particle left a vacant space at this location which was filled by nearby particles (due to the emergent cohesion effects), thus causing the blob to shrink slightly."

검사 주기 Gf, Sf 가 인구의 turnover rate를 정한다. 성장·수축 판정은 입자마다 따로 계산해 Boolean 태그로 남긴다(ROAD09).

| 논문 | 분열 조건 (이동 성공 필수) | 생존 조건 | 주기 | 결과물 |
|---|---|---|---|---|
| PRPM09 | 3×3 창 점유 θmin > 0, θmax < 4 (전진면에서 새 입자 생성) | — | — | foraging 망 |
| ROAD09 | 9×9에 1~10개 | 5×5에 0~24개 | 2 스텝 | 망 |
| ADD10 | 9×9에 1~10개 | 5×5에 0~20개 | 3 스텝 | 망 |
| VOR13 | 9×9에 1~10개 | 5×5에 0~24개 | 3 스텝 ("high turnover rate ... to ensure a resilient network structure") | 망 |
| TSP13 | 9×9에 1~10개 | 9×9에 0~80개 | 분열 5 스텝, 제거 10 스텝 | 수축하는 시트(덩어리) |
| SHAPE15 Fig. 5 | Gw 9, 0~15개 | Sw 5, 0~24개 | Gf 3, Sf 3 | 망 (foraging, 초기 입자 10개) |
| SHAPE15 Fig. 10 | Gw 9, 0~20개 | Sw 9, 0~80개 | Gf 3, Sf 50 | 수축하는 덩어리 |
| SHAPE15 Fig. 12 | Gw 9, 0~30개 | Sw 9, 0~80개 | Gf 5, Sf 50 | 합쳐지며 속이 차는 덩어리 |
| SHAPE15 Fig. 13–15 | Gw 9, 0~20개 | Sw 9, 0~80개 | Gf 3, Sf 10 | MST에서 부풀어 concave hull |
| SHAPE15 Fig. 16 | Gw 9, Gmax 5~30 | Sw 9, 0~80개 | Gf 3, Sf 10 | Gmax로 오목↔볼록 조절 |

읽는 법 **[추론 포함]**:
- 9×9 = 81칸. 분열 상한 10/81 = 12%, 15/81 = 19%, 20/81 = 25%, 25/81 = 31%, 30/81 = 37%.
- 분열 상한이 **10~15/81 (12~19%)** 인 실험은 전부 망이고, **20/81 (25%) 이상**인 실험은 전부 속이 찬 덩어리다. 2.3절의 %p 영역(망 ≤ 약 15%, 시트 > 40%)과 맞는다. 이 대응은 표에서 내가 읽어낸 것이고 Jones가 그렇게 서술한 것은 아니다. 또 덩어리 실험들은 감각 파라미터도 덩어리 쪽(SA 60°/RA 60°, 또는 SA 90°/RA 45° + SO 1–19 무작위)이라 Gmax의 효과와 SA/RA의 효과가 섞여 있다. Gmax만 바꾼 비교는 SHAPE15 Fig. 16(덩어리 안에서 오목↔볼록)뿐이다.
- SHAPE15 3.8 **[본문]**: "As Gmax increased, the concavity reduced until at Gmax = 25 the final blob was fully convex ... At higher Gmax values the growth was not constrained by the stimuli from the point sources, causing uncontrolled growth patterns". Gmax = 30에서 무제한 성장(3000 스텝에서 중단).
- 생존 조건 "5×5에 0~24개"는 창이 완전히 찼을 때만 죽는다는 뜻이다(자기 자신을 세는지는 본문에 없다). 망이 수축해 경로가 합쳐지면 경로 안이 과밀해져 초과분이 죽는 구조로 보인다 **[추론]**.
- TSP13: 수축만 필요한데도 분열 검사를 두는 이유 — "to ensure that the adaptation of the blob sheet is uniform across the sheet to prevent 'tears' or holes forming within the blob sheet".
- 무작위 제거 방식(IJUC10 plasmodial shrinkage): 시트가 균일해진 뒤 스텝당 확률 0.001로 입자를 제거한다("a greater frequency of removal presents the risk of re-occurrence of holes in the sheet"). 제거된 입자는 노드 픽셀에서만 다시 생성될 수 있다.
- SHAPE15 Fig. 5 e–h **[그림]** (입자 10개에서 시작, SA 22.5°/RA 45°/SO 5, Gw 9·Gmax 15, Sw 5·Smax 24, Gf = Sf = 3, proj_a 12.75, Dept 5, Dw 5, Dd 0.1, 빛 마스크 없음): t = 500에 구석에서 가지 친 가는 망이 뻗기 시작하고 t = 1500에는 arena 전체가 가는 선의 그물로 덮인다. 자극점이 없는 곳까지 퍼진다("unconstrained growth outside the pattern of attractants"). 이 조합이 "스스로 퍼지며 유지되는 가는 그물"의 구체 레시피다. 전진은 가지가 삐죽 나가는 식이고 시트형 전진면은 아니다.
- 시간 규모 **[그림에서 읽은 대략값]**: ROAD09 Fig. 5a에서 그물은 t ≈ 400까지 촘촘하고, t ≈ 800~1900에 성기어지며, t ≈ 10000에 최소 트리가 된다(SO 5, SA = RA = 45°, 검사 주기 2).
- 필라멘트 foraging(IJUC10 4.2): 입자를 노드 위치에서만 점차 투입한다. 노드에 갇히는 것을 피하려고 SA를 잠시 15°로 낮췄다가 45°로 되돌린다. 초기에 Delaunay 삼각망이 나타났다가 Steiner 트리로 수축한다.

---

## 6. 전진면 — 시트형 / 부채꼴 / 수지상을 가르는 것

Jones 모델에서 전진면은 5절의 성장 규칙에서 나온다: 자극 기울기가 가장자리 입자를 끌어 이동을 성공시키고, 이동에 성공한 성긴 곳의 입자가 분열한다.

MECH15 5.1 **[본문]**: "The movement of the population stimulates division at the periphery of the collective and a pseudopod-like process emerges and moves towards the source of food. The width of the pseudopodium active region is dependent on the size of the chemoattractant gradient. When the food source is reached the engulfment by the particles suppresses the diffusion from the node and the connection is stabilised and minimised."

MECH15 5.9 **[본문]** — 배경 기질 농도 실험(같은 귀리 배치, 배경 농도만 다름; 배경 영양은 닿으면 즉시 소비됨):

| 배경 농도 | 성장 형태 | 최대 인구 | 탐색 완료 | 최종 망 |
|---|---|---|---|---|
| 0.01 | "wave-like and expansive" 방사형 전진면 | 21,258 (470 스텝) | 470 스텝 | RNG 비슷, 고리 여러 개 |
| 0.001 | "dendritic growth patterns", 느림 | 13,574 | 3440 스텝 | 트리형, 작은 안쪽 고리 하나 |

- 두 조건 모두 탐색이 끝나고 배경 영양이 고갈되면 "spontaneously undergo network contraction and minimisation" 하며, 인구는 15,000 스텝 안에 수렴한다.
- 기제: "In the high concentration condition, the background presents a stronger stimulus to the periphery of the model plasmodium and the 'pull' of the environment causes expansive movement outwards and provides space for growth. As nutrients are depleted by the outwardly moving population, the background stimulus moves further outward from the edge of the collective". 저농도에서는 배경 기울기가 trail 유량 수준과 비슷해 끌림이 약하고, 국소 소비로 농도 차가 생길 때만 바깥으로 자란다.
- 누적 생성 입자 수: 고농도 870만, 저농도 940만. 수지상 탐색은 가까운 먹이를 자주 "놓친다".
- ROAD09 Fig. 5도 같은 3조건: (a) 영양 풍부 기질 → 방사형 전진면 후 망 적응, (b) 빈 기질 + 고농도·고확산 먹이 → 전진면이 먹이를 차례로 찾고 최소화, (c) SA 30° foraging → 계속 재구성되는 분기망.
- 실제 점균에 대한 서술(VOR13 3절): "Depending on the strength of the gradient the extension is via pseudopodium-like processes (weak stimuli) or via a fan-like growth front (stronger stimuli). A special case exists if the plasmodium is surrounded by very high concentration stimuli. In this case the growth will be outward in all directions, generating a radial pattern". APP15: "a weak stimulus from only one direction would induce a conical foraging pseudopodium shape, whereas multiple strong stimuli would present a radial growth pattern".
- ENV15: "low-concentration stimuli results in pseudopod-like growth fronts and dendritic networks, whereas high-concentration stimuli generates florid radial growth".

그림에서 본 것 **[그림]**:
- **ROAD09 Fig. 5a (영양 풍부 기질, SA 45°/RA 45°/SO 5, 5개 입자에서 시작).** t = 111: 접종 덩어리에서 **부채꼴로 퍼진 호(arc) 모양 전진대**가 보이고, 호와 접종점 사이를 가는 방사형 살(spoke)들이 잇는다. 전진대는 입자가 성긴 점선 띠다(조밀한 시트가 아니다). t = 186~377: 전진대가 지도 전체로 나아가고 그 뒤에 다각형 그물이 남는다. t = 836~9992: 그물눈이 줄어 먹이를 잇는 성긴 트리로 수축한다. 경로 굵기는 거의 균일하고, 굵은 것은 먹이 위의 덩어리뿐이다. 부채꼴인 이유 중 하나는 접종점이 서식 가능 영역의 구석에 있었기 때문이다.
- **MECH15 Fig. 16 (배경 0.01, 가운데 접종).** 닫힌 원형 테두리선이 바깥으로 퍼지고 그 안쪽이 다각형 그물로 채워진다. 전진면은 원형이다(부채꼴 아님). 이후 그물이 수축해 고리 몇 개를 가진 망이 남는다.
- **MECH15 Fig. 17 (배경 0.001).** 테두리가 들쭉날쭉하고 가지가 삐죽삐죽 뻗는 수지상 전진. 안쪽에는 역시 그물이 남는다.
- **MECH15 Fig. 7 (먹이 한두 개를 향한 위족).** 접종점에서 먹이 쪽으로 가는 줄기가 나가고, 끝이 먹이 쪽으로 넓어지는 원뿔형 입자 구름이 된다. 먹이에 닿으면 구름이 Y자 관으로 응축된다. 먹이를 지우면 그 가지가 후퇴하고 두 점을 잇는 직선 하나가 남는다.

정리하면 Jones의 성장 모델은 "얇은 전진대 + 뒤따르는 균일 굵기의 그물 + 시간에 따른 조대화"까지는 그림으로 보여 준다. 다음 두 가지는 보이지 않는다.
- **조밀한 시트형 전진면.** 전진대는 성긴 점선 띠다.
- **굵기 위계.** 경로 굵기는 SO와 단면 입자 수로 정해지고 한 화면 안에서는 거의 같다. 굵기 위계에 대한 서술도 Jones 모델 쪽에서 찾지 못했다. 고정 인구에서 조대화가 진행되면 남은 경로가 전체적으로 굵어질 뿐이다(MECH15 Fig. 5 e–h).

---

## 7. 진동과 아메바 운동 (oscillatory motor rule)

출처: AMOE12, ENG12, PRPM09, GUIDE15 **[본문]**. Tsuda & Jones 2011 원문은 못 읽음.

규칙 (AMOE12 원문):
> "Instead of randomly selecting a new direction if a move forward is blocked, the particle increments separate internal co-ordinates until the nearest cell directly in front of the particle is free. When a cell becomes free, the particle occupies this new cell and deposits chemoattractant into the lattice."
> "The strength of the inertial effect can be damped by a parameter (pID) which determines the probability of a particle resetting its internal position coordinates, lower values providing stronger inertial movement."

PRPM09의 같은 규칙 서술: 부동소수점 위치와 이산 위치를 따로 유지한다. 앞 칸이 막혀도 부동소수점 위치는 계속 전진하고("slide past"), 실제 점유는 칸이 빌 때만 일어난다. 확률 0.05로 "change direction" 사건이 일어나면 부동소수점 위치를 이산 위치로 되돌리고 방향을 무작위로 바꾼다.

결과:
- 비진동 조건에서 먼저 규칙적 "vacancy domain"이 생기고, 진동 규칙을 켜면 무너지면서 유동(밝음)/막힘(어두움) 영역이 생겨 경쟁·동조한다. 막힘 = 겔, 갑작스런 풀림 = 졸.
- 덩어리: 9380 입자, SA 90°, RA 45°, SO 15, damp 0.07. 비진동이면 균일한 원형으로 응집하고 외부 자극으로 변형돼도 자극이 사라지면 원형으로 돌아간다. pID 0.05에서 진동이 퍼지고, **pID 0.01에서 진동이 경계를 크게 일그러뜨려 덩어리 전체가 이동**한다. SO가 작거나 다른 SA/RA 조합에서는 덩어리가 조각날 수 있다.
- **부피 보존에 해당하는 서술**: "Because the population maintains its cohesion, any distortion of the boundary on one side must result in a shift in population distribution from the opposite side (since the collective is non-compressible and occupies a fixed area)."
- **작은 조각의 돔형 전진** (AMOE12 Fig. 4): 900 입자, SA 90°, RA 45°, SO 9, pID 0.001. 경계 변형이 "approximately semicircular domed shape"이 되고 낮은 pID의 관성 때문에 그 모양이 유지되며 매끄럽게 전진한다. 입자는 돔 앞쪽으로 갔다가 옆으로 빠지고 뒤처진 뒤 가운데로 다시 들어온다. pID가 높으면 방향을 자주 바꾼다. **입자 수를 늘리면 한쪽 돔을 유지하지 못하고 맥동·혼돈 운동이 된다.**
- AMOE12 Fig. 4b **[그림]**: 이동하는 작은 조각의 입자 분포는 앞쪽이 빽빽한 반달(돔)이고 뒤쪽은 흩어진 성긴 입자 꼬리다. Fig. 3c **[그림]**: 큰 덩어리(pID 0.01)에서는 유량이 진행 방향 가장자리의 초승달 띠에 몰리고 덩어리 윤곽이 약간 D자로 일그러진다. 부채꼴이라고 부를 만큼 펼쳐지지는 않는다.
- 유인: 지속 자극을 두면 가장자리 입자가 먼저 끌리고 위족처럼 뻗으며, 자극 방향으로 진행파가 생겨 덩어리가 옮겨간다. 소비되면 다시 원형.
- 진행파와 입자 표류(ENG12, 관 모양 arena, 90% 점유): 진행파는 입자 표류와 **반대 방향**으로 간다(빈칸이 뒤로 이동, 교통 체증과 같음). 파는 약 400 스텝에 arena를 건너고 입자는 약 8000 스텝이 걸린다(20:1). 입자 방향 정렬 비는 약 53:47.
- 원형 우물에서 SO를 키우면 회전 → 좌우 왕복(bilateral) → 고리(annular) 패턴으로 바뀐다(ENG12; Tsuda & Jones 2011 요약).

한계: 진동은 "셀당 1개 + 높은 점유율(90%) + 순차 무작위 갱신"에 의존한다. 성장 규칙과 진동 규칙을 합친 결과는 ROAD09 시점에 "We aim to integrate growth behaviours with oscillatory behaviours" 로 미완이었고, 이후 합쳤는지는 확인하지 못했다.

---

## 8. 다른 저자의 입자 모델 확장

### 8.1 Monte Carlo Physarum Machine (Elek et al. 2022) **[본문]**
- Jones 규칙(최대 침착 방향 추종 = "Max-PM")을 확률화. 센서 표본은 전방 1개 + "mutation" 방향 1개. 분기 확률:
  `Pmut(d0, d1, s) = d1^s / (d0^s + d1^s)` — d0 전방 침착, d1 변이 방향 침착, s ≥ 0 sampling exponent. s → ∞ 이면 Max-PM.
- 방향 Pdir: 전방 원뿔 안 균등. 거리 Pdist: Maxwell–Boltzmann 등. "in the simplest case of constant sensing and movement distances, the model will be sensitive to only one characteristic feature size"; 여러 스케일이 필요하면 분포의 볼록 결합을 쓸 수 있다고 한다.
- 경험칙: sensing angle ≈ 2 × move angle; sensing distance ≈ 10 × move distance.
- 값 예: (SA 60°, MA 30°, SD 3.0, MD 0.05, deposit 10, persistence 0.95, s 5; 영역 100 단위) / (SA 20°, MA 10°, SD 50 vox, MD 0.65 vox, s 5; 720³) / 천문 맞춤에서는 s = 2.2~4.
- s를 키우면 "sharper and more concentrated filamentary structures"가 되고 연결성과 데이터 포괄이 떨어진다.
- 점유 제한 없음. 침착(확산됨)과 별도로 확산하지 않는 trace 장을 두어 구조를 읽는다.
- GPU: 10M 에이전트, 1024³ 격자에서 반복당 150~200ms (DirectX compute).
- 한계: 몸·성장·굵기 위계는 다루지 않는다.

### 8.2 Reginato, Proverbio & Giordano 2024 **[본문]**
- 세 모델: NM(망 형성만), EM(탐색 σ1 + 망 형성 σ2), LCM(출생·사망 추가). 먹이는 비확산.
- 환경 80×80 칸(칸 0.1875mm), 센서 팔 lA = 2, θA = 45°, 속도 vA = 0.7, trail 침착 QT = 1(σ2에서만), 증발 μT = 0.7, 칸당 상한 Tmax = 3. trail은 확산하지 않는다. 먹이 유인 F = Fmax / (1 + r²), Fmax = 15, rF = 7.
- σ1(탐색): **농도가 낮은 쪽으로** 회전(같으면 직진 + ±π/8 잡음). 굶주림 카운터가 TS = 100 + N(0,10)에 닿으면 σ2로 전환.
- σ2(망 형성): 농도 높은 쪽으로 회전, 침착.
- LCM: 굶주림 카운터가 TD = 250을 넘으면 사망. 이웃 수 NA > TN(= 18, 반경 lA 원이 가득 찬 경우)이면 사망. 먹이 위에 있고 이웃 수 NA < TB(< 8)이면 복제.
- 재현: 먹이 2개 사이 연결(단일·이중 가닥). 굵기 위계, 전진면 형태는 다루지 않는다.

### 8.3 de Almeida 2021 (성장 + 유량 적응, 그래프 모델; 입자 모델 아님) **[본문]**
우리 실패 (a), (d)와 직접 관련되어 포함한다.
- 부피 보존형 적응식 (3.19): `d√D_ij/dτ = (V/β) · g_ij / Σ_(k,m) L_km g_km − √D_ij`, g = |Q|^γ. γ = 2/3이면 정상 상태가 소산 최소.
- 성장 모델(5장): Delaunay 메시의 변을 점차 활성화. **먹이 = source, 경계(전진면) 노드 = sink.** 경계 노드는 받은 유량을 저장했다가 비활성 변의 생성 비용을 치르고 새 관(D0 = 0.1)을 만든다. I0 = 0.1, Δτ = 0.02.
- 결과: γ = 2/3 → 트리형 망, "as the network grows the inner channels are highly optimised, leading to the formation of distinct fan-shaped growth fronts with a more dense branching as we move away from the source". 단 주맥 사이 고리는 불안정해 사라진다. γ < 1/2 → 고리 많고 "there isn't a clear hierarchy of veins".
- **격자 대칭 문제**: 정사각·삼각·육각 격자에서는 노드 위치에 잡음을 줘도 전진면이 원형이 되지 않고 격자 대칭이 드러났다. Delaunay 불규칙 메시에서만 등방적이었다.
- 저자 스스로의 결론: 이 단순한 성장-최적화 모델은 실제 망 위상을 완전히 재현하지 못한다(고리 유지 실패).

### 8.4 Gunji et al. 2008 CELL 모델 (HSU21의 재서술 **[2차]**)
- 칸 상태 0(바깥/버블), 1(세포질), 2(세포골격 = 경계).
- 반복: (1) 상태 2 칸 하나를 자극점으로 고른다. (2) 그 상태 0 이웃과 교환 → 버블이 세포 안으로 들어온다. (3) 방문 표시를 지운다. (4–7) 버블이 방문하지 않은 세포 칸과 무작위로 자리를 바꾸며 이동(최대 n회, 버블 이웃 중 0이 s개면 정지). (8) 상태 1/2 재지정.
- HSU21의 값: n = 1000, s = 3. 자극점을 무작위로 고르면 아메바 운동, 특정 활성 구역에서만 고르면 구역 사이 망이 생긴다.
- 질량이 정확히 보존되고 "앞이 나가면 뒤가 빠지는" 구조지만, 버블 하나씩 순차 처리라 GPU 병렬화에 맞지 않는다.

### 8.5 초록·스니펫만 본 것
- Ma, Johansson, Tero, Nakagaki, Sumpter 2013, "Current-reinforced random walks for constructing transport networks", J. R. Soc. Interface 10:20120864 **[초록]**: 입자(랜덤 워커)의 흐름이 변을 강화한다. 밀도 기반 강화는 자기강화 고리에 빠지지만 전류(순유량) 기반 강화는 최단 경로로 수렴한다고 한다. 망 형성에는 비선형 전류 강화가 필요하다고 한다. 식은 확인하지 못했다.
- Liu et al. 2017, "A new multi-agent system to simulate the foraging behaviors of Physarum", Natural Computing 16(1):15–29 **[초록]**: 탐색용·수렴용 두 종류 에이전트와 전이 규칙 3개. 규칙 원문은 못 읽음.
- Schenz, Shima, Kuroda, Nakagaki, Ueda 2017, J. Phys. D 50:434001 **[초록]**: 전진면 반응-확산 + 정맥 강화를 합친 연속 모델. 원문 못 읽음.
- Baumgarten, Jones, Hauser 2015, Acta Phys. Pol. B 46:1201 **[초록]**: Jones 모델의 망 조대화(정맥 밀도, 분기점 수, 평균 구간 길이)를 실제 점균과 비교. 수치 못 읽음.
- Sage Jenson "36 Points" **[2차 스니펫]**: 입자 파라미터(센서 거리·각, 회전각, 보폭 등)를 입자 위치에서 읽은 trail 값의 함수로 바꾼다고 한다. 식은 확인하지 못했다.

---

## 9. 우리 실패에 대한 대조

프로토타입(`specs/plasmodium-core/prototype/hybrid.py`) 값: SO 5, **SA 0.6 rad = 34.4°, RA 0.6 rad = 34.4°**, 보폭 1, 점유 제한 없음(cap 1e9), 입자 수 고정, trail 3×3 평균 × 0.9.

README 명령과 코드로 계산한 입자 밀도(몸 면적 대비; 몸이 h → 1로 퍼졌다고 가정한 값은 추정이고, 실제 면적은 실행 로그가 없어 확인하지 못했다):

| 실행 | 초기 몸 지름 / SO | 입자 / 초기 몸 칸 | 퍼진 뒤 추정 |
|---|---|---|---|
| 기본 160² (7000) | 7.0 | 719% | 288% |
| h2 160² (5000) | 7.0 | 514% | 206% |
| L1 288² (25000) | 23.0 | 240% | 109% |
| M3 200², cap 2 (4000) | 12.8 | 124% | 96% |

### (b) 갇힌 입자가 굵은 직선 관 하나로 뭉침
**문헌에 같은 결과가 있다.** MECH15 Fig. 8 **[그림]**: 양 끝에 영양원 2개가 있는 복도에서 **고정 인구**는 촘촘한 그물 → 성긴 그물 → **굵은 띠 하나**로 끝난다. 같은 조건에서 **적응형 인구**(성장·수축 규칙)는 그물 → 고리 몇 개 → 가는 선 하나로 끝난다. 즉 "고정 인구 + 고정점 2개 이하 → 굵은 관 하나"는 Jones 모델의 정상 종착점이고, 프로토타입의 결과는 구현 오류가 아니라 이 영역에 있었던 것으로 보인다.

그 영역에 있게 만든 원인 후보 다섯 가지. 어느 것이 지배적인지는 실험으로 갈라야 한다.
1. **RA = SA 였다.** PRPM09: 둘이 같으면 초기 망을 수축시키고, RA > SA 여야 자발적 분기가 생긴다. Jones의 분기망 값은 SA 15/RA 45(SO 15), SA 22.5/RA 45(SO 9), SA 30/RA 45(SO 5).
2. **고정점이 사실상 0~2개였다.** 고정점 없는 Jones 망은 원형 덩어리로, 고정점 2개면 직선 하나로 수축하는 것이 모델의 정상 거동이다(3절). h2 실행은 pfood = 0이었고, L1은 먹이 6개 중 1~2개만 닿았다.
3. **밀도가 망 영역 밖이었다.** Jones의 망은 %p 2~15%, 40% 이상은 시트다. 프로토타입은 몸 칸당 1~7개(100~700%)였고 점유 제한이 없어 전부 한 능선에 겹칠 수 있었다.
4. **스케일.** 안정 망의 그물눈이 SO의 수 배(SO 15에서 변 43~117px)이므로 지름이 SO의 7~23배인 몸에는 그물눈이 한두 개밖에 못 들어간다.
5. **새 망의 공급원이 없었다.** Jones의 성장 모델에서 가는 망은 전진면의 분열로 계속 만들어지고 뒤에서 수축·조대화된다. 입자 수가 고정된 갇힌 집단은 조대화만 한다 **[추론]**.

### (c) 셀당 1개 제한을 넣자 입자가 흩어짐
- Jones 모델은 원래 셀당 1개 + 성공 이동 시에만 침착이고, 그 조건에서 망이 생긴다. 다만 %p 15% 안팎에서다.
- M3 실행은 몸 면적 대비 약 96~124%에 cap 2였다. Jones의 서술로는 이 밀도는 "almost solid mass" 영역이고, 막힌 입자는 침착하지 않고 방향을 무작위로 바꾼다. 즉 점유 제한 자체가 아니라 **밀도가 원인일 가능성이 크다.** 확인하려면 cap 1, 입자 수를 몸 면적의 5~15%로 낮춰 다시 돌려야 한다. 아직 확인되지 않은 가설이다.
- GPU 병렬 갱신에서는 Jones의 "무작위 순서 순차 갱신"을 그대로 쓸 수 없다. 현재 `src/config.ts` 주석("논문의 one particle per cell이 격자 원인")은 이 차이에서 나온 문제로 보인다. MCPM은 점유 제한을 없애고 확률적 분기로 대체했다.

### (a) Tero식 적응을 연속 격자에 올리면 얼룩만 생김
- Jones 계열 문헌은 이 문제를 직접 다루지 않는다.
- ALM21: 관이 위계를 갖고 자란 조건은 (i) 먹이 = source, 전진면 = sink 인 지속적 관통 유량, (ii) γ = 2/3, (iii) 부피 정규화(전역 항), (iv) **불규칙 메시**였다. 규칙 격자에서는 격자 대칭이 드러났다고 명시한다. 우리 연속체는 국소 탄성 압력에 의한 왕복 유량만 있고 source→sink 관통 유량이 없었다.
- Ma et al. 2013 **[초록]**: 밀도가 아니라 순유량(전류) 강화여야 한다.
- 위 두 가지는 다른 문헌 조사 담당(Tero/연속 모델)이 본문으로 확인할 필요가 있다.

### (d) 몸이 원반, 부채꼴 전진면 없음
- Jones의 고정 인구 덩어리(SA 90/RA 45)도 표면장력처럼 최소 형태(원)로 돌아간다. 원반은 응집 모델의 기본 평형이다.
- 방향성 있는 전진 모양이 나온 조건은 두 가지뿐이다: (i) 작은 조각(900 입자) + 강한 관성(pID 0.001)의 돔형 이동 — 크기를 키우면 깨진다. (ii) 성장 규칙 + 소비되는 자극 기울기 — 기울기가 강하고 넓으면 방사/부채꼴, 약하면 위족·수지상. "The width of the pseudopodium active region is dependent on the size of the chemoattractant gradient."
- 그림으로 확인한 부채꼴은 ROAD09 Fig. 5a 하나다(영양 풍부 배경을 닿는 즉시 소비 + 성장 규칙 + 구석에서 접종). 가운데에서 접종한 MECH15 Fig. 16은 원형 전진면이었다.
- 즉 문헌상 부채꼴은 **한쪽으로만 열린 공간 또는 한쪽에서 오는 강한 기울기 + 닿으면 소비·억제되는 자극 + 전진면에서의 생성**의 조합이다. 등방 환경에서 스스로 부채꼴이 되는 규칙은 Jones 계열에서 찾지 못했다.
- 우리 모델에서 "한쪽으로만 열린 공간"에 해당할 수 있는 것은 점액 흔적 s다(지나온 쪽은 기피되어 닫힌다) **[추론]**. 이것이 부채꼴을 만드는지는 시험된 적이 없다.

---

## 10. 실험 제안 (우선순위 순)

0. **먼저 순수 Jones 성장 모델을 그대로 재현한다(몸 h 없이).** ROAD09 Fig. 5a 조건: 셀당 1개, SA 45°/RA 45°/SO 5, 침착은 성공 이동 시에만, 7×7 평균 × 0.9, 먹이 투사 weight 0.01(덮이면 × 0.001), 닿으면 즉시 소비되는 배경 영양(ROAD09에는 배경 값이 수치로 없다. MECH15의 0.01과 0.001을 시작값으로 쓰되 침착 5 대비 단위가 불확실하므로 4절의 단위 메모를 참고해 몇 자릿수를 훑는다), 9×9에 1~10개 + 이동 성공 → 분열, 5×5에 25개 → 제거, 주기 2 스텝, 입자 5개에서 시작. "호 모양 전진대 + 뒤따르는 그물 + 조대화"가 나오는지 확인하고, 그다음 SHAPE15 Fig. 5 조건(SA 22.5°/RA 45°, Gmax 15)으로 바꿔 그물이 유지되는지 본다. 이것이 재현되지 않으면 아래 실험의 해석이 흔들린다.
1. **RA > SA 스윕.** 다른 것은 그대로 두고 (SA, RA) = (22.5°, 45°), (30°, 45°), (15°, 45°)와 현재값 (34.4°, 34.4°), 그리고 (45°, 45°), (60°, 60°)를 비교한다. 측정: 일정 스텝 뒤 D의 골격 분기점 수와 고리 수.
2. **밀도 스윕.** 입자 수를 몸 면적(칸)의 3%, 5%, 10%, 15%, 40%, 100%로 바꾼다. cap = 1(엄격), cap = ∞ 둘 다. (c)가 밀도 탓인지 가른다.
3. **스케일.** SO를 3, 5, 9로 하고 몸 지름을 SO의 30배 이상으로 잡는다(예: 512² 격자, 몸 반경 150, SO 5). SO 3이 Jones가 말하는 하한이다.
4. **고정점.** 몸 안에 지속 투사원 3~6개(매 스텝 3×3에 depT의 0.25~25배, 덮이면 1/100로 억제하는 경우와 억제하지 않는 경우)를 두고 망이 Steiner형으로 걸리는지 본다. 인력 세기 창(너무 강하면 고리 유지, 너무 약하면 찢어짐)을 찾는다.
5. **전진면에서 입자 생성 + 과밀 제거.** 새로 젖은 칸(h가 h_min을 막 넘은 곳) 근처에서, 이동에 성공했고 9×9 이웃이 1~10개인 입자가 분열. 5×5 이웃이 20~24개를 넘으면 제거. 주기 2~5 스텝. 망이 앞에서 가늘고 뒤에서 성기게 되는지(조대화 구배) 본다.
6. **소비되는 배경 자극으로 전진면 끌기.** 점액이 없는 새 기질을 약한 유인 장으로 두고(MECH15의 0.01 대 0.001에 해당하는 두 수준), 몸이 덮으면 소비한다. 방사 파동형 ↔ 수지상 전환이 나오는지, 한쪽 먹이 기울기를 더하면 부채꼴이 되는지 본다.
7. **확률적 분기(MCPM).** 점유 제한 없이 `P = d1^s / (d0^s + d1^s)`, s = 2, 3, 5, ∞. sensing angle = 2 × move angle, sensing distance = 10 × move distance. (b)의 과응집이 줄어드는지 본다.
8. **SO 혼합.** 입자마다 SO를 다르게(예: 3/9/15 세 집단, 또는 매 스텝 범위에서 무작위) 주어 굵기가 다른 경로가 공존하는지 본다. 문헌 근거는 "SO가 경로 굵기·그물눈을 정한다"와 MCPM의 다중 스케일 언급뿐이고, 위계가 실제로 생긴다는 보고는 찾지 못했다.
9. **진동 운동 규칙.** cap 1, 점유율 90%, pID 0.05 / 0.01 / 0.001로 진행파가 생기는지, 900 입자급 작은 조각에서 돔형 전진이 재현되는지 본다. h 장의 위상 진동자와 어느 쪽이 싼지 비교용.
10. **연속 Tero 재시도 조건**(다른 담당과 조율): 먹이 = source, 전진면 = sink로 관통 유량을 만들고, γ = 2/3, 격자에 고정 무작위 이방성(칸별 전도도 잡음)을 넣어 격자 대칭을 깬다.

---

## 11. WebGL2 구현 메모 **[추론]**

- 9×9, 5×5 이웃 수: 점유 텍스처에 분리형 박스 필터 2패스.
- 셀당 1개 점유: 입자를 점으로 그려 "이 칸의 승자 ID"를 남기는 패스 + 각 입자가 자기가 승자인지 확인하는 패스. 동률은 해시로 깬다. 순차 무작위 갱신과 같지 않으므로 격자 아티팩트 여부를 따로 확인해야 한다.
- 분열·제거: 상태 텍스처 크기가 고정이므로 alive 플래그를 쓴다. 분열은 "죽은 슬롯 i가 해시로 고른 살아 있는 입자 j가 이번 프레임 분열 조건을 만족하면 그 옆에 태어난다"는 pull 방식으로 리드백 없이 가능하다. 출생률이 죽은 슬롯 수에 비례하게 되므로 Jones의 규칙과 정확히 같지는 않다.
- 진동 운동 규칙: 입자 상태에 부동소수점 위치와 이산 위치를 함께 저장해야 한다(RGBA32F 한 장으로는 방향까지 넣기 빠듯함).
- 덮인 먹이 억제: 먹이 투사 패스에서 점유 박스 필터 값이 0보다 크면 투사량에 0.01~0.001을 곱한다.

---

## 12. 접근하지 못한 것

- Jones 2010, "Characteristics of pattern formation and evolution in approximations of Physarum transport networks", Artificial Life 16(2):127–153 — MIT Press, UWE 저장소 모두 차단. SA/RA/%p 전체 지도와 기본 파라미터 표를 1차로 확인하지 못했다.
- Jones 2011, "Influences on the formation and evolution of Physarum polycephalum inspired emergent transport networks", Natural Computing 10(4):1345–1369 — Springer, UWE, Utrecht 사본 모두 차단. 적응형 인구(성장·수축)의 원 서술과 노드 각·SO·농도 실험이 여기 있다. 같은 규칙은 ROAD09/ADD10/VOR13/TSP13/SHAPE15 부록으로 확인했다.
- Tsuda & Jones 2011, "The emergence of synchronization behavior in Physarum polycephalum and its particle approximation", BioSystems 103(3):331–341 — 초록 스니펫만.
- Jones 2015, "From Pattern Formation to Material Computation" (Springer) — 목차 일부만.
- Baumgarten, Jones & Hauser 2015, Acta Phys. Pol. B 46:1201 — 차단.
- Ma et al. 2013 (PMC), Liu et al. 2017, Wu et al. 2015, Schenz et al. 2017, Gunji et al. 2008 원문 — 차단 또는 미시도.
- Sage Jenson "physarum" 페이지(cargocollective.com), Bleuje/interactive-physarum 셰이더 — 차단.
- 대부분의 그림과 모든 보충 영상. 0절에 적은 그림만 이미지로 봤고, 나머지는 캡션과 본문 서술로만 판단했다. Jones의 보충 영상(uncomp.uwe.ac.uk)은 열어 보지 않았다. 전진면과 조대화의 시간 경과는 영상으로 확인하는 편이 정확하다.
