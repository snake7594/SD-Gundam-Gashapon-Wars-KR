# -*- coding: utf-8 -*-
"""폭 초과 KO 대사만 골라 토큰 보존 재래핑(<=WRAP 폭, 줄수 <=MAXLINES)."""
import sys, io, os, json, re, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92); SINGLE = BS + 'n'; DOUBLE = BS + BS + 'n'
WRAP = 24.0          # 목표 최대 표시폭(전각 단위)
MAXLINES = 5

ko = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
TOKEN = re.compile(r'@[a-z0-9][0-9a-f]')

def cw(ch):
    return 0.0 if False else (0.5 if ord(ch) < 0x100 else 1.0)

def disp_width(line):
    line = TOKEN.sub('', line)
    return sum(cw(c) for c in line)

def nl_form(s):
    # 삽입 개행은 항상 SINGLE(\n, 2바이트)로 -> 바이트 절약(게임은 두 형태 모두 개행 처리)
    return SINGLE

def tokenize(s):
    """제어토큰과 텍스트를 순서 보존해 토큰 리스트로. 토큰은 ('T',code), 문자 ('C',ch)."""
    out = []; i = 0
    while i < len(s):
        m = TOKEN.match(s, i)
        if m:
            out.append(('T', m.group(0))); i = m.end(); continue
        out.append(('C', s[i])); i += 1
    return out

def rewrap(s):
    form = nl_form(s)
    # 기존 개행/정렬공백 제거 -> 하나의 흐름으로
    flat = s.replace(DOUBLE, ' ').replace(SINGLE, ' ')
    flat = flat.replace('　', ' ')            # 전각 공백 -> 일반 공백
    flat = re.sub(r' {2,}', ' ', flat).strip()  # 연속 공백 축소
    toks = tokenize(flat)
    # 단어 단위(공백 경계)로 청크. 각 청크는 토큰/문자 리스트 + 표시폭.
    words = []; cur = []
    def wwidth(chunk):
        return sum(0 if t == 'T' else cw(c) for t, c in chunk)
    for t, c in toks:
        if t == 'C' and c == ' ':
            if cur: words.append(cur); cur = []
            words.append([('C', ' ')])          # space as its own word
        else:
            cur.append((t, c))
    if cur: words.append(cur)
    # greedy pack
    lines = [[]]
    def linew(ln): return sum(0 if t == 'T' else cw(c) for t, c in ln)
    for w in words:
        wtext = ''.join(c for t, c in w)
        if wtext == ' ':
            if lines[-1] and linew(lines[-1]) > 0:
                lines[-1].append(('C', ' '))
            continue
        ww = wwidth(w)
        if ww > WRAP:  # 한 단어가 너무 길면 문자 단위로 쪼갬
            for t, c in w:
                if linew(lines[-1]) + (0 if t == 'T' else cw(c)) > WRAP and any(x != 'T' for x, _ in lines[-1]):
                    lines.append([])
                lines[-1].append((t, c))
            continue
        if linew(lines[-1]) + ww > WRAP and any(x != 'T' for x, _ in lines[-1]):
            lines.append([])
        lines[-1].extend(w)
    # strip trailing spaces per line
    outlines = []
    for ln in lines:
        while ln and ln[-1] == ('C', ' '):
            ln.pop()
        outlines.append(''.join(c for t, c in ln))
    outlines = [l for l in outlines if l != '']
    return form.join(outlines), len(outlines)

# 대상: 어떤 줄이든 폭 > WRAP 인 문자열
targets = []
for i, s in ko.items():
    parts = re.split(re.escape(BS) + r'+n', s)
    if any(disp_width(p) > WRAP for p in parts):
        targets.append(i)

print("rewrap 대상 문자열:", len(targets))
over_lines = []
changed = {}
for i in targets:
    new, nlines = rewrap(ko[i])
    changed[i] = new
    if nlines > MAXLINES:
        over_lines.append((i, nlines, new[:40]))

print("재래핑 후 줄수 > %d 인 문자열:" % MAXLINES, len(over_lines))
for x in over_lines: print("   ", x)

# 미리보기: before/after 상위 10
import itertools
print("\n--- before/after 샘플 ---")
for i in targets[:10]:
    print("id", i)
    print("  before:", ko[i][:70])
    print("  after :", changed[i][:70])

# 적용
if '--apply' in sys.argv:
    shutil.copyfile(os.path.join(HERE, 'ko_final.json'), os.path.join(HERE, 'ko_final.prewrap.json'))
    for i, v in changed.items():
        ko[i] = v
    json.dump(ko, open(os.path.join(HERE, 'ko_final.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print("\nAPPLIED. backup: ko_final.prewrap.json")
else:
    print("\n(dry run; --apply 로 반영)")
