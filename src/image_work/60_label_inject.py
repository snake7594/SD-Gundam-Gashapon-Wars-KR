# -*- coding: utf-8 -*-
"""bank102 일영병기 메뉴 라벨(160x52): 위 일본어->한글 재작화, 아래 영어 보존, C4 재인코딩 주입."""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageFont, ImageDraw
BASE = os.path.join(HERE, '..', 'files')
ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true')
ap.add_argument('--preview', action='store_true'); args = ap.parse_args()

FONTBD = os.path.join(HERE, '..', 'fonts', 'NanumSquareNeocBd.ttf')
DARK = (33, 33, 33, 255)
WHITE = (255, 255, 255, 255)

# 라벨: offset -> 한글(위)
LABELS = {
    0xAC6A0: '모드 선택',
    0xAD880: '싱글 플레이',
    0xAEA60: '멀티 플레이',
    0xAFC40: '옵션',
    0xB0E20: '진동',
    0xB2000: '사운드 설정',
    0xB31E0: '메모리 카드',
}

def find_gap(img):
    px = img.load(); h = img.height; w = img.width
    ink = [sum(1 for x in range(w) if px[x, y][3] > 100) for y in range(h)]
    # 첫 잉크블록(JP) 끝 이후의 갭
    seen = False
    for y in range(h):
        if ink[y] > 10:
            seen = True
        elif seen and ink[y] < 3:
            return y
    return h * 3 // 5

def draw_korean(text, w, ht):
    """폭 w, 높이 ht 영역에 한글을 어두운글자+흰외곽선으로 중앙 렌더."""
    img = Image.new('RGBA', (w, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(ht, 6, -1):
        f = ImageFont.truetype(FONTBD, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=2)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 4 and th <= ht - 2:
            x = (w - tw) // 2 - bb[0]
            y = (ht - th) // 2 - bb[1]
            d.text((x, y), text, font=f, fill=DARK, stroke_width=2, stroke_fill=WHITE)
            return img
    return img

def build(b):
    """반환: {off: new_imgdata_bytes}"""
    out = {}
    prev = {}
    for o, ko in LABELS.items():
        hd = TX.parse_header(b, o)
        pal = TX.read_palette(b, hd['pal_off'], hd['palcnt'])
        orig = TX.decode(b, o)
        gap = find_gap(orig)
        # 새 이미지: 위(한글) + 아래(원본 영어)
        new = Image.new('RGBA', (orig.width, orig.height), (0, 0, 0, 0))
        # 아래 영어 복사 (gap 이후)
        en = orig.crop((0, gap, orig.width, orig.height))
        new.paste(en, (0, gap))
        # 위 한글 (0~gap)
        kimg = draw_korean(ko, orig.width, gap)
        new.paste(kimg, (0, 0), kimg)
        out[o] = TX.encode_c4(new, pal, hd['w'], hd['h'])
        prev[o] = new
    return out, prev

b = open(os.path.join(BASE, 'Info/arc/bank102.arc'), 'rb').read()
newdata, prev = build(b)

if args.preview:
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    W = 170
    mont = Image.new('RGB', (W, 60 * len(prev)), (100, 100, 105))
    for i, (o, img) in enumerate(prev.items()):
        bg = Image.new('RGB', img.size, (100, 100, 105)); bg.paste(img, (0, 0), img)
        mont.paste(bg, (4, i * 60 + 4))
    mont.save(os.path.join(HERE, 'out', 'label_kr_preview.png'))
    print("preview saved")

if args.apply:
    bb = bytearray(b)
    for o, data in newdata.items():
        hd = TX.parse_header(b, o)
        assert len(data) == hd['imgsize']
        bb[hd['img_off']: hd['img_off'] + hd['imgsize']] = data
    dst = os.path.join(HERE, '..', 'text_patch_work', 'patched_files', 'Info', 'arc', 'bank102.arc')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bb)
    assert os.path.getsize(dst) == len(b)
    print("APPLIED bank102.arc (size same:", os.path.getsize(dst) == len(b), ")")
print("labels:", len(LABELS))
