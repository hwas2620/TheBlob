# 문헌 조사 노트 — morphology-growth-biology (원형질체 형태·성장 모델과 사실성 판정용 정량 자료)

작성일 2026-11-12. 대상 독자: 이 노트를 읽고 numpy/WebGL 실험을 설계·채점할 담당자.
자매 노트: `jones-extensions.md`(Jones 입자 모델 계열), `vein-formation-models.md`(Tero·Hu–Cai·Marbach·Schenz 등 정맥 형성 모델). 겹치는 내용은 그쪽을 가리키고 여기서는 반복하지 않는다.

## 0. 접근 상태와 표기 규칙 (먼저 읽을 것)

- 이 세션에서 실제로 열린 학술 호스트는 **arxiv.org 하나**였다. `da.lib.kobe-u.ac.jp`(Gunji 2008 저자본), `eprints.lib.hokudai.ac.jp`(Kuroda 2015 저자본)는 curl(프록시 403)과 WebFetch(DNS 거부) 모두 실패했다. `scholar.archive.org`는 허용 목록에 있으나 계속 "Rate limit reached"만 돌려줬다. PMC, 학술지 사이트, bioRxiv, ResearchGate, GitHub의 제3자 저장소는 모두 막혀 있다.
- 따라서 **과제의 핵심 1차 문헌 대부분(Takamatsu 2009, Gunji 2008/2011, Niizato 2010, Kuroda 2015, Akita 2017, Baumgarten 2010/2013/2014, Dirnberger 2017, Westendorf 2016/2018, Fricker 2017, Reid 2012, Schenz 2017, Vogel 2017, Patino-Ramirez 2019/2021)은 본문을 읽지 못했다.** 이들은 (i) 같은 저자·같은 그룹의 arXiv 논문 본문에 인용된 서술, (ii) 검색 엔진이 돌려준 초록·발췌로만 확인했다.
- 표기
  - **[본문]** arXiv PDF를 내려받아 pdftotext로 직접 읽었다.
  - **[2차·본문]** 내가 본문을 읽은 다른 논문(주로 총설)이 해당 1차 문헌을 인용하며 적은 내용. 수치는 그 총설의 표기 그대로다.
  - **[발췌]** 검색 결과가 돌려준 초록/스니펫만 봤다. 수치·식의 세부는 확인 못 했다.
  - **[기억]** 기억에만 의존. 신뢰도 낮음. 구현 근거로 쓰지 말 것.
  - **[추론]** 문헌에 그대로 쓰여 있지 않고 내가 끌어낸 해석·환산.
- 내려받은 PDF와 텍스트: `/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research/dl_morph/` (이 조사에서 받은 것), 자매 담당이 받은 것은 `.../scratchpad/dl/arxiv/`, `.../scratchpad/research/dl_cc/`.
- PDF 추출 과정에서 일부 식의 분수·첨자가 깨졌다. 그런 식은 "재구성"이라고 표시했다. 구현 전에 PDF 쪽을 직접 볼 것.

---

## 1. 한 장 요약

### 1.1 사실성 판정에 쓸 수치 (출처는 2절)

| 항목 | 값 | 등급 |
|---|---|---|
| 수축 주기 | 약 100 s. 고리 가둠 실험에서 f = (1.04 ± 0.18)×10⁻² Hz, 크기 무관. 총설 표기 "1–2분", "120 s" | [본문] |
| 느린 변조 | 15–20분(총설이 Kuroda 2015 인용), 고리 실험에서 약 10³ s | [2차·본문], [본문] |
| 연동파 파장 | **개체 크기와 같다**(2 mm–2 cm 범위). 고리 실험에서는 파장 ≈ 고리 지름(기울기 약 1) | [2차·본문], [본문] |
| 관 내 왕복 유속 | 50 µm/s – 1 mm/s, 최대 약 1 mm/s | [2차·본문] |
| 전진 속도(망 크기 2.5–90 mm²) | 약 0.05 mm/min = 3 mm/h. lightning 상태는 crescent의 약 2배 | [본문] |
| 전진 속도(총설 일반값) | "2–3 cm/hour"에 도달 | [2차·본문] |
| 전진 속도(면적 0.2–2 mm² 소형) | run 24.5 µm/min, tumble 12.9 µm/min (plain agar) | [본문] |
| 속도–두께 | v ∝ h_max^0.94, ℓ ∝ V^0.66, h_max ∝ V^0.42 (V = 단위 길이당 부피). 앞이 가장 두껍고 뒤로 지수적으로 얇아짐 | [2차·본문], [발췌] |
| 크기 문턱 | < 100 µm 정지, 100–200 µm에서 극성 생김, 300–800 µm 올챙이형, 약 0.5–1 mm 이상에서 망 구조와 **전진면 여러 개** | [2차·본문] |
| 전진면 손가락 분열 | 임계 곡률 κ = 2.5 mm⁻¹(곡률 반경 0.4 mm)에서 분열. 전진과 정체가 주기적으로 교대 | [2차·본문], [발췌] |
| 등방 → 손가락(digitated) 전환 | 반지름이 처음의 약 2배가 될 때 | [발췌] |
| 정맥 반경 | 평균 50 µm, 폭 분포 로그정규. 조대화가 진행되면 분포 폭이 줄어듦 | [2차·본문] |
| 정맥 구간 길이·그물눈 면적 | 지수분포 | [발췌] |
| 접합점 차수 | 3 (정규 평면 그래프). 차수 4와 끝점(차수 1)이 소수 | [2차·본문], [발췌] |
| Murray 지수 | 2.53–3.29 (좁은 출구로 빠져나가는 배출 망에서 측정). 이론값 3 | [발췌] |
| 균질 시트에서 망이 나타나는 시간 | 지수 성장 시간 T_E = (1.95 ± 0.86)×10⁴ s (가둔, 이주하지 않는 개체) | [본문] |
| 망 재배향 시간 | T_α = (0.93 ± 0.32)×10⁴ s | [본문] |
| 세 가지 망 상태 | stationary / crescent / lightning. 점유율 먹이 없음 10:70:15 %, 먹이 있음 20:50:30 % | [본문] |
| 솔리디티 A/A_c | stationary ≈ 1, lightning에서 0.2까지 | [본문] |
| run / tumble 평균 지속 | 48.2분 / 17.9분 (plain), 103.2분 / 20.6분 (영양 기질) | [본문] |
| 점액 흔적 기피 거리 | 과거 궤적에서 몸 폭 중앙값의 2배 이내로 접근하지 않는 규칙으로 MSD 재현. w̄ = 954 µm(plain) | [본문] |
| 점액 기억 지속 | 큰 개체(1 cm²)는 최대 6일(Reid 계열 인용). 0.65 mm² 미만 소형은 약 3시간 뒤부터 자기 흔적을 넘음 | [2차·본문], [본문] |
| 장시간 MSD 지수 | β ≈ 1.5 (2차원 자기회피 보행), 4분 척도에서는 ≈ 2 | [본문] |

찾지 못한 것: **전진면(시트) 폭 대 정맥 간격의 측정값, 정맥 분기각의 측정값, 단위 면적당 고리 수의 측정값.** 접근 가능한 자료에는 숫자가 없었다. 2.4절에 이론적 대용 기준만 적었다.

### 1.2 우리 실패에 대한 이 조사 범위의 결론

- **(d) 원반·부채꼴 없음.** 실제 점균에서도 잘 먹인 초기 1–5시간은 등방 원반(stationary)이다. 부채꼴(crescent)은 이주가 시작된 뒤의 상태다. 접근 가능한 문헌에서 부채 위치를 정하는 것으로 확인된 요인은 (i) 몸 전체를 한 파장으로 가로지르는 연동파의 방향, (ii) 국소 수축 정지·이완, (iii) 질량이 모자라 둘레 전체를 유지하지 못하는 상황(반지름 약 2배에서 손가락형으로 전환)이다. 프로토타입을 계측해 보니(4.5절) 위상 패턴은 **가장자리가 앞서는 동심원**(파가 안쪽으로 진행)이고 질량중심은 1 px도 움직이지 않았다. 288² 실행에서는 중심–가장자리 위상 감김 수가 9.5주기 동안 0.34 → 2.25로 계속 늘어 위상 고정이 되지 않았다. 실제 점균의 "긴 축을 따라 한 바퀴"인 선형 위상 구배와 대칭성이 다르다. 전진면의 손가락 분열을 역학적으로 설명한 모델은 "아직 제안되지 않았다"고 2023년 총설이 적고 있다.
- **(b) 관 하나로 뭉침.** 실제 점균의 lightning 상태가 바로 "굵은 관 몇 개로 된 트리"다(솔리디티 0.2). 굵기 위계는 한 시점의 평형 구조가 아니라 **나이 구배**다. 전진면 바로 뒤에서 가는 관이 계속 새로 생기고, 뒤로 갈수록 조대화가 진행된다. 조대화 시간은 수축 주기의 약 100배다. 프로토타입에는 전진면에서 관을 새로 만드는 과정이 없고 관의 적응이 주기보다 빠르다(`continuum.py`: 1/rD = 50 시간단위, 주기 62.8–125.7 시간단위. `hybrid.py`: trail 감쇠 0.9/스텝 → 약 10 스텝, 주기 628 스텝).
- **(a) 연속장 Tero가 얼룩.** 실제 정맥은 "시트 안에 채널이 생긴 뒤 **사이 시트가 물러나서**" 생긴다. 즉 관 사이의 몸은 사라진다. 프로토타입은 h ≈ h*인 연속 시트를 끝까지 유지한다. 이 차이가 (a)의 원인인지는 문헌으로 확인되지 않았다. 시험할 가설이다.
- **(c) 점유 제한.** 이 조사 범위에서 추가할 내용 없음.

