# -*- coding: utf-8 -*-
import sys, io, os, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
carrier = None  # byte length computed independent of carrier (hangul=2)

def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def enc_len(s):
    n = 0
    for ch in s:
        ch = '・' if ch == '·' else ch
        if is_h(ch): n += 2
        else:
            try: n += len(ch.encode('cp932'))
            except UnicodeEncodeError: n += 1
    return n

TOKEN = re.compile(r'@[a-z][0-9a-z]')
def toks(s): return collections.Counter(TOKEN.findall(s))
def nlcount(s): return s.count('\n')

entries = []          # {jp, ko, occ, budget}
overs = []; tokbad = []; nlbad = []

# set 1: the 590
uniq = {u['id']: u for u in json.load(open(os.path.join(HERE, 'dol_strings_uniq.json'), encoding='utf-8'))}
work = {w['id']: w for w in json.load(open(os.path.join(HERE, 'dol_work.json'), encoding='utf-8'))}
ko1 = json.load(open(os.path.join(HERE, 'dol_ko.json'), encoding='utf-8'))
for i, w in work.items():
    ko = ko1.get(str(i), w['jp'])
    if ko == w['jp']:
        continue
    entries.append({'jp': w['jp'], 'ko': ko, 'occ': uniq[i]['occ'], 'budget': w['budget']})

# set 2: the missed multiline strings.
# ⚠ dol_missed 재생성으로 id가 배치와 어긋날 수 있어 JP 기준으로 매칭한다.
missed = json.load(open(os.path.join(HERE, 'dol_missed.json'), encoding='utf-8'))
# 배치 jp <-> 출력 ko 를 id로 이어 jp->ko 맵 구성
batch_jp = {}
for k in range(5):
    bp = os.path.join(HERE, 'dolm_batches', f'dolm_{k}.json')
    if os.path.exists(bp):
        for it in json.load(open(bp, encoding='utf-8')):
            batch_jp[it['id']] = it['jp']
jp2ko = {}
for k in range(5):
    p = os.path.join(HERE, 'dolm_out', f'dolm_{k}.json')
    if os.path.exists(p):
        for it in json.load(open(p, encoding='utf-8')):
            jp = batch_jp.get(it['id'])
            if jp is not None:
                jp2ko[jp] = it['ko']
seen_jp = set(e['jp'] for e in entries)
for m in missed:
    ko = jp2ko.get(m['jp'])
    if ko is None or ko == m['jp'] or m['jp'] in seen_jp:
        continue
    seen_jp.add(m['jp'])
    entries.append({'jp': m['jp'], 'ko': ko, 'occ': m['occ'], 'budget': m['budget']})
    if toks(m['jp']) != toks(ko): tokbad.append((m['id'], m['jp'], ko))
    if nlcount(m['jp']) != nlcount(ko): nlbad.append((m['id'], repr(m['jp'][:30]), repr(ko[:30])))

# validate budgets
for e in entries:
    if enc_len(e['ko']) > e['budget']:
        overs.append((e['budget'], enc_len(e['ko']), e['jp'][:24], e['ko'][:24]))

print("total DOL inject entries:", len(entries))
print("over budget:", len(overs))
for x in overs[:15]: print("   budget=%d need=%d  %s -> %s" % x)
print("token mismatch (missed set):", len(tokbad))
for x in tokbad[:8]: print("   ", x)
print("newline count mismatch (missed set):", len(nlbad))
for x in nlbad[:8]: print("   ", x)

json.dump(entries, open(os.path.join(HERE, 'dol_inject_all.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# syllable set of all DOL ko
syl = set()
for e in entries:
    syl |= set(c for c in e['ko'] if is_h(c))
json.dump(sorted(syl), open(os.path.join(HERE, 'dol_all_syl.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print("DOL total hangul syllables:", len(syl))
