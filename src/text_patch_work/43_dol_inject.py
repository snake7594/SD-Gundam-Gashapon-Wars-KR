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
# CSV 헤더/키 문자열은 번역하면 파싱 붕괴 -> 제외
_excl = set(json.load(open(os.path.join(HERE, 'dol_exclude_keys.json'), encoding='utf-8')))
entries = [e for e in entries if e['jp'] not in _excl]
# 추출범위 밖 보충 표시문구(はい/いいえ/とじる 등)
_extra_p = os.path.join(HERE, 'dol_extra.json')
if os.path.exists(_extra_p):
    entries += json.load(open(_extra_p, encoding='utf-8'))
print("key-excluded, injecting entries:", len(entries))
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

# 모든 주입 후보(occurrence) 평탄화: (off, nb, payload)
cand = []
over = 0
for e in entries:
    payload = enc(e['ko'])
    if len(payload) > e['budget']:
        over += 1; continue
    for occ in e['occ']:
        off, nb = occ['off'], occ['nbytes']
        if len(payload) > nb:
            continue
        cand.append((off, nb, payload))

# 겹침 제거: off 오름차순, 같은 off면 nb 큰(바깥) 것 우선 -> 바깥만 채택, 안쪽 가짜 tail 스킵
cand.sort(key=lambda c: (c[0], -c[1]))
selected = []
last_end = -1
dropped_overlap = 0
for off, nb, payload in cand:
    end = off + nb + 1
    if off < last_end:          # 이전 채택 구간과 겹침 -> 스킵(가짜 tail)
        dropped_overlap += 1
        continue
    selected.append((off, nb, payload))
    last_end = end

changed = 0; skipped = 0
for off, nb, payload in selected:
    if in_tex(off, nb + 1):
        skipped += 1; continue
    dol[off: off + nb + 1] = payload + b'\x00' * (nb + 1 - len(payload))
    changed += 1
print("overlap dropped (fake tails):", dropped_overlap)

print("DOL string occurrences changed:", changed, " over:", over, " skipped(tex):", skipped)
if args.apply:
    Path(os.path.join(HERE, 'patched_main.dol')).write_bytes(dol)
    print("patched_main.dol updated")
else:
    print("(dry run)")