---

## 2. 생물학적 정량 자료

### 2.1 크기와 형태 단계

- 출처: Le Verge-Serandour & Alim, "Physarum polycephalum: Smart network adaptation", arXiv:2306.09063 (Annu. Rev. Condens. Matter Phys. 투고본) [본문]. 아래 인용의 괄호 번호는 그 총설의 참고문헌 번호이고, 대응 문헌을 함께 적었다.
  - "Below 100 µm, a microplasmodium is immobile (115)... Around 100-200µm in size, radial symmetry breaks, and a front-rear axis is formed, with the rear distinguished by a local increase in the stiffness of the cytoskeleton." (115 = Rodiek, Takagi, Ueda, Hauser 2015 Eur. Biophys. J. 44:349)
  - "Above a certain size, about 1 mm, several migration front appear (115)... These fronts evoke viscous fingering and emerge spontaneously below a critical curvature κ = 2.5 mm−1, however, a model has yet to be proposed to describe this phenomenon at the mechanical level (131). The fronts are initially large protoplasmic sheets with no apparent structure, but as the front advances, veins emerge and start to form a network (102). The veins in the direction of the shuttle stream are strengthened while others disappear." (131 = Baumgarten, Jones, Hauser 2015 Acta Phys. Pol. B 46:1201; 102 = Oettmeier & Döbereiner 2019 PLoS ONE)
  - 주의: "critical curvature"라는 표현은 Baumgarten & Hauser 2014 EPL 108:50010 초록에도 있다 [발췌: "finger splitting happens once fingers reach a critical curvature"]. 2.5 mm⁻¹이라는 값이 어느 논문의 것인지는 원문으로 확인하지 못했다.
- Alim, "Fluid flows shaping organism morphology", arXiv:1801.02464 [본문]: "Plasmodia of 100 µm to 500 µm length adopt an amoeboid shape migrating rapidly... Plasmodia that exceed ∼ 500 µm form a full network structure often including multiple migration fronts. Over the peristaltic cycle a front location advances and retracts asymmetrically leading to net advancement at long time scales [Baumgarten & Hauser 2014]."
- Zhang, Guy, Lasheras, del Álamo, arXiv:1703.09691 [본문]: 지름 약 100 µm 이상 조각이 지속 이동, "Fragments larger than ∼ 500 µm formed complex branched structures markedly different from" 올챙이형.
- Schick, Kramar, Alim, arXiv:2408.17134 [본문]: 2.5–90 mm² 망을 썼고 "smaller plasmodia do not form a hierarchical network structure".

### 2.2 맥동

- 주기: Busson, Saiseau, Durand, "Emergence of dynamic contractile patterns in slime mold confined in a ring geometry", arXiv:2207.13812 [본문]: f = (1.04 ± 0.18)×10⁻² Hz, 고리 둘레 6.0–13.5 cm 범위에서 크기와 무관. 파장은 고리 지름에 선형(기울기 약 1), 폭 2.1–11.4 mm는 영향 없음. 조직된 모드에 있는 시간은 전체의 67 %이고 나머지는 무질서 구간이다.
- 파장 = 개체 크기: 1801.02464 [본문] "the wavelength of the peristaltic wave matches organism size spanning two orders of magnitude [Alim 2013 PNAS]"; 2306.09063 [본문] "Contractions are typically coordinated in a peristaltic pattern aligned along the longest axis of the organism or alternating between equally long directions". Alim 2013 초록 [발췌]: "Transport is maximized within the network when the wavelength of the peristaltic wave is of the order of the size of the network", 왕복 주기 약 100 s.
- 고조파: 2306.09063 [본문] 수축 시계열은 기본 주파수 + 고조파로 분해되고, 기본 주파수는 15–20분 주기로 느리게 변조된다(Kuroda 2015 인용). Saiseau, Busson, Durand, arXiv:2501.02651 [본문]: 느린 변조의 교대 패턴 주기는 약 10³ s.
- 진폭: Schick 2024 [본문]는 유량 계산에 "peristaltic wave of 20% contraction amplitude along the network's longest axis"를 썼고, 실측 관 동역학과 맞는다고 했다. 1703.09691 [본문]: 소형 조각의 두께는 이동 중 최대 50 %까지 변한다.
- 수송 거리: 1801.02464 [본문] 입자는 반 주기 안에 망 반대편까지 운반되었다가 되돌아온다. 순수 확산이면 한 주기에 0.25 mm.
- 연동파의 방향과 이동: 2306.09063 [본문] 올챙이형에서 "centripetal contractions start at the rear... and travel to the front". 1801.02464 [본문] "Reorientation of migration direction for example toward a food source is associated with a redirection of the peristaltic wave direction to that site". Bäuerle, Kramar, Alim, arXiv:1710.08784 [본문]: 절단 후 "network reinstates a peristaltic wave toward peripheral fan regions".
- 화학 자극과 주파수: 2306.09063 [본문] "frequency increases with attractants, relaxing the tensile forces near the attractant... Conversely, the frequency decreases with repellents".

### 2.3 전진면

- 구조: 2306.09063 [본문] 전진면(fan)은 "protrusions of a thin protoplasmic sheet, which inflates and deflates with the contractions of the upstream network and as the cytoplasmic flow is pushed into them... Some fans are retracted as Physarum migrates on surface, while others persist and eventually form channels to become tubes". Schick 2024 [본문]: "Migration fronts... only play a passive role in the overall flow and contractility".
- 세 구역: Baumgarten 계열 서술 [발췌] "apical zone, which consists of a poroelastic medium, an intermediate domain, and a vast network of tubular strands or veins". 각 구역의 폭 수치는 찾지 못했다.
- 두께 분포: Kuroda 2015 초록 [발췌] "the organism is thickest close to the front, and decreases exponentially in thickness" 뒤쪽으로. 평균 속도는 전면부 최대 두께 평균에 비례.
- 전진–정체 교대: Baumgarten & Hauser 2014 초록 [발췌] 전진면은 손가락 모양 굴곡을 만들고, 전진 구간과 정체 구간이 주기적으로 교대한다. 두 구간의 분산 관계는 성장률 부호만 다르고 대칭이다. 수치(속도, 주기)는 확인 못 했다.
- 부채 위치와 연동파: Schick 외, "Decision-making in light-trapped slime molds involves active mechanical processes", arXiv:2506.12803 [본문]: 청색광 다각형 덫 안에서 "We find protrusions to align with the direction of peristaltic contraction waves driving mass relocation." 탈출 전 약 1.5시간 동안 부채가 여러 방향으로 나왔다 물러나기를 반복하고, 수축 모드가 수송에 가장 효율적인 모드로 정착할 때 가장 긴 축 방향으로 탈출한다.
- 상처 반응: 1710.08784 [본문] 관을 완전히 자르면 21건 중 21건에서 다시 융합하고 절단부에 부채가 자란다. 수축 정지(최소 3분) → 부채 성장 → 약 60–90분에 원래 형태로 복귀. 저자들의 해석은 "severing surprisingly acts like an attractive stimulus"다.
- 핵: 2306.09063 [본문] 흐름에 실린 핵이 새 전진면에 "seed" 된다. 구현과 직접 관련은 없다.

### 2.4 정맥망 통계

