# -*- coding: utf-8 -*-
"""SPB 리소스 참조 이름 오번역 수정.
버그: 유닛명·지형/맵 데이터명 등 '리소스 참조'가 대사(04 00 텍스트명령)로 오인돼 번역됨
 -> 게임이 그 이름으로 유닛/맵/지형을 로드하지 못해 진행 정지(미션4 등).
판별: @ 색상/제어토큰이 없는 '맨 이름'(문장부호 없음) = 참조 -> 일본어 원본 유지.
수정: 해당 텍스트명령 페이로드를 원본 일본어로 되돌림(동일 크기 제자리)."""
import sys, io, os, json, struct, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '..', 'files')
PF = os.path.join(HERE, 'patched_files')
NL = chr(10); BS = chr(92)
SENT_PUNCT = set('。！？、…（）') | {NL}

def is_ref(jp):
    """리소스 참조인가: @토큰·\\n 없고, 문장부호 없는 이름."""
    if '@' in jp or BS in jp:
        return False
    s = jp.strip()
    if not (1 <= len(s) <= 24):
        return False
    if any(c in SENT_PUNCT for c in s):
        return False
    if any(ord(c) < 0x20 for c in s):
        return False
    if not any(0x3040 <= ord(c) <= 0x30ff or 0x4e00 <= ord(c) <= 0x9fff or 0xFF00 <= ord(c) <= 0xFFEF for c in s):
        return False
    return True

da = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))
# group reference entries by file
by_file = {}
for e in da:
    if is_ref(e['jp']):
        by_file.setdefault(e['file'], []).append(e)

total = 0
names = set()
for rel, entries in sorted(by_file.items()):
    orig_path = os.path.join(BASE, rel.replace('/', os.sep))
    pat_path = os.path.join(PF, rel.replace('/', os.sep))
    if not os.path.exists(pat_path):
        continue
    o = open(orig_path, 'rb').read()
    p = bytearray(open(pat_path, 'rb').read())
    changed = 0
    for e in entries:
        so = e['str_off']; ln = e['length']
        if o[so:so + ln] != bytes(p[so:so + ln]):
            p[so:so + ln] = o[so:so + ln]   # revert payload to original JP
            changed += 1
            names.add(e['jp'])
    if changed:
        assert len(p) == len(o)
        open(pat_path, 'wb').write(bytes(p))
        total += changed
        print('%s: reverted %d reference(s)' % (os.path.basename(rel), changed))
print('total references reverted:', total)
print('unique reference names kept in Japanese:', sorted(names))
