# -*- coding: utf-8 -*-
"""룰 설정 라벨(bank113/114/118) @Texture C4 한글 재작화.
 - full: 라벨 전체 텍스트를 한글로 재작화(팔레트에서 채움/외곽선 색 자동검출).
 - terrain: 지형 알약(위 한자 + 아래 영어) — 위만 한글, 아래 영어 보존.
 - keeptop: 난이도(위 Lv.N 배지 + 아래 단어) — 위 배지 보존, 아래 단어만 한글.
동일 크기 제자리 재인코딩(원본 팔레트 사용)."""
import sys, io, os, json, argparse
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

# off -> (korean, mode)
SPEC = {
 'Info/arc/bank113.arc': {
    0x5C600: ('지상', 'terrain'), 0x5CA60: ('수중', 'terrain'),
    0x5CEC0: ('우주', 'terrain'), 0x5D320: ('공중', 'terrain'),
    0x5D780: ('기본값으로', 'full'), 0x5ECE0: ('시간 설정', 'full'),
    0x5FA00: ('아이템 출현', 'full'), 0x60720: ('기믹', 'full'),
    0x61440: ('아군 히트', 'full'), 0x62160: ('가위바위보', 'full'),
    0x62E80: ('COM 레벨', 'full'),
    0x652E0: ('약함', 'keeptop'), 0x65E80: ('보통', 'keeptop'),
    0x66A20: ('강함', 'keeptop'), 0x675C0: ('엄청 강함', 'keeptop'),
    0x68160: ('뉴타입', 'keeptop'),
    0x68D00: ('없음', 'full'),
    0x698A0: ('15초', 'full'), 0x6A440: ('30초', 'full'),
    0x6AFE0: ('45초', 'full'), 0x6BB80: ('60초', 'full'),
    0x6C720: ('75초', 'full'), 0x6D2C0: ('90초', 'full'),
 },
 'Info/arc/bank114.arc': {
    0x380: ('쉬움', 'full'), 0x9E0: ('어려움', 'full'), 0x1040: ('엄청 어려움', 'full'),
    0x4AAE0: ('클리어 타임', 'full'), 0x4B2C0: ('쓰러뜨린 적 수', 'full'),
    0x4EB60: ('지상', 'terrain'), 0x4EFC0: ('수중', 'terrain'),
    0x4F420: ('우주', 'terrain'), 0x4F880: ('공중', 'terrain'),
 },
 'Info/arc/bank118.arc': {
    0x17E40: ('기본값으로', 'full'), 0x193A0: ('일수', 'full'),
    0x1A000: ('시간 제한', 'full'), 0x1AC60: ('하이드', 'full'),
    0x1B8C0: ('카드', 'full'), 0x1E8C0: ('없음', 'full'),
    0x1F460: ('5일', 'full'), 0x20000: ('10일', 'full'), 0x20BA0: ('15일', 'full'),
    0x21740: ('20일', 'full'), 0x222E0: ('25일', 'full'), 0x22E80: ('30일', 'full'),
    0x23A20: ('30초', 'full'), 0x245C0: ('60초', 'full'), 0x25160: ('90초', 'full'),
    0x25D00: ('120초', 'full'), 0x268A0: ('150초', 'full'),
 },
}


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.586 * c[2]


def sat(c):
    m, M = min(c[:3]), max(c[:3])
    return (M - m)


def pick_colors(pal):
    """채움색(밝고 채도높거나 흰색) + 외곽선색(가장 어두운 불투명) 선택."""
    op = [c for c in pal if c[3] > 150]
    if not op:
        op = [c for c in pal if c[3] > 60] or [(255, 255, 255, 255)]
    # 채움: 채도*1.2 + 밝기 최대 (노랑/파랑/흰 모두 커버)
    fill = max(op, key=lambda c: sat(c) * 1.3 + luma(c))
    # 외곽선: 가장 어두운 불투명
    outline = min(op, key=lambda c: luma(c))
    # 외곽선이 채움과 너무 비슷하면 검정 대체
    if abs(luma(outline) - luma(fill)) < 40:
        outline = (0, 0, 0, 255)
    return (fill[0], fill[1], fill[2], 255), (outline[0], outline[1], outline[2], 255)


def opaque_rows(img):
    px = img.load(); w, h = img.width, img.height
    rows = [sum(1 for x in range(w) if px[x, y][3] > 100) for y in range(h)]
    return rows


