# -*- coding: utf-8 -*-
import sys, io, json, glob, os, re, statistics
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spb_lib import extract_file
from pathlib import Path

BASE = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files'))
files = sorted(glob.glob(str(BASE / 'Spb' / '**' / '*.SPB'), recursive=True))

allrows = []
per_file = {}
total = 0
uniq = {}
for fp in files:
    rel = os.path.relpath(fp, BASE).replace(os.sep, '/')
    info = extract_file(Path(fp))
    n = len(info['cmds'])
    per_file[rel] = n
    total += n
    for idx, c in enumerate(info['cmds']):
        row = {
            'file': rel, 'idx': idx,
            'str_off': c['str_off'], 'length': c['length'],
            'jp': c['text'],
        }
        allrows.append(row)
        uniq.setdefault(c['text'], []).append(len(allrows) - 1)

json.dump(allrows, open(os.path.join(os.path.dirname(__file__), 'dialogue_all.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print("SPB files:", len(files))
print("text commands:", total)
print("unique JP strings:", len(uniq))
fold = {}
for r in allrows:
    parts = r['file'].split('/')
    k = parts[1] if len(parts) > 1 else parts[0]
    fold[k] = fold.get(k, 0) + 1
print("per-folder:", fold)
lens = [r['length'] for r in allrows]
print("length bytes(incl null): min=%d max=%d mean=%.1f" % (min(lens), max(lens), statistics.mean(lens)))

# duplicate savings
dupcount = sum(len(v) - 1 for v in uniq.values() if len(v) > 1)
print("duplicate strings (repeats):", dupcount)

# sample a few
print("\n--- samples ---")
for r in allrows[:3]:
    print(" ", r['file'], r['idx'], repr(r['jp'][:60]))
