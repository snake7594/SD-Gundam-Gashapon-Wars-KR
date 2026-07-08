# -*- coding: utf-8 -*-
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
jp = {w['id']: w['jp'] for w in uniq}
ko = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
for i in [34, 35, 40, 491, 557, 558, 559, 633, 988, 990, 1099]:
    print("id", i)
    print("  JP:", repr(jp[i]))
    print("  KO:", repr(ko[str(i)]))
