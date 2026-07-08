# -*- coding: utf-8 -*-
import sys, io, os, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from spb_lib import find_text_commands
from pathlib import Path

ISO = Path(os.path.join(HERE, '..', 'SD Gundam Gashapon Wars (KR text).iso'))
carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
rev = {v: k for k, v in carrier.items()}

def dec(raw):
    out = []; i = 0; n = len(raw)
    while i < n:
        if raw[i:i+2] in rev: out.append(rev[raw[i:i+2]]); i += 2; continue
        c = raw[i]
        if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i+1 < n:
            try: out.append(raw[i:i+2].decode('cp932')); i += 2; continue
            except: pass
        try: out.append(bytes([c]).decode('cp932'))
        except: out.append('?')
        i += 1
    return ''.join(out).split('\x00')[0]

with ISO.open('rb') as f:
    hdr = f.read(0x440)
    dol_off = struct.unpack('>I', hdr[0x420:0x424])[0]
    fst_off = struct.unpack('>I', hdr[0x424:0x428])[0]
    fst_sz = struct.unpack('>I', hdr[0x428:0x42C])[0]
    f.seek(fst_off); fst = f.read(fst_sz)
    N = struct.unpack('>I', fst[8:12])[0]
    sb = N * 12
    def nm(o):
        return fst[sb+o: fst.index(b'\x00', sb+o)].decode('cp932', 'replace')
    # find target SPBs
    targets = ['M00_00.SPB', 'M50_00.SPB', 'M00_10.SPB']
    found = {}
    ds = []
    for i in range(1, N):
        while ds and i >= ds[-1][1]: ds.pop()
        node = fst[i*12:(i+1)*12]; typ = node[0]
        no = struct.unpack('>I', b'\x00'+node[1:4])[0]
        a, b = struct.unpack('>II', node[4:12])
        name = nm(no)
        if typ == 1: ds.append((name, b))
        elif name in targets and name not in found:
            found[name] = (a, b)
    # 1) DOL font check: read a carrier cell char code area? Simpler: compare dol in iso vs patched_main.dol
    f.seek(dol_off); dol_in_iso = f.read(len(Path(os.path.join(HERE,'patched_main.dol')).read_bytes()))
    same = dol_in_iso == Path(os.path.join(HERE, 'patched_main.dol')).read_bytes()
    print("main.dol in ISO == patched_main.dol:", same)
    # 2) decode SPBs straight from ISO
    for name, (o, s) in found.items():
        f.seek(o); data = f.read(s)
        cmds = find_text_commands(data)
        print("\n===", name, "@0x%X size=%d, text cmds=%d ===" % (o, s, len(cmds)))
        shown = 0
        for c in cmds:
            t = dec(c['raw'])
            if any(0xAC00 <= ord(ch) <= 0xD7A3 for ch in t):
                print("   ", t[:64])
                shown += 1
                if shown >= 6: break
