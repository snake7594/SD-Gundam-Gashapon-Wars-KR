# -*- coding: utf-8 -*-
"""bank102 대형 메뉴 타이틀(368/316x74, 흰색 버블 실루엣) 한글 재작화.
판독이 확실한 10개만(사용자 지시 "읽히는 것만"). 팔레트=흰색+알파 그라디언트라
흰색 한글을 두껍게(stroke) 그리면 안티에일리어싱 가장자리가 알파 팔레트로 매핑됨.
bank102는 v1.8 소형 라벨이 이미 patched_files에 있으므로 그 위에 스택 주입."""
import sys, io, os, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageFont, ImageDraw

BASE = os.path.join(HERE, '..', 'files')
PATCHED = os.path.join(HERE, '..', 'text_patch_work', 'patched_files')
FONT = os.path.join(HERE, '..', 'fonts', 'NanumSquareNeocBd.ttf')
ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--preview', action='store_true')
args = ap.parse_args()

REL = 'Info/arc/bank102.arc'
# 판독 확정 대형 타이틀만
TITLES = {
    0x309A0: '모드 선택', 0x36E40: '싱글 플레이', 0x3D2E0: '멀티 플레이',
    0x43780: '옵션', 0x4A3A0: '시나리오 게임', 0x840A0: '도움말',
    0x8B440: '사운드 플레이어', 0x927E0: '진동', 0x99B80: '사운드 설정',
    0xA0F20: '메모리 카드',
}
WHITE = (255, 255, 255, 255)


def read_base(rel):
    pf = os.path.join(PATCHED, rel)
    return open(pf if os.path.exists(pf) else os.path.join(BASE, rel), 'rb').read()


def draw_white(text, w, ht, sw=3):
    """흰색 굵은 글자(버블 느낌), 투명 배경."""
    img = Image.new('RGBA', (w, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(ht, 6, -1):
        f = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 10 and th <= ht - 4:
            x = (w - tw) // 2 - bb[0]; y = (ht - th) // 2 - bb[1]
            d.text((x, y), text, font=f, fill=WHITE, stroke_width=sw, stroke_fill=WHITE)
            return img
    return img


b = read_base(REL)
out = {}; prev = []
for o, ko in TITLES.items():
    hd = TX.parse_header(b, o)
    pal = TX.read_palette(b, hd['pal_off'], hd['palcnt'])
    orig = TX.decode(b, o)
    img = draw_white(ko, orig.width, orig.height, sw=3)
    out[o] = TX.encode_c4(img, pal, hd['w'], hd['h'])
    prev.append((o, img, ko))

if args.preview:
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    W = max(i.width for _, i, _ in prev)
    H = sum(i.height for _, i, _ in prev) + len(prev) * 6
    m = Image.new('RGB', (W, H), (60, 60, 70)); d = ImageDraw.Draw(m); y = 0
    for o, img, ko in prev:
        bg = Image.new('RGB', img.size, (60, 60, 70)); bg.paste(img, (0, 0), img)
        m.paste(bg, (0, y)); d.text((2, y + 1), f"{o:X}", fill=(0, 255, 0)); y += img.height + 6
    m.save(os.path.join(HERE, 'out', 'menu_titles_preview.png'))
    print("preview saved:", len(prev))

if args.apply:
    bb = bytearray(b)
    for o, data in out.items():
        hd = TX.parse_header(b, o)
        assert len(data) == hd['imgsize'], (hex(o), len(data), hd['imgsize'])
        bb[hd['img_off']: hd['img_off'] + hd['imgsize']] = data
    dst = os.path.join(PATCHED, REL)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bb)
    assert os.path.getsize(dst) == len(b)
    print("APPLIED", REL, "titles:", len(out))
print("total:", len(prev))
