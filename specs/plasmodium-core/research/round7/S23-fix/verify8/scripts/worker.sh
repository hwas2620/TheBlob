#!/bin/bash
# verify8 실행 하나: worker.sh SCN SEED TAG [덧붙일 설정…]  (모델 실행 -> 측정 -> 필요하면 디스크 덜기)
M=/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/verify8
CAND="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9 scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=200 tip_home=1 tri_rnd=1 mg_deep=1 mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5"
scn=$1; seed=$2; tag=$3; shift 3
name=b_${scn}_s${seed}_${tag}
avail=$(df --output=avail -k / | tail -1)
if [ "$avail" -lt $((1300*1024)) ]; then echo "$(date -u +%FT%TZ) SKIP_DISK $name avail_kB=$avail" >> $V/jobs_log.txt; exit 0; fi
cfg=""; [ "$tag" = v8v ] && cfg="$CAND"
echo "$(date -u +%FT%TZ) START $name $*" >> $V/jobs_log.txt
cd $M && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 export_ref.py b $scn $seed $cfg "$@" tag=$tag > $V/logs/$name.log 2>&1
rc=$?
echo "$(date -u +%FT%TZ) END $name rc=$rc" >> $V/jobs_log.txt
OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 $V/scripts/measure.py $M/runs/$name $V/data >> $V/logs/measure_$name.log 2>&1
echo "$(date -u +%FT%TZ) MEASURED $name rc=$?" >> $V/jobs_log.txt
avail=$(df --output=avail -k / | tail -1)
if [ "$avail" -lt $((2000*1024)) ]; then      # 디스크가 2G 아래면 측정이 끝난 이 실행의 vs 파일을 100 시간 간격과 마지막만 남긴다
  last=$(ls $M/runs/$name/vs_t*.npz | sort | tail -1)
  for f in $M/runs/$name/vs_t*.npz; do t=$(basename $f .npz); t=$((10#${t#vs_t})); [ $((t % 100)) -eq 0 ] || [ "$f" = "$last" ] || rm -f "$f"; done
  echo "$(date -u +%FT%TZ) THINNED $name avail_kB=$avail" >> $V/jobs_log.txt
fi
