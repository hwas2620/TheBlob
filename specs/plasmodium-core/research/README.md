# 원형질체 모델 연구 자료

`spec.md`의 모델 선택을 뒷받침하는 조사·실험 자료.

## lit/ — 문헌 노트
각 노트는 본문을 직접 읽은 것과 초록만 본 것을 구분해 적었다.

| 파일 | 내용 |
|---|---|
| `vein-formation-models.md` | 전진 중 정맥 형성 모델 (arXiv 본문 기준) |
| `jones-extensions.md` | Jones 입자 모델 후속 연구 |
| `continuum-channelization.md` | 연속체 채널화 이론과 실패 진단 |
| `morphology-growth-biology.md` | 형태·성장 모델과 생물학 실측값 |
| `realtime-implementations.md` | 실시간 GPU 구현 사례와 압력 풀이 비용 |
| `schenz-fulltext.md` | Schenz 학위논문(2019) 4장 정독: 전진면 + 관망 + 수축파 결합 모델의 식과 파라미터 |
| `alim-front-fulltext.md` | Marbach 2023, Kramar & Alim 2021, Alim 2013/2017, Kuroda 2015, Oettmeier 2019, Akita 2017, Reid 2012 등 원문 |
| `FULLTEXT-IMPLICATIONS.md` | 위 두 노트의 식 24개를 원문과 대조한 결과와, 원문에 근거하지 않은 주장 목록, 모델 시사점 |

## common/eval_morph.py
모든 실험에 쓰는 공통 형태 채점기 (분기점 수, 고리 수, 굵기 위계, 연결성).

## round2/ — 2차 수치 실험
실험 7개와 독립 검증 6건, 종합 1건. 판정은 전부 "부분 지지"다. **먼저 `round2/SYNTHESIS.md`를 읽는다.**
담당자 자기 평가(`result.json`, `REPORT.md`)보다 검증자 판정(`verification.json`)을 우선한다.

| 폴더 | 물은 것 | 검증 뒤 남은 결론 |
|---|---|---|
| `E1-front-sink-reinforcement` | 전역 압력 풀이 + 간선 전도도 초선형 강화로 분기 정맥이 나오는가 | 나온다(Strahler 5~7, 새 시드 재현). 단 소스가 점일 때만, 몸 윤곽은 미리 준 것, 고리 없음 |
| `E9-solver-feasibility` | 그 풀이를 GPU 예산 안에서 근사할 수 있는가 | 멀티그리드 V(2,2) 1사이클/스텝이면 512²까지 나무 유지(새 시드 재현). Jacobi·저해상도 압력은 실패. 750² 이상과 WebGL 실측은 없음 |
| `E7-flux-driven-front` | 전진면을 미리 정하지 않고 부피 보존으로 스스로 나가게 할 수 있는가 | 시트 전진면 + 뒤따르는 정맥 + 마른 흔적이 나온다. 이주는 나이 수축 규칙이 만든다. 격자 방향 잠김 있음 |
| `E10-pulsation-front` | E7에 맥동을 넣어도 유지되는가 | 맥동·왕복 유량·계단식 전진이 나오고 뒤쪽 정맥이 굵어진다(새 시드 재현). 한 방향 이주는 먹이 구배가 있을 때만, 정맥이 조각남 |
| `E8-implicit-thickness` | 음함수 두께 모델 하나로 통합되는가 | 대표 실행은 재현. 침투 깊이 문턱 주장과 "Jacobi로도 된다"는 주장은 반박됨 |
| `E6-shuttle-flow-loops` | 왕복 유량이 고리를 만드는가 | 파 방향이 둘 이상이거나 바뀔 때만 고리. 고리는 가늘고 시드 의존. 몸은 고정 마스크 |
| `E2-jones-at-scale` | Jones 입자가 큰 스케일에서 그물을 유지하는 조건 | 칸당 1입자 제한 + 가둠이 필요조건이라는 보고. **독립 검증 없음** |

각 폴더: 코드(`*.py`), 결과 표, 대표 이미지, `result.json`(담당자 보고 전문), `verification.json`(검증자 보고 전문), `verify/`(검증자 스크립트와 그림).
실행별 원자료(`runs/`)는 용량 때문에 넣지 않았다.

주의: `common/eval_morph.py`의 렌더 기반 판정(`all_three`)은 변별력이 약한 것으로 확인됐다. 폭주 중인 실행이나 유량이 거의 없는 대조도 통과한다. 정맥 판정은 간선 그래프 지표(각 `verify/`의 스크립트)로 한다.
