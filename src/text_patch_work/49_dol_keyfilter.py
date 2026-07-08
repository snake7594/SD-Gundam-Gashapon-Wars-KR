# -*- coding: utf-8 -*-
"""main.dol UI 문자열 중 'CSV 헤더/키'인 것을 찾아 주입 제외 목록 생성.
게임이 .vsc 파싱 시 strcmp하는 키를 번역하면 매칭 실패->크래시."""
import sys, io, os, json, glob, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode

# 1) 모든 .vsc의 '셀' 문자열 수집 (헤더 포함 전체) — main.dol과 공유되면 키 의심
# 표시용 .vsc(번역 대상)는 col0가 키 아님 -> col0 제외에서 뺌
DISPLAY_VSC = ('key_help.vsc', 'game_help.vsc', 'capsule_box.vsc')
vsc_cells = set()
vsc_headers = set()   # 모든 .vsc 헤더(row0) = strcmp 컬럼키
vsc_col0 = set()      # 데이터 .vsc col0 값 = 조회 키(유닛명/지형명/맵명 등)
for p in glob.glob(os.path.join(HERE, '..', 'files', '**', '*.vsc'), recursive=True):
    try:
        txt = vsc_decode(open(p, 'rb').read()).decode('cp932', 'replace')
    except Exception:
        continue
    is_display = os.path.basename(p) in DISPLAY_VSC
    rows = [ln.split(',') for ln in txt.split('\r\n')]
    for ri, row in enumerate(rows):
        for ci, c in enumerate(row):
            c = c.strip()
            if c:
                vsc_cells.add(c)
                if ri == 0:
                    vsc_headers.add(c)
                if ci == 0 and ri >= 1 and not is_display:
                    vsc_col0.add(c)
print("전체 .vsc 셀:", len(vsc_cells), " 헤더:", len(vsc_headers), " 데이터col0:", len(vsc_col0))

# 2) main.dol 주입 대상 중 .vsc 셀과 일치(=키 의심) 찾기
dol = open(os.path.join(HERE, '..', 'sys', 'main.dol'), 'rb').read()
def secs():
    r = []
    for i in range(18):
        off = struct.unpack('>I', dol[i*4:i*4+4])[0]; addr = struct.unpack('>I', dol[0x48+i*4:0x48+i*4+4])[0]; size = struct.unpack('>I', dol[0x90+i*4:0x90+i*4+4])[0]
        if off and size: r.append((off, addr, size))
    return r
S = secs()
def f2ram(fo):
    for off, addr, size in S:
        if off <= fo < off+size: return addr+(fo-off)
    return 0
# 참조 포인터 집합 (4바이트 BE)
refs = set()
for i in range(0, len(dol)-3):
    v = struct.unpack('>I', dol[i:i+4])[0]
    if 0x80003000 <= v < 0x80400000: refs.add(v)

def has_kana(s): return any(0x3040 <= ord(c) <= 0x30FF for c in s)

entries = json.load(open(os.path.join(HERE, 'dol_inject_all.json'), encoding='utf-8'))
exclude = []
keep = []
for e in entries:
    jp = e['jp']
    ram = f2ram(e['occ'][0]['off'])
    referenced = ram in refs
    # 정밀 제외 규칙(크래시 원인=CSV 헤더 매칭):
    #  (a) .vsc 컬럼 헤더(row0)와 일치 = 파서가 strcmp하는 키
    #  (b) 순수한자 & 포인터 미참조 = strcmp 키/데이터 의심(설정라벨 등, 정상플레이 미노출)
    is_key = (jp in vsc_headers) or (jp in vsc_col0) or ((not has_kana(jp)) and (not referenced))
    if is_key:
        exclude.append(jp)
    else:
        keep.append(jp)

json.dump(exclude, open(os.path.join(HERE, 'dol_exclude_keys.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("\n제외(키 의심):", len(exclude), "  주입유지:", len(keep))
print("\n제외 샘플:")
for j in exclude[:30]: print("   ", j[:22])
print("\n유지 샘플(표시용):")
for j in keep[:15]: print("   ", j[:26].replace('\n',' '))
