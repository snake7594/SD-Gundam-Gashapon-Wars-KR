# -*- coding: utf-8 -*-
"""개행(0x0A/0x0D/0x09) 포함 DOL 문자열까지 재추출, 기존 dol_work에 없는 것만."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
dol = open(os.path.join(HERE, '..', 'sys', 'main.dol'), 'rb').read()
REGION_LO, REGION_HI = 0x2D0000, 0x2E8000

def is_lead(c): return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC
def kana(s): return any(0x3040 <= ord(c) <= 0x30FF for c in s)
def cjk(c): return 0x4E00 <= ord(c) <= 0x9FFF
def allowed(s):
    t = s.replace('\n', '').replace('\r', '').replace('\t', '')
    if kana(t): return True
    if len(t) >= 2 and all(cjk(c) or ('！' <= c <= '～') or c in '・ー０１２３４５６７８９' for c in t):
        return True
    return False

existing = set(w['jp'] for w in json.load(open(os.path.join(HERE, 'dol_work.json'), encoding='utf-8')))

found = []
i = REGION_LO
while i < REGION_HI:
    if dol[i] == 0:
        i += 1; continue
    j = i; buf = bytearray(); ok = True
    while j < REGION_HI and dol[j] != 0:
        c = dol[j]
        if 0x20 <= c <= 0x7E or c in (0x09, 0x0A, 0x0D):
            buf.append(c); j += 1
        elif is_lead(c) and j+1 < REGION_HI and 0x40 <= dol[j+1] <= 0xFC and dol[j+1] != 0x7F:
            buf += dol[j:j+2]; j += 2
        else:
            ok = False; break
    if ok and j < REGION_HI and dol[j] == 0 and j > i:
        try:
            s = bytes(buf).decode('cp932')
            if len(s.replace('\n', '').replace('\r', '')) >= 2 and allowed(s) and s not in existing:
                found.append({'off': i, 'nbytes': j - i, 'jp': s})
        except UnicodeDecodeError:
            pass
        i = j + 1
    else:
        i = (j + 1) if j > i else (i + 1)

uniq = {}
for r in found:
    uniq.setdefault(r['jp'], []).append({'off': r['off'], 'nbytes': r['nbytes']})
print("NEW DOL strings (newline-containing / missed):", len(uniq))
out = [{'id': 10000 + i, 'jp': k, 'budget': min(o['nbytes'] for o in v), 'occ': v}
       for i, (k, v) in enumerate(uniq.items())]
json.dump(out, open(os.path.join(HERE, 'dol_missed.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out[:30]:
    print("  id=%d budget=%d  %s" % (r['id'], r['budget'], repr(r['jp'][:46])))
