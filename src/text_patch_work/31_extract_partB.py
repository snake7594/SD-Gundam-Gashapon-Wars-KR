# -*- coding: utf-8 -*-
"""Part B 추출: 클린 유닛명 집합 + 도움말(key_help/game_help) 번역 대상."""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode
BASE = os.path.join(HERE, '..', 'files')

def decode(rel):
    return vsc_decode(open(os.path.join(BASE, rel), 'rb').read()).decode('cp932', 'replace')

def grid(rel):
    return [ln.split(',') for ln in decode(rel).split('\r\n')]

# ---- clean unit names (from PB + gallery col0) ----
clean = []
seen = set()
for rel in ['Unit/PbMode/pbmode_unit.vsc', 'Kaw/gallery.vsc']:
    for r in grid(rel)[1:]:
        if not r or not r[0].strip():
            continue
        nm = r[0].strip()
        # strip trailing markers （削除）（欠番）
        core = re.sub(r'（[^）]*）', '', nm).strip()
        if core and core not in seen and re.search(r'[ぁ-んァ-ヶ一-龥]', core):
            seen.add(core); clean.append(core)
# also collect cores from AB unit-data (strip NNN- prefix, [SPARK], （）)
for r in grid('Unit/AbMode/ユニットデータ.vsc')[1:]:
    if not r or not r[0].strip():
        continue
    nm = r[0].strip()
    core = re.sub(r'^\d+\-', '', nm)
    core = re.sub(r'\[[^\]]*\]', '', core)
    core = re.sub(r'（[^）]*）', '', core).strip()
    if core and core not in seen and re.search(r'[ぁ-んァ-ヶ一-龥]', core):
        seen.add(core); clean.append(core)

# sort by length desc for later longest-match replacement
clean_sorted = sorted(clean, key=len, reverse=True)
json.dump(clean_sorted, open(os.path.join(HERE, 'unit_names_clean.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("clean unique unit-name cores:", len(clean_sorted))
print("sample:", clean_sorted[:25])

# ---- help / menu text (key_help, game_help) ----
# represent as list of translatable cells with location so we can reinsert
def cells(rel, text_cols=None):
    g = grid(rel)
    out = []
    for ri, row in enumerate(g):
        for ci, cell in enumerate(row):
            c = cell.strip()
            if not c:
                continue
            # translatable if it has JP (kana/kanji), skip pure @tokens/numbers
            if re.search(r'[ぁ-んァ-ヶ一-龥]', c):
                out.append({'row': ri, 'col': ci, 'jp': cell})
    return out

help_items = []
for rel in ['Kaw/key_help.vsc', 'Kaw/game_help.vsc']:
    cs = cells(rel)
    print(f"{rel}: {len(cs)} translatable cells")
    for x in cs:
        x['file'] = rel
    help_items += cs
json.dump(help_items, open(os.path.join(HERE, 'help_cells.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("total help cells:", len(help_items))
print("sample help:", [h['jp'][:20] for h in help_items[:15]])
