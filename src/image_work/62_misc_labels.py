# -*- coding: utf-8 -*-
"""기타 라벨 이미지 한글 재작화:
 - bank111: 100% 클리어 조건 배너 3종 (금색+검은 외곽선, full 재작화)
 - bank101/bank110: ほうげき(砲撃) -> 포격 (흰색, full)
 - bank106/bank118: ランダムマップ 플라크 로고 -> 랜덤/맵 (흰 플라크·격자 배경 보존, 남색 2줄)
원본 팔레트 유지, 동일 크기 제자리 재인코딩."""
import sys, io, os, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageFont, ImageDraw

BASE = os.path.join(HERE, '..', 'files')
FONT = os.path.join(HERE, '..', 'fonts', 'NanumSquareNeocBd.ttf')
ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--preview', action='store_true')
args = ap.parse_args()

# full 재작화 라벨: file -> {off: korean}
FULL = {
 'Info/arc/bank111.arc': {0xE580: '100% 유닛 생환', 0x103E0: '100% 점령', 0x12240: '100% 거점 점령'},
 'Info/arc/bank101.arc': {0x2AA0: '포격'},
 'Info/arc/bank110.arc': {0x2A80: '포격'},
}
# 플라크(배경 보존, 2줄) 라벨
PLAQUE = {
 'Info/arc/bank118.arc': {0x15DE0: ('랜덤', '맵')},
 'Info/arc/bank106.arc': {0x13820: ('랜덤', '맵')},
}


PATCHED = os.path.join(HERE, '..', 'text_patch_work', 'patched_files')


def read_base(rel):
    """이미 패치된 파일이 있으면 그 위에 쌓고, 없으면 원본에서."""
    pf = os.path.join(PATCHED, rel)
    src = pf if os.path.exists(pf) else os.path.join(BASE, rel)
    return open(src, 'rb').read()


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.586 * c[2]


def sat(c):
    return max(c[:3]) - min(c[:3])


def pick_colors(pal):
    op = [c for c in pal if c[3] > 150] or [(255, 255, 255, 255)]
    fill = max(op, key=lambda c: sat(c) * 1.3 + luma(c))
    outline = min(op, key=lambda c: luma(c))
    if abs(luma(outline) - luma(fill)) < 40:
        outline = (0, 0, 0, 255)
    return (fill[0], fill[1], fill[2], 255), (outline[0], outline[1], outline[2], 255)


def draw_full(text, w, ht, fill, outline, sw=2):
    img = Image.new('RGBA', (w, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(ht, 6, -1):
        f = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 6 and th <= ht - 2:
            x = (w - tw) // 2 - bb[0]; y = (ht - th) // 2 - bb[1]
            d.text((x, y), text, font=f, fill=fill, stroke_width=sw, stroke_fill=outline)
            return img
    return img


def white_bbox(img):
    """흰 플라크 내부(밝은 픽셀) bounding box."""
    px = img.load(); w, h = img.width, img.height
    x0, y0, x1, y1 = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 200 and r > 200 and g > 200 and b > 200:
                x0 = min(x0, x); y0 = min(y0, y); x1 = max(x1, x + 1); y1 = max(y1, y + 1)
    return x0, y0, x1, y1


def build_full(rel, spec):
    b = read_base(rel)
    out = {}; prev = {}
    for o, ko in spec.items():
        hd = TX.parse_header(b, o)
        pal = TX.read_palette(b, hd['pal_off'], hd['palcnt'])
        orig = TX.decode(b, o)
        fill, outline = pick_colors(pal)
        img = draw_full(ko, orig.width, orig.height, fill, outline, sw=2)
        out[o] = TX.encode_c4(img, pal, hd['w'], hd['h'])
        prev[o] = (img, ko)
    return b, out, prev


def build_plaque(rel, spec):
    b = read_base(rel)
    out = {}; prev = {}
    for o, (top, bot) in spec.items():
        hd = TX.parse_header(b, o)
        pal = TX.read_palette(b, hd['pal_off'], hd['palcnt'])
        orig = TX.decode(b, o).convert('RGBA')
        # 남색 텍스트 색(가장 어두운 채도있는 불투명) + 흰 플라크
        op = [c for c in pal if c[3] > 200]
        navy = min(op, key=lambda c: luma(c))
        navy = (navy[0], navy[1], navy[2], 255)
        x0, y0, x1, y1 = white_bbox(orig)
        # 내부 인셋(테두리 침범 방지)
        ins = 6
        rx0, ry0, rx1, ry1 = x0 + ins, y0 + ins, x1 - ins, y1 - ins
        new = orig.copy()
        d = ImageDraw.Draw(new)
        # 텍스트 영역 흰색으로 정리
        d.rectangle((rx0, ry0, rx1 - 1, ry1 - 1), fill=(255, 255, 255, 255))
        rw = rx1 - rx0; rh = (ry1 - ry0) // 2
        for i, line in enumerate((top, bot)):
            k = draw_full(line, rw, rh, navy, (255, 255, 255, 255), sw=0)
            new.paste(k, (rx0, ry0 + i * rh), k)
        out[o] = TX.encode_c4(new, pal, hd['w'], hd['h'])
        prev[o] = (new, top + bot)
    return b, out, prev


results = {}; allprev = []
for rel, spec in FULL.items():
    b, out, prev = build_full(rel, spec)
    results[rel] = (b, out)
    for o, (img, ko) in prev.items():
        allprev.append((rel, o, img, ko))
for rel, spec in PLAQUE.items():
    b, out, prev = build_plaque(rel, spec)
    results[rel] = (b, out)
    for o, (img, ko) in prev.items():
        allprev.append((rel, o, img, ko))

if args.preview:
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    cols = 3; cw, ch = 260, 100
    rows = (len(allprev) + cols - 1) // cols
    mont = Image.new('RGB', (cols * cw, rows * ch), (70, 90, 70))
    d = ImageDraw.Draw(mont)
    for i, (rel, o, img, ko) in enumerate(allprev):
        cx = (i % cols) * cw; cy = (i // cols) * ch
        bg = Image.new('RGB', img.size, (70, 90, 70)); bg.paste(img, (0, 0), img)
        mont.paste(bg, (cx + 4, cy + 16))
        d.text((cx + 4, cy + 2), f"{rel[-11:]} {o:X}", fill=(255, 255, 0))
    mont.save(os.path.join(HERE, 'out', 'misc_labels_preview.png'))
    print("preview saved:", len(allprev))

if args.apply:
    for rel, (b, out) in results.items():
        bb = bytearray(b)
        for o, data in out.items():
            hd = TX.parse_header(b, o)
            assert len(data) == hd['imgsize'], (rel, hex(o))
            bb[hd['img_off']: hd['img_off'] + hd['imgsize']] = data
        dst = os.path.join(HERE, '..', 'text_patch_work', 'patched_files', rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bb)
        assert os.path.getsize(dst) == len(b)
        print("APPLIED", rel, "labels:", len(out))
print("total:", len(allprev))
