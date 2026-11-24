#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표> [덧붙일 설정...]  — 7차 S22(균핵이 몸에서 생기게 + 풀이 정확도) 실행 하나 (numpy, model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S22-form
REF=$D/model
scn=$1; seed=$2; tag=$3; shift 3
W="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9"   # S18 후보 s18w
G="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=200 tip_home=1 tri_rnd=1 mg_deep=1"   # S21 후보 s21gm
case "$tag" in
  s22c)  extra="";;                  # 지금 모델
  s22g)  extra="$G";;                # S21 후보 그대로 (기준)
  s22d)  extra="$G mgdump=100";;     # S21 후보 + 풀이 입력 저장 (10 시간마다)
  s22p)  extra="$G mg_deep=0 mg_pcg=1";;   # S21 후보 + 켤레기울기 풀이 (예전 V 사이클을 앞풀이로)
  s22x)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.8 scl_tgflood=1";;   # S22 후보: 켤레기울기 풀이 + 짙은 곳에서 맺히는 균핵
  x*)    extra="$G";;                # 진단: S21 후보 + 명령줄 덧붙임
  *) echo "bad tag $tag"; exit 2;;
esac
[ "$scn" = "slimeall" ] && extra="$extra T=800"
name=b_${scn}_s${seed}_${tag}
mkdir -p $D/logs
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1200 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra "$@" tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