- 2306.09063 [본문], 5.1절: "Physarum's characteristic meshwork of tubes forms in the rear of an advancing migration front. At first, channels emerge in the large protoplasmic sheets of the migration front, and as the front advances, tubes become clearly defined and the thin protoplasmic layer in between tubes thins away - a finely interlaced network forms... the network is best described as a regular, planar graph of node degree three (Baumgarten, Ueda, Hauser 2010). Some nodes of degree four and dangling ends of degree one may be present (Fessel 2012)... Network tube radii have an average of 50 µm (Fricker 2017) and follow a log-normal distribution (Baumgarten 2010). As the network coarsens over time the width of the distribution shrinks (Fricker 2017; Marbach 2016)."
- Baumgarten, Ueda, Hauser 2010 PRE 82:046113 초록 [발췌]: 차수 3 노드만 있는 정규 그래프. 구간 길이와 면적은 지수분포, 폭은 로그정규. 함수형은 망이 조대화하는 동안 유지되고 지수만 시간에 따라 변한다. 적합 파라미터 값은 확인 못 했다.
- Akita 외 2017 J. Phys. D 50:024001 초록 [발췌]: 좁은 출구로 생체량을 빼내는 배출 망에서 Murray 지수 2.53–3.29. 출구 쪽으로 갈수록 굵어지고 반복 분기하는 **트리**다. current-reinforcement 모델의 스케일 지수를 3으로 두면 실험 망과 맞는다. (모델 쪽 세부는 `vein-formation-models.md` 3절.)
- Fricker 외 2017 J. Phys. D 50:254005 [발췌]: "veins form from retraction of the intervening plasmodial sheets"라 망이 뚜렷해지기 전에는 분할이 어렵다. 두께는 투과광 + Lambert–Beer로 추정. 수치는 확인 못 했다.
- Dirnberger & Mehlhorn 2017, Westendorf 2016/2018, Baumgarten & Hauser 2013: 서지와 초록 수준만 확인. 평균 차수가 3에 가깝다는 서술 외에 수치를 얻지 못했다.
- 망 형성 시간: Saiseau 외, "Network emergence and reorganization in confined slime moulds", arXiv:2209.11305 [본문]. 고리 방에 가둔, 망이 없는 균질 시트 11개에서 정맥 신호(coherency 가중 구조텐서 에너지)가 exp(t/T_E)로 자라고 T_E는 1.0–4.0×10⁴ s, 평균 (1.95 ± 0.86)×10⁴ s. 3×10⁴ s 뒤 평균 2.53배. 이미 등방 망이 있던 7개에서는 정맥이 고리 방향으로 재정렬되고 T_α = (0.93 ± 0.32)×10⁴ s. 저자 결론: 수축파 방향이 먼저 정해지고 망이 시간 적분된 흐름을 따라간다. 시간 척도는 수축 주기의 약 100배. 귀리 한천이 있으면 망 없는 균질 시트가 되는 경향이 뚜렷하다. 형성 속도는 영양 유무와 상관이 없었다.
  - 한계 [추론]: 이 값은 이주하지 않는 개체의 것이다. 관통 유량이 큰 이주 전진면 뒤에서는 더 빠를 수 있으나 그 수치는 찾지 못했다.
- 이론적 대용 기준 [추론]
  - 연결된 3-정규 평면 그래프에서 고리 수 = E − V + 1 = V/2 + 1. 즉 완전히 그물형이면 **고리 수 ≈ 분기점 수의 절반**, 트리면 0. `eval_morph.py`의 `loops / branch_points`를 그대로 쓸 수 있다.
  - Murray 지수 3에서 대칭 분기의 최적 사잇각은 약 75° [기억: Murray 1926의 고전 결과], 길이 최소(Steiner) 접합은 120°. 실제 점균의 분기각 측정값은 찾지 못했다.

### 2.5 세 가지 망 상태 — Schick, Kramar, Alim 2024 (PRX Life 2:033005) [본문]

접근 URL: https://arxiv.org/pdf/2408.17134

- 실험: 16개체, 2.5–90 mm², 1.5 % 무영양 한천, 5–10분 간격으로 46–60시간. 절반에는 열처리 대장균 먹이 패치. 접종 후 1–5시간은 이주 없이 등방 성장하고 그 뒤 이주를 시작한다. 망은 분~시간 척도로 계속 재편된다.
- 상태
  - **stationary**: 등방 성장, 이동 없음, 그물형. 솔리디티 ≈ 1, R_gr/√A 작음.
  - **crescent**: 느린 이주, 그물형 + 넓게 펼쳐진 전진면.
  - **lightning**: 빠른 이주(crescent의 약 2배), 굵은 관 몇 개로 된 트리, 솔리디티 0.2까지.
- 분류 지표: R_gr/√A (픽셀 강도 가중 회전반경을 망 면적의 제곱근으로 나눔), A/A_c (볼록껍질 대비), v_front. 질량중심 속도는 가지치기만으로도 움직여서 쓰지 않았다. 지표는 크기와 환경에 거의 무관하다.
- 탐색 전략: 전진면에 투입하는 생체량 비율(%/분)은 stationary가 한 자릿수 작고, crescent와 lightning은 같다. 전진면 각폭은 lightning이 crescent의 절반이다(그림 축 눈금은 0.5–2 rad. 정확한 평균값은 본문 텍스트에 없다). lightning은 몸의 주축 방향으로만, crescent와 stationary는 사방으로 탐색한다.
- 비용 (재구성. PDF 추출이 깨짐):
  - `C_trans = ⟨ Σ_k Q_k(t)² / C_k ⟩_t / Σ_k V_k`, `C_k = π a_{0,k}⁴ / (8 µ l_k)`, `Q_k = π a_{0,k}² ū_k`, µ = 0.275 Pa·s
  - `C_build = E_el = ⟨ Σ_k [Y h_k π a_{0,k} / (1 − ν²)] · [(a_k(t) − a_{0,k})² / a_{0,k}²] · l_k ⟩_t`, ν = 1/2, h_k = 0.1 a_{0,k}, Y = 10 kPa
  - 건설 비용: stationary ≈ 2 × crescent ≈ 4 × lightning. 수송 비용은 그 반대 순서로 2배씩.
- 상태 점유율: 먹이를 만난 개체 20 : 50 : 30 %, 못 만난 개체 10 : 70 : 15 % (stationary : crescent : lightning). 전이는 눈에 보이는 환경 자극 없이도 자주 일어난다.
- 시사점: 채점 목표를 "분기망이 항상 유지될 것"으로 두면 실제 점균보다 엄격하다. 실제 개체도 시간의 15–30 %는 굵은 관 몇 개짜리 트리다. 목표는 **세 상태를 오가는 것**, 그리고 crescent일 때 전진면 뒤에 그물이 있는 것이다.

### 2.6 기질(영양·기피물질)과 형태

- Takamatsu 2009의 실험 결과(3.1절 참조): 1 mM KCl 한천 → 수지상(트리형), 귀리 한천 → 원반(격자형 그물). Kagawa & Takamatsu, arXiv:0904.1456의 Fig. 1 설명과 서론 [본문]. Yoneoka & Takamatsu 2023 서론 [발췌]: 기피물질·기아 → 수지상/트리, 영양 풍부 → 그물 + 얇은 시트형 전진면.
- Patino-Ramirez 외 2019, 2021 (Sci. Rep.) [발췌]: 중성 기질 → 가는 정맥의 성긴 망(빈 공간 많음, 총 길이 김). 영양 기질 → 굵은 정맥의 조밀하고 짧은 중심형 망(빈 영역은 적고 큼). 기피 기질 → 굵은 정맥의 촘촘하고 작은 망, 확장 속도와 연결 수를 최소화, 이미 지나간(점액이 깔린) 영역을 오히려 선호. 200 mM 포도당에서는 탐색 시작이 늦어진다.
- 2306.09063 [본문]의 정리: "a compact morphology and slowed exploratory dynamics in high concentrations of nutrients (high nutrition) or salts (minimization of contact), in contrast to a trade-off between rapid migration, main branches, and optimal assimilation in nutrient-poor environments".
- Vogel 외 2017 J. Phys. D 50:014002 [발췌]: 개체는 등방 성장으로 시작해 "switched to a digitated growth in a limited number of directions when they approximately doubled their radius". 초기 거리, 크기, 먹이 유무와 질이 최종 망 연결성에 영향.
- Halvorsrud & Wagner 1998 PRE 57:941 초록 [발췌]: 영양을 한천 방울에 가둔 비균일 기질. 방울이 작으면 분기 성장, 크면 조밀 성장. 공간 상관 함수로 두 영역을 구분.
- Lee, Oettmeier, Döbereiner 2018 J. Phys. D 51:244002 초록 [발췌]: 영양이 부족할 때만 나타나는 비망상 성장. 시트형 운동체 'satellite'(mesoplasmodium)가 떨어져 나와 일정한 모양과 일정한 방향으로 이동하고, 확산 신호의 문턱 모델로 정지 거리를 설명. Oettmeier & Döbereiner 2019 초록 [발췌]: mesoplasmodium은 최대 2 mm², 모양이 일정. 피질이 국소적으로 물러지면 그쪽으로 유입이 늘어 순이동이 생긴다. 내부 채널계가 저역 통과 필터로 작용해 전진면이 등방으로 확장된다(학위논문 요약).
- Rosina & Grube 2025 J. R. Soc. Interface [발췌]: 점액(ECM) 점도가 높으면(MgCl₂로 조절) 망 확장이 뚜렷이 느려지지만 최종 망 복잡도(프랙탈 차원)는 같은 값으로 수렴한다. 모델 식은 확인 못 했다.

### 2.7 이주와 점액 기피

