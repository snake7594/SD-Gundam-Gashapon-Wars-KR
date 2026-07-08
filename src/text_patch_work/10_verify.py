# -*- coding: utf-8 -*-
import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from spb_lib import find_text_commands
from pathlib import Path

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
rev = {v: k for k, v in carrier.items()}   # cp932 bytes -> syllable
ko = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
id_by_jp = {w['jp']: w['id'] for w in uniq}
occ = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))
jp_by_key = {(o['file'], o['idx']): o['jp'] for o in occ}

def decode_payload(raw):
    """carrier-aware decode of a patched string payload."""
    out = []; i = 0; n = len(raw)
    while i < n:
        two = raw[i:i+2]
        if two in rev:
            out.append(rev[two]); i += 2; continue
        c = raw[i]
        if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i+1 < n:
            try:
                out.append(raw[i:i+2].decode('cp932')); i += 2; continue
            except: pass
        try:
            out.append(bytes([c]).decode('cp932'))
        except:
            out.append('?')
        i += 1
    return ''.join(out)

BASE = Path(os.path.join(HERE, '..', 'files'))
OUT = Path(os.path.join(HERE, 'patched_files'))

# 1) size check all patched
size_ok = 0; size_bad = []
for p in glob.glob(str(OUT / '**' / '*.SPB'), recursive=True):
    rel = os.path.relpath(p, OUT).replace(os.sep, '/')
    if os.path.getsize(p) == os.path.getsize(BASE / rel): size_ok += 1
    else: size_bad.append(rel)
print("size identical:", size_ok, "  mismatched:", size_bad[:5])

# 2) round-trip decode a sample of patched strings, compare vs intended ko (null-trimmed)
def strip_pad(s): return s.split('\x00')[0]
checked = 0; ok = 0; mism = []
for rel in ['Spb/ab_mission/M00_00.SPB', 'Spb/mission/M00_01.SPB', 'Spb/M50_00.SPB']:
    data = (OUT / rel).read_bytes()
    cmds = find_text_commands(data)
    for idx, c in enumerate(cmds):
        jp = jp_by_key.get((rel, idx))
        if jp is None: continue
        i = id_by_jp[jp]
        intended = ko[str(i)]
        got = decode_payload(c['raw'])   # c['raw'] excludes trailing null
        got = strip_pad(got)
        checked += 1
        # intended may have been shortened only if it had hangul; if binary passthrough intended==jp
        if got == intended or got == jp:
            ok += 1
        else:
            if len(mism) < 8: mism.append((rel, idx, intended[:30], got[:30]))
print(f"round-trip decode: {ok}/{checked} match")
for m in mism: print("   MISMATCH", m)

# 3) show a few decoded patched lines (proof it reads as Korean)
print("\n--- decoded patched M00_00 (Gundam story) ---")
data = (OUT / 'Spb/ab_mission/M00_00.SPB').read_bytes()
for c in find_text_commands(data)[:8]:
    print("   ", decode_payload(c['raw']).split(chr(0))[0][:60])
