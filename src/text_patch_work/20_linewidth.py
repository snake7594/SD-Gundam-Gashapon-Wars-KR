# -*- coding: utf-8 -*-
import sys, io, os, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)
uniq = json.load(open(os.path.join(HERE, 'unique_jp.json'), encoding='utf-8'))
jp_by_id = {w['id']: w['jp'] for w in uniq}
ko = json.load(open(os.path.join(HERE, 'ko_final.json'), encoding='utf-8'))

TOKEN = re.compile(r'@[a-z0-9][0-9a-f]')
FURI = re.compile(r'\|([^|()]*)\(([ぁ-ゖ゛-ゟ゠-ヿー]+)\)')

def display_lines(s, strip_furi=True):
    s = TOKEN.sub('', s)
    if strip_furi:
        s = FURI.sub(lambda m: m.group(1), s)   # keep base kanji, drop ruby
    s = s.replace('|', '')
    # split on newline tokens (both \n and \\n) and real newline
    s = s.replace(BS + BS + 'n', '\n').replace(BS + 'n', '\n')
    return s.split('\n')

def width(line):
    # fullwidth char = 1.0, halfwidth (ascii) = 0.5
    w = 0.0
    for ch in line:
        w += 0.5 if ord(ch) < 0x100 else 1.0
    return w

# original JP: max line width distribution
jp_line_w = []
for jp in jp_by_id.values():
    for ln in display_lines(jp):
        jp_line_w.append(width(ln))
jp_line_w.sort()
print("JP display line width (fullwidth units):")
print("  count=%d max=%.1f  p99=%.1f p95=%.1f p90=%.1f mean=%.1f" % (
    len(jp_line_w), jp_line_w[-1], jp_line_w[int(len(jp_line_w)*0.99)],
    jp_line_w[int(len(jp_line_w)*0.95)], jp_line_w[int(len(jp_line_w)*0.90)],
    sum(jp_line_w)/len(jp_line_w)))
# histogram of top widths
c = collections.Counter(int(round(w)) for w in jp_line_w)
print("  width histogram (>=18):", {k: c[k] for k in sorted(c) if k >= 18})

# show a few widest JP lines
alljp = []
for jp in jp_by_id.values():
    for ln in display_lines(jp):
        alljp.append((width(ln), ln))
alljp.sort(reverse=True)
print("\nwidest JP lines:")
for w, ln in alljp[:8]:
    print("  %.1f  %s" % (w, ln[:50]))

# KO current: lines exceeding a threshold
print("\n--- KO current line widths ---")
THRESH = jp_line_w[-1]   # use JP max as the box limit
ko_over = []
for i, s in ko.items():
    for ln in display_lines(s):
        w = width(ln)
        if w > THRESH:
            ko_over.append((w, int(i), ln))
ko_over.sort(reverse=True)
print("KO lines wider than JP-max(%.1f): %d" % (THRESH, len(ko_over)))
for w, i, ln in ko_over[:15]:
    print("  %.1f id=%d  %s" % (w, i, ln[:50]))
