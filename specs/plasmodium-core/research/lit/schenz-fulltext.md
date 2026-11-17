# Schenz 원문 정독 노트 (schenz-fulltext)

작성 시작: 2026-11-12. 논문 하나를 읽을 때마다 덧붙인다.
규칙: 식·수치는 원문 표기 그대로, 쪽(PDF 쪽 번호 / 인쇄 쪽 번호)과 식 번호를 단다. 원문에서 직접 확인하지 못한 것은 "(미확인)"으로 표시.

## 0. 대상 문헌
1. Daniel Schenz, 학위논문, Hokkaido University, 2019, 90쪽.
   - 로컬: /tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research/dl2/schenz-thesis/thesis.pdf
2. Schenz, Shima, Kuroda, Nakagaki, Ueda 2017 J. Phys. D: Appl. Phys. 50:434001, doi 10.1088/1361-6463/aa88e9 (본문은 구독 장벽으로 못 읽음. 2절 참조)

목차: 1 학위논문 / 2 2017 논문 접근 결과 / 3 내가 한 재현 계산 / 4 질문 (a)–(f) 답 / 5 시사점 / 6 접근 기록

---
## 1. Schenz 학위논문 (2019) — 전문 정독 (4장의 식·표·초기값은 쪽 이미지 PDF 52–56, 58, 61쪽과 대조해 확정)

- 서지: Daniel Thorsten Schenz, "Transportation Network Optimisation during Exploratory Migration in Physarum polycephalum", 博士(生命科学) 甲第13606号, Hokkaido University, 2019-03-25. DOI 10.14943/doctoral.k13606, https://hdl.handle.net/2115/74323 (HUSCAP).
- 로컬: .../research/dl2/schenz-thesis/thesis.pdf (90쪽, 전문 읽음). 텍스트 추출본: .../research/work-schenz/thesis.txt
- 쪽 번호 규칙: 아래 "p.N"은 인쇄 쪽 번호. PDF 쪽 = 인쇄 쪽 + 9.
- 읽은 범위: 초록, 1장, 2장 전체(2.2.1, 2.2.2, 2.2.3 포함), 3장 전체, 4장 전체, 5장, 참고문헌.

### 1.1 핵심 한 줄
모델은 "전역 압력 푸아송 풀이"가 아니다. (i) 전진면 = 공급항 없는 Gray-Scott 펄스(u 는 경기장 전체에 미리 깔려 있음), (ii) 관 = 미리 깔아 둔 삼각 격자 간선 위의 관성-저항-용량(RLC) 동역학 + 포화형 전류 강화, (iii) 수축 = Smith-Saldana 칼슘 진동자의 반응-확산 파동. 결합은 4개 항뿐이다(1.4절).


### 1.2 2장 배경 모델 (학위논문이 인용·재서술한 것)

**2.2.1 The network adapts to flows (p.9–12)**
- 식 (2.1) p.11: `dD/dT = f(Q) − kD`, `D = r^4`("conductivity"), Q = 관 유량, f = 증가함수, k = 상수. 완화형으로 다시 쓰면 `dD/dt = −k(D − (1/k) f(Q))`.
- 식 (2.2a) p.11: `f(Q) = a|Q|^µ`
- 식 (2.2b) p.11: `f(Q) = |Q|^µ / (1 + a|Q|^µ)`
- p.12: "µ ... has experimentally determined as µ = 4/3, which also is in agreement with Murray's law [3]"(Akita et al. 2017 J.Phys.D 50:024001). 포화형 (2.2b)는 유량이 크면 가는 관 여러 개가 남고 유량이 작으면 관 하나만 남는다 → "probably the more biologically relevant form [81]".
- 식 (2.3) p.12: `Q = π ΔP r^4 / (8 η L)` (Hagen-Poiseuille).
- p.10: 관의 첫 원기(anlage)는 전진면 바로 뒤. endoplasm 이 ectoplasm 사이를 흐르며 proto-channel 을 만든다(Guy, Nakagaki, Wright 2011 [29]). 액틴 섬유가 흐름 방향으로 정렬(shear banding [44]). 후방에서는 "세포 활동이 있는 곳으로 이어지지 않는" 모든 관이 뒤에서부터 차례로 수축해 사라지고 한천에 점액 자국을 남긴다(그림 2.4b).

**2.2.2 Contraction waves (p.12–19)**
- p.12–13: 수축 주기 "around once in 2 minutes". 외질 수축 → 국소 압력 상승 → 내질이 압력 낮은 쪽으로. 주기적·조율된 수축이라 흐름 방향이 주기적으로 바뀜(shuttle streaming).
- Smith & Saldana 1992 [73] 0차원 Ca 진동자. 식 (2.4) p.14:
  `dc/dt = kL (Nc − c(t)) − kV nc(t)`
  `dφ/dt = kQ(nc(t)) (1 − φ(t)) − kE φ(t)`
  (Nc 총 Ca, c 세포질 Ca, nc 자유 Ca, φ 인산화된 MLCK 분율, kL 누출, kV 펌프)
- 식 (2.5) p.15 보존식: `c = nc + NM Σ_{k=1}^{2} k ( q_k^a(nc)(1−φ) + q_k^b(nc) φ )`
- 식 (2.6) p.15: `q_k^a(nc) = (Ka nc)^k / (1 + Ka nc)^2`, `q_k^b(nc) = (Kb nc)^k / (1 + Kb nc)^2`, Ka ≫ Kb.
- 식 (2.7) p.15: `kQ(nc) = kQ* ( K* nc / (1 + K* nc) )^β` (β = Hill 상수)
- 식 (2.8) p.16: 3변수 완화형 `dnc/dt = −k ( nc − (c − A(nc, φ)) )`, k ≫ O(kV).
- p.16–17: 고정점은 안장점, 모든 초기값이 한계순환으로 수렴. K* = 1.5 ([73] 값)에서 불안정·진동. kQ* ≫ kL 이라 φ(빠름)-c(느림) 완화 진동.
- p.17: 국소 압력 진동 → 이웃으로 유량 → 막이 늘어나며 기계감응 Ca 채널이 열림 → 이웃 진동자를 끌어들임(stretch entrainment) [39, 7].

