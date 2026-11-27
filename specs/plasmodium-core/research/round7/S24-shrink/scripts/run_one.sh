#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표> [덧붙일 설정...]  — 7차 S24(균핵 오그라듦·가운데 두께·먹이 늦음) 실행 하나 (numpy, model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink
REF=$D/model
scn=$1; seed=$2; tag=$3; shift 3
W="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9"   # S18 후보 s18w
G="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=200 tip_home=1 tri_rnd=1 mg_deep=1"   # S21 후보 s21gm
case "$tag" in
  s24c)  extra="";;                  # 지금 모델
  s24v)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5";;   # S23 후보 s23v 그대로 (S24 의 출발점)
  s24a)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5 scl_dord=2 scl_dtn=170 scl_dtf=30 scl_tgcap=3 scl_tggrow=1";;   # S24 후보: s23v + 바깥을 몸 따라 먼 칸부터 차례로(마름 시각 30~170) + 방울 모양 무게 3 + 자리 고리 넓히기
  s24b)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5 scl_dord=5 scl_dtn=120 scl_dtf=20 scl_tgcap=3 scl_tggrow=1 scl_rstep=1 scl_hstep=25 scl_hcol=1";;   # S24 둘째 후보: s23v + 거리 순위 마름 시각(20~120, 그 전엔 안 마름·지나면 가장자리 거둠) + 거두기 묶음 풂 + 구멍 한 색씩 천천히 + 방울 무게 3 + 고리 넓히기
  s24d)  extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5 scl_dord=6 scl_dtn=120 scl_dtf=20 scl_tgcap=3 scl_tggrow=1 scl_rstep=1 scl_hstep=25 scl_hcol=1";;   # S24 셋째 후보: s24b 에서 몸을 따라 잰 거리를 실제 길이로(대각선 √2, scl_dord=6)
  y*)    extra="$G mg_deep=0 mg_pcg=1 scl_disc=0 scl_star=0 scl_freeze=0 scl_Hramp=0 scl_nofis=1 scl_tgt=5 scl_tgfrac=0.7 scl_tgq=2 scl_tgmin=1.2 scl_tgflood=1 scl_tgs2=10 scl_tgfrac=0.8 scl_hole=4 tip_fed=1 tip_fage=60 mg_guard=2 mg_kadapt=0.2 mg_kmax=4 scl_tgcap=1 scl_tgfill=3.5";;   # 진단: s23v + 명령줄 덧붙임
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
