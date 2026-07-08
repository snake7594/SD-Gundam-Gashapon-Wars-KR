# -*- coding: utf-8 -*-
import sys, io, os, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode
ISO = os.path.join(HERE, '..', 'SD Gundam Gashapon Wars (KR text).iso')
ORIG = os.path.join(HERE, '..', 'kanji_dokuon_auto_patch_tool', 'SD Gundam Gashapon Wars.iso')
carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
rev = {v: k for k, v in carrier.items()}

def dec(raw, stop_null=True):
    out = []; i = 0; n = len(raw)
    while i < n:
        if stop_null and raw[i] == 0: break
        if raw[i:i+2] in rev: out.append(rev[raw[i:i+2]]); i += 2; continue
        c = raw[i]
        if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i+1 < n:
            try: out.append(raw[i:i+2].decode('cp932')); i += 2; continue
            except: pass
        try: out.append(bytes([c]).decode('cp932'))
        except: out.append('?')
        i += 1
    return ''.join(out)

f = open(ISO, 'rb'); fo = open(ORIG, 'rb'); hdr = f.read(0x440)
dol_off = struct.unpack('>I', hdr[0x420:0x424])[0]
fst_off = struct.unpack('>I', hdr[0x424:0x428])[0]
f.seek(fst_off); fst = f.read(struct.unpack('>I', hdr[0x428:0x42C])[0])
N = struct.unpack('>I', fst[8:12])[0]; sb = N * 12
def nm(o): return fst[sb+o: fst.index(b'\x00', sb+o)].decode('cp932', 'replace')
want = ['ユニットデータ.vsc', 'pbmode_unit.vsc', 'gallery.vsc', 'pbmode_character.vsc', 'pbmode_attr.vsc']
found = {}; ds = []
for i in range(1, N):
    while ds and i >= ds[-1]: ds.pop()
    nd = fst[i*12:(i+1)*12]; typ = nd[0]; no = struct.unpack('>I', b'\x00'+nd[1:4])[0]
    a, b = struct.unpack('>II', nd[4:12]); name = nm(no)
    if typ == 1: ds.append(b)
    elif name in want and name not in found: found[name] = (a, b)

def rows(name):
    o, s = found[name]; f.seek(o); return dec(vsc_decode(f.read(s)), stop_null=False)

print("=== 키 무결성 (원본과 동일해야 유닛/참조 정상) ===")
for name in ['ユニットデータ.vsc', 'pbmode_unit.vsc', 'gallery.vsc']:
    o, s = found[name]; f.seek(o); p = f.read(s); fo.seek(o); og = fo.read(s)
    print(f"  {name}: 원본동일={p == og}")

print("\n=== 캐릭터 표시명 (col1 한글, col0 키 원본) ===")
for r in [l.split(',') for l in rows('pbmode_character.vsc').split('\r\n')][1:6]:
    print("  key(col0)=%s  disp(col1)=%s" % (r[0], r[1] if len(r) > 1 else ''))

print("\n=== 지형 표시명 ===")
for r in [l.split(',') for l in rows('pbmode_attr.vsc').split('\r\n')][1:8]:
    print("  key=%s  disp=%s" % (r[0], r[1] if len(r) > 1 else ''))

print("\n=== main.dol UI (ISO에서) ===")
f.seek(dol_off); dol = f.read(fst_off - dol_off)
entries = json.load(open(os.path.join(HERE, 'dol_inject_all.json'), encoding='utf-8'))
samples = ['ポーズメニュー', 'よろしいですか？', 'まかせた！', 'ゲーム|再開', 'セーブ']
shown = 0
for e in entries:
    if any(s.split('|')[0] in e['jp'] for s in samples) or shown < 8:
        off = e['occ'][0]['off']
        print("  %s -> %s" % (e['jp'][:22].replace('\n', ' '), dec(dol[off:off+e['occ'][0]['nbytes']+1]).replace('\n', ' ')[:26]))
        shown += 1
    if shown >= 14: break
print("\n폰트앵커 존재:", '一右雨円王音'.encode('cp932') in dol)
