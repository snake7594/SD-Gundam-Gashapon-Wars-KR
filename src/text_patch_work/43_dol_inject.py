# -*- coding: utf-8 -*-
"""main.dol UI 문자열(dol_inject_all.json)을 캐리어 인코딩 동일 크기 제자리 치환."""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'kanji_dokuon_auto_patch_tool'))
import patch_kanji_dokuon_font_auto as T
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
args = ap.parse_args()

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
entries = json.load(open(os.path.join(HERE, 'dol_inject_all.json'), encoding='utf-8'))
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

dol = bytearray(Path(os.path.join(HERE, 'patched_main.dol')).read_bytes())
tex_ranges = []
for tex in T.DEFAULT_KANJI_TEXTURES:
    info = T.read_texture_info(dol, tex)
    tex_ranges.append((info.image_offset, info.image_offset + info.image_size))
def in_tex(off, nb):
    return any(off < b and off + nb > a for a, b in tex_ranges)

changed = 0; over = 0; skipped = 0
for e in entries:
    payload = enc(e['ko'])
    if len(payload) > e['budget']:
        over += 1; continue
    for occ in e['occ']:
        off, nb = occ['off'], occ['nbytes']
        if len(payload) > nb: continue
        if in_tex(off, nb + 1): skipped += 1; continue
        dol[off: off + nb + 1] = payload + b'\x00' * (nb + 1 - len(payload))
        changed += 1

print("DOL string occurrences changed:", changed, " over:", over, " skipped(tex):", skipped)
if args.apply:
    Path(os.path.join(HERE, 'patched_main.dol')).write_bytes(dol)
    print("patched_main.dol updated")
else:
    print("(dry run)")