def find_en_gap(img):
    """지형 알약: 위 한자블록 끝 y (아래 영어와의 경계)."""
    rows = opaque_rows(img); h = img.height; seen = False
    for y in range(h):
        if rows[y] > 4:
            seen = True
        elif seen and rows[y] <= 1:
            return y
    return h * 3 // 5


def find_badge_box(img):
    """난이도: 위 Lv.N 배지의 bounding box (y1, x0, x1) 반환.
    첫 잉크 행블록을 배지로 보고, 그 행들 안의 x 범위를 구한다."""
    px = img.load(); w, h = img.width, img.height
    rows = opaque_rows(img); seen = False; y0 = 0; y1 = h // 3
    for y in range(h):
        if rows[y] > 2:
            if not seen:
                y0 = y; seen = True
        elif seen and rows[y] <= 0:
            y1 = y; break
    y1 = min(y1, h // 2)
    x0, x1 = w, 0
    for y in range(y0, y1):
        for x in range(w):
            if px[x, y][3] > 100:
                x0 = min(x0, x); x1 = max(x1, x + 1)
    if x0 >= x1:
        x0, x1 = 0, w
    return y1, x0, x1


def draw_text_region(text, w, ht, fill, outline, sw=2):
    img = Image.new('RGBA', (w, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(ht, 6, -1):
        f = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 4 and th <= ht - 2:
            x = (w - tw) // 2 - bb[0]
            y = (ht - th) // 2 - bb[1]
            d.text((x, y), text, font=f, fill=fill, stroke_width=sw, stroke_fill=outline)
            return img
    return img


def build(rel, spec):
    b = open(os.path.join(BASE, rel), 'rb').read()
    out = {}; prev = {}
    for o, (ko, mode) in spec.items():
        hd = TX.parse_header(b, o)
        pal = TX.read_palette(b, hd['pal_off'], hd['palcnt'])
        orig = TX.decode(b, o)
        W, H = orig.width, orig.height
        fill, outline = pick_colors(pal)
        new = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        if mode == 'terrain':
            gap = find_en_gap(orig)
            en = orig.crop((0, gap, W, H)); new.paste(en, (0, gap))
            k = draw_text_region(ko, W, gap, fill, outline, sw=1)
            new.paste(k, (0, 0), k)
        elif mode == 'keeptop':
            y1, x0, x1 = find_badge_box(orig)
            badge = orig.crop((x0, 0, x1, y1))       # Lv.N 배지만 잘라 보존
            new.paste(badge, (x0, 0))
            k = draw_text_region(ko, W, H - y1, fill, outline, sw=2)
            new.paste(k, (0, y1), k)
        else:  # full
            k = draw_text_region(ko, W, H, fill, outline, sw=2)
            new.paste(k, (0, 0), k)
        out[o] = TX.encode_c4(new, pal, hd['w'], hd['h'])
        prev[o] = (new, ko)
    return b, out, prev


results = {}
allprev = []
for rel, spec in SPEC.items():
    b, out, prev = build(rel, spec)
    results[rel] = (b, out)
    for o, (img, ko) in prev.items():
        allprev.append((rel, o, img, ko))

if args.preview:
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    cols = 4; cw, ch = 240, 90
    rows = (len(allprev) + cols - 1) // cols
    mont = Image.new('RGB', (cols * cw, rows * ch), (70, 70, 75))
    d = ImageDraw.Draw(mont)
    for i, (rel, o, img, ko) in enumerate(allprev):
        cx = (i % cols) * cw; cy = (i // cols) * ch
        bg = Image.new('RGB', img.size, (70, 70, 75)); bg.paste(img, (0, 0), img)
        mont.paste(bg, (cx + 4, cy + 16))
        d.text((cx + 4, cy + 2), f"{rel[-12:]} {o:X}", fill=(0, 255, 0))
    mont.save(os.path.join(HERE, 'out', 'rule_labels_preview.png'))
    print("preview saved:", len(allprev), "labels")

if args.apply:
    for rel, (b, out) in results.items():
        bb = bytearray(b)
        for o, data in out.items():
            hd = TX.parse_header(b, o)
            assert len(data) == hd['imgsize'], (rel, hex(o), len(data), hd['imgsize'])
            bb[hd['img_off']: hd['img_off'] + hd['imgsize']] = data
        dst = os.path.join(HERE, '..', 'text_patch_work', 'patched_files', rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bb)
        assert os.path.getsize(dst) == len(b)
        print("APPLIED", rel, "labels:", len(out))
print("total labels:", len(allprev))
