# -*- coding: utf-8 -*-
import sys, io, os, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))

names = json.load(open(os.path.join(HERE, 'unit_names_clean.json'), encoding='utf-8'))
name_map = {}
for k in range(3):
    for it in json.load(open(os.path.join(HERE, 'partB_out', f'units_{k}.json'), encoding='utf-8')):
        if it['id'] < len(names):
            name_map[names[it['id']]] = it['ko'].strip()
# coverage
miss = [n for n in names if n not in name_map]
print("unit names: %d, translated: %d, missing: %d" % (len(names), len(name_map), len(miss)))
if miss: print("  missing sample:", miss[:10])
json.dump(name_map, open(os.path.join(HERE, 'unit_name_map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

help_cells = json.load(open(os.path.join(HERE, 'help_cells.json'), encoding='utf-8'))
help_ko = {it['id']: it['ko'] for it in json.load(open(os.path.join(HERE, 'partB_out', 'help_0.json'), encoding='utf-8'))}
for idx, h in enumerate(help_cells):
    h['id'] = idx
    h['ko'] = help_ko.get(idx, h['jp'])
json.dump(help_cells, open(os.path.join(HERE, 'help_final.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("help cells translated:", sum(1 for h in help_cells if h.get('ko')))

# ---- syllable inventory: dialogue + names + help ----
def hangul(s):
    return set(c for c in s if 0xAC00 <= ord(c) <= 0xD7A3)

ko_dlg = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
syl = set()
for s in ko_dlg.values(): syl |= hangul(s)
dlg_syl = set(syl)
for v in name_map.values(): syl |= hangul(v)
for h in help_cells: syl |= hangul(h.get('ko', ''))

print("\nsyllables: dialogue=%d, +names+help total=%d (new from partB=%d)" % (
    len(dlg_syl), len(syl), len(syl - dlg_syl)))
print("kanji carrier cells available: 951")
json.dump(sorted(syl), open(os.path.join(HERE, 'syllables_all.json'), 'w', encoding='utf-8'), ensure_ascii=False)

# preview name translations
print("\nunit-name samples:")
for jp in list(name_map)[:15]:
    print("  ", jp, "->", name_map[jp])
print("\nhelp samples:")
for h in help_cells[:6]:
    print("  ", repr(h['jp'][:22]), "->", repr(h['ko'][:22]))