- Tröger, Goirand, Alim, "Size-dependent self-avoidance enables superdiffusive migration in macroscopic unicellulars", arXiv:2409.12825 (PNAS 2024) [본문]. 접근 URL: https://arxiv.org/pdf/2409.12825
  - 실험: 면적 0.2–2 mm² 개체, 1.5 % 한천, 24.4 °C, 4분 간격, 최대 134시간. 궤적 14개(plain) + 9개(영양: 배양액 10 %).
  - 규칙(자료에서 뽑은 모델): run과 tumble을 교대. 지속 시간은 두 멱법칙의 결합. 속도는 상태별 상수. run 중 방향 변화는 평균 φ_R의 지수분포, tumble 중에는 [−π, π] 균등. **과거 궤적에서 평균 몸 폭 w̄의 2배 이내로는 발을 딛지 않는다**(부록 C). 본문에는 "does not come closer to its past trajectory than the median width"라고도 적혀 있어 계수 표기가 한 곳에서 다르다.
  - 파라미터 표(원문 Table II): 열은 α_{R,T} / χ_{R,T} / b_{R,T}[분] / v_{R,T}[µm/분] / φ_R[rad] / w̄[µm]
    - PA(plain): 1.1, 0.2 / 2.8, 5.3 / 98, 28 / 24.5, 12.9 / 0.24 / 954
    - NA(영양): 1.1, 0.8 / 2.2, 4.1 / 132, 36 / 24.9, 16.7 / 0.25 / 1811
    - SP(소형): 1.2, 0.03 / 2.9, 3.6 / 96, 20 / 21.6, 11.8 / 0.25 / 674
    - LP(대형): 1.0, 0.2 / 3.1, 4.6 / 124, 28 / 27.9, 14.3 / 0.23 / 1340
  - 결과: MSD 지수 β는 4분 척도에서 약 2, 10시간쯤에서 약 1.5로 수렴. 자기회피를 빼면 장시간에 확산으로 떨어진다. 영양 기질에서는 평균 run이 48.2분 → 103.2분으로 늘고 tumble은 17.9 → 20.6분으로 거의 같다. 큰 개체는 작은 개체보다 폭이 2배, 29 % 빠르고, run 시간이 31 % 길다.
  - 소형(0.65 mm² 미만)은 자기 흔적을 넘는다(7개 중 4개가 약 90시간 동안 1–7회). 넘는 것은 흔적을 남긴 지 3시간 이후다. 큰 개체는 작은 개체와 큰 개체의 흔적을 모두 피하고, 작은 개체는 어느 쪽도 피하지 않는다.
  - 흔적을 감지하는 거리가 0보다 큰 경우가 많다. 저자들은 기피 성분이 한천 속으로 확산하기 때문으로 추정한다.
  - 28분보다 긴 run 중 흔적을 만나 멈춘 것은 2.4 %뿐이다.
- Reid, Latty, Dussutour, Beekman 2012 PNAS 109:17490: 초록 수준 [발췌] — 지나간 곳을 피함으로써 공간 기억을 만들고 U자 덫을 빠져나온다. 표면을 미리 점액으로 덮으면 이 기억을 쓰지 못한다. 수치 [기억, 신뢰도 낮음]: Y자 선택에서 40회 중 39회가 점액 없는 쪽을 선택, U자 덫에서 120시간 안에 목표 도달이 빈 한천 96 % 대 점액 도포 33 %. **이 수치는 원문으로 확인하지 못했다.** 2306.09063 [본문]은 "allowing it to dodge - if possible - regions already traversed"로 적는다. 즉 절대 장벽이 아니라 선택이다.
- 점액의 성질: 2306.09063 [본문] 점액은 exocytosis로 분비되는 뮤코다당층으로 원형질체 부피의 큰 부분을 차지한다. 이주한 자리에 흔적으로 남는다.

### 2.8 게임 스케일로의 환산 [추론]

실제 치수의 무차원 비만 옮긴다. (평균 정맥 지름 d_v = 0.1 mm, 주기 T = 100 s 기준)

| 비 | 실제 | 게임에서 d_v = 3 px, T = 주기일 때 |
|---|---|---|
| 몸 지름 / d_v (1–3 cm 개체) | 100–300 | 300–900 px |
| 주기당 전진 거리 / d_v (1 cm/h) | 약 2.8 | 약 8 px / 주기 |
| 주기당 전진 거리 / d_v (0.05 mm/min) | 약 0.8 | 약 2.5 px / 주기 |
| 연동파 파장 / 몸 지름 | 약 1 | 몸 전체에 위상 한 바퀴 |
| 손가락 분열 지름(2/κ = 0.8 mm) / d_v | 약 8 | 약 24 px 크기의 엽 |
| 망 형성·재배향 시간 / T | 약 100–200 | 100–200 주기 (전진면 뒤에서는 더 빠를 수 있음, 미확인) |
| run / tumble 지속 / T | 약 29 / 11 | 29 / 11 주기 |
| 자기회피 거리 / 몸 폭 | 1–2 | 몸 폭의 1–2배 |

프로토타입과의 대조 [추론]: `hybrid.py`의 주기는 2π/ω = 62.8 시간단위 = 628 스텝. 실행 길이 12,000–16,000 스텝은 19–25 주기다. 실제 망 형성 시간(100–200 주기)의 1/5–1/10에 해당한다. 반대로 `continuum.py`의 D 적응 시간 1/rD = 50 시간단위는 1주기보다 짧아, 실제(100주기)보다 100배쯤 빠르다. 왕복 흐름의 부호가 바뀌기 전에 D가 따라가므로, D가 시간 평균 유량이 아니라 순간 유량 크기를 추종한다.

---

## 3. 모델별 노트

### 3.1 Takamatsu, Takaba, Takizawa 2009 — 환경 의존 형태와 망 성장 모델

- 서지: J. Theor. Biol. 256(1):29–44 (2009), DOI 10.1016/j.jtbi.2008.09.010. **본문 미접근.**
- 확인된 것
  - 초록 [발췌]: 환경 조건에 따른 분기 망 성장 패턴을 조사. 형태를 정량 분석한 뒤 성장 과정을 지배하는 국소 규칙을 추출해 단순한 망 성장 모델을 구성. 모델은 특정 계에 의존하지 않고 **규칙 두 개만** 쓴다. 세균 군집 패턴과 비교해 논의한다. 키워드: pattern formation, oscillation, growth dynamics, bacterial colony, network.
  - 실험 조건 [본문, 0904.1456 Fig. 1]: 1 mM KCl 한천 → 수지상, 귀리 한천 → 원반.
  - 모델의 종류 [2차·본문, Jones arXiv:1511.05869]: "Takamatsu's hexagonal CA mimics the growth patterns displayed under differing nutrient concentrations and substrate hardness. The patterns reflect experimental results well but do not (at least at this stage - oscillatory behaviour is in development) show morphological adaptation as the plasmodium grows."
- 확인하지 못한 것: 두 규칙의 내용, 파라미터, 상도표, 정량 지표(프랙탈 차원 등). **규칙을 지어내지 않는다.** [기억, 신뢰도 낮음]으로는 "전진 끝이 격자 위에서 확률적으로 자라고, 끝에서 원점까지 경로 위의 관이 굵어진다"는 형태였던 것 같으나 구현 근거로 쓰면 안 된다.
- 재현 범위와 한계(2차 서술 기준): 영양 농도·기질 굳기에 따른 성장 패턴(조밀 ↔ 수지상). 진동 없음, 성장 뒤 재편(조대화) 없음, 이주 없음.
- 후속 [발췌]: Takamatsu 외 2017 J. Phys. D 50:154003 "Energy-saving with low dimensional network in Physarum plasmodium"(초록도 못 봄). Yoneoka & Takamatsu 2023 Front. Cell Dev. Biol. 11:1249165 — 습관화 학습 중 망이 트리형에서 그물형으로 바뀌고, 두께 진동 주파수가 망 형태에 의존한다.
- 관련 [본문]: Kagawa & Takamatsu, arXiv:0904.1456. 점균 망을 "트리 + 격자 혼합" 가중 평면 그래프로 추상화했다. Cayley 트리(분기수 b, 깊이 d_max)에 같은 깊이 노드를 고리로 잇고, 가중치를 `R = w(d+1)/w(d)`(중심 가중 ↔ 주변 가중), `S = v(d)/w(d)`(트리 변 대 고리 변), 총 가중 w_tot로 정한다. 같은 위상·같은 총 가중에서도 가중 분포가 동기화 확률을 크게 바꾼다. 우리에게는 "관 굵기 분포가 위상 패턴을 정한다"는 정성적 근거다.
- 시사점: 형태 전환의 실험 사실(영양 → 시트/그물, 기피·기아 → 수지상)은 채점 기준으로 쓸 수 있다. 모델 자체는 원문을 구하기 전에는 쓸 수 없다.

### 3.2 Gunji 외 2008 CELL 모델, Niizato 2010, Gunji 2011 VP 모델

- 서지: Gunji, Shirakawa, Niizato, Haruna, "Minimal model of a cell connecting amoebic motion and adaptive transport networks", J. Theor. Biol. 253(4):659–667 (2008). Niizato, Shirakawa, Gunji, BioSystems 100(2):108–112 (2010). Gunji, Shirakawa, Niizato, Yamachiyo, Tani, J. Theor. Biol. 272(1):187–200 (2011). **세 편 모두 본문 미접근.**
- 규칙 [2차·본문]: Hsu, Schaposnik Massolo, Schaposnik, arXiv:2110.08233, II.A절의 재서술. 접근 URL: https://arxiv.org/pdf/2110.08233
  - 격자 칸 상태: 0 = 바깥, 1 = 세포질, 2 = 세포골격("essentially the boundary of the cell").
  - 반복:
    1. "Randomly choose a square of state 2, which we will call the stimulus point."
    2. "Choose a neighbor (a cell to the north, south, west, or east) of the stimulus point that is in state 0. Swap the states of the stimulus point and the selected neighbor. This represents the zero, which we now call a bubble, invading the cell."
    3. "Replace state 1 with 2 so all squares that are part of an organism are in state 2. Set the number of moves to zero. Mark all sites as not visited."
    4. "Mark the site of the bubble as visited"
    5. "If s of the bubble's neighbors are zero, go to 8. Otherwise, go to 6."
    6. "If the number of moves is larger than n, go to 8. Otherwise, go to 7."
    7. "Randomly select one of the bubble's neighbors of state 2 and not previously visited. Swap the state of the bubble and the selected neighbor. Increase the number of moves by 1 and go to step 4."
    8. "Reassign states 1 and 2. If a square has no neighbors that are 0, it should have a state 1. Return to step 1."
  - 파라미터: n(버블 최대 교환 횟수), s(버블이 멈추는 바깥 이웃 수). HSU21은 n = 1000, s = 3. 초기 모양은 마름모.
  - 자극점을 무작위로 고르면 아메바 운동, 특정 활성 구역에서만 고르면 구역 사이에 트리 망이 생긴다.