**2.2.3 The growth front (p.20–21)** — 전진면이 관망과 독립이라는 근거
- p.20: "the extension of the growth front does not directly depend on the tube network (in the same way as a car's fuel comes from a petrol station, but the petrol station is not directly necessary for the operation of the car)."
- 절단 실험(Takagi et al. 2007 [75]): 좁은 통로를 전진하는 원형질체의 앞쪽 0.8–5 mm 만 남기고 뒤를 잘라내도 전진면은 "at least another 10 minutes at almost unaffected rates" 로 계속 전진. 수축 진동은 절단 즉시 멈춤. 그러나 전진면은 점점 얇아져 절단 후 약 20분에 멈춤 [85] → 장기적으로는 세포질 공급이 필요.
- 그래서 전진면 = 1차원 Gray-Scott. 식 (2.9) p.20:
  `∂u/∂t = Du ∂²u/∂x² − u v² + f (1 − u)`
  `∂v/∂t = Dv ∂²v/∂x² + u v² − (f + k(x)) v`
  u = 자원, v = 전진을 유지하는 생성물. k(x) = k0 (+c: 국소 불리/유리 조건). "f can be set to 0 if no supply of u is permitted. In this case, the reaction will eventually fully consume u and then stop." (p.21)

### 1.3 3.2절 — "전류 강화만으로는 부족"의 정확한 내용 (p.37–40)  [질문 (d)]
- 실험(3.1절): 폭 5 mm 통로(총 면적 35 mm² 로 기재, p.24), 먹이 없음, 20±2 mg 전진면 조각. U자(90° 두 번) n=15, 뱀 모양 n=8. 3분마다 촬영. 주 정맥은 통로 중심선도 최단 경로도 아닌 "centre-in-centre"(모퉁이 안쪽을 자르고 다시 중심으로 복귀) 궤적. 최단 경로보다 4.6% 길고(중심선은 18.5% 김), 접근성(모든 점에서 정맥까지 평균 최소 거리)은 중심선보다 27.9% 나쁨(최단 경로는 76.4% 나쁨). 전체 탐색 15±4 시간, 주 정맥은 전진면이 지나간 뒤 "typically some 50 minutes" 에 나타나고 그 뒤 위치가 거의 변하지 않음(먹이를 놓아도 변하지 않음, 그림 3.5). (p.26–31)
- 효율 결합식 (3.1) p.31: `E = (w − 1)L + wD` (원문 그대로. L 길이, D 평균 최소 거리, w 가중). 최적 적합 w = 0.167 → 길이 최소화 쪽에 무게.
- Physarum Solver([81])를 U자 경기장 전체에 깐 격자에 돌리고 양 끝을 소스/싱크로 두면, 단일 정맥이 "the geometrically shortest possible path closely" 를 따르고 두 모퉁이 사이 구간에서 안쪽 벽에서 떨어지지 않는다(그림 3.10) → centre-in-centre 가 나오지 않는다. (p.37)
- 결론(p.37): "the vein network dynamics described by the Physarum Solver model alone are insufficient to capture the mechanism driving the emergence of the vein network during extension." 이유: Solver 는 몸이 경기장을 이미 다 덮고 모든 관이 같은 굵기라는 전제(전역 정보)에서 출발한다. 실제는 영역이 늘어나는 중에 관이 만들어진다.
- Akita et al. 2017 [2] 는 Solver 로 centre-in-centre 를 얻었지만, 이는 격자의 무작위성·이웃 모퉁이 배치·초기 굵기 요동에 의존한 "전역 최적화의 결과"라고 구분(그림 3.11 a–f). 이 논문의 정의: 같은 방향 모퉁이가 연속돼도, 다른 선택지가 있어도, 벽의 안내 없이 정맥이 중심으로 복귀하는 것.

### 1.4 4.1절 복합 모델 — 변수·지배식 (쪽 이미지로 대조 완료)  [질문 (a)]

세 요소 + 두 층. 전진면과 수축파는 연속 2차원 공간(FEM), 관망은 "a pre-defined grid of nodes and vertices"(=같은 공간에 미리 깐 그래프) 위(p.42, 46).

**(i) 전진면 (p.43), 식 (4.1a–c)**
```
τ2 ∂u/∂t = Du Δu − u v²                (4.1a)
τ2 ∂v/∂t = Dv Δv + u v² − α1 v         (4.1b)
τ2 dw/dt = h(v),   h(v) = α2 v          (4.1c)
```
- u = "regulatory factors"(solation regulation factors) 농도, v = "solation factors" 농도, w = 개체 두께. Δ = ∂²/∂x² + ∂²/∂y².
- (2.9)와 비교하면 공급항 f(1−u) 가 없다(f = 0). 대신 u 를 경기장 전체에 미리 3 으로 깔아 둔다(초기값 참조). p.42: "the concentration of the the solation regulation factors is high even outside the body mass. In other words, these chemicals are modelled as if the pre-existed in the arena. This certainly is not a realistic situation."
- 변수 해석은 잠정적: 원래 [75]에서는 'intracellular ATP'/'nutrients', [85]에서는 'solation factors'/'solation regulation factors'.
- w 에는 손실항·보존식이 없다. w 는 v 가 지나간 적분량일 뿐이다(= (α2/τ2)∫v dt).

**(ii) 관망 (p.44), 식 (4.2a–c)**
```
dq_ij/dt = (1 / Ĩ_ij(D_ij)) { (p_i − p_j) − R̃_ij(D_ij) q_ij }     (4.2a)
dp_j/dt  = Σ_i (1 / C̃_ij(D_ij)) q_ij                              (4.2b)
dD_ij/dt = |q|^µ / (1 + a_d |q|^µ) − r D_ij                        (4.2c)
```
- q_ij = 노드 i–j 사이 관의 유량, p_i = 노드 i 압력. Ĩ, R̃, C̃ = 관의 유체 관성(inductance)·저항·용량(capacitance). 반지름 0 에서 발산하지 않게 고친 꼴(p.44):
  - `Ĩ_ij(D_ij) = L_ij / (ā_i + a_i D_ij^{1/2})`
  - `R̃_ij(D_ij) = L_ij / (ā_r + a_r D_ij)`
  - `C̃_ij(D_ij) = (ā_c + a_c D_ij^{3/4}) L_ij`
  - `D_ij(t) := d_ij^4(t)` (d_ij = 관 반지름), L_ij = 관 길이.
  - `a_i = 4π/9ρ`, `a_r = 8π/81ν`, `a_c = 2π(1−σ²)/(Eθ)` (ρ 밀도, ν 점성, E 벽 영률, θ 벽 두께, σ 푸아송비). ā_i, ā_r, ā_c 는 포화항을 만드는 임의 상수.
  - 근거 문헌: Rideout & Dick 1967 "Difference-Differential Equations for Fluid Flow in Distensible Tubes" [64].
