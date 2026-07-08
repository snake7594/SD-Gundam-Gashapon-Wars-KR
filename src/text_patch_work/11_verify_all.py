# -*- coding: utf-8 -*-
import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from spb_lib import find_text_commands
from pathlib import Path

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
rev = {v: k for k, v in carrier.items()}
ko = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
id_by_jp = {w['jp']: w['id'] for w in uniq}
occ = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))
by_key = {(o['file'], o['idx']): o for o in occ}
OUT = Path(os.path.join(HERE, 'patched_files'))
BASE = Path(os.path.join(HERE, '..', 'files'))

def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def decode_payload(raw):
    out = []; i = 0; n = len(raw)
    while i < n:
        if raw[i:i+2] in rev:
            out.append(rev[raw[i:i+2]]); i += 2; continue
        c = raw[i]
        if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i+1 < n:
            try: out.append(raw[i:i+2].decode('cp932')); i += 2; continue
            except: pass
        try: out.append(bytes([c]).decode('cp932'))
        except: out.append('?')
        i += 1
    return ''.join(out).split('\x00')[0]

total_hangul = 0; match = 0; mism = []
for p in glob.glob(str(OUT / '**' / '*.SPB'), recursive=True):
    rel = os.path.relpath(p, OUT).replace(os.sep, '/')
    data = Path(p).read_bytes()
    for idx, c in enumerate(find_text_commands(data)):
        o = by_key.get((rel, idx))
        if not o: continue
        intended = ko[str(id_by_jp[o['jp']])]
        if not any(is_h(ch) for ch in intended):
            continue  # skip passthrough / non-hangul
        total_hangul += 1
        got = decode_payload(c['raw'])
        if got == intended: match += 1
        elif len(mism) < 12: mism.append((rel, idx, intended[:35], got[:35]))

print(f"hangul-bearing strings: {total_hangul}, round-trip match: {match}")
print("mismatches:", len(mism))
for m in mism: print("   ", m)
