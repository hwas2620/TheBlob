#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S19(균핵 다시 짓기) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S19-sclero2
REF=$D/model
scn=$1; seed=$2; tag=$3
W="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9"   # S18 후보 s18w
MIR='foods=[[-27,70]]'      # 이주 유인원을 거울 자리(−27°)에
case "$tag" in
  s19c)   extra="";;                    # 지금 모델
  s19w)   extra="$W";;                  # S18 후보 그대로
  s19cm)  extra="$MIR";;                # 지금 모델, 거울 유인원
  s19wm)  extra="$W $MIR";;             # S18 후보, 거울 유인원
  s19a)   extra="$W scl_stay=1";;                                   # + 한 번 맺힌 균핵은 먹기 전엔 안 풀림
  s19b)   extra="$W scl_stay=1 scl_rundry=1";;                      # + 균핵 때 마르는 줄을 통째로 거둠
  s19d)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1";;           # + 흐름 제한을 늘 켬
  s19e)   extra="${W/scl_disc=1/scl_disc=0} scl_stay=1 scl_rundry=1 dlim_all=1 scl_nofis=1";;   # s19d에서 원반 대신 가장 큰 굵은 덩이 제 모양으로
  s19f)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 t_eat0=50";;      # s19d + 처음엔 배부름(굶음 규칙은 t 100부터)
  s19g)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1";;     # s19d + 먹이 쪽으로 오르는 부채는 경쟁에서 아끼기
  s19h)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1";;              # s19d + 균핵 때 핵 밖 관 몫 없앰(버린 관이 빔)
  s19i)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 scl_nowet=1";;  # s19h + 원반 안으로도 젖지 않음(불규칙한 덩어리)
  g_nos7)  extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 sup_age=0";;          # 이주 방향 빼보기: 굶음 경쟁(S7) 끔
  g_nosz)  extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 sup_size=0";;         # 작은 덩이 더 늙기 끔
  g_nosc)  extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 sup_scent=0";;        # 냄새 쪽 경쟁 끔
  g_nohc)  extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 hang_C=0";;           # 지켜진 실 전도도 끔
  g_noret) extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 ret_h=0 ret_glob=0";; # 오그라듦 끔
  g_notri) extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 tri_k=0";;            # 흐르는 맥동 무늬 끔
  c_notri) extra="tri_k=0";;                # 대조, 흐르는 맥동 무늬 끔
  g_tau80) extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 sup_tau=80";;            # S7 흐름 평균을 맥동 무늬 한 주기로
  g_rot)   extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 sup_rot=1";;             # S7 구역 넓히기 방향 순서 돌리기
  g_both)  extra="$W scl_stay=1 scl_rundry=1 dlim_all=1 sup_climb=1 sup_tau=80 sup_rot=1";;  # 둘 다
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
