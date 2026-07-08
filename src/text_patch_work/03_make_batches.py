# -*- coding: utf-8 -*-
import sys, io, json, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))

# unique JP strings -> stable ids
uniq = {}
for r in rows:
    uniq.setdefault(r['jp'], None)
keys = list(uniq.keys())
worklist = [{'id': i, 'jp': jp} for i, jp in enumerate(keys)]
json.dump(worklist, open(os.path.join(HERE, 'unique_jp.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# split into batches
NB = 20
batches = [[] for _ in range(NB)]
for w in worklist:
    batches[w['id'] % NB].append(w)
os.makedirs(os.path.join(HERE, 'batches'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'translated'), exist_ok=True)
for i, b in enumerate(batches):
    json.dump(b, open(os.path.join(HERE, 'batches', f'batch_{i:02d}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
print("unique strings:", len(worklist))
print("batches:", NB, "avg size:", len(worklist) // NB)