- 왜 키르히호프(전기회로) 풀이를 버렸나(p.43–44): 전진면이 관망과 거의 독립으로 나아가므로 "cytoplasmic flow sinks may not always be available at the same rate as fluid is supplied from the rear" — 공급이 흡수보다 많을 수도, 전진면이 채워지기 전에 더 나갈 수도 있다. 새로 열린 영역은 "empty tubes of zero diameter" 로 덮여 있다. 그래서 "the tube network must be able to compensate for flow in a pressure-dependent manner by distensible tube walls". 압력과 유량을 각각 동적 변수로 둔다.
- (4.2c)는 (2.1)+(2.2b)의 포화형. a_d, µ 가 비선형성 제어.

**(iii) 수축파 (p.45–46), 식 (4.3)**
```
τ1 ∂c/∂t = −kV nc(c, φ) + kL (Nc − c) + Dc Δc
τ1 ∂φ/∂t = KQ(nc(c, φ)) (1 − φ) − kE φ                              (4.3)
KQ(nc) = kQ [ K* nc(c,φ) / (1 + K* nc(c,φ)) ]
nc(c, φ) = [1 + 0.17 (c − 7.5)] (a0 + a1 φ + a2 φ² + a3 φ³)          (p.46, (2.5)의 적합식, Smith 1994 [72])
```
- c = 총 세포질 Ca, φ = MLCK 인산화 확률, Dc = Ca 확산 상수. (원문은 "cf. equations (2.9)" 라고 썼으나 내용상 (2.4)/(2.8)을 가리킨다 — 원문 오기로 보임.)
- 무작위 소스/싱크 쌍을 버린 이유(p.45): (a) 영역이 매 반복 커지므로 전진면 노드가 뽑힐 확률이 급감 — 비실용적, (b) 전체 흐름에 일관된 패턴이 없어짐 — 비현실적. 그래서 "pressure waves that are generated at the starting point for the simulation and propagate throughout the organism".

**(iv) 층 사이 결합 4개 (p.46–47)**  [질문 (b)]
```
(1) ∂v/∂t = (Dv Δv + u v² − α1 v)/τ2 + k B(w) D̃(x)                 (4.4)
    D̃(x_i) := Σ_j D_ij      (노드 i 에 닿는 관들의 전도도 합)
    B(w) = 1  if w ∈ [w_ext, w_int],  0 otherwise                    (4.5)
(2),(3) dp_j/dt = Σ_i [ 1 / ( C̃_ij(D_ij) (1 + a_v v_ij) ) ] q_ij − κ (c_j − c̄)     (4.6)
    v_ij := [v(x_i) + v(x_j)]/2,  c_j := c(x_j),  c̄ = 기저 Ca 농도
(4) dD_ij/dt = Γ(w_ij) |q|^µ / (1 + a_d |q|^µ) − r D_ij               (4.7)
    Γ(w) := 1 if w > w_th, 0 otherwise;  w_ij := [w(x_i) + w(x_j)]/2
```
- (1) 관 → 전진면: "v is advected to network nodes in amounts proportional to the conductivities D of all tubes ending at the node." 유량 q 가 아니라 **전도도 합 D̃** 에 비례해 v 를 주입한다. 주입은 전진면 띠(w_ext ≤ w ≤ w_int)에서만. k = "interaction strength (for example the concentration of advected v)". 효과: "the advection of additional reactant v destabilises the behaviour of the growth front [70, 12]". (원문 p.46 은 "regulation factor v being ubiquitously located" 라고 썼으나 (4.1)의 정의로는 u 가 regulatory factor 다 — 원문 표기 혼선.)
- (2) Ca → 압력: −κ(c_j − c̄). Ca 가 높으면 수축이 약하므로 κ > 0. 이것이 유량의 구동원.
- (3) v → 벽 강성: 용량에 (1 + a_v v_ij) 를 곱함. "The high concentration of solation factors at the growth front and the resulting low pressure there creates a sink at the growth front." 즉 싱크는 명시적 유출항이 아니라 **전진면에서 벽이 물러져(용량 증가) 압력이 낮아지는 것**이다.
- (4) w → D: 관은 개체 "안"(w > w_th)에서만 굵어질 수 있다. 가는 관의 조밀한 격자는 처음부터 깔려 있다.

**초기값 (p.49)**
```
p_j(0) = 0 (j = 1..N);  q_ij(0) = 0
D_ij(0) = 0.1 if x_i ∈ Ω0 or x_j ∈ Ω0;  0 otherwise
c(x,0) = 1.0 (x ∈ Ω0), 0.0 (x ∈ Ω\Ω0);  φ(x,0) = 0 (x ∈ Ω)
u(x,0) = 3 (x ∈ Ω);  v(x,0) = 1.0 (x ∈ Ω0), 0.0 (x ∈ Ω\Ω0);  w(x,0) = 0 (x ∈ Ω)
```
Ω ⊂ R² = 경기장 내부, Ω0 = 접종 영역.

**파동원 (p.49), 식 (4.8)**: `τ1(x) = τ̄1/3 (x ∈ Ω0),  τ̄1 (otherwise)` — 접종 영역의 진동자만 3배 빠르게 해서 페이스메이커로 삼는다. "a periodic contraction wave propagating from Ω0 to the leading edge is observed. In addition, due to the interaction term κ(c_j − c̄) in (4.6), a to-and-fro sol flow reminiscent of the 'shuttle streaming' ... occurs."

**수치 기법 (p.48)**: "We used the finite element method to solve the contraction wave and the growth front dynamics, employing Neuman boundary conditions. We generated the spatial mesh (figure 4.1) by using the software FreeFEM++ [32]." 관망 ODE (4.2)의 시간 적분법, 시간 간격, 격자 크기(노드 수·간선 길이)는 학위논문에 **적혀 있지 않다**. 그림 4.1 제목이 "the spatial mesh generated for the evolution of the tube network" 이므로 FEM 삼각 격자의 간선이 곧 관망 간선이다.

