# -*- coding: utf-8 -*-
import sys, io, os, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
uq = json.load(open(os.path.join(HERE, 'dol_strings_uniq.json'), encoding='utf-8'))

def is_path(s):
    return ('/' in s) or ('.csv' in s) or ('.vsc' in s) or ('.dat' in s) or ('.arc' in s) \
        or ('.bin' in s) or ('.thp' in s) or ('.tpl' in s) or ('\\' in s) or s.endswith('.h')

def is_unit_name(s):
    # 유닛명은 키라 번역 금지 — 가타카나 단독 명사는 위험. 하지만 UI엔 드묾.
    return False

work = []
skipped = 0
for r in uq:
    s = r['jp']
    if is_path(s):
        skipped += 1
        continue
    # byte budget = min nbytes over occurrences (null 제외; slot=nbytes, +1 null 있음)
    minb = min(o['nbytes'] for o in r['occ'])
    work.append({'id': r['id'], 'jp': s, 'budget': minb, 'occ': len(r['occ'])})

json.dump(work, open(os.path.join(HERE, 'dol_work.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("translatable DOL UI strings:", len(work), " (skipped paths:", skipped, ")")
# budget stats
import statistics
bs = [w['budget'] for w in work]
print("byte budget: min=%d max=%d mean=%.1f" % (min(bs), max(bs), statistics.mean(bs)))
tight = [w for w in work if w['budget'] <= 6]
print("very tight (<=6 bytes, <=3 kana):", len(tight))
for w in tight[:15]:
    print("   budget=%d  %s" % (w['budget'], w['jp']))
