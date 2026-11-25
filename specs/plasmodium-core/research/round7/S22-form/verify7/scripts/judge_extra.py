#!/usr/bin/env python3
"""verify7 보충 판정 (CRITERIA_CHANGES.md 1절): 주장 6 을 다른 두 읽기로 다시 본다. 등록 판정(judge.py)은 그대로 둔다.
  B (나무꼴 외가닥 길이): 골격에서 그물 고리를 뺀 나무꼴 부분의 가장 긴 길. 긴 꼬리 = 큰 속 하나에만 닿고 자유 끝이 있는 것의 길이 >= 30,
                         멀리 뻗은 외가닥 = 굵은 부분끼리 잇는 것(큰 속 둘 이상)을 뺀 것의 길이 > 100
  C (몸에서의 거리): 큰 속을 가진 몸의 셀 가운데 큰 속에서 가장 먼 셀의 거리 > 100
장면: 등록 기준과 같다 (본 실행 전부, t >= 40, 후보는 t <= t_scl)
usage: judge_extra.py -> judge_extra.json"""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import judge as JG
OK, NO, UND = JG.OK, JG.NO, JG.UND


def main():
    D = JG.load(); out = {}
    for tag in ('v7c', 'v7y'):
        fr_all = []; per = {}
        for r in JG.runs(D, tag, JG.MAIN_SCN):
            E = json.load(open(os.path.join(JG.DATA, r['name'] + '.extra.json')))
            t1 = r['t_scl'] if (tag == 'v7y' and r['t_scl'] is not None) else 1e18
            fr = [x for x in E['frames'] if 40 - 1e-9 <= x['t'] <= t1 + 1e-9]
            fr_all += fr
            per[r['name']] = dict(tree100=sum(x['n_tree100'] >= 1 for x in fr), reach100=sum(x.get('reach', 0) > 100 for x in fr), frames=len(fr))
        n = len(fr_all)
        out[tag] = dict(frames=n, frac_tree_tail30=sum(x['n_tree_tail30'] >= 1 for x in fr_all) / max(n, 1),
                        tree100_frames=int(sum(p['tree100'] for p in per.values())), runs_tree100_ge2=[k for k, p in per.items() if p['tree100'] >= 2],
                        reach100_frames=int(sum(p['reach100'] for p in per.values())), runs_reach100_ge2=[k for k, p in per.items() if p['reach100'] >= 2],
                        frac_tree100=sum(x['n_tree100'] >= 1 for x in fr_all) / max(n, 1), frac_reach100=sum(x.get('reach', 0) > 100 for x in fr_all) / max(n, 1),
                        max_tree=max((x['tree_max'] for x in fr_all), default=0), max_reach=max((x.get('reach', 0) for x in fr_all), default=0),
                        p95_reach=float(np.percentile([x.get('reach', 0) for x in fr_all], 95)) if fr_all else None,
                        by_scn={s: dict(frames=sum(p['frames'] for k, p in per.items() if f'_{s}_' in k), tree100=sum(p['tree100'] for k, p in per.items() if f'_{s}_' in k),
                                        reach100=sum(p['reach100'] for k, p in per.items() if f'_{s}_' in k)) for s in JG.MAIN_SCN})
    y = out['v7y']
    out['verdict_B'] = OK if (y['tree100_frames'] == 0 and y['frac_tree_tail30'] <= 0.05) else (NO if (y['runs_tree100_ge2'] or y['frac_tree_tail30'] > 0.15) else UND)
    out['verdict_C'] = OK if (y['reach100_frames'] == 0 and y['frac_tree_tail30'] <= 0.05) else (NO if (y['runs_reach100_ge2'] or y['frac_tree_tail30'] > 0.15) else UND)
    json.dump(out, open(os.path.join(JG.OUTD, 'judge_extra.json'), 'w'), indent=1, ensure_ascii=False)
    print('claim6 B', out['verdict_B'], 'C', out['verdict_C'])


if __name__ == '__main__':
    main()