**파라미터 표 4.1 (p.52, 원문 그대로)**
| 기호 | 값 | 기호 | 값 | 기호 | 값 |
|---|---|---|---|---|---|
| a0 | 0.349353 | Dc | 0.2 | w_ext | 0.1 |
| a1 | -0.0454567 | Du | 0.2 | w_in | 0.9 |
| a2 | 1.15905 | Dv | 0.02 | w_th | 1.0 |
| a3 | 1.823858 | k | 0.01 | α1 | 0.01 |
| a_c | 0.03 | kE | 0.1 | α2 | 0.1 |
| a_d | 0.01 | kL | 0.004 | κ | 1.0 |
| a_i | 5.0 | kQ | 1.0 | µ | 1.3 |
| ā_i | 10.0 | kV | 0.12 | τ̄1 | 0.0072 |
| a_r | 13.5 | K* | 1.75 | τ2 | 20 |
| ā_c | 0.1 | Nc | 25.0 | | |
| a_v | 0.01 | r | 0.15 | | |
| ā_r | 2.5 | R | 1.0 | | |
| c̄ | 7.0 | | | | |
- 표 설명: "Values from [73, 72, 3], see also [69]." 표의 `R = 1.0` 은 본문 어디에도 정의가 없다(미확인 기호). 표는 w_in, 본문 (4.5)는 w_int 로 표기.
- 차원이 붙은 값(길이·시간 단위)은 없다. 모두 무차원 모델 단위.

**시간 척도 (p.47, 52)**
- τ1/τ2 비: "approximately 600 contraction waves run through the body until it has extended over the whole arena, which is in concordance with experimental observations."
- τ1, τ2 절대값: "chosen such that the resulting vein network visually resembles the structure in the real organism."
- 실험에서 정맥 형성 유효 시간 척도 = 195 s (흡광도 적합 `A = 76·e^{−t/195} + 9`, 그림 4.5, p.54). "the tube network formation is not on the same time scale as the (faster) growth front extension, but the difference (a factor of roughly 10) is not so large as to call the two processes uncoupled (as is, for example, the case between the actomyosin contractions and the other two processes)." (p.52)
- 즉 수축(빠름, 완전 분리) ≪ 전진면 ≲ 관 형성(약 10배 차이, 분리되지 않음).

### 1.5 4.1.3–4.1.5 결과·파라미터 변화·해석 (p.49–57)

**표준 조건 결과 (p.49, 그림 4.3, 4.4)**
- "the main veins are formed at a short distance behind the growth front; the position of the main vein, once it has emerged, remains constant over time; and the trajectory of the main vein follows a centre-in-centre pattern at each corner."
- 그림 4.4: 모델 평균 정맥 위치는 실험과 거의 모든 측정점에서 통계적으로 구별되지 않음. 둘째 모퉁이 직후 몇 점에서만 유의차(p<0.05, p<0.02 표시) — 모델의 분산이 지나치게 작기 때문.
- 모델에서도 전진면 바로 뒤에 여러 정맥이 생겼다가 하나만 남는다(그림 4.3b).

**파라미터 변화 1: k = 0 (p.54–55, 그림 4.6)** — 관 → 전진면 결합 제거
- "the shape of the growth front does not any longer depend on the state of the tube network."
- 결과: 주 정맥이 최단 경로 쪽으로 훨씬 붙고 실험과 더 많은 지점에서 달라진다. 그러나 centre-in-centre 는 여전히 보인다 — "vein network formation still occurs in close temporal and spatial connection to the growth front extension. Therefore, the position of the emergence of the main vein is still mainly guided by local information. But we learn that the shape of the network sensitively depends on the specific shape of the growth front."
- 즉 전진면은 k = 0 이어도 스스로 전진한다(전진 자체는 유량과 무관).

**파라미터 변화 2: τ2 감소 (p.55–57, 그림 4.7)** — 전진면을 관 형성보다 훨씬 빠르게
- τ2 를 줄이면 전진 속도 증가. τ1 도 같이 줄여 τ1/τ2 비(=탐색 완료까지 수축파 수)는 유지.
- 그림 4.7 에 적힌 값: 표준 τ2 = 20, 분리 조건 τ2 = 2.
- 결과: "the main veins do not any longer emerge shortly behind the growth front ... The main vein does now not exhibit the centre-in-centre trajectory, but runs alongside the inner boundary between the two 90° turns." → Physarum Solver 와 같은 전역 최단 경로로 되돌아간다.
- 해석(p.56): "in this situation the network is forming in a globalised hydrodynamic regime, that is, with most of the arena's geometry accessible to the developing network" → centre-in-centre 는 "a product of local optimisation in the tight interplay between growth front and tube network dynamics".

**해석 (4.1.5, p.56)**
- "instead of allowing the tube network to develop over the whole space at once, the growth front grants access to the network only gradually; or, vice versa, instead of letting the growth front propagate freely, its speed was limited to the developmental time scale of the tube network."
- "the organism couples the development of its vein network to the extension of the growth front such that current-reinforcement-based optimisation can work locally, while still allowing for the rapid construction of a tube network."

### 1.6 4.2절 단순 알고리즘 (p.58–66)  [질문 (e)]
입력: 전진면 위치의 시간열만(실험 영상에서 추출). 출력: 주 정맥 궤적 예측.
규칙(원문 p.58–61, 그림 4.9):
1. 전진면 정의: "The wave front is defined as the largest set of newly occupied pixels in each frame."(그림 4.9 설명) — 프레임 간격 ΔT 마다의 전진면 곡선 F_0 … F_M.
2. 정방향 서술: 연속한 두 전진면에 대해, 나중(새) 전진면의 각 점에서 이전(옛) 전진면의 **가장 가까운 점**으로 직선을 긋는다. 근거: 전진 중에 다수의 proto-channel 이 대략 직선으로 바깥을 향해 생긴다 [29].
3. 모든 연속 쌍에 반복한 뒤, **맨 마지막(최신) 전진면에서 맨 처음(최고령) 전진면까지 끊기지 않고 이어지는 연결만** 남긴다. 근거: 막다른 관은 흐름을 잃어 퇴화하고, 끝에서 끝까지 잇는 관만 흐름을 받아 굵어진다.
4. 계산 단순화(역시간 구현): 최신 전진면 F_M 의 모든 점에서 F_{M−1} 로 최단 직선을 구한다. 다음 단계부터는 **직전 단계에서 도착한 점들만** 출발점으로 삼아 F_{m} → F_{m−1} 최단 연결을 구한다(m = M … 1). 결과는 정방향과 같다.
5. 보통 정맥 하나만 남는다. 전진면 바로 뒤의 "여러 평행 정맥 → 몇 개의 굵은 정맥 → 하나"로 합쳐지는 분기 패턴도 재현(p.61).
수치:
- 촬영 3분 간격. 본문 결과는 ΔT = 9분(3장마다 1장, 3가지 부분열을 겹쳐 그림). n = 8 중 1개만 세 예측이 어긋남(그림 4.12).
- 예측 정맥–실제 정맥 평균 거리는 최단 경로–실제 정맥 평균 거리의 절반 미만(그림 4.11).
- ΔT 가 너무 작으면 2차 정맥이나 일시적 주 정맥을 집어냄. 너무 크면(>30분) 정확도 하락. 중앙값 최소는 약 15분이나 표본 간 변동이 커서 유의차 없음 — "we could not establish a single time interval ∆T (≤30min) yielding the best result for all studied samples."(p.65)
- 정맥이 여러 개 남는 곳: 전진면 바로 뒤, 그리고 전진면이 넓은 호로 퍼진 곳(모퉁이에서 새 방향이 열릴 때). "if the angle of aspect of the growth front is large from a given distance from it, local path length minimisation will require more than one end point." 전진면이 멀어지고 다시 모이면 경로 수가 줄어든다. 때로 (보통 2개) 평행 정맥이 오래 살아남음 [43].

