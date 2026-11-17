# 하이브리드 프로토타입: 두께장 h + 진동자 + 점액  /  Jones 입자 = 몸 안에 갇힌 "관 형성자" (트레일 = 전도도 D)
import numpy as np, sys, json
from PIL import Image
rng = np.random.default_rng(2)
N = int(sys.argv[1]); STEPS = int(sys.argv[2]); tag = sys.argv[3]
P = dict(
    dt=0.1, kappa=1.0, hstar=1.0, eta=0.6,
    amp=0.5, omega=0.1, K=0.05, wfood=0.3, wthin=0.5, wslime=0.2,
    m0=0.05, mD=0.95,
    yield0=0.2, ys=1.0, yc=0.5, ynoise=0.3,
    hdry=0.05, squeeze=0.8, hthin=0.4,
    ps=1.0, chi=0.8,
    sdep=0.01, sdecay=0.99995,
    mass=2.5, r0=0.11, eat=0.004, foodr=0.16,
    npart=7000, pfood=0.0, pslime=0.0, pmin=0.4, cap=1.0, SO=5.0, SA=0.6, RA=0.6, dep=1.0, tdecay=0.9, t0=6.0, adv=1.0, fluxdep=0.0, q0=0.05,
)
if len(sys.argv) > 4: P.update(json.loads(sys.argv[4]))
g = lambda k: P[k]
def R(a, dx, dy): return np.roll(np.roll(a, -dy, 0), -dx, 1)
yy, xx = np.mgrid[0:N, 0:N]
def gauss(cx, cy, r): return np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*r*r))
h = g('mass')*(((xx-N/2)**2+(yy-N/2)**2) < (N*g('r0'))**2).astype(float)
s = np.zeros((N,N)); tr = np.zeros((N,N)); D = np.zeros((N,N))
z = np.exp(1j*rng.uniform(0, 6.28, (N,N)))
foods = [(0.80,0.5),(0.3,0.2),(0.33,0.82),(0.62,0.18),(0.15,0.52),(0.68,0.85)]
famt = [1.0]*6
def foodfield(): return sum(a*gauss(fx*N, fy*N, N*g('foodr')) for a,(fx,fy) in zip(famt, foods))
c = foodfield()
noise = rng.uniform(-1, 1, (N,N)); M0 = h.sum()
# 입자
n = int(g('npart')); ang0 = rng.uniform(0, 6.28, n); rad0 = N*g('r0')*np.sqrt(rng.uniform(0,1,n))
px = N/2 + rad0*np.cos(ang0); py = N/2 + rad0*np.sin(ang0); pa = rng.uniform(0, 6.28, n)
ux = np.zeros((N,N)); uy = np.zeros((N,N)); qmagc = np.zeros((N,N)); occ = np.zeros((N,N))
def samp(f, x, y): return f[np.floor(y).astype(int) % N, np.floor(x).astype(int) % N]

