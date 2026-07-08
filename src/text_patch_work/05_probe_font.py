# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'kanji_dokuon_auto_patch_tool')
sys.path.insert(0, TOOL)
import patch_kanji_dokuon_font_auto as T
from pathlib import Path

dol = Path(os.path.join(HERE, '..', 'sys', 'main.dol')).read_bytes()
chars, off = T.extract_font_char_table(dol)
print("table offset=0x%X, chars=%d" % (off, len(chars)))

# visible cells per texture
vis = []
for block, tex in enumerate(T.DEFAULT_KANJI_TEXTURES):
    info = T.read_texture_info(dol, tex)
    cols = info.width // T.CELL_SIZE
    rows = info.height // T.CELL_SIZE
    visible = cols * rows
    print(f"  tex #{tex}: {info.width}x{info.height} cells={cols}x{rows}={visible}")
    for cell in range(256):
        idx = block * 256 + cell
        if idx >= len(chars):
            continue
        ch = chars[idx]
        if cell < visible and ch not in (' ', '　', '\x00'):
            vis.append((tex, cell, ch))
print("total visible usable cells:", len(vis))
# show a carrier sample and its sjis code
print("first 5 visible:", [(t, c, ch, hex(int.from_bytes(ch.encode('cp932'), 'big'))) for t, c, ch in vis[:5]])
print("last 5 visible:", [(t, c, ch, hex(int.from_bytes(ch.encode('cp932'), 'big'))) for t, c, ch in vis[-5:]])
