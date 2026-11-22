# 실행 시작 뒤 바꾼 것

바꿔도 CRITERIA.md 의 판정 문턱과 정의는 그대로다.

## 1. `scripts/vrun.py` — 끼워 넣은 함수의 인자 (2026-11-22 12:03 UTC, 같음 시험 중)

- 무엇: 같음 시험(시드 220, T=40)의 `vrun.py` 실행이 t=40 에서 멈췄다. `graphm.full` 이 안에서 `quick(S, cthr)` 를 부르는데,
  모듈 이름을 바꿔 끼웠으므로 그 부름도 내 함수로 왔고, 내 함수는 인자를 하나만 받았다.
- 고침: 인자가 둘 이상이면 본래 `graphm.quick` 로 그대로 넘긴다 (`def hook(S, *a, **kw): if a or kw: return orig(S, *a, **kw)`).
  재는 것과 저장하는 것은 바뀌지 않는다.
- 같음 시험은 고친 뒤 다시 돌린다.
- 다시 돌린 결과 (12:05 UTC): `export_ref.py` (tag v15kt0) 와 고친 `vrun.py` (tag v15k) 의 끝 `h.npy`, `wet.npy`, `C_edges.npy`, `age.npy`, `sage.npy`, `theta.npy`,
  `series.npz` 가 비트 단위로 같았다. t=40 의 `vs_t0040.npz` 와 `lv_t0040.npz` 의 h, wet, C 도 같다. 그래서 long 은 계획대로 `vrun.py` 로 돌린다.
  같음 시험에 쓴 실행은 3개(하나는 위의 오류로 멈춤)다. 시드 220 은 판정에 쓰지 않는다.
- 고친 `vrun.py` 의 sha256 은 아래에 따로 적는다 (criteria_sha256.txt 의 값은 고치기 전의 것이다).
- vrun.py (고친 뒤) sha256: 643c5791ca24402c2383f81729533060833a2e015988d1e5d7f92253864bf96c
