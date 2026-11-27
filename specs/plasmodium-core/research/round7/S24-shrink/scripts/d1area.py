"""[S24 진단 1] 균핵 맺힘의 넓이 변화가 한 창에 몰리는지: 여덟째 검증자의 area_timing 을 S23 실행에 그대로 댄다 (판정 아님)."""
import sys, os, json, glob, numpy as np
V8 = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/verify8/scripts'; sys.path.insert(0, V8)
from measure import area_timing
R = sys.argv[1] if len(sys.argv) > 1 else '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model/runs'
pat = sys.argv[2] if len(sys.argv) > 2 else '*_s23v'
for rd in sorted(glob.glob(os.path.join(R, 'b_*' + pat))):
    m = json.load(open(os.path.join(rd, 'metrics.json'))); P = json.load(open(os.path.join(rd, 'params.json')))
    ts = m.get('t_scl')
    if ts is None: continue
    ser = np.load(os.path.join(rd, 'series.npz')); a = ser['area']; dt = P['dt']
    o = area_timing(a, dt, ts)
    i0 = int(round(ts / dt)); aa = a[i0:]; w = int(round(10 / dt))
    jm = int(np.argmax(np.abs(aa[w:] - aa[:-w]))) if aa.size > w else 0
    print(f"{os.path.basename(rd):28s} t_scl {ts:7.1f} A0 {o['A0']:5d} Aend {o['A_end']:5d} t10 {o.get('t10')} t50 {o.get('t50')} t90 {o.get('t90')} max10 {o.get('max10')} at +{jm*dt:.0f}h  "
          f"A(+20,+40,+60,+80) {[int(aa[min(int(k/dt), aa.size-1)]) for k in (20, 40, 60, 80)]}")
