# -*- coding: utf-8 -*-
"""캐릭터/지형 '표시명'(col1)만 번역 주입. 키(col0)는 원본 유지 -> 안전. 동일 크기."""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode, vsc_encode
BASE = os.path.join(HERE, '..', 'files')
OUT = os.path.join(HERE, 'patched_files')

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
args = ap.parse_args()

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
dm = json.load(open(os.path.join(HERE, 'disp_map.json'), encoding='utf-8'))
NORMALIZE = {'·': '・'}

def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def enc(s):
    out = bytearray()
    for ch in s:
        ch = NORMALIZE.get(ch, ch)
        if is_h(ch): out += carrier[ch]
        else:
            try: out += ch.encode('cp932')
            except UnicodeEncodeError: out += b'?'
    return bytes(out)

# (file, display-col-index, map)
TARGETS = [
    ('Character/PbMode/pbmode_character.vsc', 1, dm['char']),
    ('Field/PbMode/pbmode_attr.vsc', 1, dm['terrain']),
]

def process(rel, col, mp):
    raw = open(os.path.join(BASE, rel), 'rb').read()
    plain = vsc_decode(raw)
    text = plain.decode('cp932')
    rows = [ln.split(',') for ln in text.split('\r\n')]
    assert '\r\n'.join(','.join(r) for r in rows) == text
    changed = 0
    for r in rows[1:]:
        if col < len(r) and r[col] in mp:
            r[col] = mp[r[col]]; changed += 1
    new_plain = b'\r\n'.join(b','.join(enc(c) for c in r) for r in rows)
    if len(new_plain) > len(plain):
        return rel, changed, len(new_plain) - len(plain), None
    pad = len(plain) - len(new_plain)
    if new_plain.endswith(b'\r\n'):
        new_plain = new_plain[:-2] + b' ' * pad + b'\r\n'
    else:
        new_plain = new_plain + b' ' * pad
    assert len(new_plain) == len(plain)
    new_raw = vsc_encode(new_plain)
    assert len(new_raw) == len(raw)
    return rel, changed, 0, new_raw

for rel, col, mp in TARGETS:
    rel_, changed, over, new_raw = process(rel, col, mp)
    if over:
        print(f"  [OVERFLOW] {rel}: +{over} bytes")
    else:
        print(f"  {rel}: {changed} cells changed, fits")
        if args.apply and new_raw is not None:
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(new_raw)
print("APPLIED" if args.apply else "(dry run)")
