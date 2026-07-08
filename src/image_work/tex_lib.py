# -*- coding: utf-8 -*-
"""@Texture(GameCube) 블록 파서 + 디코더. C4/C8 팔레트(RGB5A3/RGB565) 지원."""
import struct
from PIL import Image

MAGIC = b'@Texture'


def find_blocks(data):
    out = []
    i = 0
    while True:
        i = data.find(MAGIC, i)
        if i < 0:
            break
        out.append(i)
        i += 1
    return out


def rgb5a3(v):
    # GameCube RGB5A3: bit15=1 -> RGB555(opaque); bit15=0 -> ARGB3444
    if v & 0x8000:
        r = (v >> 10) & 0x1F; g = (v >> 5) & 0x1F; b = v & 0x1F
        return (r << 3 | r >> 2, g << 3 | g >> 2, b << 3 | b >> 2, 255)
    else:
        a = (v >> 12) & 0x7; r = (v >> 8) & 0xF; g = (v >> 4) & 0xF; b = v & 0xF
        return (r << 4 | r, g << 4 | g, b << 4 | b, (a << 5 | a << 2 | a >> 1))


def parse_header(data, off):
    w = struct.unpack_from('>I', data, off + 0x10)[0]
    h = struct.unpack_from('>I', data, off + 0x14)[0]
    palcnt = struct.unpack_from('>I', data, off + 0x18)[0]
    imgsize = struct.unpack_from('>I', data, off + 0x38)[0]
    pal_off = off + 0x40
    img_off = pal_off + palcnt * 2
    return {'w': w, 'h': h, 'palcnt': palcnt, 'imgsize': imgsize,
            'pal_off': pal_off, 'img_off': img_off}


def read_palette(data, pal_off, palcnt):
    pal = []
    for i in range(palcnt):
        v = struct.unpack_from('>H', data, pal_off + i * 2)[0]
        pal.append(rgb5a3(v))
    return pal


def _nearest(pal, rgba):
    # 알파 우선(투명/불투명 구분) 후 RGB 거리
    r, g, b, a = rgba
    best = 0; bestd = 1 << 30
    for i, (pr, pg, pb, pa) in enumerate(pal):
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2 + 3 * (pa - a) ** 2
        if d < bestd:
            bestd = d; best = i
    return best


def encode_c4(img, pal, w, h):
    """PIL RGBA 이미지를 팔레트 최근접 인덱스로 C4(4bpp,8x8타일) 바이트로 인코딩."""
    img = img.convert('RGBA')
    px = img.load()
    # 픽셀->인덱스 (캐시)
    cache = {}
    def idx(x, y):
        if x >= w or y >= h:
            return 0
        c = px[x, y]
        if c not in cache:
            cache[c] = _nearest(pal, c)
        return cache[c]
    def align(n, a): return (n + a - 1) // a * a
    pw, ph = align(w, 8), align(h, 8)
    out = bytearray()
    for ty in range(0, ph, 8):
        for tx in range(0, pw, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    hi = idx(tx + x, ty + y)
                    lo = idx(tx + x + 1, ty + y)
                    out.append(((hi & 0xF) << 4) | (lo & 0xF))
    return bytes(out)


def decode(data, off):
    """@Texture 블록 -> PIL RGBA Image (실패시 None)."""
    hd = parse_header(data, off)
    w, h, palcnt = hd['w'], hd['h'], hd['palcnt']
    if w <= 0 or h <= 0 or w > 1024 or h > 1024:
        return None
    if palcnt not in (16, 256):
        return None
    pal = read_palette(data, hd['pal_off'], palcnt)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = img.load()
    raw = data[hd['img_off']: hd['img_off'] + hd['imgsize']]
    bpp4 = (palcnt == 16)
    # 8x8 타일
    p = 0
    def align(n, a): return (n + a - 1) // a * a
    pw = align(w, 8); ph = align(h, 8)
    try:
        if bpp4:
            for ty in range(0, ph, 8):
                for tx in range(0, pw, 8):
                    for y in range(8):
                        for x in range(0, 8, 2):
                            byte = raw[p]; p += 1
                            for nib, dx in ((byte >> 4, x), (byte & 0xF, x + 1)):
                                X, Y = tx + dx, ty + y
                                if X < w and Y < h:
                                    px[X, Y] = pal[nib]
        else:  # C8
            for ty in range(0, ph, 8):
                for tx in range(0, pw, 8):
                    for y in range(8):
                        for x in range(8):
                            idx = raw[p]; p += 1
                            X, Y = tx + x, ty + y
                            if X < w and Y < h and idx < len(pal):
                                px[X, Y] = pal[idx]
    except IndexError:
        return None
    return img
