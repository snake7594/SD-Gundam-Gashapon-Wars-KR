# -*- coding: utf-8 -*-
import sys, io, json, collections, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))
BS = chr(92)  # backslash
forms = collections.Counter()
for r in rows:
    s = r['jp']; i = 0
    while i < len(s):
        if s[i] == BS:
            j = i
            while j < len(s) and s[j] == BS:
                j += 1
            nxt = s[j] if j < len(s) else ''
            forms[(j - i, nxt)] += 1
            i = j + 1
        else:
            i += 1
print("backslash-run forms (num_backslashes, next_char): count")
for k, v in forms.most_common():
    print("  ", k, v)

single = BS + 'n'
double = BS + BS + 'n'
for r in rows:
    if single in r['jp'] and double not in r['jp']:
        print("SINGLE example:", repr(r['jp'][:50]), "len=", r['length']); break
for r in rows:
    if double in r['jp']:
        print("DOUBLE example:", repr(r['jp'][:50]), "len=", r['length']); break