- 규칙의 물리적 의미 [추론]: 1–2단계에서 몸 칸 하나가 바깥으로 한 칸 나가고(자극점에서 돌출) 그 자리에 구멍이 생긴다. 구멍이 몸 안을 무작위로 걸으면 지나간 경로의 몸 칸들이 한 칸씩 자극점 쪽으로 밀린다(경로 = 흐름). 구멍은 바깥 이웃이 3개인 곳, 즉 **폭 한 칸짜리 돌기의 끝이나 오목한 틈**에서 멈춰 몸 밖이 된다. 결과적으로 질량이 정확히 보존되고, 자극점에서 한 칸 전진하고 가는 막다른 끝에서 한 칸 후퇴한다. 막다른 가지가 먼저 먹히므로 가지치기가 내장되어 있다.
- 확인하지 못한 것: 원 논문에 있다고 알려진 "버블 이동에 따른 세포골격 재조직"의 정확한 규칙(총설 arXiv:1712.02910은 "during transport the bubble is accompanied by cytoskeleton, which leads to a re-organization of the distribution of the cytoskeleton"라고만 적는다), Niizato 2010의 규칙, VP 모델의 "particle transformation" 규칙.
- VP 모델 초록 [발췌]: 입자 수를 줄이는 변형 VP-S는 먹이에 끌릴 때의 적응 망을, 늘리는 변형 VP-D는 성장하는 점균의 패턴을 흉내 낸다. 탐색과 활용의 균형, 척도 없는(scale-free) 부분 영역을 보인다. Liu 외는 버블이 하나뿐이라 효율이 낮다고 비판하고 다중 버블판을 제안했다.
- 재현 범위: 아메바 운동, 촉수 형성, 미로, Steiner/스패닝 트리, 여러 세포의 융합. 한계: 순차 갱신(버블 하나씩)이라 GPU 병렬에 맞지 않는다. 진동·두께·굵기 위계 없음(굵기는 칸 수로만 표현). 등방 환경에서는 부채꼴이 아니라 무정형 아메바.
- 시사점: "전진 한 칸 = 막다른 끝 한 칸 후퇴"라는 **질량 교환의 짝**과 "바깥 이웃이 많은 칸부터 후퇴"라는 규칙은 우리 flux-form 모델에 연속형으로 옮길 수 있다(5절 실험 E6).

### 3.3 Adamatzky — 준흥분성 Oregonator 파편(wave-fragment)으로서의 전진면

- 서지와 URL: Adamatzky, "Steering plasmodium with light: Dynamical programming of Physarum machine", arXiv:0908.0850 [본문]; Adamatzky, "Slime mould computes planar shapes", arXiv:1106.0305 [본문]. 원 아이디어는 Adamatzky, De Lacy Costello, Shirakawa 2008과 Adamatzky 2007(미접근)에 있다고 인용된다.
- 관찰 주장 [본문, 0908.0850]: "When plasmodium is cultivated on a non-nutrient substrate a profile of its pseudopodium's propagating tip, and particularly the profile of the plasmodium propagating as a whole, is isomorphic to shapes of and behaves as wavefragments in sub-excitable reaction-diffusion chemical media." "In an ideal situation the plasmodium propagates as wave-fragment and — unless encounters an obstacle on the way — keeps its shape and velocity vector".
- 식(원문 표기):
  - `∂u/∂t = (1/ε)(u − u² − (f v + φ)(u − q)/(u + q)) + D_u ∇²u`
  - `∂v/∂t = u − v`
  - v에는 확산 항이 없다.
- 파라미터 [본문]: Euler, 5점 라플라시안, Δt = 5·10⁻³, Δx = 0.25, ε = 0.03, f = 1.4, q = 0.022. 0908.0850: φ₀ = 0.0804(준흥분성), 빛 장애물 안 φ = 0.085(비흥분성), `φ = φ₀ − α/2`, A = 0.0011109. 1106.0305: φ₀ = 0.0766, `φ = φ₀ − η/2`(η는 유인물질 기울기). D_u 값은 두 논문 본문에 명시되어 있지 않다. 초기 자극은 11×11 또는 15×15 칸에 u = 1.0.
- 해석 [본문, 1106.0305]: u = 원형질 국소 밀도, v = 대사물·영양 농도. 관 형성은 모델에 없고, u > 0.1이 지나간 칸을 행렬 L에 누적한 뒤 침식(erosion)을 반복해 관을 그린다.
- 거동 [본문]: 준흥분성에서는 국소 교란이 자기 국재화된 파편을 만들고, 파편은 "preserve their shape for finite period of time and then either expand or collapse". 타원 자극은 반대 방향으로 가는 파편 둘로 갈라진다. 비흥분 영역에 닿은 부분은 꺼지고 나머지가 계속 간다.
- 재현 범위: 무영양 기질에서 **초승달 모양으로 국재된 전진면**이 일정한 모양과 속도로 진행, 장애물에서의 분열·회피. 한계: 질량 보존 없음(u는 반응으로 생기고 사라진다), 진동·정맥·점액 없음, 준흥분성은 좁은 파라미터 창이라 파편이 결국 퍼지거나 소멸한다. 정량 비교는 없고 "phenomenological match"다.
- 시사점: 접근 가능한 문헌 중 **등방 환경에서 스스로 부채(초승달)꼴 전진면이 되는** 식이 명시된 유일한 모델이다. 2장(u, v)만 쓰고 명시적 3×3 갱신이라 WebGL2에 그대로 올라간다. 다만 Δt = 5·10⁻³은 격자 한 칸을 넘는 데 수백 스텝이 필요하다는 뜻이라, 프레임당 패스 수십 회로 맞추려면 시간·공간 재척도가 필요하다. 우리 모델에 쓰려면 u를 h의 원천이 아니라 **전진면의 항복압/이완을 조절하는 흥분 변수**로 써서 질량 보존을 유지해야 한다(5절 E5).

### 3.4 Schenz 외 2017 — "routing while scouting" (요약만)

- 서지: Schenz, Shima, Kuroda, Nakagaki, Ueda, J. Phys. D 50:434001 (2017). 본문 미접근. 세부는 `vein-formation-models.md` 9절.
- 초록·발췌로 확인된 구조: (1) 정맥망 발달 = current reinforcement, (2) 전진면 = 졸–겔 전환으로 구동되는 반응–확산, (3) 개체 전체로 퍼지는 액토미오신 수축파. 연속층 하나와 망용 미세 격자 하나, 두 층에서 수치 풀이한다(2306.09063 [본문]의 서술: "combining reinforcement models with reaction-diffusion and gel-sol models at the migration front"). 초록 [발췌]: 전진면 동역학과 정맥망 발달의 연결이 특징적 정맥 궤적을 만드는 데 중요하다.
- 시사점: 접근 가능한 범위에서 "부채꼴 전진면 + 뒤따르는 정맥"을 한 모델로 낸 것은 이것과 de Almeida–Dilão(자매 노트 5.2절, 그래프 모델)뿐이다. 두 모델 모두 전진면을 **별도의 메커니즘**으로 두고 정맥 적응과 결합한다. 압력 하나로 몸·전진·정맥을 모두 내는 모델은 찾지 못했다.

### 3.5 Julien & Alim 2018 — 연동파 파장이 개체 크기를 따라가는 조건

- 서지와 URL: "Oscillatory fluid flow drives scaling of contraction wave with system size", arXiv:1806.05933 (PNAS 115:10612) [본문].
- 식 (관 반경 a(z,t), 단면 평균 유속 ū, 단면 적분 농도 C = πa²c, 변형 ε = (a − a*)/a*):
  - (1) `∂a²/∂t = −∂/∂z (a² ū)`
  - (2) `ū = −(a²/8µ) ∂/∂z (σ_c + σ_e)`
  - (3) `σ_e = Eε + κε³ + η ∂ε/∂t`
  - (4) `σ_c = σ₀ (C/C*)(1 − ε/ε_σ)` — 재구성. 수축 응력은 농도에 비례하고, 수축된 피질에서 섬유 겹침이 늘어 자기 증폭한다.
  - (5) `∂C/∂t = 2πa[p_c(1 + ε/ε_c) − d_c C/(πa²)] + ∂/∂z[−Cū + (D + a²ū²/(48D)) πa² ∂/∂z (C/(πa²))]` — 재구성. 신장 활성 유입 + Taylor 분산을 포함한 이류–확산.
  - 평형 `C* = πa*² p_c/d_c`. 불안정 조건과 λ_lin의 닫힌 식(원문 식 6–8)은 추출이 깨져 옮기지 않았다.
