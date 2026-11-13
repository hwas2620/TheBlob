# builds verify/n1v.py = copy of ../n1.py + verification hooks (model lines untouched)
import re, os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'n1.py')).read()
def rep(a, b):
    global src
    assert src.count(a) == 1, (src.count(a), a)
    src = src.replace(a, b)
# 1. hook import
rep("HERE = os.path.dirname(os.path.abspath(__file__))\n",
    "HERE = os.path.dirname(os.path.abspath(__file__))\nimport vhook\n")
# 2. new params
rep("limit=0, limit_reinforce='pre', dtype='f8', check_every=10,",
    "vh_every=0, limit=0, limit_reinforce='pre', dtype='f8', check_every=10,")
# 3. create hook object
rep("    ckpt = set(int(s) for s in P['ckpt_steps'])\n",
    "    ckpt = set(int(s) for s in P['ckpt_steps'])\n    VH = vhook.Hook(P, out) if P['vh_every'] > 0 else None\n    p_warm = None\n")
# 4. capture warm start (approximate solvers only)
rep("            if solver == 'mg':\n                mg.build(True)\n",
    "            p_warm = mg.p[0][sy_, sx_].copy()\n            if solver == 'mg':\n                mg.build(True)\n")
# 5. after flux
rep("        # ---- check against the exact solve from the same state ----\n",
    "        if VH is not None and step > 0 and step % P['vh_every'] == 0: VH.after_solve(step, W, rhs, wet, p, Q, C, act, h, hstar, Cn, p_warm, (y0, y1, x0, x1))\n"
    "        # ---- check against the exact solve from the same state ----\n")
# 6. after h update (every step: true minimum)
rep("        hm_ = float(h[wet].min()) if wet.any() else 0.0\n",
    "        hm_ = float(h[wet].min()) if wet.any() else 0.0\n        if VH is not None: VH.after_h(step, h, wet, hstar, p, age)\n")
# 7. save
rep("    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)\n",
    "    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)\n    if VH is not None: VH.save()\n")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n1v.py'), 'w').write(src)
print('ok')
