# 3층 모델 수치 프로토타입 v2 (주기 경계, 명시적 flux-form)
import numpy as np, sys, json
from PIL import Image
rng = np.random.default_rng(1)
N = int(sys.argv[1]); STEPS = int(sys.argv[2]); tag = sys.argv[3]
P = dict(
    dt=0.1, kappa=1.0, hstar=1.0, eta=0.8,
    amp=0.4, omega=0.05, K=0.05, wfood=0.3, wthin=0.3,
    m0=0.1, mD=0.9,
    yield0=0.3, ys=1.0, yc=0.5, ynoise=0.3,
    hdry=0.05, squeeze=0.8, hthin=0.4,
    ps=0.5, chi=0.6,
    rD=0.02, gamma=1.5, q0=0.05, diffD=0.01,
    sdep=0.004, sdecay=0.99995,
    mass=3.0, r0=0.09, eat=0.0,
)
if len(sys.argv) > 4: P.update(json.loads(sys.argv[4]))
g = lambda k: P[k]
def R(a, dx, dy): return np.roll(np.roll(a, -dy, 0), -dx, 1)
def lap(a): return R(a,1,0)+R(a,-1,0)+R(a,0,1)+R(a,0,-1)-4*a
yy, xx = np.mgrid[0:N, 0:N]
def gauss(cx, cy, r): return np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*r*r))
h = g('mass')*(((xx-N/2)**2+(yy-N/2)**2) < (N*g('r0'))**2).astype(float)
D = np.zeros((N,N)); s = np.zeros((N,N))
z = np.exp(1j*rng.uniform(0, 6.28, (N,N)))
foods = [(0.80,0.5),(0.3,0.22),(0.33,0.8)]
famt = [1.0, 1.0, 1.0]
def foodfield(): return sum(a*gauss(fx*N, fy*N, N*0.07) for a,(fx,fy) in zip(famt, foods))
c = foodfield()
noise = rng.uniform(-1, 1, (N,N)); het = np.exp(0.8*rng.normal(size=(N,N)))
qavg = np.zeros((N,N)); M0 = h.sum()

def step(t):
    global h, D, s, z, qavg, noise, c
    dt = g('dt'); wet = h > g('hdry')
    zz = np.where(wet, z, 0); cnt = sum(R(wet,dx,dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
    nb = R(zz,1,0)+R(zz,-1,0)+R(zz,0,1)+R(zz,0,-1)
    z = z + g('K')*(nb - cnt*z)*wet
    om = g('omega')*(1 + g('wfood')*c + g('wthin')*np.clip(g('hstar')-h, -1, 1))
    z = z*np.exp(1j*om*dt); z = z/np.maximum(np.abs(z), 1e-6)
    ph = np.angle(z)
    p = g('kappa')*(h - g('hstar') - g('eta')*D) + g('amp')*np.sin(ph) \
        + g('squeeze')*np.clip(1 - h/g('hthin'), 0, 1) + g('ps')*s - g('chi')*c
    mob = g('m0')*het + g('mD')*D
    yld = g('yield0') + g('ys')*s - g('yc')*c + g('ynoise')*noise
    dh = np.zeros_like(h); qmag = np.zeros_like(h)
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
        dh -= q; dh += R(q,-dx,-dy)
        qmag += 0.5*(np.abs(q) + np.abs(R(q,-dx,-dy)))
    h = np.maximum(h + dt*dh, 0)
    qavg = 0.995*qavg + 0.005*qmag
    f = (qavg/g('q0'))**g('gamma')
    D = D + dt*(g('rD')*(f/(1+f) - D) + g('diffD')*lap(D))
    D = np.clip(D, 0, 1)*(h > g('hdry'))
    s = np.minimum(s*g('sdecay') + g('sdep')*dt*(h > g('hdry')), 1.0)
    if g('eat') > 0 and t % 20 == 0:
        for i,(fx,fy) in enumerate(foods):
            if h[int(fy*N), int(fx*N)] > 0.5: famt[i] = max(0, famt[i] - g('eat'))
        c = foodfield()
    if t % 100 == 0: noise = 0.8*noise + 0.2*rng.uniform(-1,1,(N,N))
    return ph

def render(path):
    hv = np.clip(h/2.5, 0, 1)
    gx = (R(h,1,0)-R(h,-1,0)); gy = (R(h,0,1)-R(h,0,-1))
    shade = np.clip(0.8 + 0.8*(-gx-gy)*0.5, 0.35, 1.5)
    fg = np.stack([(70+185*hv**0.7)*shade, (50+165*hv**0.7)*shade, (5+40*hv)*shade], -1)
    bg = np.stack([14+34*s, 26+30*s, 12+10*s], -1)
    a = np.clip(h/0.3, 0, 1)[..., None]
    img = np.clip(bg*(1-a) + fg*a, 0, 255).astype(np.uint8)
    for i,(fx, fy) in enumerate(foods):
        if famt[i] > 0: img[int(fy*N)-1:int(fy*N)+2, int(fx*N)-1:int(fx*N)+2] = (255,255,255)
    dimg = np.stack([np.clip(D*255,0,255)]*3, -1).astype(np.uint8)
    Image.fromarray(np.concatenate([img, dimg], 1)).resize((N*6, N*3), Image.LANCZOS).save(path)

for t in range(STEPS+1):
    ph = step(t)
    if t % (STEPS//8) == 0:
        wet = h > g('hdry')
        qa = qavg[wet]
        print(t, 'mass %.0f/%.0f' % (h.sum(), M0), 'area', int(wet.sum()), 'hmax %.2f' % h.max(),
              'qavg p50/p90/p99 %.3f %.3f %.3f' % tuple(np.percentile(qa, [50,90,99])),
              'D>0.5 frac %.3f' % ((D > 0.5).sum()/max(wet.sum(),1)), 'food', np.round(famt,2), flush=True)
        render(f'{tag}_{t:06d}.png')
