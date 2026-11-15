#!/usr/bin/env python3
"""두 먹이 덩어리의 두께 진동이 같은 박자인지 어긋난 박자인지. usage: phase.py RUN [RUN ...]
hfood.npy (스텝별 덩어리 평균 두께 2열 + 덩어리 평균 위상 2열)에서, 먹이를 먹는 구간(t=100~340)의 두께를 주기 4 로 대역 통과해 두 덩어리의 상관과 위상차를 낸다."""
import numpy as np, sys, os, json
HERE=os.path.dirname(os.path.abspath(__file__))
for r in sys.argv[1:]:
    f=os.path.join(HERE,'runs',r,'hfood.npy')
    if not os.path.exists(f): print(r,'(hfood 없음)'); continue
    a=np.load(f); dt=0.1; t=np.arange(len(a))*dt; m=(t>=100)&(t<=340)
    x=a[m,0].astype(float); y=a[m,1].astype(float); n=40                      # 한 주기 = 40스텝
    k=np.ones(n)/n; xs=x-np.convolve(x,k,'same'); ys=y-np.convolve(y,k,'same')   # 주기 평균을 빼서 맥동 성분만
    xs=xs[n:-n]; ys=ys[n:-n]
    corr=float(np.corrcoef(xs,ys)[0,1])
    # 주기 4 성분의 복소 진폭으로 위상차
    tt=np.arange(len(xs))*dt; e=np.exp(-1j*2*np.pi*tt/4.0)
    # 창별(10주기) 위상차
    W=400; dph=[]; amp=[]
    for i in range(0,len(xs)-W+1,W):
        ax=(xs[i:i+W]*e[i:i+W]).mean(); ay=(ys[i:i+W]*e[i:i+W]).mean()
        dph.append(float(np.degrees(np.angle(ay/ax)))); amp.append((2*abs(ax),2*abs(ay)))
    th=a[m,2:4].astype(float); dth=np.degrees(np.angle(np.exp(1j*(th[:,1]-th[:,0]))))
    print(f'{r:26s} 두께 맥동 상관 {corr:+.2f} | 창별 두께 위상차(도) {[round(v) for v in dph]} | 진폭 {[ (round(p,3),round(q,3)) for p,q in amp][:3]} | 진동자 위상차(도) 중앙 {np.nanmedian(dth):+.0f}, 범위 {np.nanmin(dth):+.0f}~{np.nanmax(dth):+.0f}')
