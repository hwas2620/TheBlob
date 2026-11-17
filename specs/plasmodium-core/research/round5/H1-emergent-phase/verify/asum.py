#!/usr/bin/env python3
"""[verify5] 작성자 실행(../runs/<RUN>)을 vmet.summarise 로 다시 재서 A/summ/<RUN>.json 에 둔다(작성자 summ 에 있으면 그것과 대조). usage: asum.py mig|food RUN ..."""
import json, os, sys, vmet
kind = sys.argv[1]
for r in sys.argv[2:]:
    cf = f'A/summ/{r}.json'
    if os.path.exists(cf): print(r, '(이미 있음)'); continue
    if not os.path.exists(f'../runs/{r}/metrics.json'): print(r, '(아직 없음)'); continue
    o = vmet.summarise(f'../runs/{r}', kind); o.pop('rows', None); o = json.loads(json.dumps(o)); json.dump(o, open(cf, 'w'), ensure_ascii=False)
    af = f'../summ/{r}.json'
    if os.path.exists(af):
        c = json.load(open(af)); d = {k: (o.get(k), c.get(k)) for k in set(o) | set(c) if o.get(k) != c.get(k)}
        print(r, '작성자 캐시와 일치' if not d else f'불일치 {d}')
    else: print(r, '새로 잼(작성자 summ 없음)')
