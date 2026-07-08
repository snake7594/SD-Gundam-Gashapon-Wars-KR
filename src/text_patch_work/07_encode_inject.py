# -*- coding: utf-8 -*-
"""
한글 대사를 캐리어 코드로 인코딩해 SPB에 동일 크기 제자리 치환.
dry-run(기본): 오버플로/문제만 보고. --apply: 실제 patched_files/에 기록.
"""
import sys, io, os, json, struct, shutil, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from spb_lib import find_text_commands
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
args = ap.parse_args()

occ = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))
ko_by_id = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
id_by_jp = {w['jp']: w['id'] for w in uniq}
carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}

# cp932에 없는 문자 -> 렌더 가능한 등가 문자로 정규화
NORMALIZE = {
    '·': '・',   # · (MIDDLE DOT) -> ・ (KATAKANA MIDDLE DOT, cp932 0x8145)
}

def norm(s):
    return ''.join(NORMALIZE.get(c, c) for c in s)

def is_hangul(ch):
    return 0xAC00 <= ord(ch) <= 0xD7A3

def encode_ko(ko):
    out = bytearray()
    for ch in ko:
        if is_hangul(ch):
            out += carrier[ch]
        else:
            try:
                out += ch.encode('cp932')
            except UnicodeEncodeError:
                out += b'?'
    return bytes(out)

def fit(payload, slot):
    """payload(널 제외) 를 slot(널 포함) 에 맞춤. 길면 문자 경계로 자름."""
    if len(payload) + 1 <= slot:
        return payload + b'\x00' * (slot - len(payload)), False
    # truncate: decode carrier-aware is hard; just cut on cp932 safe boundary won't work for carriers.
    # Instead re-encode char by char until it fits.
    return None, True  # signal overflow, handle by caller with char-wise trim

def encode_ko_fit(ko, slot):
    ko = norm(ko)
    out = bytearray()
    for ch in ko:
        b = carrier[ch] if is_hangul(ch) else (ch.encode('cp932') if _cp932ok(ch) else b'?')
        if len(out) + len(b) + 1 > slot:   # +1 for null
            return bytes(out), True         # truncated
        out += b
    return bytes(out), False

def _cp932ok(ch):
    try:
        ch.encode('cp932'); return True
    except UnicodeEncodeError:
        return False

# group occurrences by file
by_file = {}
for o in occ:
    by_file.setdefault(o['file'], []).append(o)

BASE = Path(os.path.join(HERE, '..', 'files'))
OUT = Path(os.path.join(HERE, 'patched_files'))

overflow = []
total = 0
changed = 0
for rel, items in sorted(by_file.items()):
    src = BASE / rel
    data = bytearray(src.read_bytes())
    for o in items:
        total += 1
        jp = o['jp']
        i = id_by_jp.get(jp)
        ko = ko_by_id.get(str(i), jp)
        slot = o['length']
        so = o['str_off']
        # binary passthrough: if ko == jp and no hangul, keep original bytes
        if ko == jp and not any(is_hangul(c) for c in ko):
            continue
        payload, trunc = encode_ko_fit(ko, slot)
        if trunc:
            overflow.append((rel, o['idx'], slot, len(encode_ko(ko)), ko[:30]))
        newslot = payload + b'\x00' * (slot - len(payload))
        assert len(newslot) == slot
        if args.apply:
            data[so: so + slot] = newslot
        changed += 1
    if args.apply:
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        # size must equal original
        assert dst.stat().st_size == src.stat().st_size, f"size changed {rel}"

print("total occurrences:", total, "changed:", changed)
print("overflow (truncated):", len(overflow))
for x in overflow[:25]:
    print("   ", x)
if args.apply:
    print("APPLIED -> patched_files/")
else:
    print("(dry run; use --apply to write)")
