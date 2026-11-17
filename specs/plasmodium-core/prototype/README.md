# 수치 프로토타입 (numpy)

spec의 지배 식을 그대로 옮긴 CPU 프로토타입. 의존성은 `numpy`, `Pillow`.
각 결과 이미지는 왼쪽이 두께 `h`(음영 포함, 어두운 테두리는 점액 `s`), 오른쪽이 전도도 `D`. 흰 점은 먹이.

```bash
# 순수 연속체: Tero식 전도도 적응
python3 continuum.py 128 20000 c3 '{"m0":0.02,"mD":1.0,"sdep":0.02,"omega":0.1,"q0":0.03,"ps":1.5,"yield0":0.15,"amp":0.6}'

# 하이브리드: 두께장 + 갇힌 Jones 입자 (cap 을 크게 주면 점유 제한 없음)
python3 hybrid.py 160 16000 h2 '{"cap":1e9,"pmin":0.4,"fluxdep":2.0,"npart":5000}'
python3 hybrid.py 288 14000 L1 '{"cap":1e9,"foodr":0.09,"r0":0.2,"mass":2.2,"eat":0.003,"npart":25000,"pfood":1.0,"pslime":0.5,"pmin":0.15}'
python3 hybrid.py 200 12000 M3 '{"foodr":0.1,"r0":0.16,"eat":0.003,"pmin":0.15,"mass":1.3,"npart":4000,"pfood":2.0,"pslime":1.0,"cap":2,"ps":1.5,"t0":4}'
```

인자: 격자 크기, 스텝 수, 출력 접두어, 파라미터 덮어쓰기(JSON).
`result-hybrid-160.png`은 먹이 3개 배치였던 이전 판으로 만든 것이라, 위 명령으로는 먹이 6개 배치로 재현된다.

| 파일 | 내용 | 결과 |
|---|---|---|
| `result-continuum.png` | 순수 연속체 4종 | 원반 + 맥동파. 관이 생기지 않음 |
| `result-hybrid-160.png` | 하이브리드 160², 먹이 3개 | 굵은 관 하나를 따라 몸이 늘어나 먹이에 도달 |
| `result-hybrid-288.png` | 하이브리드 288², 먹이 6개 | 여전히 직선 관 하나. 분기 없음 |
| `result-hybrid-occupancy.png` | 셀 점유 제한 추가 | 입자가 흩어져 관 자체가 생기지 않음 |