def step(t):
    global h, s, z, noise, c, tr, D, px, py, pa, ux, uy, qmagc, occ
    dt = g('dt'); wet = h > g('hdry')
    zz = np.where(wet, z, 0); cnt = sum(R(wet,dx,dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
    nb = R(zz,1,0)+R(zz,-1,0)+R(zz,0,1)+R(zz,0,-1)
    z = z + g('K')*(nb - cnt*z)*wet
    om = g('omega')*(1 + g('wfood')*c + g('wthin')*np.clip(g('hstar')-h, -1, 1) - g('wslime')*s)
    z = z*np.exp(1j*om*dt); z = z/np.maximum(np.abs(z), 1e-6)
    p = g('kappa')*(h - g('hstar') - g('eta')*D) + g('amp')*np.sin(np.angle(z)) \
        + g('squeeze')*np.clip(1 - h/g('hthin'), 0, 1) + g('ps')*s - g('chi')*c
    mob = g('m0') + g('mD')*D
    yld = g('yield0') + g('ys')*s - g('yc')*c + g('ynoise')*noise
    dh = np.zeros_like(h); qs = []
    for dx, dy in ((1,0),(0,1)):
        hn, pn, wn = R(h,dx,dy), R(p,dx,dy), R(wet,dx,dy)
        dp = p - pn
        mf = 0.5*(mob + R(mob,dx,dy))
        q = mf*np.where(dp > 0, h, hn)*dp
        yn = R(yld,dx,dy)
        q = np.where(wet & ~wn, mf*h*np.maximum(p - yn, 0), q)
        q = np.where(wn & ~wet, -mf*hn*np.maximum(pn - yld, 0), q)
        q = np.where(~wet & ~wn, 0, q)
        q = np.clip(q, -0.2*hn/dt, 0.2*h/dt)
        dh -= q; dh += R(q,-dx,-dy); qs.append(0.5*(q + R(q,-dx,-dy)))
    h = np.maximum(h + dt*dh, 0)
    hs = np.maximum(h, 0.3)
    ux, uy = qs[0]/hs, qs[1]/hs
    qmagc = 0.99*qmagc + 0.01*np.hypot(qs[0], qs[1])
    s = np.minimum(s*g('sdecay') + g('sdep')*dt*(h > g('hdry')), 1.0)
    # --- Jones 입자 (몸 안에 갇힘) ---
    SO, SA, RA = g('SO'), g('SA'), g('RA')
    sf = tr + g('t0')*(g('pfood')*c - g('pslime')*s)
    F = samp(sf, px+SO*np.cos(pa), py+SO*np.sin(pa))
    L = samp(sf, px+SO*np.cos(pa-SA), py+SO*np.sin(pa-SA))
    Rr = samp(sf, px+SO*np.cos(pa+SA), py+SO*np.sin(pa+SA))
    rnd = rng.uniform(0,1,n)
    turn = np.where((F > L) & (F > Rr), 0.0, np.where((F < L) & (F < Rr), np.where(rnd>0.5, RA, -RA), np.where(L > Rr, -RA, RA)))
    pa = pa + turn
    nx = (px + np.cos(pa) + g('adv')*dt*samp(ux, px, py)) % N
    ny = (py + np.sin(pa) + g('adv')*dt*samp(uy, px, py)) % N
    same = (np.floor(nx)==np.floor(px)) & (np.floor(ny)==np.floor(py))
    ok = (samp(h, nx, ny) > g('pmin')) & (same | (samp(occ, nx, ny) < g('cap')))
    px = np.where(ok, nx, px); py = np.where(ok, ny, py)
    pa = np.where(ok, pa, rng.uniform(0, 6.28, n))
    lost = samp(h, px, py) <= g('hdry')
    if lost.any():
        good = np.flatnonzero(~lost)
        if len(good):
            src = rng.choice(good, lost.sum()); px[lost] = px[src]; py[lost] = py[src]
    occ = np.bincount((np.floor(py).astype(int)%N)*N + (np.floor(px).astype(int)%N), minlength=N*N).reshape(N,N)
    w = g('dep')*(1 + g('fluxdep')*samp(qmagc, px, py)/g('q0'))
    np.add.at(tr, (np.floor(py).astype(int) % N, np.floor(px).astype(int) % N), w*ok)
    tr = sum(R(tr,dx,dy) for dx in (-1,0,1) for dy in (-1,0,1))/9.0*g('tdecay')
    D = tr/(tr + g('t0'))
    if g('eat') > 0 and t % 20 == 0:
        for i,(fx,fy) in enumerate(foods):
            if h[int(fy*N), int(fx*N)] > 0.5: famt[i] = max(0, famt[i] - g('eat'))
        c = foodfield()
    if t % 100 == 0: noise = 0.8*noise + 0.2*rng.uniform(-1,1,(N,N))

def render(path):
    hh = h
    hv = np.clip(hh/2.2, 0, 1)
    gx = (R(hh,1,0)-R(hh,-1,0)); gy = (R(hh,0,1)-R(hh,0,-1))
    shade = np.clip(0.8 + 0.9*(-gx-gy)*0.5, 0.35, 1.6)
    fg = np.stack([(80+175*hv**0.7)*shade, (58+160*hv**0.7)*shade, (5+40*hv)*shade], -1)
    bg = np.stack([14+34*s, 26+30*s, 12+10*s], -1)
    a = np.clip(h/0.3, 0, 1)[..., None]
    img = np.clip(bg*(1-a) + fg*a, 0, 255).astype(np.uint8)
    for i,(fx, fy) in enumerate(foods):
        if famt[i] > 0: img[int(fy*N)-1:int(fy*N)+2, int(fx*N)-1:int(fx*N)+2] = (255,255,255)
    dimg = np.stack([np.clip(D*255,0,255)]*3, -1).astype(np.uint8)
    Image.fromarray(np.concatenate([img, dimg], 1)).resize((N*6, N*3), Image.LANCZOS).save(path)

for t in range(STEPS+1):
    step(t)
    if t % (STEPS//8) == 0:
        wet = h > g('hdry')
        print(t, 'mass %.0f/%.0f' % (h.sum(), M0), 'area', int(wet.sum()), 'hmax %.2f' % h.max(),
              'D mean %.2f, frac>0.5 %.3f' % (D[wet].mean(), (D>0.5).sum()/max(wet.sum(),1)), 'food', np.round(famt,2), flush=True)
        render(f'{tag}_{t:06d}.png')