- 결과 [본문]
  - 닫힌 경계 관에서는 파 크기가 선형 불안정 파장 λ_lin에서 포화한다.
  - 주기 경계 관에서 길이 2λ_lin일 때 300회 실행의 패턴은 5종이고, 관 길이와 같은 단일 진행파는 12 %뿐이다. 거의 50 %는 순유량이 0인 반대칭 파다. 단일 진행파가 순유량이 가장 크다.
  - **관을 0.2 λ_lin에서부터 천천히 키우면**(성장 속도 ≪ 수축 주기) 파 크기가 관 길이를 따라 L_lim = 6.6 λ_lin까지 커진다. 그 위에서는 6–7개의 작은 파로 쪼개진다. 외부에서 진동 유량을 주는 경계 조건으로도 스케일링이 생긴다.
  - λ_lin ∝ µ^(−1/4), L_lim ∝ µ^(−1/2). 어림식 `λ_lin ≃ 1 m^(1/2) (h a*)^(1/4)`(h = 피질 두께). 2207.13812 [본문]는 이 모델의 λ_lin을 7.1 mm로 인용한다.
- 시사점: 몸 전체 한 파장의 연동파는 저절로 보장되지 않는다. 문헌이 확인한 조건은 "작은 상태에서 천천히 자란다"와 "수축 조절 화학물질이 왕복 흐름에 실려 간다"이다. 우리 모델의 위상장은 이웃 결합 K뿐이고 흐름에 의한 위상 이류가 없다.

### 3.6 자유 경계 2상(다공탄성) 모델 — 순이동의 조건

- Kulawiak, Löber, Bär, Engel, "Oscillatory motion of a droplet in an active poroelastic two-phase model", arXiv:1803.00337 [본문]. 1차원, 자유 경계, 선형 기질 마찰.
  - 결과: 정지, 규칙 진동, 불규칙 진동. 실험과 비슷한 주기·진폭. 그러나 "In our simulations, the droplets never exhibit net motion".
  - 논증(원문 식 12–14): 질량밀도 일정일 때 질량중심 속도 `v̄ = (1/V₀)∫_B u̇ dx = (1/V₀)∫_B (1/γ) ∂_x(σ − p) dx`. γ가 공간적으로 일정하면 Gauss 정리로 `v̄ = (1/(γV₀)) ∮_∂B (σ − p) n dS`, 자유 경계 조건에서 0. "Thus, a spatially dependent substrate friction seems to be an essential ingredient to obtain net motion."
  - 실험값 인용: 미소 원형질체 순이동 0.15–0.2 µm/s. 모델 최대 순간 속도 2.47–5.5 µm/s.
- Zhang 외, arXiv:1703.09691 [본문]: 약 300 µm 조각 40개 중 연동형 20, 양단형(amphistaltic) 8. 흐름 패턴이 대칭인 조각이 비대칭인 조각보다 유의하게 느리다. 외질의 전진은 stick–slip 전이의 연속으로 보인다. 주기 약 100 s.
- Radszuweit 외 arXiv:1307.0670 [본문 일부만 훑음], Yamada, Nakagaki, Ito arXiv:patt-sol/9805004 [본문]: 후자의 기본식은 `∂h/∂t + ∇·(h v) = 0`, `∂u_gel/∂t = F_gel(h,u) + ∇·(D_gel ∇u_gel)`, `∂u_sol/∂t + v·∇u_sol = F_sol(h,u) + (1/h)∇·(D_sol h ∇u_sol)`, `v = −q(h)∇P(u)`. 저자들이 직접 한계를 적었다: 졸–겔 전환을 무시하므로 "the cell motility, the formation and reconnection of a network of protoplasmic strands"는 다루지 못한다.
- 시사점: 우리 프로토타입은 Yamada형(두께 보존 + 화학 진동자 + 압력 구배 유동)에 항복 게이트를 붙인 것이다. Kulawiak의 논증은 균일 마찰·응력 자유 경계에 대한 것이라 항복 게이트가 있는 우리 모델에 그대로 적용되지는 않는다. 다만 **앞뒤 비대칭이 어디에서 오는지**를 모델 안에서 명시해야 한다는 점은 같다. 실제 점균에서 확인된 비대칭은 뒤쪽 피질이 더 뻣뻣함, 전진이 후퇴보다 김, 앞→뒤보다 뒤→앞 흐름이 큼, 접착과 수축의 조율이다(2306.09063 [본문]).

### 3.7 Tröger 외 2024 — 자기회피 run-and-tumble (2.7절)

- 규칙과 파라미터는 2.7절. 몸의 형태가 아니라 질량중심 궤적 모델이다.
- 시사점: 점액 기피의 채점 기준이 된다. 몸 폭의 1–2배 거리에서 회피, 장시간 MSD 지수 1.5, run 48분 대 tumble 18분(주기 수로 29 대 11). tumble 단계는 "stationarity with small positional oscillations"이고 방향을 잃은 둥근 모양과 겹친다(2306.09063 [본문]: 느린 재배향 단계는 원형 모양과 일치). 즉 원반 상태가 주기적으로 나타나는 것은 정상이다.

### 3.8 셀룰러 오토마타 — Tsompanas 외

- 서지와 URL: Tsompanas, Dourvas, Ioannidis, Sirakoulis, Hoffmann, Adamatzky, "Cellular Automata Applications in Shortest Path Problem", arXiv:1712.05202, 7절 [본문]. 원 모델 논문(Tsompanas & Sirakoulis 2012)은 미접근.
- 칸 상태: `C_{i,j}^t = {Topology, Chem, Dir, Phys, Pseudo}`. Moore 이웃. Chem = 유인물질 농도(이웃으로 확산), Dir = 유인 방향 편향 계수, Phys = 세포질 부피(이웃으로 확산, Dir로 편향), Pseudo ∈ [0,1] = 최종 관 경로 표시(질량이 가장 큰 이웃을 따라감). 갱신식의 계수는 이 장에 없다.
- 결과: 50×50 미로를 1500 스텝에 해결. GPU(CUDA) 구현.
- 한계: 질량 확산에 편향을 준 것이라 전진면은 확산형이고, 관은 창발이 아니라 경로 추적이다. 진동·위계 없음. 우리 문제에는 직접 도움이 되지 않는다.

### 3.9 그 밖에 훑어본 것

- David, Boussard, Riane, Lapidus, Dussutour, "Emergent Loewner Dynamics in Slime Mold Growth", arXiv:2603.10201 [본문]: 지름 13 mm 개체 하나가 90 mm 접시(1 % 한천, 25 °C)를 24시간 탐색. 위족 경계에서 재구성한 Loewner 구동 함수가 Brown 운동과 비슷한 통계를 보인다. `D = 1 + κ/8`로 κ를 추정. 개체 하나의 분석이고 본문 텍스트에 D나 κ의 대표값이 없다. 성장 규칙은 주지 않는다.
- Göttlich, Knapp, Weber, arXiv:2006.03975 [초록만]: 입자 모델에서 유도한 aggregation–diffusion 방정식. 형태·전진면과 무관.
- Bajpai 외, arXiv:2510.19976 [초록·방법 일부]: 500개 이상 표본의 면적·둘레·원형도·프랙탈 차원 시계열. 원형도 `4π·면적/둘레²`. 수치는 그림에만 있다.
- Kay 외 2022 Sci. Rep. [발췌]: 디지털 점균 모델을 "편향 메싱"과 "망 정제" 두 단계로 분리. 도시 설계용이라 생물 재현 모델은 아니다.

---

## 4. 우리 실패 (a)–(d)에 대한 시사점

문헌에 직접 근거한 문장과 내 해석을 구분했다.

### (d) 몸이 원반, 부채꼴 없음

근거가 있는 것:
1. 원반(stationary)은 실제 점균의 정상 상태 중 하나다. 이주 개체도 tumble 단계에서 둥글어진다 [본문].
2. 부채는 연동파가 향하는 쪽에 생긴다 [본문, 2506.12803]. 그 연동파는 몸 전체가 한 파장이다 [2차·본문].
3. 등방 → 손가락 전환은 반지름이 약 2배가 될 때 일어난다 [발췌, Vogel 2017].
4. 국소적으로 수축이 멈추거나 이완되면 그 자리에 부채가 자란다 [본문, 1710.08784; 2306.09063의 유인물질 → 이완].
5. 전진면은 전진과 정체를 주기적으로 교대하고, 손가락은 임계 곡률에서 갈라진다 [발췌].
6. 손가락 분열의 역학 모델은 2023년 시점에 없다고 총설이 적는다 [본문].

