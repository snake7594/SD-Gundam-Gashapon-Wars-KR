# -*- coding: utf-8 -*-
import sys, io, json, os, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)
SINGLE = BS + 'n'          # \n   (2 bytes)
DOUBLE = BS + BS + 'n'     # \\n  (3 bytes)

uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
jp_by_id = {w['id']: w['jp'] for w in uniq}

ko_by_id = {}
for i in range(20):
    p = os.path.join(HERE, 'translated', f'batch_{i:02d}.json')
    arr = json.load(open(p, encoding='utf-8'))
    for it in arr:
        ko_by_id[it['id']] = it['ko']

# 1) coverage
missing = [i for i in jp_by_id if i not in ko_by_id]
print("total unique:", len(jp_by_id), "translated:", len(ko_by_id), "missing:", len(missing))
if missing:
    print("  MISSING ids:", missing[:30])

TOKEN = re.compile(r'@[a-z][0-9a-f]')

def tokens(s):
    return collections.Counter(TOKEN.findall(s))

def nl_form(s):
    """dominant newline form of a string: 'double','single','mixed','none'"""
    has_d = DOUBLE in s
    tmp = s.replace(DOUBLE, '')
    has_s = SINGLE in tmp
    if has_d and has_s: return 'mixed'
    if has_d: return 'double'
    if has_s: return 'single'
    return 'none'

def set_nl_form(ko, form):
    """collapse ko newlines then apply source form"""
    x = ko.replace(DOUBLE, SINGLE)   # collapse to single
    if form == 'double':
        x = x.replace(SINGLE, DOUBLE)
    return x

# 2) validate + fix newline form
issues = {'token': [], 'furigana': [], 'kana_left': [], 'nl_count': []}
FURI = re.compile(r'\|[^|()]*\([ぁ-ゖ゛-ゟ゠-ヿー]+\)')
fixed = {}
for i, jp in jp_by_id.items():
    ko = ko_by_id.get(i, '')
    # token multiset
    if tokens(jp) != tokens(ko):
        issues['token'].append(i)
    # furigana residue
    if FURI.search(ko) or ('|' in ko and re.search(r'\([ぁ-ゟ゠-ヿ]+\)', ko)):
        issues['furigana'].append(i)
    # leftover japanese kana in ko (allow if source item is 'binary passthrough' i.e. ko==jp)
    if ko != jp:
        if re.search(r'[ぁ-ゟ゠-ヿ]', ko):
            issues['kana_left'].append(i)
    # newline: fix ko to match jp's form (only when jp form is clean single/double)
    f = nl_form(jp)
    ko_fixed = ko
    if f in ('single', 'double'):
        ko_fixed = set_nl_form(ko, f)
    # newline count check (count 'n'-terminated backslash runs)
    def nlcount(s):
        return len(re.findall(re.escape(BS) + r'+n', s))
    if nlcount(jp) != nlcount(ko_fixed):
        issues['nl_count'].append(i)
    fixed[i] = ko_fixed

for k, v in issues.items():
    print(f"issue[{k}]: {len(v)}  ids={v[:15]}")

# 3) syllable inventory
syll = collections.Counter()
for i, ko in fixed.items():
    for ch in ko:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            syll[ch] += 1
print("\nunique Hangul syllables used:", len(syll))
print("top20:", ''.join(c for c, _ in syll.most_common(20)))

# save fixed translations
json.dump({str(i): fixed[i] for i in fixed}, open(os.path.join(HERE, 'ko_final.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
json.dump(sorted(syll.keys()), open(os.path.join(HERE, 'syllables.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
print("\nsaved ko_final.json, syllables.json")