### 1.7 5장 Outlook (p.67–69)
- 세 과정: 단방향 전진면 확장, 액토미오신 수축에 의한 세포질 유동, 몸 안쪽에서의 정맥망 형성. "the vein network formation depends on both the contraction waves and the growth front expansion, while the latter requires advection of protoplasm which also destabilises the wave propagation [70, 12]."
- 정적 모델(Solver)에서는 먹이가 몸 질량의 끌개여서 방향성 흐름을 만든다. 자연 상태(탐색)에서는 "it is the expansion of the growth front, in particular the sol-gel transformation, that acts as the body mass sink causing a directional flow." → 전류 강화의 이점은 주로 효율적 공간 탐색에 있다는 주장.
- 수치 모델은 생리 파라미터에 묶여 있어 "does not enjoy wide applicability". 반면 알고리즘은 "the local minimisation of connections and the pruning of globally disadvantageous connections due to their carrying less flow" 라는 일반 원리 — 도로망, 뿌리, 균사 등 "flow-responsive networks that form within an expanding domain" 에 적용 가능성 제기(검증은 없음).

### 1.8 그림에서 직접 본 것 (PNG 로 확인)
- 그림 4.1 (p.48, PDF 57쪽): FreeFEM++ 비정형 삼각 격자. 통로 폭 방향으로 노드가 대략 10–12개(눈으로 센 값). Ω0 는 통로 한쪽 끝의 얇은 띠(격자 한 칸 폭 정도). U자·뱀 모양 두 경기장.
- 그림 4.2 (p.50, PDF 59쪽): (a) 통로 안에서 전진면은 진행 방향으로 볼록한 호, 그 뒤에 주 정맥에서 전진면으로 갈라지는 가지들, 뒤쪽에서 오는 수축파. (b) x 방향 단면: u 는 뒤에서 높고(그림상) 전진면에서 움푹 꺼졌다가 앞쪽에서 다시 높음, v 는 전진면에 국한된 단일 봉우리, w 는 뒤쪽 고원에서 전진면을 지나며 0 으로 단조 감소. w_th 선이 w_in 선 바로 위에 있어 Γ = 1 영역(관 성장 허용)은 v 봉우리의 뒤쪽 가장자리에서 끝난다 — 관은 전진 띠보다 뒤에서만 굵어진다.
  - 주의: u 가 펄스 뒤에서 다시 높게 그려져 있다. (4.1a)에 공급항이 없으니 식대로라면 뒤쪽 u 는 소모된 채여야 한다. 그림이 개념도인지 식에 빠진 항이 있는지 학위논문만으로는 판단 불가(미확인).
- 그림 4.3 (p.51, PDF 60쪽): (a) 실험 429/543/726분. (b) 모델 t = 800/1040/1280(모델 시간 단위). 굵은 선 = 전진면(통로 폭을 가로지르는 볼록한 톱니 호), 회색 점 = v 가 있는 성장대(전진면 뒤로 대략 통로 폭 1개 깊이의 띠), 실선 = 정맥. 전진면 뒤에 정맥 2–4가닥이 부채살처럼 갈라져 있고 뒤로 가며 한 가닥으로 합쳐진다. 접종 끝에는 Y자 갈래가 남아 있다.
- 그림 4.4 (p.53, PDF 62쪽): U자에서 모델 평균 궤적(실선)이 실험 표준편차 띠 안. 두 모퉁이 사이 구간에서 정맥이 안쪽 벽에서 떨어져 중심으로 복귀. 눈금 5 mm.
- 그림 4.7 (p.57, PDF 66쪽): τ2 = 20(표준)에서는 전진면 바로 뒤에 여러 정맥이 생겨 곧 하나로. τ2 = 2 에서는 전진면보다 한참 뒤에야 평행한 정맥 여러 가닥이 나타나고 최종 궤적이 안쪽 벽에 붙는다.
- 그림 4.9 (p.60, PDF 69쪽): 전진면 곡선 (M−6)ΔT … MΔT 와, 최신 전진면의 여러 점에서 수직에 가깝게 뻗은 예측선들이 뒤로 가며 한 가닥으로 합류하는 모습. 격자 화소 = 새로 점유된 화소(명암으로 시각 구분).
- 그림 3.10 (p.38, PDF 47쪽): U자 경기장 전체에 깐 삼각 격자 + 양 끝 소스/싱크 노드. Solver 결과 정맥(노란 선)은 두 모퉁이 사이에서 안쪽 벽에 딱 붙은 직선.
- 그림 4.10 (p.62, PDF 71쪽): 뱀 모양 경기장 실험 5장(눈금 10 mm). 실제 전진면은 통로 폭을 다 채우는 물결 모양 부채(여러 개의 둥근 엽). 알고리즘 예측선은 전진면 바로 뒤에서 **부채살 모양 다발**(수십 가닥)로 시작해 통로 폭 1–2개 뒤에서 한 줄기로 합쳐진다 — 알고리즘만으로 "부채꼴 전진면 뒤의 수렴하는 나무"가 나온다(고리는 없음).

