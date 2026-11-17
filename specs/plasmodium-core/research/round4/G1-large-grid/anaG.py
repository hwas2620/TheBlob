#!/usr/bin/env python3
"""큰 격자 실행 요약. usage: anaG.py RUN [RUN ...]  (log_<RUN>.txt 와 runs/<RUN>/ 의 최종 배열)"""
import json, sys, os, numpy as np
from scipy import ndimage as ndi
HERE=os.path.dirname(os.path.abspath(__file__))
def grab(log, tag):
    for line in open(log):
        if f' {tag} ' in line:
            try: return json.loads(line.split(f' {tag} ',1)[1])
            except Exception: return None
for r in sys.argv[1:]:
    log=os.path.join(HERE,f'log_{r}.txt'); d=os.path.join(HERE,'runs',r)
    if not os.path.exists(log): print(r,'(로그 없음)'); continue
    met=grab(log,'MET'); g=grab(log,'GRAPH'); chk=grab(log,'CHK')
    if met is None: print(r,'(진행 중)', open(log).read()[-200:].replace('\n',' ')); continue
    P=json.load(open(d+'/params.json'))
    wet=np.load(d+'/wet.npy'); h=np.load(d+'/h.npy'); C=np.load(d+'/C_edges.npy'); age=np.load(d+'/age.npy'); th=np.load(d+'/theta.npy'); N=wet.shape[0]
    lab,n=ndi.label(wet,structure=np.ones((3,3))); sz=np.bincount(lab.ravel())[1:]; big=lab==(1+np.argmax(sz))
    vol_big=float(h[big].sum()/h.sum())
    # 윤곽의 둥근 정도: 전체 젖은+말랐던 영역(슬라임 포함) 대신 젖은 집합의 볼록 껍질 대신, 중심에서 방향별 최대 반지름의 축/대각 비
    ys,xs=np.nonzero(wet); cy,cx=ys.mean(),xs.mean(); ang=np.degrees(np.arctan2(ys-cy,xs-cx))%360; rr=np.hypot(ys-cy,xs-cx)
    reach={a:float(rr[np.abs(((ang-a+180)%360)-180)<=7.5].max()) for a in range(0,360,45)}
    ax=np.mean([reach[a] for a in (0,90,180,270)]); dg=np.mean([reach[a] for a in (45,135,225,315)])
    # 살아 있는 띠의 폭: 젖은 셀의 가장자리로부터의 거리 분포 (젖은 집합 + 구멍 채움의 경계까지)
    filled=ndi.binary_fill_holes(ndi.binary_closing(wet,iterations=3)); dist=ndi.distance_transform_edt(filled)
    veinc=np.zeros((N,N),bool)
    for k,(dx,dy) in enumerate([(1,0),(0,1),(1,1),(1,-1)]):
        e=C[k]>4; veinc|=e; yy,xx=np.nonzero(e); veinc[(yy+dy)%N,(xx+dx)%N]=True
    dv=dist[veinc&wet]; dw=dist[wet]
    a=age[big]; t=th[big]; o=np.argsort(a); n10=max(3,a.size//10); ph=(np.nanmean(t[o[-n10:]])-np.nanmean(t[o[:n10]]))/(2*np.pi)
    print(f"== {r}  N={N} tau_a={P['tau_a']} wave={P.get('wave_lambda',0)} T={met['t_end']}")
    print(f"   유량오차 중앙/p90/최대 {chk['err_all']['med']:.3f}/{chk['err_all']['p90']:.3f}/{chk['err_all']['max']:.3f} (n={chk['err_all']['n']}) | 음수 스텝 {met['neg_steps']} | 부피오차 {met['mass_err_max']:.1e}")
    print(f"   이동 {met['disp']} 셀, 방향 {met['disp_dir_deg']}° (목표 {P.get('food_angle',0)}°) | 면적 {met['area_end']} | 몸 조각 {met['body_components']} | 가장 큰 몸 성분 부피 {vol_big:.3f}")
    print(f"   정맥: 간선 {g['vein_edges']}, 최대 성분 {g['vein_largest_frac']}, 순환 {g['cycles']}, Spearman {g['spearman_logC_pos']}, 총/순 {g['vein_gross_over_net']}, Strahler {g['strahler_max_spanning']}, 격자 방향 현 {g['chord_lattice_frac_7p5']}")
    print(f"   윤곽 대각/축 도달 {dg/ax:.3f} (축 {ax:.0f}, 대각 {dg:.0f}) | 가장자리에서의 거리: 젖은 셀 중앙 {np.median(dw):.0f}, 90% {np.percentile(dw,90):.0f}; 정맥 셀 중앙 {np.median(dv):.0f}, 90% {np.percentile(dv,90):.0f}, 최대 {dv.max():.0f} | 몸 반지름(축) {ax:.0f}")
    print(f"   맥동: 위상 잠금 {met.get('lock_R')}, 시트 진폭 {met.get('hamp_sheet_mean')}, 늙은-젊은 위상차 {ph:.2f} 바퀴")
