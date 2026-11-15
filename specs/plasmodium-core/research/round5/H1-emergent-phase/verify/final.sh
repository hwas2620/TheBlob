#!/bin/bash
# [verify5] 내 실행 전체의 요약과 집계를 한 번에. 출력은 out_*.txt
cd "$(dirname "$0")"
S=41,42,43,44,45,46
YM=$(for v in base wave tri; do for s in 41 42 43 44 45 46; do echo Ym_${v}_s$s; done; done)
Y3=$(for v in base wave tri; do for s in 41 42 43 44 45 46; do echo Y3_${v}_s$s; done; done)
python3 vsum.py mig $YM Ym_trirev_s41 Ym_trirev_s42 > out_vsum_mig.txt 2>&1
python3 vsum.py food $Y3 Y3_triP48_s41 Y3_triP48_s42 Y3_triP48_s43 Y3_triT320_s41 Y3_trio24_s41 > out_vsum_food.txt 2>&1
python3 agg.py . $S base wave tri > out_agg.txt 2>&1
python3 agg.py . 41,42,43 base wave tri triP48 trirev triT320 trio24 > out_agg_extra.txt 2>&1
(python3 pair.py . $S tri wave; python3 pair.py . $S tri base; python3 pair.py . $S wave base) > out_pair.txt 2>&1
python3 delay.py . $S wave tri > out_delay.txt 2>&1; python3 delay.py . 41,42,43 trirev triP48 triT320 trio24 >> out_delay.txt 2>&1
(python3 side2.py . $S Ym base wave tri; python3 side2.py . $S Y3 base wave tri; python3 side2.py . 41,42,43 Y3 triP48 triT320 trio24; python3 side2.py . 41,42 Ym trirev) > out_side.txt 2>&1
python3 aniso.py . mig $YM Ym_trirev_s41 Ym_trirev_s42 > out_aniso_mig.txt 2>&1
python3 aniso.py . food $Y3 Y3_triP48_s41 Y3_triP48_s42 Y3_triP48_s43 Y3_triT320_s41 Y3_trio24_s41 > out_aniso_food.txt 2>&1
(for T in 40 60; do echo "--- t=$T"; python3 reach.py . $T $S base wave tri; done; echo "--- 추가 변형 t=60 (시드 41)"; python3 reach.py . 60 41 base tri trio24 triP48 triT320) > out_reach.txt 2>&1
python3 m2v.py $YM Ym_trirev_s41 Ym_trirev_s42 > out_m2v.txt 2>&1
echo done
