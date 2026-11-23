import sys, shutil, os
SP = '/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad'
src_dir, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for f in ('export_ref.py', 'mgt.py', 'graphm.py'): shutil.copy(os.path.join(src_dir, f), dst)
s = open(os.path.join(src_dir, 'ref_model.py')).read()
ins = open(SP + '/instr/ref_model.py').read()
helper = ins[ins.index('\n_DBG = dict('):ins.index('\ndef run(name, over):')]
def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)
rep("def run(name, over):", helper + "\ndef run(name, over):")
rep("        h = h - dt * div\n", "        h = h - dt * div\n        _chk('flux', step, t, scl, h, wet, V_crumb, Vinj, V0)\n")
rep("        if Dm.any():\n            stay = wet & ~Dm; ns = np.zeros((N, N))", "        _chk('mid', step, t, scl, h, wet, V_crumb, Vinj, V0)\n        if Dm.any():\n            stay = wet & ~Dm; ns = np.zeros((N, N))")
rep("        if fill is not None and fill.any() and P['neg_fill_global']:", "        _chk('dry', step, t, scl, h, wet, V_crumb, Vinj, V0)\n        if fill is not None and fill.any() and P['neg_fill_global']:")
rep("        if fill is not None and fill.any():\n            fill &= wet\n", "        _chk('gfill', step, t, scl, h, wet, V_crumb, Vinj, V0)\n        if fill is not None and fill.any():\n            fill &= wet\n")
rep("        # ---- wetting (thickness yield) ----", "        _chk('lfill', step, t, scl, h, wet, V_crumb, Vinj, V0)\n        # ---- wetting (thickness yield) ----")
rep("        if P['f32']:      # the state the next step starts from", "        _chk('end', step, t, scl, h, wet, V_crumb, Vinj, V0)\n        if P['f32']:      # the state the next step starts from")
# record details of end-negative cells: step, h, whether in fill, kept (bad_), hang C, neighbour sum
rep("    met = dict(name=name,", "    met_dbg = dict(mass=_DBG['mass'], negorig={f'{a}|{b}': v for (a, b), v in _DBG['negorig'].items()}, negend_steps=_DBG['negend_steps'], dryh=_DBG['dryh'], negsteps=_DBG.get('negsteps', []))\n    json.dump(met_dbg, open(os.path.join(out, 'dbg.json'), 'w'))\n    met = dict(name=name,")
open(os.path.join(dst, 'ref_model.py'), 'w').write(s)
print('ok')
