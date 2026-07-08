# -*- coding: utf-8 -*-
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode
BASE = os.path.join(HERE, '..', 'files')

def rows(rel):
    d = vsc_decode(open(os.path.join(BASE, rel), 'rb').read()).decode('cp932', 'replace')
    return [ln.split(',') for ln in d.split('\r\n')]

# unit-data.vsc : column 0 = unit name
ud = rows('Unit/AbMode/ユニットデータ.vsc')
print("ユニットデータ.vsc rows:", len(ud), "header:", ud[0][:6])
ab_names = [r[0].strip() for r in ud[1:] if r and r[0].strip() and not r[0].startswith('//')]
print("AB unit names (col0), count:", len(ab_names))
print("  sample:", ab_names[:20])

pu = rows('Unit/PbMode/pbmode_unit.vsc')
pb_names = [r[0].strip() for r in pu[1:] if r and r[0].strip()]
print("\nPB unit names count:", len(pb_names), "sample:", pb_names[:20])

ga = rows('Kaw/gallery.vsc')
gal_names = [r[0].strip() for r in ga[1:] if r and r[0].strip()]
print("\ngallery names count:", len(gal_names), "sample:", gal_names[:20])

# union of unit names
allnames = []
seen = set()
for n in ab_names + pb_names + gal_names:
    n = n.strip()
    if n and n not in seen and not n.isdigit():
        seen.add(n); allnames.append(n)
# filter obvious non-names (numbers, empty, header-ish)
allnames = [n for n in allnames if re.search(r'[ぁ-んァ-ヶ一-龥A-Za-zＡ-Ｚ]', n)]
print("\nUNION unique unit names:", len(allnames))
json.dump(allnames, open(os.path.join(HERE, 'unit_names.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("sample union:", allnames[:40])
