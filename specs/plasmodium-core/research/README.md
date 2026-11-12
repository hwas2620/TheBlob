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
실험별 코드, 결과 표, 담당자 보고(`result.json`), 대표 이미지. 독립 검증 결과가 붙기 전의 것은 담당자 자기 평가다.