### 1.9 저자가 밝힌 한계·실패 (원문 근거)  [질문 (f)]
1. u 가 몸 밖에도 미리 높은 농도로 존재한다는 가정: "This certainly is not a realistic situation."(p.42)
2. 전진면 모델의 변수·파라미터가 무엇인지 불분명: "its variables and parameters are not well defined and the model remains a phenomenological one at this level."(p.43)
3. 전진면을 뒤쪽과 독립으로 둔 것은 "enough body mass is present for the organism to extend throughout the whole of the available arena space" 라는 전제 위에서만 타당(p.42). 즉 질량 제약이 없다.
4. 관망은 "pre-defined grid" 에 미리 깔려 있고(지름 0), 개체 안에서만 굵어지게 한 것은 "a rather technical point"(p.47).
5. τ1, τ2 절대값은 결과가 실물과 "visually resembles" 하도록 고름(p.47). 관 형성 시간 척도는 "difficult to calculate and may, in fact, have multiple time scales"(p.52).
6. 둘째 모퉁이에서 실험과 유의차(모델 분산이 지나치게 작음)(p.52, 그림 4.4).
7. 모델은 "highly complex (even though very incomplete)"(p.56). 생리에 묶여 있어 범용성 없음(p.68).
8. 알고리즘은 실험의 전진면 이력을 입력으로 받는다 — 전진면 자체를 예측하지 않는다(p.41: "these predictions are based on the input of some experimental data, specifically, the growth front history").
9. 알고리즘 실패: ΔT 가 작으면 2차/일시 정맥을 집음. 8개 중 1개 표본에서 세 부분열 중 하나가 셋째–넷째 모퉁이 사이에서 이탈(그 선은 실제로 잠깐 있었다가 해체된 2차 정맥을 따라감). 최적 ΔT 를 하나로 정할 수 없음(p.61, 65).
10. 실험·모델 모두 폭 5 mm 통로(사실상 1차원 전진), 먹이 없음. 열린 평면에서의 부채꼴 전진·먹이 연결은 다루지 않는다(p.24: "we basically restrict the organism to one-dimensional extension").
11. 효율 분석(3.1.4)은 "very superficial"(p.33).

---
## 2. Schenz, Shima, Kuroda, Nakagaki, Ueda 2017, J. Phys. D: Appl. Phys. 50(43):434001 — 본문 접근 실패(초록·서지·참고문헌 목록만)

- 접근 URL: https://iopscience.iop.org/article/10.1088/1361-6463/aa88e9 (HTTP 200, HTML 19만 바이트). 로컬: .../research/dl2/schenz2017-iop/
- 결과: **프록시 차단이 아니라 구독 장벽**. 페이지 문구: "The computer you are using is not registered by an institution with a subscription to this article." `/pdf` 는 같은 HTML(구독 안내)을 돌려주고, `/xml` 은 사이트가 403 "Forbidden" 을 돌려줌. 허용 목록에 호스트를 더해도 본문은 열리지 않는다(기관 로그인 또는 저자 최종본 필요).
- 공개본 탐색: HUSCAP 옛 검색 경로(/dspace/simple-search)는 404(저장소가 /repo/huscap/ 로 이전). 웹 검색에서도 공개 전문은 찾지 못함.
- 페이지에서 확인한 사실: 접수 2017-02-16, 수리 2017-08-29, 게재 2017-09-28. 저자 소속(Schenz: Hokkaido Univ. 생명과학원, Shima·Ueda: Univ. of Toyama, Kuroda·Nakagaki: Hokkaido RIES). 교신: Ueda.
- 초록 요지(원문): 폭이 일정한 통로를 지나게 함 → 모퉁이에서 centre-in-centre 주 정맥 → "a new algorithm that can predict the main vein's position from the frontal tip's progression" → "a numerical model that incorporates reaction-diffusion dynamics for the behaviour of the organism's growth front and current reinforcement dynamics for the formation of the vein network in its wake, as well as interactions between the two" → "studying variants of the model".
- 참고문헌 목록(페이지 메타데이터, 39건)에 Rideout & Dick 1967, Smith & Saldana 1992, Smith 1994, Hecht(FreeFEM++) 2012, Yamada et al. 2007, Ueda et al. 2011(PRE 83:021916), Akita et al. 2017(Murray), Sesaki & Ogihara 1997, Hasegawa 1980, Kobayashi 2006 이 있음 → 학위논문 4장과 같은 구성 요소.
- **학위논문과의 차이(확인 가능한 범위)**: 본문을 읽지 못해 식·파라미터 대조는 못 함(미확인). 학위논문 쪽 표시로 보면 그림 3.4, 4.3, 4.8–4.13 은 "From [69]", 그림 3.10, 4.1, 4.2, 4.4, 4.6, 4.7 은 "Modified from [69]", 표 4.1 은 "see also [69]" → 4장 내용은 2017 논문과 사실상 같은 모델로 보인다. 학위논문에만 있는 것으로 보이는 부분: 2장의 Smith-Saldana 3변수 분석(그림 2.6–2.8), 3.1.4 효율 분석(w = 0.167), 그림 3.11(centre-in-centre 정의 6가지), 그림 4.5(흡광도 195 s, 출처 표시 없음). 초록 순서는 2017 논문이 "알고리즘 → 수치 모델", 학위논문은 "수치 모델 → 알고리즘".

---
## 3. 내가 한 재현 계산 (원문에 없는 것. 인쇄된 식과 표 4.1 값을 그대로 넣어 확인)

스크립트: .../research/work-schenz/gs1d.py, osc0d.py, osc0d_b.py

**3.1 전진면 (4.1a–c) 1차원** (dx = 0.02, 양해법, u0 = 3, 왼쪽 끝 폭 1 구간에 v = 1)
- 진행파가 생긴다. 속도 ≈ 0.0076 길이/시간(τ2 = 20 기준, 즉 τ2 로 나눈 시간으로는 ≈ 0.15). v 최댓값 ≈ 2.9–4.6(천천히 감소), 전진면 뒤 u ≈ 0(완전 소모).
- v 는 뒤쪽으로 매우 긴 꼬리(감쇠율 α1/τ2 = 0.0005/시간 → e-감쇠 2000 시간 단위). 전진면에서 8 길이 단위 뒤에도 v ≈ 2.2.
- w 는 단조 증가: 전진면(v = 0.5 등고선)에서 0.1 뒤 w ≈ 0.1(=w_ext), 0.4 뒤 0.41, 1.0 뒤 1.5, 2 뒤 3.4, 8 뒤 14.5. 최종값은 대략 α2·u0/α1 = 30 까지 간다. → w_th = 1.0 은 전진면에서 약 0.7 길이 단위(약 95 시간 단위) 뒤에서 넘는다. B(w) 띠(0.1–0.9)는 전진면 뒤 0.1–0.65 구간.
- 그림 4.3b 의 프레임 시각(t = 800, 1040, 1280)과 전진 거리로 어림하면 통로 폭 하나를 지나는 데 110–135 시간 단위 → **통로 폭 ≈ 0.85–1.0 모델 길이 단위(추정)**, 격자 간격 ≈ 0.1(추정). 그러면 관이 굵어지기 시작하는 곳은 전진면에서 통로 폭의 약 0.7배 뒤.
- 시간 척도 비교(추정): 관 완화 1/r = 6.7 시간 단위 ≪ 전진면이 통로 폭을 지나는 시간 ≈ 120 시간 단위(비 ≈ 0.05). τ2 = 2 로 바꾸면 비 ≈ 0.5 — 이때 모델이 전역 최단 경로로 되돌아간다(그림 4.7).