프로토타입 계측(4.5절)과 해석 [추론]:
- 계측 결과 위상 패턴은 가장자리가 앞서는 동심원이다. 진동수 식 `ω = ω0(1 + w_c c + w_h(h* − h) − w_s s)`에서 얇은 가장자리가 빨리 도는 것과 일치한다. 방사 대칭인 파는 어느 한쪽으로의 순수송을 만들지 못한다(Julien & Alim: 반대칭 파 패턴은 순유량 0). 질량중심 이동은 0.1–0.7 px였다.
- 160² 실행(몸 등가 반경 약 30 px)에서는 중심–가장자리 위상차가 약 0.5바퀴에서 멈췄다(위상 고정, 파장 ≈ 몸 지름). 288² 실행(등가 반경 약 65 px)에서는 9.5주기 동안 계속 늘었다. K = 0.05는 큰 몸을 위상 고정시키기에 모자란다. 실제 게임 스케일(몸 지름 수백 px)에서는 더 모자랄 것이다.
- 처음에 세운 가설 "안쪽으로 가는 파가 질량을 중심으로 퍼 올려 원반을 유지한다"는 **계측으로 지지되지 않았다.** 시간 평균 반경 방향 유량은 모든 반경에서 바깥쪽(+)이었다. 몸이 아직 퍼지는 중이라 압력 구배에 의한 확산형 유량이 지배하고, 연동 성분은 분리하지 못했다.
- 프로토타입 초기 질량은 h = 2.2–2.5 h*다. 160² 실행은 12.7주기에 면적이 초기의 3.36배(반지름 1.83배, 평균 두께 0.73 h*)까지 퍼졌고 아직 느리게 커지는 중이었다. Vogel의 "반지름 2배" 부근이지만 손가락형 전환은 보이지 않았다(솔리디티 0.75, 먹이 쪽 엽 때문으로 보임). 288² 실행은 9.5주기에 1.43배에 그쳤다.
- 실제 점균은 앞이 가장 두껍고 뒤가 얇다(Kuroda). w_h > 0 규칙에서는 얇은 뒤가 파원이 되어 파가 뒤 → 앞으로 가므로, 극성이 일단 생기면 총설의 서술("contractions start at the rear... and travel to the front")과 같은 방향이 된다. 문제는 대칭 상태에서 가장자리 전체가 얇다는 점이다. 한쪽이 두꺼워지면 그쪽이 파의 종착점으로 남는 양의 되먹임이 생기는지는 시험해야 안다.
- 프로토타입에서 마른 칸으로의 유입은 `p > yield`일 때만 일어난다. p가 yield를 크게 넘으면 사방으로 균일하게 전진한다(Eden형). p가 진동의 정점에서만 yield를 넘도록 맞추면 5번의 전진–정체 교대가 되고, yield 잡음이 약한 곳에서만 뚫려 엽이 생길 수 있다. 문헌으로 확인된 메커니즘은 아니다.

### (b) 굵은 직선 관 하나

근거가 있는 것:
1. 실제로도 굵은 관 몇 개짜리 트리(lightning)가 시간의 15–30 %를 차지한다 [본문].
2. 그물은 전진면 뒤에서 계속 새로 만들어진다. 시트에 채널이 생기고 사이 층이 얇아져 사라진다 [2차·본문].
3. 조대화·재배향은 수축 주기의 약 100배 시간 척도다 [본문].
4. 폭 분포는 로그정규이고 조대화가 진행되면 좁아진다 [2차·본문]. 즉 넓은 굵기 분포는 젊은 망과 늙은 망이 한 화면에 공존할 때 생긴다.

해석 [추론]: 위계는 "전진 속도 × 조대화 시간"만큼의 길이에 걸친 나이 구배다. 전진면에서 가는 관이 생기는 과정이 없거나 조대화가 전진보다 훨씬 빠르면 관 하나만 남는다. 프로토타입은 두 조건에 모두 해당한다.

### (a) 연속장 Tero가 얼룩

근거가 있는 것: 실제 정맥 사이의 시트는 물러나 없어진다 [2차·본문, 발췌]. 귀리 한천(영양 풍부)에서는 망 없는 균질 시트가 유지되는 경향이 있다 [본문, 2209.11305].

해석 [추론]: 프로토타입의 압력 `κ(h − h* − ηD)`는 h에 대해 단조라 시트가 두 상(두꺼운 관 / 마른 바닥)으로 갈라질 이유가 없다. 영양이 풍부할 때의 균질 시트에 해당하는 영역에 머물러 있다고 볼 수 있다. 시트가 스스로 갈라지게 하려면 p(h)에 비단조 구간(얇은 막이 불안정한 구간)이 필요하다. spec의 "몸의 탈젖음" 가설과 같은 방향이고, 문헌이 직접 지지하는 식은 찾지 못했다.

### (c) 점유 제한

추가 근거 없음.

### 4.5 프로토타입 계측 (이 조사에서 직접 돌린 것)

문헌 해석이 프로토타입에 맞는지 확인하려고 `hybrid.py`를 저장소 밖으로 복사해 마지막 루프만 계측 루프로 바꿔 돌렸다. 저장소 파일은 건드리지 않았다.

- 스크립트: `/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research/work_morph/make_diag.py` (사본 `hybrid_diag.py`를 만든다)
- 계측: 젖은 면적비, 중심과 가장자리 두께, 질량중심에서 16방위 광선을 따라 푼 위상의 감김 수(양수 = 가장자리가 위상 앞섬), 질량중심 이동, 후반부 시간 평균 반경 방향 유량 `q_r`, 솔리디티.
- 각 조건 1회 실행(시드 고정)이다. 통계가 아니다.

| 조건 | 주기 수 | 면적/초기 | 평균 h | 위상 감김(중앙값, 시간순) | 질량중심 이동 | 시간 평균 q_r (r/R 0–0.3 → 0.9–1.2) | 솔리디티 |
|---|---|---|---|---|---|---|---|
| 160², README의 h2 파라미터, 8000 스텝 | 12.7 | 2.28 → 2.98 → 3.23 → 3.36 | 1.10 → 0.73 | 0.57 → 0.53 → 0.40 → 0.46 | 0.3–0.7 px | +0.0017 → +0.0090 | 0.748 |
| 288², README의 L1 파라미터, 6000 스텝 | 9.5 | 1.19 → 1.30 → 1.37 → 1.43 | 1.85 → 1.53 | 0.34 → 0.73 → 1.45 → 2.25 | 0.1 px | +0.0032 → +0.0091 | 0.917 |

읽는 법: 순간 유량 크기는 0.009–0.044이고 시간 평균 반경 성분은 그 10–60 % 수준의 양수다. 두 실행 모두 끝까지 퍼지는 중이었다. 288² 실행의 위상 감김이 수렴하는지는 이 길이로는 알 수 없다.

---

## 5. 실험 제안 (이 조사 범위에서 나온 것. 우선순위 순)

채점은 `scratchpad/research/common/eval_morph.py`와 6절 지표를 쓴다.

