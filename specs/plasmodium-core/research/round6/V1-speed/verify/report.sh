#!/bin/bash
# [검증자] 끝난 실행의 요약(vsum.py)을 만들고 블록별 표(ana.py)를 찍는다. 여러 번 돌려도 된다(summ/ 은 캐시).
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
done_runs() { for n in "$@"; do [ -f runs/$n/metrics.json ] && echo $n; done; }
S1="61 62 63 64 65 66"
YM=$(done_runs $(for s in $S1; do echo Ym_base_s$s Ym_cand_s$s; done) YmL_base_s92 YmL_cand_s92 Mx_base_s81 Mx_cand_s81 Ym_base_s61k7 Ym_cand_s61k7)
FD=$(done_runs $(for s in $S1; do echo Y3_base_s$s Y3_cand_s$s; done) Y3_ctrl_s61 Y3_ctrl_s62 Yx_base_s82 Yx_cand_s82 Yx_base_s83 Yx_cand_s83 Yu_base_s84 Yu_cand_s84 \
     A3_base_s71 A3_cand_s71 A3_base_s72 A3_cand_s72 A3_base_s73 A3_cand_s73 S3_base_s74 S3_cand_s74 S3_base_s75 S3_cand_s75 R0_Y3_cand_s21 A3_cand_s101 A3_cand_s102 A3_cand_s103 A3_cand_s104 A3_cand_s105 A3_cand_s106 A3_cand_s107 A3_cand_s108 Y3_base_s61k7 Y3_cand_s61k7)
[ -n "$YM" ] && python3 vsum.py mig $YM > summ_mig.txt 2>&1
[ -n "$FD" ] && python3 vsum.py food $FD > summ_food.txt 2>&1
echo "##### 이주 시험: 실행별"; [ -n "$YM" ] && python3 ana.py mig $YM
echo; echo "##### 먹이 시험: 실행별"; [ -n "$FD" ] && python3 ana.py food $FD
echo; echo "##### 짝 비교"
python3 ana.py pair mig Ym 61,62,63,64,65,66
python3 ana.py pair food Y3 61,62,63,64,65,66
python3 ana.py pair food A3 71,72,73
python3 ana.py pair food S3 74,75
python3 ana.py pair mig Mx 81
python3 ana.py pair food Yx 82,83
python3 ana.py pair food Yu 84
python3 ana.py pair mig YmL 92
python3 ana.py pair food Y3 61,62 base ctrl
python3 ana.py pair food Y3 61,62 cand ctrl
