# -*- coding: utf-8 -*-
import sys, io, os, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92); SINGLE = BS + 'n'; DOUBLE = BS + BS + 'n'

uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
jp_by_id = {w['id']: w['jp'] for w in uniq}
ko = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))

# apply overflow overrides
applied = 0
for k in range(3):
    for it in json.load(open(os.path.join(HERE, 'of_translated', f'of_{k}.json'), encoding='utf-8')):
        ko[str(it['id'])] = it['ko']; applied += 1
print("overflow overrides applied:", applied)

TOKEN = re.compile(r'@[a-z][0-9a-f]')
def toks(s): return collections.Counter(TOKEN.findall(s))
def nl_form(s):
    hd = DOUBLE in s; hs = SINGLE in s.replace(DOUBLE, '')
    return 'mixed' if hd and hs else 'double' if hd else 'single' if hs else 'none'
def set_nl(x, f):
    x = x.replace(DOUBLE, SINGLE)
    return x.replace(SINGLE, DOUBLE) if f == 'double' else x

# re-normalize newline form + token check on overridden ids
tok_iss = []
for i, jp in jp_by_id.items():
    s = ko[str(i)]
    f = nl_form(jp)
    if f in ('single', 'double'):
        s = set_nl(s, f)
    ko[str(i)] = s
    if toks(jp) != toks(s):
        tok_iss.append(i)
print("token mismatches after merge:", len(tok_iss), tok_iss[:10])

# syllable inventory
syll = set()
for s in ko.values():
    for ch in s:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            syll.add(ch)
old = set(json.load(open(os.path.join(HERE, 'syllables.json'), encoding='utf-8')))
new_syll = syll - old
print("total unique syllables now:", len(syll), " (was", len(old), ") new:", len(new_syll))
if new_syll:
    print("  NEW syllables:", ''.join(sorted(new_syll)))

json.dump(ko, open(os.path.join(HERE, 'ko_final.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(sorted(syll), open(os.path.join(HERE, 'syllables.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print("updated ko_final.json + syllables.json")
