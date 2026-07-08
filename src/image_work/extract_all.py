# -*- coding: utf-8 -*-
"""텍스처 파일에서 @Texture 블록 추출 -> PNG + 파일별 컨택트시트 + 인벤토리."""
import sys, io, os, glob, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageDraw
BASE = os.path.join(HERE, '..', 'files')
OUT = os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)

MINW, MINH = 24, 12   # 이보다 작은 아이콘/파츠는 제외(라벨/로고 위주)
BG = (100, 100, 105)

def process(rel):
    b = open(os.path.join(BASE, rel), 'rb').read()
    if b'@Texture' not in b:
        return None
    items = []
    for o in TX.find_blocks(b):
        try:
            hd = TX.parse_header(b, o)
        except Exception:
            continue
        w, h = hd['w'], hd['h']
        if w < MINW or h < MINH or w > 900 or h > 500:
            continue
        if hd['palcnt'] not in (16, 256):
            continue
        img = TX.decode(b, o)
        if img is None:
            continue
        items.append((o, img))
    return items

# 대상: Info/arc, 타이틀 .dat, cardicon, Effect(제외-이펙트라 텍스트 적음)
targets = sorted(glob.glob(os.path.join(BASE, 'Info', 'arc', '*.arc')))
targets += [os.path.join(BASE, 'cardicon.ARC')]

inventory = []
for tp in targets:
    rel = os.path.relpath(tp, BASE).replace(os.sep, '/')
    items = process(rel)
    if not items:
        continue
    # 컨택트시트: 그리드 배치, 각 텍스처 위에 인덱스+크기 라벨
    cols = 3
    cellw = 380; cellh = 130
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cellw, rows * cellh), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for idx, (o, img) in enumerate(items):
        cx = (idx % cols) * cellw; cy = (idx // cols) * cellh
        # 알파를 회색 배경에 합성 + 축소
        bg = Image.new('RGB', img.size, BG); bg.paste(img, (0, 0), img)
        maxw, maxh = cellw - 8, cellh - 20
        scale = min(maxw / img.width, maxh / img.height, 1.0)
        disp = bg.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
        sheet.paste(disp, (cx + 4, cy + 16))
        draw.rectangle((cx, cy, cx + cellw - 1, cy + cellh - 1), outline=(80, 80, 80))
        draw.text((cx + 4, cy + 2), f"#{idx} @0x{o:X} {img.width}x{img.height}", fill=(0, 255, 0))
        inventory.append({'file': rel, 'idx': idx, 'off': o, 'w': img.width, 'h': img.height})
    name = rel.replace('/', '_')
    sheet.save(os.path.join(OUT, name + '.png'))
    print(f"{rel}: {len(items)} textures -> {name}.png")

json.dump(inventory, open(os.path.join(HERE, 'inventory.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("총 텍스처:", len(inventory))