**3.2 수축 진동자 (4.3) 0차원**
- 인쇄된 식 그대로(KQ = kQ·K*nc/(1 + K*nc), 지수 없음)와 표 4.1 값으로는 **진동하지 않는다**: c → 3.49, φ → 0.85 의 안정 고정점.
- (2.7)의 Hill 지수 β 를 넣어 `KQ = kQ (K* nc/(1+K* nc))^β` 로 하면: β = 4, K* = 1.75 에서 c ∈ [5.86, 7.86], **평균 6.98 ≈ c̄ = 7.0**, 주기 140.9(τ1 = 1 단위) → 모델 시간으로 본체 1.01, Ω0 0.34. β = 1, 2 는 무진동, β = 3 은 K* = 1.5 에서만 약하게 진동.
- 해석(추정): 실제 구현에는 β = 4 가 들어 있었고 학위논문 4.1.1 의 KQ 식에서 지수가 빠진 것으로 보인다. c̄ = 7.0 은 진동 평균에 맞춘 값이어서 −κ(c − c̄) 가 압력을 한쪽으로 밀지 않게 된다. Smith-Saldana 원문에서 β 값을 확인해야 한다(미확인).

**3.3 식에서 따라 나오는 점 (추정 포함)**
- D 의 평형값: D* = (1/r)·|q|^µ/(1 + a_d|q|^µ), 최댓값 1/(r·a_d) = 667. 작은 유량에서는 D* ≈ |q|^1.3/0.15.
- (4.2a) 의 전도는 ā_r + a_r D = 2.5 + 13.5 D — D = 0 인 간선(개체 밖 포함)도 기본 전도 2.5 를 가진다. (4.2), (4.3)에는 w 에 의한 차단이 없어서, 인쇄된 식대로라면 압력·유량·칼슘은 경기장 전체 격자에서 진화한다(학위논문은 이 점을 명시하지 않음).
- (4.7)은 |q| 를 쓴다. 알짜 흐름이 없어도 왕복 유동만으로 관이 강화된다.
- a_v = 0.01, v ≤ 약 4.6 이므로 (1 + a_v v) ≤ 1.05 — 전진면 "싱크" 항은 용량을 5% 이내로 바꾸는 약한 항이다(내 1차원 계산 기준). 저자는 이것이 전진면 싱크를 만든다고 서술(p.47).

---
## 4. 질문별 답

**(a) 변수·지배식·파라미터·격자·수치 기법·시간 척도** → 1.4절. 요약: 연속층 {u, v, w, c, φ}(FEM, Neumann, FreeFEM++ 비정형 삼각 격자) + 이산층 {q_ij, p_j, D_ij}(같은 격자의 간선·노드). 식 (4.1a–c), (4.2a–c), (4.3), 결합 (4.4)–(4.7), 파동원 (4.8), 표 4.1. 압력은 푸아송 풀이가 아니라 용량을 가진 노드의 시간 적분. 격자 크기·시간 간격·ODE 적분법은 기재 없음.

**(b) 전진면–정맥 결합**
- 소스: 명시적 질량 소스 없음. 유동의 구동원은 칼슘 파동에 의한 압력 강제 −κ(c_j − c̄)(접종 영역 Ω0 가 3배 빠른 페이스메이커). 
- 싱크: 전진면에서 v 가 높아 벽이 물러짐 → 용량 ×(1 + a_v v) → 압력이 낮음. 5장: "the expansion of the growth front, in particular the sol-gel transformation, ... acts as the body mass sink".
- 전진면 전진은 유량에 의존하는가: **기본적으로 독립**. 전진면은 미리 깔린 u 를 태우며 스스로 나아가는 Gray-Scott 펄스다. 관의 영향은 kB(w)D̃ 항(전진 띠 노드에 전도도 합에 비례한 v 주입)뿐이고, 유량 q 는 직접 들어가지 않는다. k = 0 이어도 전진한다.
- 질량 보존: **없다**. w 는 v 의 시간 적분으로 단조 증가하며 관망의 유체량과 연결되지 않는다. 저자도 "enough body mass is present" 를 전제로 둠.
- 정맥 쪽은 전진면에 강하게 종속: Γ(w) 로 전진면이 지나간 곳에서만 관이 굵어진다.

**(c) 부채꼴은 창발하는가**: 아니다. 실험·모델 모두 폭 5 mm 통로에서 사실상 1차원 전진이고, 전진면 모양은 통로 폭 + RD 펄스 + (관 끝에서의 v 주입에 의한 국소 돌출)로 정해진다. 열린 평면에서 부채꼴(한쪽으로만 나아가는 호)이 스스로 생기는 규칙은 이 모델에 없다. 방향성은 "한쪽 끝에서 시작해 통로를 따라간다"는 초기·경계 조건에서 온다. 다만 "전진면 모양이 관망 배치를 민감하게 결정한다"(k = 0 실험)는 것과, 알고리즘 그림 4.10 처럼 전진면이 부채면 그 뒤에 수렴하는 나무가 자동으로 생긴다는 것은 확인된다.

**(d) "전류 강화만으로는 부족"**: 다 덮인 U자 경기장에 Solver(전류 강화 + 양 끝 소스/싱크)를 돌리면 전역 최단 경로(안쪽 벽에 붙음)가 나와 실험의 centre-in-centre 와 다르다(그림 3.10). 추가된 요소: (1) 전진면이 영역을 점진적으로 열어 줌(Γ(w)), (2) 무작위 소스/싱크 대신 수축파로 유동 생성, (3) 전진면을 싱크로(벽 연화), (4) 소스·싱크 불균형을 흡수하는 팽창성 관(관성·용량), (5) 관 → 전진면 되먹임(v 주입), (6) 시간 척도 맞춤(전진면이 관 형성보다 너무 빠르면 다시 전역 최단 경로).

**(e) 단순 알고리즘** → 1.6절. 새 전진면의 각 점 → 직전 전진면의 최근접점으로 직선, 최신 전진면까지 이어지는 사슬만 남김. 역시간으로 구현. ΔT 9–15분.

**(f) 한계·실패** → 1.9절.

