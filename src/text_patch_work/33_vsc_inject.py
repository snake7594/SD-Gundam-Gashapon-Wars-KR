# -*- coding: utf-8 -*-
"""
.vsc(메뉴/도움말/유닛명) 번역 주입. 동일 크기(후행 공백 패딩) + 캐리어 인코딩.
대상: Kaw/key_help.vsc, Kaw/game_help.vsc (도움말 셀 치환)
      Kaw/gallery.vsc, Unit/PbMode/pbmode_unit.vsc, Unit/AbMode/ユニットデータ.vsc (col0 유닛명)
"""
import sys, io, os, json, re, argparse
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
name_map = json.load(open(os.path.join(HERE, 'unit_name_map.json'), encoding='utf-8'))
help_final = json.load(open(os.path.join(HERE, 'help_final.json'), encoding='utf-8'))
NORMALIZE = {'·': '・'}

def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def enc_text(s):
    out = bytearray()
    for ch in s:
        ch = NORMALIZE.get(ch, ch)
        if is_h(ch):
            out += carrier[ch]
        else:
            try: out += ch.encode('cp932')
            except UnicodeEncodeError: out += b'?'
    return bytes(out)

# 유닛명: 길이 내림차순으로 substring 치환 (최장일치)
names_sorted = sorted(name_map.keys(), key=len, reverse=True)
def translate_name_cell(cell):
    s = cell
    for jp in names_sorted:
        if jp in s:
            s = s.replace(jp, name_map[jp])
    return s

# help 치환 맵: file -> {(row,col): ko}
help_by_file = {}
for h in help_final:
    help_by_file.setdefault(h['file'], {})[(h['row'], h['col'])] = h['ko']

NAME_FILES = {}  # 유닛명은 내부 키라 미번역(가타카나 유지)
HELP_FILES = ['Kaw/key_help.vsc', 'Kaw/game_help.vsc']

def process(rel):
    raw = open(os.path.join(BASE, rel), 'rb').read()
    plain = vsc_decode(raw)                       # bytes
    text = plain.decode('cp932')                  # str
    rows = [ln.split(',') for ln in text.split('\r\n')]

    # round-trip identity self-check (구조 안전성)
    rebuilt = '\r\n'.join(','.join(r) for r in rows)
    assert rebuilt == text, f"CSV round-trip mismatch in {rel}"

    changed = 0
    if rel in HELP_FILES:
        hm = help_by_file.get(rel, {})
        for (ri, ci), ko in hm.items():
            if ri < len(rows) and ci < len(rows[ri]):
                rows[ri][ci] = ko; changed += 1
    if rel in NAME_FILES:
        for ci in NAME_FILES[rel]:
            for ri in range(1, len(rows)):
                if ci < len(rows[ri]) and rows[ri][ci].strip():
                    new = translate_name_cell(rows[ri][ci])
                    if new != rows[ri][ci]:
                        rows[ri][ci] = new; changed += 1

    # serialize to bytes with carrier encoding
    row_bytes = []
    for r in rows:
        row_bytes.append(b','.join(enc_text(c) for c in r))
    new_plain = b'\r\n'.join(row_bytes)

    orig_len = len(plain)
    if len(new_plain) > orig_len:
        return rel, changed, len(new_plain) - orig_len, None   # overflow
    # pad: 마지막 \r\n 앞(마지막 필드 끝)에 공백 삽입 -> 새 행 안 생김
    pad = orig_len - len(new_plain)
    if new_plain.endswith(b'\r\n'):
        new_plain = new_plain[:-2] + b' ' * pad + b'\r\n'
    else:
        new_plain = new_plain + b' ' * pad
    assert len(new_plain) == orig_len
    new_raw = vsc_encode(new_plain)
    assert len(new_raw) == len(raw)
    return rel, changed, 0, new_raw

for rel in list(NAME_FILES) + HELP_FILES:
    rel_, changed, over, new_raw = process(rel)
    if over:
        print(f"  [OVERFLOW] {rel}: +{over} bytes (need shorten)")
    else:
        print(f"  {rel}: {changed} cells changed, fits (pad ok)")
        if args.apply and new_raw is not None:
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(new_raw)

print("APPLIED to patched_files/" if args.apply else "(dry run)")
