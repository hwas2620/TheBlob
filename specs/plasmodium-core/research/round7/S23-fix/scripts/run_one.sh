#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표> [덧붙일 설정...]  — 7차 S23(균핵 구멍·자유 꼬리·드문 풀이 오류) 실행 하나 (numpy, model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix
REF=$D/model
scn=$1; seed=$2; tag=$3; shift 3
W="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9"   # S18 후보 s18w
G="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=200 tip_home=1 tri_rnd=1 mg_deep=1"   # S21 후보 s21gm
case "$tag" in
  s23c)  extra="";;                  # 지금 모델
  s23y)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1";;   # S22 후보 s22y 그대로 (기준)
  s23z)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4";;   # S23 후보: s22y + 자리 고르기(σ 10, 0.8, 틈 메우기) + 먹은 몸의 멈춘 실 끝 되감기 + a배 웜스타트·반복 늘리기
  s23w)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1";;   #  S23 둘째 후보: s23z + 방울 모양 두께 (scl_tgcap=1)
  s23v)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5";;   #  S23 셋째 후보: s23w + 가장 작은 자리 넓이 V/3.5 (scl_tgfill=3.5)
  x*)    extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1";;   # 진단: s22y + 명령줄 덧붙임
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
