# -*- coding: utf-8 -*-
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

occ = json.load(open(os.path.join(HERE, 'dialogue_all.json'), encoding='utf-8'))
ko_by_id = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))
uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
id_by_jp = {w['jp']: w['id'] for w in uniq}
jp_by_id = {w['id']: w['jp'] for w in uniq}
carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}

def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def enc_len(ko):
    n = 0
    for ch in ko:
        if is_h(ch): n += 2
        else:
            try: n += len(ch.encode('cp932'))
            except UnicodeEncodeError: n += 1
    return n

# slot per unique id = min original length across its occurrences (all equal, but be safe)
slot_by_id = {}
for o in occ:
    i = id_by_jp[o['jp']]
    slot_by_id[i] = min(slot_by_id.get(i, 1 << 30), o['length'])

work = []
for i, jp in jp_by_id.items():
    ko = ko_by_id[str(i)]
    slot = slot_by_id[i]
    need = enc_len(ko) + 1  # + null
    if need > slot:
        # budget in *korean syllables*: (slot-1 - fixed_nonhangul_bytes)/2
        fixed = sum(0 if is_h(c) else (len(c.encode('cp932')) if _ok(c) else 1) for c in ko) if False else None
        work.append({'id': i, 'jp': jp, 'ko': ko, 'slot': slot,
                     'cur_bytes': need, 'over': need - slot,
                     'max_korean_syllables': (slot - 1) // 2})
def _ok(c):
    try: c.encode('cp932'); return True
    except: return False

work.sort(key=lambda w: -w['over'])
json.dump(work, open(os.path.join(HERE, 'overflow_work.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("unique overflow strings:", len(work))
print("max over:", work[0]['over'] if work else 0, "bytes")
for w in work[:12]:
    print(f"  id={w['id']} slot={w['slot']} over={w['over']}  ko={w['ko'][:45]}")
