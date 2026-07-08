# -*- coding: utf-8 -*-
import sys, io, json, re, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))

# token inventory
tok = collections.Counter()
for r in rows:
    for m in re.findall(r'@[a-z][0-9a-f]', r['jp']):
        tok[m] += 1
print("control tokens (@xN):", dict(tok.most_common()))

# newline forms
nl_single = sum(r['jp'].count('\\n') for r in rows)
print("backslash-n occurrences (each \\n literal):", nl_single)

# furigana pattern |kanji(reading)
furi = 0
for r in rows:
    furi += len(re.findall(r'\|[^|(]+?\([ぁ-ゖ゛-ゟー]+\)', r['jp']))
print("furigana ruby |漢字(かな):", furi)

# bracket 「」
br = sum(r['jp'].count('「') for r in rows)
print("corner brackets:", br)

# speaker-name-only strings (no kana, short)  e.g. マリュー
def is_name(s):
    t = re.sub(r'@[a-z][0-9a-f]', '', s)
    return len(t) <= 10 and '\n' not in t and '@' not in s and all(ord(c) > 0x2000 or c in '・ー' for c in t) and t

# byte budget check: strip control -> how many text bytes; korean of similar char count fits?
def strip_ctrl(s):
    s = re.sub(r'@[a-z][0-9a-f]', '', s)
    s = s.replace('\\n', '')
    s = re.sub(r'\|', '', s)
    s = re.sub(r'\([ぁ-ゖ゛-ゟー]+\)', '', s)   # remove furigana readings
    return s

# For same-size injection: budget = length-1 (null). control codes cost fixed bytes.
# korean text bytes = 2 * (num korean syllables). estimate feasibility:
tight = 0
examples = []
for r in rows:
    body = r['jp']
    ctrl_bytes = 0
    # @xN = 3 bytes ascii, \n = 2 bytes ascii -> preserved as-is
    ctrl_bytes += len(re.findall(r'@[a-z][0-9a-f]', body)) * 3
    ctrl_bytes += body.count('\\n') * 2
    # visible japanese chars (after removing control + furigana markup)
    vis = strip_ctrl(body)
    vis_jp = sum(1 for c in vis if ord(c) > 0x2000 or c in '！？。、「」・…')
    budget = r['length'] - 1 - ctrl_bytes   # bytes left for korean payload
    max_kor_syll = budget // 2
    # rough: korean usually <= japanese visible-char count
    if max_kor_syll < vis_jp * 0.75:
        tight += 1
        if len(examples) < 8:
            examples.append((r['file'], vis_jp, max_kor_syll, body[:40]))
print("\nrows where korean budget may be tight (<0.75*jp chars):", tight, "/", len(rows))
for e in examples:
    print("  jp_vis=%d max_kor=%d  %s" % (e[1], e[2], e[3]))
