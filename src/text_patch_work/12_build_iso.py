# -*- coding: utf-8 -*-
"""
원본 GameCube ISO에 (1) 한글 폰트 patched_main.dol, (2) 번역된 SPB들을
전부 '동일 크기 제자리 덮어쓰기'로 주입해 패치 ISO 생성.
"""
import sys, io, os, json, struct, shutil, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--iso', default=os.path.join(HERE, '..', 'kanji_dokuon_auto_patch_tool', 'SD Gundam Gashapon Wars.iso'))
ap.add_argument('--out', default=os.path.join(HERE, '..', 'SD Gundam Gashapon Wars (KR text).iso'))
args = ap.parse_args()

iso = Path(args.iso)
raw = iso.read_bytes() if not args.apply else None

def rd(f, off, n):
    f.seek(off); return f.read(n)

with iso.open('rb') as f:
    hdr = rd(f, 0, 0x440)
    dol_off = struct.unpack('>I', hdr[0x420:0x424])[0]
    fst_off = struct.unpack('>I', hdr[0x424:0x428])[0]
    fst_sz = struct.unpack('>I', hdr[0x428:0x42C])[0]
    fst = rd(f, fst_off, fst_sz)

N = struct.unpack('>I', fst[8:12])[0]
str_base = N * 12
def name_at(o):
    e = fst.index(b'\x00', str_base + o)
    return fst[str_base + o: e].decode('cp932', 'replace')

# traverse FST -> {fullpath: (offset,size)}
files = {}
dir_stack = []       # (name, end_index)
end_stack = [N]
for i in range(1, N):
    while dir_stack and i >= dir_stack[-1][1]:
        dir_stack.pop()
    node = fst[i*12:(i+1)*12]
    typ = node[0]
    name_off = struct.unpack('>I', b'\x00' + node[1:4])[0]
    a, b = struct.unpack('>II', node[4:12])
    name = name_at(name_off)
    if typ == 1:  # dir: a=parent, b=next_index
        dir_stack.append((name, b))
    else:
        path = '/'.join([d[0] for d in dir_stack] + [name])
        files[path] = (a, b)

print("FST entries:", N, "files:", len(files))
print("dol_off=0x%X fst_off=0x%X" % (dol_off, fst_off))

# sanity: verify a couple SPB match extracted originals
BASE = Path(os.path.join(HERE, '..', 'files'))
import random
sample = [p for p in files if p.endswith('.SPB')][:3]
with iso.open('rb') as f:
    for p in sample:
        o, s = files[p]
        disc = rd(f, o, s)
        loc = (BASE / p).read_bytes()
        print(f"  check {p}: iso@0x{o:X} size={s} match_original={disc == loc}")

# collect patch set
PF = Path(os.path.join(HERE, 'patched_files'))
patchset = []   # (path, offset, size, bytes)
# main.dol
newdol = Path(os.path.join(HERE, 'patched_main.dol')).read_bytes()
patchset.append(('<main.dol>', dol_off, len(newdol), newdol))
missing = []
n_spb = n_vsc = 0
for p in sorted(files):
    pf = PF / p
    if pf.exists():
        o, s = files[p]
        b = pf.read_bytes()
        if len(b) != s:
            print("  SIZE MISMATCH", p, len(b), s); missing.append(p); continue
        patchset.append((p, o, s, b))
        if p.endswith('.SPB'): n_spb += 1
        elif p.endswith('.vsc'): n_vsc += 1
print("patch targets:", len(patchset), "(1 dol +", n_spb, "SPB +", n_vsc, "vsc)")

if args.apply:
    out = Path(args.out)
    print("copying ISO ->", out)
    shutil.copyfile(iso, out)
    with out.open('r+b') as f:
        for p, o, s, b in patchset:
            f.seek(o); f.write(b)
    print("patched ISO written:", out, "size", out.stat().st_size)
    # verify size unchanged
    print("size == original:", out.stat().st_size == iso.stat().st_size)
else:
    print("(dry run; use --apply to write ISO)")
