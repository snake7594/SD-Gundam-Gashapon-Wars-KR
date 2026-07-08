# -*- coding: utf-8 -*-
"""v15: 엣지 main.dol 문구 -> dol_extra, 필드맵(이름+설명) -> filed_select.vsc 주입 준비."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
out = {it['id']: it['ko'] for it in json.load(open(os.path.join(HERE, 'v15_out.json'), encoding='utf-8'))}
edge = json.load(open(os.path.join(HERE, 'edge_worklist.json'), encoding='utf-8'))

# 1) 엣지 -> dol_extra.json 에 병합 (오프셋+ko)
extra = json.load(open(os.path.join(HERE, 'dol_extra.json'), encoding='utf-8'))
extra_off = set(o['off'] for e in extra for o in e['occ'])
added = 0
for i, e in enumerate(edge):
    ko = out.get(f'E{i}')
    if ko is None:
        continue
    if e['off'] in extra_off:
        continue
    extra.append({'jp': e['jp'], 'ko': ko, 'budget': e['budget'], 'occ': [{'off': e['off'], 'nbytes': e['nbytes']}]})
    added += 1
json.dump(extra, open(os.path.join(HERE, 'dol_extra.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("dol_extra에 엣지 추가:", added, "총", len(extra))

# 2) 필드맵 -> filed_select 주입맵 {row: {col: ko}}
field = json.load(open(os.path.join(HERE, 'field_worklist.json'), encoding='utf-8'))
fmap = {}   # row -> {0:name, 3:c1, 4:c2, 5:c3}
for r in field:
    row = r['row']; d = {}
    if f"N{row}" in out and r['name'].strip():
        d[0] = out[f"N{row}"]
    for ci, col in [('1', 3), ('2', 4), ('3', 5)]:
        k = f"C{row}_{ci}"
        if k in out and r['c%s' % ci].strip():
            d[col] = out[k]
    if d:
        fmap[row] = d
json.dump(fmap, open(os.path.join(HERE, 'field_map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("filed_select 주입 행:", len(fmap))
# 샘플
for row in list(fmap)[:3]:
    print("  row", row, {k: v[:18] for k, v in fmap[row].items()})
