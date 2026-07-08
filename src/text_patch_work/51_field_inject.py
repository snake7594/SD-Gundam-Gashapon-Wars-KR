# -*- coding: utf-8 -*-
"""filed_select.vsc 에 맵명(col0)+설명(col3~5) 주입. 헤더/데이터열 유지, 동일 크기."""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode, vsc_encode
BASE = os.path.join(HERE, '..', 'files')
OUT = os.path.join(HERE, 'patched_files')
ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); args = ap.parse_args()

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
fmap = {int(k): v for k, v in json.load(open(os.path.join(HERE, 'field_map.json'), encoding='utf-8')).items()}
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

REL = 'Field/AbMode/filed_select.vsc'
raw = open(os.path.join(BASE, REL), 'rb').read()
plain = vsc_decode(raw)
text = plain.decode('cp932')
rows = [ln.split(',') for ln in text.split('\r\n')]
assert '\r\n'.join(','.join(r) for r in rows) == text
changed = 0
for ri, cols in fmap.items():
    if ri >= len(rows):
        continue
    for ci, ko in cols.items():
        ci = int(ci)
        if ci < len(rows[ri]):
            rows[ri][ci] = ko; changed += 1
new_plain = b'\r\n'.join(b','.join(enc(c) for c in r) for r in rows)
if len(new_plain) > len(plain):
    print("[OVERFLOW] +%d bytes" % (len(new_plain) - len(plain)))
else:
    pad = len(plain) - len(new_plain)
    if new_plain.endswith(b'\r\n'):
        new_plain = new_plain[:-2] + b' ' * pad + b'\r\n'
    else:
        new_plain = new_plain + b' ' * pad
    assert len(new_plain) == len(plain)
    new_raw = vsc_encode(new_plain)
    assert len(new_raw) == len(raw)
    print("filed_select: %d cells changed, fits" % changed)
    if args.apply:
        dst = os.path.join(OUT, REL)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(new_raw)
        print("APPLIED")
