# -*- coding: utf-8 -*-
"""main.dol 문자열 테이블 영역에서 UI 일본어 문자열 추출 (정제)."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
dol = open(os.path.join(HERE, '..', 'sys', 'main.dol'), 'rb').read()

REGION_LO = 0x2D0000
REGION_HI = 0x2E8000

def is_lead(c): return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC
def kana(s): return any(0x3040 <= ord(c) <= 0x30FF for c in s)  # 히라/가타
def cjk(c): return 0x4E00 <= ord(c) <= 0x9FFF
def allowed(s):
    # 실제 UI 문자열: 가나 포함, 또는 (한자+길이>=2). 제어문자 없음.
    if kana(s): return True
    if len(s) >= 2 and all(cjk(c) or ('！' <= c <= '～') or c in '・ー０１２３４５６７８９' for c in s):
        return True
    return False

strings = []
i = REGION_LO
while i < REGION_HI:
    if dol[i] == 0:
        i += 1; continue
    j = i; buf = bytearray(); ok = True
    while j < REGION_HI and dol[j] != 0:
        c = dol[j]
        if 0x20 <= c <= 0x7E:
            buf.append(c); j += 1
        elif is_lead(c) and j+1 < REGION_HI and 0x40 <= dol[j+1] <= 0xFC and dol[j+1] != 0x7F:
            buf += dol[j:j+2]; j += 2
        else:
            ok = False; break
    if ok and j < REGION_HI and dol[j] == 0 and j > i:
        try:
            s = bytes(buf).decode('cp932')
            if len(s) >= 2 and allowed(s):
                strings.append({'off': i, 'nbytes': j - i, 'jp': s})
        except UnicodeDecodeError:
            pass
        i = j + 1
    else:
        i = (j + 1) if j > i else (i + 1)

uniq = {}
for r in strings:
    uniq.setdefault(r['jp'], []).append({'off': r['off'], 'nbytes': r['nbytes']})
print("region 0x%X-0x%X: occurrences=%d unique=%d" % (REGION_LO, REGION_HI, len(strings), len(uniq)))
offs = [r['off'] for r in strings]
if offs: print("actual span: 0x%X ~ 0x%X" % (min(offs), max(offs)))
json.dump(strings, open(os.path.join(HERE, 'dol_strings_all.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
uq = [{'id': i, 'jp': k, 'occ': v} for i, (k, v) in enumerate(uniq.items())]
json.dump(uq, open(os.path.join(HERE, 'dol_strings_uniq.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("\nfirst 60 unique:")
for k in list(uniq)[:60]:
    print("  %-36s x%d" % (repr(k)[:38], len(uniq[k])))
