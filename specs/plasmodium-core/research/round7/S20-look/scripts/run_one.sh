#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S20(겉모습 다듬기) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S20-look
REF=$D/model
scn=$1; seed=$2; tag=$3
W="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9"   # S18 후보 s18w
MIR='foods=[[-27,70]]'      # 이주 유인원을 거울 자리(−27°)에
case "$tag" in
  s20c)   extra="";;                                   # 지금 모델
  s20y)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50";;                                # S19 후보 s19y
  s20t)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1";;                  # + 실 끝은 관 몫과 상관없이 오그라듦 (끌려 다니는 꼬리)
  s20r)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 sup_ramp=100";;                   # + 굶음 경쟁이 100 시간에 걸쳐 서서히 켜짐 (배고픔 순간 옆 뜀)
  s20n)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 scl_disc=0 scl_nofis=1";;         # + 균핵을 원판 대신 가장 굵은 덩이 제 모양으로
  s20s)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 scl_disc=0 scl_nofis=1 scl_C=5";; # s20n + 균핵 모드 전도도 바닥 20 → 5 (천천히 맺힘)
  s20d)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 scl_disc=0 scl_nofis=1 scl_dens=4 scl_dgrow=1";;   # 균핵 핵 = 빽빽한 덩이(흐림 4칸, 최대의 50% 이상) + 빈 곳 메움
  s20e)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 scl_disc=0 scl_nofis=1 scl_dens=6 scl_dgrow=1";;   # 흐림 6칸
  s20f)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1";;            # 꼬리 감기 + 서서히 배고픔 + 별 모양 핵
  s20g)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_C=8";;    # + 균핵 전도도 바닥 8 (천천히)
  s20h)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_C=4";;    # + 균핵 전도도 바닥 4 (더 천천히)
  s20i)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1";;           # 별 모양 핵을 들 때 한 번 정하고 굳힘
  s20j)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_C=4";;   # + 균핵 전도도 바닥 4
  s20k)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_C=4 scl_age=1";;     # 핵 밖이 2배로 늙음 (천천히)
  s20l)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_C=2 scl_age=0.5";;   # 1.5배, 바닥 2 (더 천천히)
  s20m)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_visc=5";;    # 균핵 때 원형질 5배 끈적 (천천히)
  s20o)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_visc=15";;   # 15배
  s20p)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_visc=5 scl_rstep=10";;   # + 균핵 때 가장자리 벗기기 10번에 한 번
  s20q)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_visc=5 scl_rstep=25";;   # 25번에 한 번
  s20u)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=100";;   # 핵 두께 100 시간에 걸쳐 오름
  s20v)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=200";;   # 200 시간
  *) echo "bad tag $tag"; exit 2;;
esac
name=b_${scn}_s${seed}_${tag}
mkdir -p $D/logs
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1200 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
