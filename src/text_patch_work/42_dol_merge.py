# -*- coding: utf-8 -*-
import sys, io, os, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
work = json.load(open(os.path.join(HERE, 'dol_work.json'), encoding='utf-8'))
jp_by_id = {w['id']: w['jp'] for w in work}
budget_by_id = {w['id']: w['budget'] for w in work}

ko = {}
for k in range(12):
    for it in json.load(open(os.path.join(HERE, 'dol_out', f'dol_{k:02d}.json'), encoding='utf-8')):
        ko[it['id']] = it['ko']

missing = [i for i in jp_by_id if i not in ko]
print("DOL strings: %d, translated: %d, missing: %d" % (len(jp_by_id), len(ko), len(missing)))

NORMALIZE = {'·': '・'}
def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def enc_len(s):
    n = 0
    for ch in s:
        ch = NORMALIZE.get(ch, ch)
        if is_h(ch): n += 2
        else:
            try: n += len(ch.encode('cp932'))
            except UnicodeEncodeError: n += 1
    return n

TOKEN = re.compile(r'@[a-z][0-9a-z]')
def toks(s): return collections.Counter(TOKEN.findall(s))

over = []; tokbad = []
for i, jp in jp_by_id.items():
    k = ko.get(i, jp)
    if enc_len(k) > budget_by_id[i]:
        over.append((i, budget_by_id[i], enc_len(k), jp, k))
    if toks(jp) != toks(k):
        tokbad.append((i, jp, k))
print("over budget:", len(over))
for x in over[:20]: print("   id=%d budget=%d need=%d  %s -> %s" % x)
print("token mismatch:", len(tokbad))
for x in tokbad[:10]: print("   ", x)

# syllable inventory delta
def hangul(s): return set(c for c in s if is_h(c))
cur = set(json.load(open(os.path.join(HERE, 'syllables.json'), encoding='utf-8')))
new = set()
for k in ko.values(): new |= hangul(k)
print("\ncurrent syllables(dialogue+help):", len(cur))
print("DOL adds new syllables:", len(new - cur))
print("TOTAL would be:", len(cur | new), " (kanji carrier cells: 951)")

json.dump(ko, open(os.path.join(HERE, 'dol_ko.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("\nsamples:")
for i in list(jp_by_id)[:12]:
    print("   %s -> %s" % (jp_by_id[i][:26], ko.get(i, '?')[:26]))