- **E1. 위상 패턴의 대칭 깨기.** 4.5절 계측으로 현재 패턴이 "가장자리가 앞서는 동심원, 큰 몸에서는 위상 고정 실패"임을 확인했다. 시험할 것: (i) K를 0.05 → 0.2, 0.5, 1.0으로 올려 288² 이상에서 위상 감김이 1 이하로 고정되는지, (ii) w_h를 +0.5, 0, −0.5로 바꿨을 때 동심원 방향이 뒤집히는지, (iii) 초기 두께를 한쪽으로 10–30 % 기울였을 때 극성(한쪽 끝에서 반대쪽 끝으로 가는 선형 위상 구배)이 자라는지 사라지는지, (iv) Julien & Alim 조건을 흉내 내어 작은 몸(지름이 목표의 1/5)에서 시작해 먹이로 천천히 키웠을 때. `make_diag.py`의 계측을 그대로 쓴다. 통과 기준: 위상이 몸의 한 축을 따라 약 한 바퀴, 질량중심이 한 방향으로 주기당 1 px 이상 이동, 솔리디티 < 0.9.
- **E2. 위상의 흐름 이류.** `∂z/∂t`에 `−u·∇z`(u = q/h)를 더한다. 한 패스 추가다. 파장이 몸 크기를 따라가는지 E1과 같은 지표로 본다.
- **E3. 질량 제한 확장.** 초기 h/h*를 2.5 → 1.2, 0.8, 0.5로 낮추거나 h*를 낮춰 평형 면적이 초기의 4배 이상이 되게 한다. 반지름이 2배쯤 될 때 둘레가 끊기고 몇 방향으로만 전진하는지 본다(Vogel 2017의 전환). 측정: 전진면 각폭(둘레 중 전진 중인 칸의 각도 합), 전환 시점의 반지름 비.
- **E4. 문턱 근처 전진.** yield0과 amp를 조절해 p가 진동의 정점에서만 yield를 넘게 한다. 전진–정체 교대와 엽 분열이 생기는지, 엽의 곡률 반경이 정맥 지름의 몇 배인지(목표 약 4배, 엽 지름 약 8배) 잰다.
- **E5. 준흥분성 전진면 변수.** Oregonator(3.3절의 식과 파라미터)를 별도 2채널로 돌려 초승달 파편이 유지되는 φ 창을 격자 256²에서 먼저 확인한다. 그다음 u를 "전진 허가"로 써서 `yield = yield0·(1 − g·u)`처럼 항복압만 낮추고 질량은 h의 유량으로만 옮긴다. 흥분성 φ를 국소 압력이나 여유 질량의 함수로 두어 질량이 모자라면 파편이 좁아지게 한다. 통과 기준: 등방 환경에서 초승달형 전진면이 20주기 이상 유지되고 총 질량 오차 1 % 이내.
- **E6. 막다른 끝 우선 후퇴(CELL 규칙의 연속형).** squeeze 항에 "마른 이웃 수"를 곱한다(8이웃 중 마른 칸 수 n_dry에 대해 `Q·(n_dry/8)^m`). 바깥 이웃이 많은 가는 돌기 끝부터 빠진다. 고리와 간선은 남고 막다른 가지만 사라지는지 `endpoints`와 `loops`로 본다.
- **E7. 탈젖음 압력.** p(h)에 비단조 구간을 넣는다. 예: `p = κ(h − h*) − W·h·exp(−h/h_c)`류로 얇은 막(h < h_c)이 불안정하게. 균질 시트가 능선 그물 + 마른 구멍으로 갈라지는지, 분기점 차수가 3인지, `loops/branch_points`가 0.5에 가까운지 본다. 문헌 근거는 "사이 시트가 물러난다"는 관찰뿐이다. 식의 형태는 내 제안이다.
- **E8. 나이 구배 위계.** 관 형성(입자든 D든)의 시간 척도를 조절해 조대화 시간이 50–200주기가 되게 하고, 전진 속도는 주기당 정맥 지름의 1–3배로 맞춘다. 측정: 전진면에서의 거리 대 정맥 폭의 기울기, 폭 분포(로그정규 적합, P90/P10), 접합점에서 `r₀^n = r₁^n + r₂^n`을 만족하는 n(목표 2.5–3.3).
- **E9. 적응 속도 분리.** `continuum.py`의 qavg 평균창을 1주기 이상으로 늘리고(계수 0.995 → 0.9995 이상, 1에 더 가깝게), rD를 0.02 → 0.001 이하로 낮춰 D가 왕복 흐름의 시간 평균을 보게 한다. 얼룩이 줄어드는지 확인한다. 실행 길이는 100주기 이상이 필요하다(128²에서 6만 스텝 이상).
- **E10. 세 상태 채점.** 긴 실행(200주기 이상)에서 6절의 세 지표를 시계열로 뽑아 stationary / crescent / lightning 점유율을 낸다. 목표: 세 상태가 모두 나타나고, 먹이 없을 때 crescent가 가장 많다.
- **E11. 점액 기피 검증.** 먹이 없는 토러스에서 질량중심 MSD를 낸다. 목표: 단시간 β ≈ 2, 장시간 β ≈ 1.5. 점액을 끄면 β → 1로 떨어지는지 대조한다. 회피가 시작되는 거리가 몸 폭의 1–2배인지 본다.
- **E12. 기질 스위치.** 배경 영양(항복압을 낮추고 h*를 올림)과 기피물질(항복압을 올림)을 전역 파라미터로 두고 시트/그물 ↔ 수지상 전환이 나오는지 본다. 목표는 2.6절의 정성 관계다: 영양 → 조밀·굵음·느림, 중성 → 성기고 가늘고 김, 기피 → 작고 촘촘함.

WebGL2 실현성 [추론]: E1–E4, E6–E9, E12는 기존 장 갱신 셰이더의 항 추가라 패스 수가 늘지 않는다. E2는 위상장에 반-라그랑지 이류 1패스. E5는 2채널 핑퐁 1개 추가이나 시간 재척도가 필요하다. 전역 선형계는 어느 것도 요구하지 않는다. E10–E11의 지표 계산은 CPU 리드백이 필요하므로 numpy 프로토타입이나 디버그 페이지의 저빈도 리드백으로만 한다.

---

## 6. 판정 지표 제안

`eval_morph.py`에 이미 있는 것: 원형도, 솔리디티, 정맥 면적비, 분기점·끝점·고리 수, 폭 분위수.

추가하면 좋은 것:
1. `R_gr/√A` — h 가중 회전반경을 젖은 면적의 제곱근으로 나눈 값. 균일 원반이면 1/√(2π) ≈ 0.399 [추론]. Schick의 값은 망 픽셀 면적 기준이라 그대로 비교할 수 없다. 상대 변화만 쓴다.
2. 전진면 각폭 θ — 일정 시간 창에서 새로 젖은 경계 칸을 질량중심 기준 각도로 사상해 덮인 각도를 합한다.
3. v_front — 전진 중인 경계의 평균 법선 속도. 질량중심 속도는 쓰지 않는다(Schick의 이유와 같음).
4. 전진면 투입 질량률 — 새로 젖은 영역의 h 합 / 총 질량 / 시간.
5. `loops / branch_points` — 0(트리)에서 0.5(완전 그물).
6. 접합점 차수 분포 — 3이 대부분이어야 한다.
7. 폭 분포의 로그정규 적합도와, 전진면으로부터의 거리에 대한 폭의 회귀 기울기.
8. Murray 지수 — 접합점마다 세 가지의 폭으로 n을 풀어 중앙값을 낸다. 목표 2.5–3.3.
9. 연동파 파장 / 몸 지름 — 위상장의 공간 스펙트럼 최빈 모드. 목표 약 1.
10. MSD 지수 β(t).

---

## 7. 접근하지 못한 것

허용 도메인 밖이라 열리지 않았다. 다시 시도하려면 세션 네트워크 설정에 호스트를 추가해야 한다.

- Takamatsu 2009 JTB 본문 (sciencedirect.com, researchgate.net, waseda.elsevierpure.com) — 모델의 두 규칙과 정량 분석 전체
- Gunji 2008 JTB 저자본 https://da.lib.kobe-u.ac.jp/da/kernel/90001518/90001518.pdf, Niizato 2010, Gunji 2011
- Kuroda 2015 JEB 저자본 https://eprints.lib.hokudai.ac.jp/repo/huscap/all/63698/3729.full.pdf — 속도·두께·주기의 실제 수치와 차원해석 모델
- Akita 2017 (ora.ox.ac.uk 공개본), Fricker 2017 (durham-repository.worktribe.com 공개본)
- Baumgarten, Ueda, Hauser 2010 PRE; Baumgarten & Hauser 2013 Phys. Biol.; Baumgarten & Hauser 2014 EPL; Baumgarten, Jones, Hauser 2015 (actaphys.uj.edu.pl)
- Dirnberger & Mehlhorn 2017, SMGR(smgr.mpi-inf.mpg.de); Westendorf 2016/2018
- Reid 2012 PNAS; Alim 2013 PNAS (pmc.ncbi.nlm.nih.gov/articles/PMC3746869)
- Vogel 2017 J. Phys. D 저자본 https://pure.roehampton.ac.uk/ws/files/285148/transition_AAM.pdf
- Patino-Ramirez 2019/2021 (nature.com, PMC6817824, PMC7810851)
- Schenz 2017; Oettmeier & Döbereiner 2019 (PMC6478327); Lee 2018; Rodiek 2015; Rieu 2015 (PMC4424688)
- Yoneoka & Takamatsu 2023 (PMC10667701); Rosina & Grube 2025 (PMC11879620)
- GitHub `davideciccarese/Physarum-polycephalum-simulation` (검색 발췌: 전진 부채용 colonization 층 + Tero형 적응 망, 부채 뒤의 막이 강화된 관으로 빠져나가며 버려진다. 취미 구현. 세션에 등록되지 않은 저장소라 읽지 못했다)
- scholar.archive.org — 허용 도메인이지만 rate limit 응답만 받았다

---

## 8. 본문을 읽은 URL

모두 `https://arxiv.org/pdf/<id>`를 curl로 받아 pdftotext로 읽었다.

- 2409.12825 Tröger, Goirand, Alim (전체)
- 2408.17134 Schick, Kramar, Alim (본문 전체, SI 일부)
- 2506.12803 Schick 외 (초록, 결과 요지, 그림 설명)
- 2306.09063 Le Verge-Serandour & Alim (2, 4, 5절)
- 1801.02464 Alim (전체 훑음)
- 1806.05933 Julien & Alim (본문 전체, SI 제외)
- 2209.11305 Saiseau 외 (전체)
- 2207.13812 Busson 외 (결과 일부)
- 2501.02651 Saiseau 외 (초록, 결과 일부)
- 1710.08784 Bäuerle, Kramar, Alim (초록, 3절 일부)
- 1803.00337 Kulawiak 외 (초록, 결과 일부, 토의)
- 1703.09691 Zhang 외 (초록, 결과 일부)
- patt-sol/9805004 Yamada, Nakagaki, Ito (1–3절)
- 0904.1456 Kagawa & Takamatsu (서론, 모델)
- 2110.08233 Hsu 외 (II절)
- 0908.0850, 1106.0305 Adamatzky (모델 절)
- 1712.05202 Tsompanas 외 (7절)
- 2603.10201 David 외 (초록, 방법)
- 1511.05869 Jones (Takamatsu 언급 부분만. 나머지는 자매 노트)
- 초록만: 2006.03975, 2510.19976