---
## 5. 우리 모델(TheBlob)에 주는 시사점

1. Schenz 모델은 "전진면과 정맥의 결합" 문제를 풀지 않았다. 전진면은 연료가 미리 깔린 자율 펄스이고 질량 보존이 없다. 부채꼴 창발 규칙을 여기서 그대로 가져올 수는 없다.
2. 그래도 결합 틀은 쓸 수 있다: (가) 관 성장은 전진면 띠보다 조금 뒤에서만 허용(Γ(w), w_th > w_int). (나) 싱크는 전진 띠 전체에 분산(우리 푸아송 틀에서는 S ∝ −dw/dt, 즉 새 몸이 흡수하는 부피율로 두면 질량 보존형이 된다). (다) 관 → 전진면 되먹임은 전진 띠 안에서만(B(w)), 관 끝이 닿는 곳의 전진을 밀어 줌. Schenz 는 Σ D 에 비례시켰지만, 우리는 도착 유량에 비례시키는 편이 보존과 맞는다.
3. 2.2.3절의 절단 실험이 질량 보존형 전진 규칙의 근거가 된다: 전진면은 공급이 끊겨도 약 10분은 같은 속도로 가고, 얇아지다가 약 20분에 멈춘다. → "전진 속도는 단기적으로 공급과 무관, 전진은 국소 두께를 소비, 두께는 정맥 유입으로만 보충, 두께가 문턱 아래면 정지" 규칙. 정맥이 닿는 엽만 계속 나아가므로 부채 선택이 여기서 나올 수 있다(내 제안. 원문에 없음).
4. 시간 척도 규칙: 관 전도도 완화 시간(1/r) 동안 전진면이 나아가는 거리가 전진 띠/몸 폭보다 훨씬 작아야(추정 비 ≈ 0.05) 전진면 바로 뒤에서 국소적으로 정맥이 골라진다. 비가 0.5 정도면 몸 전체가 다 찬 뒤 전역 최단 경로로 정리된다. 실험값: 정맥 형성 e-시간 195 s, 주 정맥은 전진면 통과 약 50분 뒤 확정, 수축 약 600회/탐색(15±4 h → 약 90 s/회).
5. 강화 함수는 포화형 `|q|^µ/(1 + a_d|q|^µ) − rD`, µ = 1.3(실험 4/3), a_d = 0.01, r = 0.15. 포화가 있으면 유량이 큰 전진면 근처에서 여러 정맥이 공존하고 뒤로 갈수록 하나로 줄어든다. 우리의 순수 초선형 강화에 포화를 더할 근거.
6. |q| 를 쓰므로 왕복(맥동) 유동만으로도 강화된다. 뒤쪽 페이스메이커(3배 빠른 진동자)에서 전진면으로 가는 수축파 + 노드 용량이 있으면, 한 관을 지나는 왕복 유량은 그 하류 용량(먹여 살리는 면적)에 비례한다 → 줄기가 굵은 위계 나무. 목표 (3)(맥동·왕복 흐름)과 (2)(위계)가 한 기작으로 묶인다(해석은 내 추론).
7. 구현 면: Schenz 는 전역 선형 풀이를 하지 않는다. `dq/dt = (Δp − R̃q)/Ĩ`, `dp/dt = Σq/C̃ − κ(c − c̄)` 는 이웃만 보는 양해 갱신이라 텍스처 2장(p, q)으로 GPU 에 올리기 쉽고, 소스·싱크가 안 맞아도 발산하지 않는다(용량이 흡수). 우리 전역 압력 풀이의 대안.
8. 4.2 알고리즘은 값싼 정맥 생성 규칙이 된다: 도착 시각장 T(x) 를 텍스처로 저장 → 현재 전진면의 각 점에서 T 가 줄어드는 쪽(직전 전진면의 최근접점)으로 따라 내려가며 누적(하천 유역 누적과 같음) → 누적량으로 굵기. 현재 전진면과 이어지지 않는 가지는 소멸. 부채꼴 전진면이면 수렴하는 나무가 바로 나온다. 고리·먹이 연결은 못 만든다.
9. 주의: (4.3)을 인쇄된 대로 옮기면 진동하지 않는다(3.2). Hill 지수 4 를 넣거나 더 단순한 진동자(예: FitzHugh-Nagumo, 위상 진동자)로 바꿀 것. w 를 "두께"로 그대로 쓰면 30 까지 자라므로 표시용으로 부적합.
10. 이 논문이 다루지 않는 것: 열린 평면의 부채꼴, 고리, 먹이 사이 연결, 점액 기피, 부피 보존. 이 목표들은 다른 문헌에서 가져와야 한다. 전진면 모델의 원전은 Ueda, Takagi, Nishiura, Nakagaki 2011 PRE 83:021916 과 Takagi et al. 2007 이다(여기서는 읽지 못함).

---
## 6. 접근 기록
| 대상 | 결과 | 원인 |
|---|---|---|
| 학위논문 PDF (HUSCAP) | 전문 읽음 | 이미 받아 둔 파일 |
| iopscience.iop.org/article/10.1088/1361-6463/aa88e9 | 초록·메타데이터만 | 구독 장벽(프록시 차단 아님). /pdf 는 구독 안내 HTML, /xml 은 사이트 403 |
| eprints.lib.hokudai.ac.jp/dspace/simple-search | 404 | 옛 검색 경로 폐지(저장소 이전) |
| journals.aps.org (Ueda 2011 PRE) | 연결 거절 | 프록시 정책 거절(CONNECT 403) |
| doi.org | 연결 거절 | 프록시 정책 거절(CONNECT 403) |
| www.biorxiv.org | 연결 거절 | 프록시 정책 거절(CONNECT 403) |
프록시 상태 기록(/__agentproxy/status, 20:54–21:01 UTC, 이 세션의 앞선 요청들)에는 다음 호스트도 "gateway answered 403 to CONNECT (policy denial or other refusal)" 로 남아 있다: www.sciencedirect.com, uwe-repository.worktribe.com, ora.ox.ac.uk, europepmc.org, www.ncbi.nlm.nih.gov, eutils.ncbi.nlm.nih.gov, cdn.ncbi.nlm.nih.gov, journals.biologists.com, link.springer.com, www.ebi.ac.uk, api.crossref.org, api.unpaywall.org, mediatum.ub.tum.de, hal.science, escholarship.org, www.bpm.ph.tum.de. (이 기록은 사이트의 봇 차단이 아니라 프록시 단계의 거절이다. 이후 허용 목록이 바뀌었는지는 다시 시험하지 않았다.)
