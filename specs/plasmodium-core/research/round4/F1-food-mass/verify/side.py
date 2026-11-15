#!/usr/bin/env python3
"""[verify] 수축파의 부작용 점검(이주 실행): 전진면(나이<5 인 젖은 셀 수), 시트(h>0.5) 넓이와 비율, 정맥 간선 수, 몸 조각, 두께 진폭(hamp/hmean, 시트 셀), 스텝 끝 최소 두께. t>=200 평균."""
import numpy as np, glob, json, sys, os
for r in sys.argv[1:]:
    fs = sorted(glob.glob(f'runs/{r}/vs_t*.npz')); rows = []
    for f in fs:
        Z = np.load(f); t = float(Z['t'])
        if t < 200: continue
        wet = Z['wet']; h = Z['h']; age = Z['age']; hamp = Z['hamp']; hmean = Z['hmean']
        sh = wet & (h > 0.5); sm = hmean > 0.5
        rows.append((int((wet & (age < 5)).sum()), int(sh.sum()), sh.sum() / wet.sum(), float((hamp[sm] / hmean[sm]).mean()) if sm.any() else np.nan, int(wet.sum()), float(h[wet].min())))
    a = np.array(rows); m = json.load(open(f'runs/{r}/metrics.json'))
    print(f"{r:18s} 전진면 셀(나이<5) {a[:,0].mean():6.0f} | 시트 셀 {a[:,1].mean():6.0f} ({a[:,2].mean():.2f}) | 시트 상대 진폭 {np.nanmean(a[:,3]):.3f} | 면적 {a[:,4].mean():.0f} | 저장 시각 최소 두께 {a[:,5].min():+.4f} | 스텝 안 최소 {m['h_min_seen']:+.4f} 스텝 끝 음수 셀·스텝 {m['neg_end_cellsteps']} | 부피오차 {m['mass_err_max']:.1e}")
