# -*- coding: utf-8 -*-
"""화자명 플레이트 진단/수정: pbmode_character.vsc의 col1(표시명, 전체) 번역에 더해
col0(キャラクター名=키)를 **다른 설정파일에서 참조되지 않는 SAFE 캐릭터만** 번역.
(시나리오 화자 플레이트가 col0를 표시하는 것으로 추정 — col1은 번역돼도 원본표시됨.)
동일 크기(공백 패딩), 원본에서 재생성."""
import sys, io, os, json, glob, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode, vsc_encode
BASE = os.path.join(HERE, '..', 'files')
OUT = os.path.join(HERE, 'patched_files')
NL = '\r\n'
ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); args = ap.parse_args()

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
dm = json.load(open(os.path.join(HERE, 'disp_map.json'), encoding='utf-8'))['char']
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

REL = 'Character/PbMode/pbmode_character.vsc'
raw = open(os.path.join(BASE, REL), 'rb').read()
plain = vsc_decode(raw)
text = plain.decode('cp932')
rows = [ln.split(',') for ln in text.split(NL)]
col0names = [r[0] for r in rows[1:] if r and r[0]]

# SAFE = col0 name not present in ANY other config file (vsc except this, + main.dol)
corpus = b''
for f in glob.glob(os.path.join(BASE, '**', '*.vsc'), recursive=True):
    if 'pbmode_character' in f: continue
    try: corpus += vsc_decode(open(f, 'rb').read())
    except Exception: pass
corpus += open(os.path.join(HERE, '..', 'sys', 'main.dol'), 'rb').read()
SAFE = set()
for n in col0names:
    try: b = n.encode('cp932')
    except Exception: continue
    if b not in corpus:
        SAFE.add(n)
print('SAFE col0 (translatable):', sorted(SAFE))

c0 = c1 = 0
for r in rows[1:]:
    if len(r) < 2: continue
    # col1 display (all mapped)
    if r[1] in dm: r[1] = dm[r[1]]; c1 += 1
    # col0 only if SAFE and mapped
    if r[0] in SAFE and r[0] in dm: r[0] = dm[r[0]]; c0 += 1
print('col0 translated:', c0, 'col1 translated:', c1)

new_plain = NL.encode('cp932').join(b','.join(enc(c) for c in r) for r in rows)
assert len(new_plain) <= len(plain), (len(new_plain), len(plain))
pad = len(plain) - len(new_plain)
if new_plain.endswith(b'\r\n'):
    new_plain = new_plain[:-2] + b' ' * pad + b'\r\n'
else:
    new_plain = new_plain + b' ' * pad
assert len(new_plain) == len(plain)
new_raw = vsc_encode(new_plain)
assert len(new_raw) == len(raw)

if args.apply:
    dst = os.path.join(OUT, REL)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(new_raw)
    print('APPLIED', REL, 'size==orig', os.path.getsize(dst) == len(raw))
