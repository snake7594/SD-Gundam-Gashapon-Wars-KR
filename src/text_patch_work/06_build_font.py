# -*- coding: utf-8 -*-
"""
캐리어-한자 방식 한글 폰트 빌더.
 - main.dol의 한자 순서표(1024) -> 실제 표시 셀 956개.
 - 뒤쪽 665셀 = 대사 한글 음절 캐리어 (해당 셀에 한글 글리프를 그림).
 - 앞쪽 291셀 = 한자 독음(미번역 메뉴 가독성용).
 - 인코더용 맵: 음절 -> 그 셀 원본 한자의 cp932 바이트.
"""
import sys, io, os, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'kanji_dokuon_auto_patch_tool')
sys.path.insert(0, TOOL)
import patch_kanji_dokuon_font_auto as T
from pathlib import Path

FONT = os.environ.get('KRFONT', r'C:\Windows\Fonts\malgun.ttf')
dol_path = Path(os.path.join(HERE, '..', 'sys', 'main.dol'))
data = bytearray(dol_path.read_bytes())

chars, off = T.extract_font_char_table(data)

# visible usable cells in table order -- CARRIERS MUST BE TRUE CJK KANJI ONLY.
# The table also contains non-kanji symbols (ν Ⅱ α ζ ㍉ ...) that real text uses
# literally; repurposing those would corrupt e.g. "ν건담"/"MK-Ⅱ". Keep them as-is.
vis = []          # kanji cells usable as carriers
skipped_sym = 0
for block, tex in enumerate(T.DEFAULT_KANJI_TEXTURES):
    info = T.read_texture_info(data, tex)
    cols = info.width // T.CELL_SIZE
    rows = info.height // T.CELL_SIZE
    visible = cols * rows
    for cell in range(256):
        idx = block * 256 + cell
        if idx >= len(chars):
            continue
        ch = chars[idx]
        if cell < visible and ch not in (' ', '　', '\x00'):
            if T.is_cjk_kanji(ch):
                vis.append((tex, cell, ch))
            else:
                skipped_sym += 1
print("non-kanji symbol cells kept intact (not carriers):", skipped_sym)

syllables = sorted(json.load(open(os.path.join(HERE, 'syllables.json'), encoding='utf-8')))
N = len(syllables)
assert N <= len(vis), f"too many syllables {N} > {len(vis)}"

split = len(vis) - N              # first `split` cells -> dokuon
dokuon_cells = vis[:split]
carrier_cells = vis[split:]       # last N cells -> hangul syllables

# assignments: cell -> glyph string ; and syllable -> carrier cp932 bytes
draw_by_tex = {}   # tex -> list of (cell, glyph_string)
carrier_map = {}   # syllable -> hex of cp932 bytes
reading_map = T.load_reading_map()

for (tex, cell, ch), syl in zip(carrier_cells, syllables):
    draw_by_tex.setdefault(tex, []).append((cell, syl))
    carrier_map[syl] = ch.encode('cp932').hex()

dokuon_count = 0
for (tex, cell, ch) in dokuon_cells:
    r = T.lookup_reading(ch, reading_map)
    if r:
        draw_by_tex.setdefault(tex, []).append((cell, r))
        dokuon_count += 1

# render into the C4 sheets
prevdir = os.path.join(HERE, 'font_preview')
os.makedirs(prevdir, exist_ok=True)
for tex, items in sorted(draw_by_tex.items()):
    info = T.read_texture_info(data, tex)
    cols = info.width // T.CELL_SIZE
    raw = bytes(data[info.image_offset: info.image_offset + info.image_size])
    indices = T.decode_c4_indices(raw, info.width, info.height)
    for cell, glyph in items:
        cx = (cell % cols) * T.CELL_SIZE
        cy = (cell // cols) * T.CELL_SIZE
        for yy in range(T.CELL_SIZE):
            for xx in range(T.CELL_SIZE):
                if cy + yy < info.height and cx + xx < info.width:
                    indices[cy + yy][cx + xx] = 0
        mask = T.draw_reading_cell(glyph, FONT)
        ci = T.mask_to_c4_indices(mask)
        for yy in range(T.CELL_SIZE):
            for xx in range(T.CELL_SIZE):
                if cy + yy < info.height and cx + xx < info.width:
                    indices[cy + yy][cx + xx] = ci[yy][xx]
    new_raw = T.encode_c4_indices(indices, info.width, info.height)
    assert len(new_raw) == info.image_size
    data[info.image_offset: info.image_offset + info.image_size] = new_raw
    T.indices_to_black_preview(indices, info.width, info.height).save(os.path.join(prevdir, f'tex_{tex}.png'))

Path(os.path.join(HERE, 'patched_main.dol')).write_bytes(data)
json.dump(carrier_map, open(os.path.join(HERE, 'carrier_map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

print("syllables:", N, "carriers assigned:", len(carrier_map), "dokuon cells:", dokuon_count)
print("patched_main.dol written; carrier_map.json written")
print("sample carrier:", syllables[0], "->", carrier_map[syllables[0]],
      "(", bytes.fromhex(carrier_map[syllables[0]]).decode('cp932'), ")")
