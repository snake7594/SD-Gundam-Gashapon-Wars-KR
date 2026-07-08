# -*- coding: utf-8 -*-
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode
BS = chr(92)
PATH_MARKS = ('/', '.csv', '.vsc', '.dat', '.arc', '.bin', '.thp', '.tpl', BS)

def is_path(s):
    return any(x in s for x in PATH_MARKS) or s.endswith('.h')

# 1) DOL missed 필터 + 배치
missed = json.load(open(os.path.join(HERE, 'dol_missed.json'), encoding='utf-8'))
mwork = [m for m in missed if not is_path(m['jp'])]
os.makedirs(os.path.join(HERE, 'dolm_batches'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'dolm_out'), exist_ok=True)
NB = 5
for k in range(NB):
    part = [x for i, x in enumerate(mwork) if i % NB == k]
    json.dump(part, open(os.path.join(HERE, 'dolm_batches', f'dolm_{k}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
print("DOL missed translatable:", len(mwork), "(skipped paths:", len(missed) - len(mwork), ") ->", NB, "batches")

# 2) 캐릭터/지형 표시명 고유
def grid(rel):
    return [l.split(',') for l in vsc_decode(open(os.path.join(HERE, '..', 'files', rel), 'rb').read()).decode('cp932', 'replace').split('\r\n')]

ch = grid('Character/PbMode/pbmode_character.vsc')
chdisp = []; seen = set()
for r in ch[1:]:
    if len(r) > 1 and r[1].strip() and r[1] not in seen:
        seen.add(r[1]); chdisp.append(r[1])
at = grid('Field/PbMode/pbmode_attr.vsc')
atdisp = []; seen = set()
for r in at[1:]:
    if len(r) > 1 and r[1].strip() and r[1] not in seen:
        seen.add(r[1]); atdisp.append(r[1])
disp = [{'id': i, 'jp': n, 'kind': 'char'} for i, n in enumerate(chdisp)] + \
       [{'id': 1000 + i, 'jp': n, 'kind': 'terrain'} for i, n in enumerate(atdisp)]
json.dump(disp, open(os.path.join(HERE, 'disp_names.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("display names (char %d + terrain %d) = %d" % (len(chdisp), len(atdisp), len(disp)))
print("  char:", chdisp)
print("  terrain:", atdisp)
