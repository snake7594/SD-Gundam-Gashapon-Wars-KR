# -*- coding: utf-8 -*-
"""
main.dol 내장 @Texture C4(4bpp) 폰트 시트를 한글 독음 글리프로 패치하고,
필요하면 GameCube ISO 안의 main.dol까지 직접 교체하는 도구입니다.

필요 패키지:
    pip install pillow

기본 대상:
    @Texture #423~#426 : 한자 폰트 시트
    셀 크기 25x25, 가로 16칸

CSV 형식(readings.csv):
    tex_id,cell,hanja,hangul
    423,0,亞,아
    423,1,哀,애

cell은 0부터 시작합니다. row/col 열을 대신 써도 됩니다.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[오류] Pillow가 필요합니다. 먼저 실행하세요: pip install pillow")
    sys.exit(1)

MAGIC = b"@Texture"
CELL_SIZE = 25
DEFAULT_COLS = 16
DEFAULT_KANJI_TEXTURES = [423, 424, 425, 426]

# DOL 안에는 423~426번 시트의 글자 순서를 나타내는 CP932 문자열 테이블이 있습니다.
# 이 앵커를 찾아 2048바이트 = 1024글자를 읽으면 4개 블록(각 256셀)의 한자 순서를 얻습니다.
FONT_TABLE_ANCHOR = "一右雨円王音下火花貝学気九休玉金"
FONT_TABLE_BYTES = 2048
FONT_TABLE_BLOCK_SIZE = 256
BUILTIN_READING_CSV = "builtin_hanja_readings.csv"


@dataclass
class TextureInfo:
    tex_id: int
    offset: int
    width: int
    height: int
    image_size: int
    palette_offset: int
    image_offset: int


def be32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def u32be(n: int) -> bytes:
    return struct.pack(">I", n)


def align_up(n: int, align: int) -> int:
    return (n + align - 1) // align * align


def find_texture_offsets(data: bytes | bytearray) -> List[int]:
    offsets: List[int] = []
    pos = 0
    while True:
        pos = data.find(MAGIC, pos)
        if pos < 0:
            break
        offsets.append(pos)
        pos += 1
    return offsets


def read_texture_info(data: bytes | bytearray, tex_id: int) -> TextureInfo:
    offsets = find_texture_offsets(data)
    if tex_id < 0 or tex_id >= len(offsets):
        raise ValueError(f"@Texture #{tex_id} 없음. 발견된 @Texture 수: {len(offsets)}")
    off = offsets[tex_id]
    width = be32(data, off + 0x10)
    height = be32(data, off + 0x14)
    image_size = be32(data, off + 0x38)
    return TextureInfo(
        tex_id=tex_id,
        offset=off,
        width=width,
        height=height,
        image_size=image_size,
        palette_offset=off + 0x40,
        image_offset=off + 0x60,
    )


def decode_c4_indices(raw: bytes, width: int, height: int) -> List[List[int]]:
    """GameCube/Wii C4: 8x8 타일, 4bpp, 1바이트에 픽셀 2개."""
    padded_w = align_up(width, 8)
    padded_h = align_up(height, 8)
    expected = padded_w * padded_h // 2
    if len(raw) < expected:
        raise ValueError(f"C4 데이터가 짧습니다: {len(raw)} < {expected}")

    out = [[0 for _ in range(width)] for _ in range(height)]
    p = 0
    for ty in range(0, padded_h, 8):
        for tx in range(0, padded_w, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    byte = raw[p]
                    p += 1
                    for nibble, dx in ((byte >> 4, x), (byte & 0x0F, x + 1)):
                        px = tx + dx
                        py = ty + y
                        if px < width and py < height:
                            out[py][px] = nibble
    return out


def encode_c4_indices(indices: List[List[int]], width: int, height: int) -> bytes:
    padded_w = align_up(width, 8)
    padded_h = align_up(height, 8)
    out = bytearray(padded_w * padded_h // 2)
    p = 0
    for ty in range(0, padded_h, 8):
        for tx in range(0, padded_w, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    vals = []
                    for dx in (x, x + 1):
                        px = tx + dx
                        py = ty + y
                        if px < width and py < height:
                            vals.append(indices[py][px] & 0x0F)
                        else:
                            vals.append(0)
                    out[p] = (vals[0] << 4) | vals[1]
                    p += 1
    return bytes(out)


def indices_to_black_preview(indices: List[List[int]], width: int, height: int) -> Image.Image:
    """인덱스 0~7을 흰색 알파로 보고 검은 배경 미리보기 생성."""
    img = Image.new("RGB", (width, height), "black")
    px = img.load()
    for y in range(height):
        row = indices[y]
        for x in range(width):
            v = row[x]
            # 이 게임의 폰트 팔레트는 0~7이 흰색 알파 단계입니다.
            if v <= 7:
                c = int(round(v * 255 / 7))
            else:
                c = 255
            px[x, y] = (c, c, c)
    return img


def find_font_file(user_font: Optional[str]) -> str:
    candidates: List[str] = []
    if user_font:
        candidates.append(user_font)

    # Windows 우선. 사용자가 별도 지정하지 않으면 맑은 고딕 사용.
    win = os.environ.get("WINDIR", r"C:\Windows")
    candidates += [
        str(Path(win) / "Fonts" / "malgun.ttf"),
        str(Path(win) / "Fonts" / "malgunbd.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError(
        "한글 TTF/TTC/OTF 폰트를 찾지 못했습니다. --font 옵션으로 malgun.ttf 같은 폰트를 지정하세요."
    )


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    # TTC도 Pillow에서 보통 그대로 열립니다.
    return ImageFont.truetype(font_path, size=size)


def draw_reading_cell(
    reading: str,
    font_path: str,
    x_offset: int = 0,
    y_offset: int = 0,
    stroke_width: int = 0,
) -> Image.Image:
    """25x25 L 이미지에 흰색 알파로 독음 한 글자/문자열을 그립니다."""
    cell = Image.new("L", (CELL_SIZE, CELL_SIZE), 0)
    draw = ImageDraw.Draw(cell)
    text = str(reading).replace("\\n", "\n").strip()
    if not text:
        return cell

    # 줄바꿈이 있으면 줄 단위로, 아니면 한 줄로 최대 크기에 맞춥니다.
    lines = text.split("\n")

    best_font = None
    best_bboxes = None
    best_total_w = 0
    best_total_h = 0

    # 한글 한 음절은 23~24px도 들어가지만, 기종별 렌더 차이를 감안해 23부터 시도.
    # 게임이 셀 오른쪽 끝을 살짝 클립하므로 폭 여유(CELL_SIZE-4)를 둔다.
    for size in range(23, 5, -1):
        font = load_font(font_path, size)
        bboxes = [draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width) for line in lines]
        widths = [b[2] - b[0] for b in bboxes]
        heights = [b[3] - b[1] for b in bboxes]
        total_w = max(widths) if widths else 0
        total_h = sum(heights) + max(0, len(lines) - 1) * 1
        if total_w <= CELL_SIZE - 4 and total_h <= CELL_SIZE - 2:
            best_font = font
            best_bboxes = bboxes
            best_total_w = total_w
            best_total_h = total_h
            break

    if best_font is None:
        best_font = load_font(font_path, 6)
        best_bboxes = [draw.textbbox((0, 0), line, font=best_font, stroke_width=stroke_width) for line in lines]
        best_total_w = max((b[2] - b[0] for b in best_bboxes), default=0)
        best_total_h = sum((b[3] - b[1] for b in best_bboxes)) + max(0, len(lines) - 1)

    y = (CELL_SIZE - best_total_h) // 2 + y_offset
    for line, bbox in zip(lines, best_bboxes):
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (CELL_SIZE - w) // 2 - bbox[0] + x_offset
        draw.text((x, y - bbox[1]), line, font=best_font, fill=255, stroke_width=stroke_width, stroke_fill=255)
        y += h + 1

    return cell


def mask_to_c4_indices(mask: Image.Image) -> List[List[int]]:
    """L 마스크 0~255를 기존 팔레트의 0~7 알파 단계로 변환."""
    mask = mask.convert("L")
    out = [[0 for _ in range(mask.width)] for _ in range(mask.height)]
    px = mask.load()
    for y in range(mask.height):
        for x in range(mask.width):
            a = px[x, y]
            out[y][x] = max(0, min(7, int(round(a * 7 / 255))))
    return out


def parse_csv_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows


def get_row_value(row: Dict[str, str], *names: str) -> str:
    lower_map = {k.lower().strip(): v for k, v in row.items() if k is not None}
    for n in names:
        v = lower_map.get(n.lower())
        if v is not None:
            return str(v).strip()
    return ""



def is_cjk_kanji(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch[0])
    return (
        0x3400 <= cp <= 0x4DBF or
        0x4E00 <= cp <= 0x9FFF or
        0xF900 <= cp <= 0xFAFF
    )


_TEX_HANJA_TAB_CACHE: Optional[List[str]] = None


def read_xetexko_hanja_tab() -> Optional[List[str]]:
    """개발/리눅스 환경에 xetexko 한자음 표가 있으면 보조 독음표로 사용합니다."""
    global _TEX_HANJA_TAB_CACHE
    if _TEX_HANJA_TAB_CACHE is not None:
        return _TEX_HANJA_TAB_CACHE
    candidates = [
        Path('/usr/share/texlive/texmf-dist/tex/xetex/xetexko/hanja_hangul.tab'),
        Path('/usr/local/texlive/texmf-local/tex/xetex/xetexko/hanja_hangul.tab'),
    ]
    for p in candidates:
        if p.exists():
            try:
                _TEX_HANJA_TAB_CACHE = p.read_text(encoding='utf-8').splitlines()
                return _TEX_HANJA_TAB_CACHE
            except Exception:
                pass
    _TEX_HANJA_TAB_CACHE = []
    return None


def get_xetexko_reading(ch: str) -> str:
    tab = read_xetexko_hanja_tab()
    if not tab or not ch:
        return ""
    cp = ord(ch)
    idx = cp - 0x4E00
    if 0 <= idx < len(tab):
        try:
            return chr(int(tab[idx].strip()))
        except Exception:
            return ""
    return ""


def load_reading_csv_into(mapping: Dict[str, str], csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    count = 0
    with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hanja = get_row_value(row, 'hanja', 'kanji', '한자')
            hangul = get_row_value(row, 'hangul', 'reading', 'dokuon', '독음', '한글')
            if hanja and hangul:
                mapping[hanja[0]] = hangul
                count += 1
    return count


def load_reading_map(map_path: Optional[Path] = None, override_map: Optional[Path] = None) -> Dict[str, str]:
    """내장 독음표를 읽고, 사용자가 지정한 표가 있으면 덮어씁니다."""
    mapping: Dict[str, str] = {}
    script_dir = Path(__file__).resolve().parent
    builtin = script_dir / BUILTIN_READING_CSV
    n_builtin = load_reading_csv_into(mapping, builtin)
    if n_builtin:
        print(f"    내장 독음표 읽음: {builtin} ({n_builtin}개)")
    else:
        print("    내장 독음표를 찾지 못했습니다. 가능한 경우 xetexko 표로 보조 변환합니다.")

    if map_path:
        n = load_reading_csv_into(mapping, map_path)
        print(f"    사용자 독음표 읽음: {map_path} ({n}개, 내장값 덮어쓰기)")
    if override_map:
        n = load_reading_csv_into(mapping, override_map)
        print(f"    보정 독음표 읽음: {override_map} ({n}개, 최종 덮어쓰기)")
    return mapping


def lookup_reading(ch: str, mapping: Dict[str, str]) -> str:
    if not ch or ch in {' ', '　', '\t', '\r', '\n'}:
        return ""
    if ch in mapping:
        return mapping[ch]
    if is_cjk_kanji(ch):
        return get_xetexko_reading(ch)
    return ""


def extract_font_char_table(data: bytes | bytearray) -> Tuple[List[str], int]:
    anchor = FONT_TABLE_ANCHOR.encode('cp932')
    pos = bytes(data).find(anchor)
    if pos < 0:
        raise ValueError("DOL에서 폰트 글자 순서 테이블을 찾지 못했습니다. 앵커: " + FONT_TABLE_ANCHOR)
    raw = bytes(data[pos : pos + FONT_TABLE_BYTES])
    if len(raw) != FONT_TABLE_BYTES:
        raise ValueError(f"폰트 글자 순서 테이블이 짧습니다: {len(raw)} < {FONT_TABLE_BYTES}")
    try:
        text = raw.decode('cp932')
    except UnicodeDecodeError as e:
        raise ValueError(f"폰트 글자 순서 테이블 CP932 디코딩 실패: {e}")
    chars = list(text)
    if len(chars) != FONT_TABLE_BYTES // 2:
        raise ValueError(f"폰트 글자 수가 예상과 다릅니다: {len(chars)} != {FONT_TABLE_BYTES//2}")
    return chars, pos


def iter_auto_reading_rows(
    data: bytes | bytearray,
    reading_map: Dict[str, str],
    textures: Iterable[int] = DEFAULT_KANJI_TEXTURES,
) -> Tuple[List[Dict[str, str]], int]:
    chars, table_offset = extract_font_char_table(data)
    texture_list = list(textures)
    info_by_tex = {tex_id: read_texture_info(data, tex_id) for tex_id in texture_list}

    rows: List[Dict[str, str]] = []
    for i, ch in enumerate(chars):
        block = i // FONT_TABLE_BLOCK_SIZE
        cell = i % FONT_TABLE_BLOCK_SIZE
        if block >= len(texture_list):
            continue
        tex_id = texture_list[block]
        info = info_by_tex[tex_id]
        cols = info.width // CELL_SIZE
        visible_cells = (info.width // CELL_SIZE) * (info.height // CELL_SIZE)
        if cell >= visible_cells:
            # 423/424 시트 뒤쪽의 패딩 공백 16/48칸은 실제 이미지 범위 밖입니다.
            continue
        if ch in {' ', '　', '\x00'}:
            continue
        hangul = lookup_reading(ch, reading_map)
        if hangul:
            status = 'ok'
        elif is_cjk_kanji(ch):
            status = 'no_reading'
        else:
            status = 'non_kanji'
        rows.append({
            'tex_id': str(tex_id),
            'cell': str(cell),
            'row': str(cell // cols),
            'col': str(cell % cols),
            'hanja': ch,
            'hangul': hangul,
            'status': status,
        })
    return rows, table_offset


def write_auto_reading_csv(rows: List[Dict[str, str]], out_csv: Path, only_patchable: bool = False) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ['tex_id', 'cell', 'row', 'col', 'hanja', 'hangul', 'status']
    with out_csv.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if only_patchable and row.get('status') != 'ok':
                continue
            writer.writerow(row)


def generate_auto_csv(
    dol_in: Path,
    out_csv: Path,
    map_path: Optional[Path],
    override_map: Optional[Path],
    only_patchable: bool,
) -> Path:
    print("[1] DOL 읽기:", dol_in)
    data = dol_in.read_bytes()
    print("[2] 폰트 글자 순서 테이블 추출")
    reading_map = load_reading_map(map_path, override_map)
    rows, table_offset = iter_auto_reading_rows(data, reading_map)
    ok = sum(1 for r in rows if r['status'] == 'ok')
    no = sum(1 for r in rows if r['status'] == 'no_reading')
    non = sum(1 for r in rows if r['status'] == 'non_kanji')
    print(f"    테이블 offset=0x{table_offset:X}, visible rows={len(rows)}, ok={ok}, no_reading={no}, non_kanji={non}")
    print("[3] 자동 독음 CSV 저장:", out_csv)
    write_auto_reading_csv(rows, out_csv, only_patchable=only_patchable)
    return out_csv


def extract_main_dol_from_gamecube_iso(iso_in: Path, dol_out: Path) -> Tuple[int, int, int]:
    with iso_in.open('rb') as f:
        f.seek(0, os.SEEK_END)
        iso_size = f.tell()
        if iso_size < 0x430:
            raise ValueError("ISO 파일이 너무 작습니다.")
        f.seek(0x420)
        dol_off = struct.unpack('>I', f.read(4))[0]
        fst_off = struct.unpack('>I', f.read(4))[0]
        fst_size = struct.unpack('>I', f.read(4))[0]
        if dol_off <= 0 or fst_off <= dol_off or dol_off >= iso_size:
            raise ValueError("일반 GameCube ISO의 main.dol 위치를 찾지 못했습니다. Wii ISO는 wit/wwt 방식이 필요합니다.")
        dol_space = fst_off - dol_off
        f.seek(dol_off)
        blob = f.read(dol_space)
    eff = dol_effective_size(blob)
    dol_out.parent.mkdir(parents=True, exist_ok=True)
    dol_out.write_bytes(blob[:eff])
    print(f"    ISO에서 main.dol 추출: offset=0x{dol_off:X}, size=0x{eff:X}, FST=0x{fst_off:X}")
    return dol_off, fst_off, eff


def auto_patch_dol_command(
    dol_in: Path,
    dol_out: Path,
    csv_out: Optional[Path],
    map_path: Optional[Path],
    override_map: Optional[Path],
    font_path: Optional[str],
    preview_dir: Optional[Path],
    x_offset: int,
    y_offset: int,
    stroke_width: int,
) -> None:
    if csv_out is None:
        csv_out = dol_out.with_name(dol_out.stem + '_auto_readings.csv')
    generate_auto_csv(dol_in, csv_out, map_path, override_map, only_patchable=False)
    patch_dol_font(
        dol_in=dol_in,
        dol_out=dol_out,
        csv_path=csv_out,
        font_path=font_path,
        preview_dir=preview_dir,
        x_offset=x_offset,
        y_offset=y_offset,
        stroke_width=stroke_width,
    )


def auto_patch_iso_command(
    iso_in: Path,
    iso_out: Path,
    work_dir: Path,
    csv_out: Optional[Path],
    map_path: Optional[Path],
    override_map: Optional[Path],
    font_path: Optional[str],
    preview_dir: Optional[Path],
    x_offset: int,
    y_offset: int,
    stroke_width: int,
) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    extracted_dol = work_dir / 'extracted_main.dol'
    patched_dol = work_dir / 'patched_main.dol'
    if csv_out is None:
        csv_out = work_dir / 'auto_readings.csv'
    print("[0] ISO에서 main.dol 추출")
    extract_main_dol_from_gamecube_iso(iso_in, extracted_dol)
    auto_patch_dol_command(
        dol_in=extracted_dol,
        dol_out=patched_dol,
        csv_out=csv_out,
        map_path=map_path,
        override_map=override_map,
        font_path=font_path,
        preview_dir=preview_dir,
        x_offset=x_offset,
        y_offset=y_offset,
        stroke_width=stroke_width,
    )
    patch_gamecube_iso(iso_in, iso_out, patched_dol)


def load_reading_patches(csv_path: Path) -> List[Tuple[int, int, str, str]]:
    patches: List[Tuple[int, int, str, str]] = []
    rows = parse_csv_rows(csv_path)
    for line_no, row in enumerate(rows, start=2):
        enabled = get_row_value(row, "enabled", "use", "사용")
        if enabled and enabled.lower() in {"0", "false", "no", "n", "x", "skip", "미사용"}:
            continue

        tex_s = get_row_value(row, "tex_id", "texture", "sheet", "시트")
        cell_s = get_row_value(row, "cell", "index", "칸", "셀")
        row_s = get_row_value(row, "row", "행")
        col_s = get_row_value(row, "col", "column", "열")
        hanja = get_row_value(row, "hanja", "kanji", "한자")
        hangul = get_row_value(row, "hangul", "reading", "dokuon", "독음", "한글")

        if not tex_s:
            raise ValueError(f"CSV {line_no}행: tex_id가 없습니다.")
        tex_id = int(tex_s, 0)

        if cell_s:
            cell = int(cell_s, 0)
        elif row_s and col_s:
            cell = int(row_s, 0) * DEFAULT_COLS + int(col_s, 0)
        else:
            raise ValueError(f"CSV {line_no}행: cell 또는 row/col이 없습니다.")

        if not hangul:
            # 템플릿의 빈 행은 건너뜁니다.
            continue
        patches.append((tex_id, cell, hanja, hangul))
    return patches


def patch_dol_font(
    dol_in: Path,
    dol_out: Path,
    csv_path: Path,
    font_path: Optional[str],
    preview_dir: Optional[Path],
    x_offset: int,
    y_offset: int,
    stroke_width: int,
) -> None:
    print("[1] DOL 읽기:", dol_in)
    data = bytearray(dol_in.read_bytes())

    print("[2] @Texture 검색")
    texture_offsets = find_texture_offsets(data)
    print(f"    발견된 @Texture 수: {len(texture_offsets)}")

    print("[3] 독음 CSV 읽기:", csv_path)
    patches = load_reading_patches(csv_path)
    print(f"    적용할 셀 수: {len(patches)}")
    if not patches:
        raise ValueError("CSV에 적용할 hangul/reading 값이 없습니다.")

    font = find_font_file(font_path)
    print("[4] 사용 폰트:", font)

    patches_by_tex: Dict[int, List[Tuple[int, str, str]]] = {}
    for tex_id, cell, hanja, hangul in patches:
        patches_by_tex.setdefault(tex_id, []).append((cell, hanja, hangul))

    for tex_id, items in sorted(patches_by_tex.items()):
        info = read_texture_info(data, tex_id)
        cols = info.width // CELL_SIZE
        rows = info.height // CELL_SIZE
        if cols <= 0 or rows <= 0:
            raise ValueError(f"@Texture #{tex_id}: 셀 계산 실패: {info.width}x{info.height}")

        print(f"[5] @Texture #{tex_id} 패치: offset=0x{info.offset:X}, size={info.width}x{info.height}, cells={cols}x{rows}")
        raw = bytes(data[info.image_offset : info.image_offset + info.image_size])
        indices = decode_c4_indices(raw, info.width, info.height)

        for cell, hanja, hangul in items:
            if cell < 0 or cell >= cols * rows:
                raise ValueError(f"@Texture #{tex_id}: cell {cell} 범위 초과. 가능 범위 0~{cols*rows-1}")
            cx = (cell % cols) * CELL_SIZE
            cy = (cell // cols) * CELL_SIZE

            # 기존 한자 글리프를 지우고 한글 독음을 새로 그림.
            for yy in range(CELL_SIZE):
                for xx in range(CELL_SIZE):
                    if cy + yy < info.height and cx + xx < info.width:
                        indices[cy + yy][cx + xx] = 0

            mask = draw_reading_cell(hangul, font, x_offset=x_offset, y_offset=y_offset, stroke_width=stroke_width)
            cell_indices = mask_to_c4_indices(mask)
            for yy in range(CELL_SIZE):
                for xx in range(CELL_SIZE):
                    if cy + yy < info.height and cx + xx < info.width:
                        indices[cy + yy][cx + xx] = cell_indices[yy][xx]

            print(f"    cell {cell:03d} ({cell//cols:02d},{cell%cols:02d}) {hanja or '-'} -> {hangul}")

        new_raw = encode_c4_indices(indices, info.width, info.height)
        if len(new_raw) != info.image_size:
            raise ValueError(f"@Texture #{tex_id}: 재인코딩 크기 불일치 {len(new_raw)} != {info.image_size}")
        data[info.image_offset : info.image_offset + info.image_size] = new_raw

        if preview_dir:
            preview_dir.mkdir(parents=True, exist_ok=True)
            prev = indices_to_black_preview(indices, info.width, info.height)
            prev_path = preview_dir / f"patched_tex_{tex_id}.png"
            prev.save(prev_path)
            print("    미리보기 저장:", prev_path)

    print("[6] 패치된 DOL 저장:", dol_out)
    dol_out.write_bytes(data)
    print("    완료")


def make_template_and_index(dol_in: Path, out_dir: Path, textures: Iterable[int]) -> None:
    print("[1] DOL 읽기:", dol_in)
    data = dol_in.read_bytes()
    out_dir.mkdir(parents=True, exist_ok=True)

    template_path = out_dir / "readings_template.csv"
    print("[2] 템플릿 CSV 생성:", template_path)
    with template_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tex_id", "cell", "row", "col", "hanja", "hangul"])
        for tex_id in textures:
            info = read_texture_info(data, tex_id)
            cols = info.width // CELL_SIZE
            rows = info.height // CELL_SIZE
            for cell in range(cols * rows):
                writer.writerow([tex_id, cell, cell // cols, cell % cols, "", ""])

    print("[3] 셀 번호 미리보기 생성")
    for tex_id in textures:
        info = read_texture_info(data, tex_id)
        raw = data[info.image_offset : info.image_offset + info.image_size]
        indices = decode_c4_indices(raw, info.width, info.height)
        img = indices_to_black_preview(indices, info.width, info.height).convert("RGB")
        draw = ImageDraw.Draw(img)
        cols = info.width // CELL_SIZE
        rows = info.height // CELL_SIZE
        try:
            number_font = ImageFont.truetype(find_font_file(None), 8)
        except Exception:
            number_font = ImageFont.load_default()
        for cell in range(cols * rows):
            x = (cell % cols) * CELL_SIZE
            y = (cell // cols) * CELL_SIZE
            # 격자선과 번호. 미리보기 이미지라 색상 지정 허용.
            draw.rectangle((x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1), outline=(80, 80, 80))
            draw.text((x + 1, y + 1), str(cell), fill=(255, 0, 0), font=number_font)
        out_path = out_dir / f"index_tex_{tex_id}.png"
        img.save(out_path)
        print("    저장:", out_path)

    print("    완료")


def dol_effective_size(dol: bytes | bytearray) -> int:
    """DOL 헤더의 섹션 오프셋+크기 기준 실제 DOL 크기 계산."""
    if len(dol) < 0x100:
        raise ValueError("DOL 파일이 너무 작습니다.")
    max_end = 0
    for i in range(18):
        file_off = be32(dol, 0x00 + i * 4)
        size = be32(dol, 0x90 + i * 4)
        if file_off and size:
            max_end = max(max_end, file_off + size)
    if max_end <= 0 or max_end > len(dol):
        raise ValueError(f"DOL 섹션 크기 계산 실패: max_end=0x{max_end:X}, file_size=0x{len(dol):X}")
    return max_end


def patch_gamecube_iso(iso_in: Path, iso_out: Path, patched_dol: Path) -> None:
    print("[1] ISO 복사:", iso_in, "->", iso_out)
    if iso_in.resolve() != iso_out.resolve():
        shutil.copyfile(iso_in, iso_out)

    new_dol = patched_dol.read_bytes()
    new_dol_eff = dol_effective_size(new_dol)
    if new_dol_eff != len(new_dol):
        print(f"    참고: DOL 유효 크기=0x{new_dol_eff:X}, 파일 크기=0x{len(new_dol):X}")

    with iso_out.open("r+b") as f:
        f.seek(0, os.SEEK_END)
        iso_size = f.tell()
        if iso_size < 0x430:
            raise ValueError("ISO 파일이 너무 작습니다.")

        f.seek(0x420)
        dol_off = struct.unpack(">I", f.read(4))[0]
        fst_off = struct.unpack(">I", f.read(4))[0]
        fst_size = struct.unpack(">I", f.read(4))[0]
        print(f"[2] GC 헤더: main.dol offset=0x{dol_off:X}, FST offset=0x{fst_off:X}, FST size=0x{fst_size:X}")

        if dol_off <= 0 or dol_off >= iso_size:
            raise ValueError("GameCube ISO의 main.dol offset을 찾지 못했습니다. Wii ISO는 이 방식으로 직접 패치할 수 없습니다.")
        if fst_off <= dol_off:
            raise ValueError("FST offset이 main.dol offset보다 앞입니다. 일반 GameCube ISO 구조가 아닙니다.")
        if dol_off + len(new_dol) > fst_off:
            raise ValueError(
                f"패치 DOL이 DOL 영역을 초과합니다: 0x{dol_off + len(new_dol):X} > FST 0x{fst_off:X}\n"
                "이 스크립트는 같은 크기/더 작은 DOL 교체만 안전하게 처리합니다."
            )

        dol_space = fst_off - dol_off
        f.seek(dol_off)
        old_dol_space = f.read(min(dol_space, len(new_dol)))
        if len(old_dol_space) >= 0x100:
            if old_dol_space[:0x100] != new_dol[:0x100]:
                print("    경고: ISO 내부 main.dol 헤더가 입력 DOL과 다릅니다. 다른 버전 ISO일 수 있습니다.")
            else:
                print("    ISO 내부 main.dol 헤더 확인 완료")

        print("[3] ISO 내부 main.dol 교체")
        f.seek(dol_off)
        f.write(new_dol)
        print("    완료:", iso_out)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="main.dol @Texture C4 한자 폰트를 한글 독음으로 패치하고 GC ISO에 재삽입합니다."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_tpl = sub.add_parser("template", help="readings_template.csv와 셀 번호 미리보기 PNG 생성")
    p_tpl.add_argument("--dol", required=True, type=Path, help="원본 main.dol")
    p_tpl.add_argument("--out-dir", default=Path("font_template"), type=Path, help="출력 폴더")
    p_tpl.add_argument("--textures", default=",".join(map(str, DEFAULT_KANJI_TEXTURES)), help="예: 423,424,425,426")

    p_patch = sub.add_parser("patch-dol", help="readings.csv를 적용해 patched_main.dol 생성")
    p_patch.add_argument("--dol", required=True, type=Path, help="원본 main.dol")
    p_patch.add_argument("--csv", required=True, type=Path, help="tex_id,cell,hanja,hangul 형식 CSV")
    p_patch.add_argument("--out", default=Path("patched_main.dol"), type=Path, help="패치된 main.dol 출력 경로")
    p_patch.add_argument("--font", default=None, help="한글 폰트 경로. 예: C:\\Windows\\Fonts\\malgun.ttf")
    p_patch.add_argument("--preview-dir", default=Path("patched_preview"), type=Path, help="패치 미리보기 PNG 출력 폴더. 끄려면 빈 문자열")
    p_patch.add_argument("--x-offset", type=int, default=0, help="글자 X 위치 보정")
    p_patch.add_argument("--y-offset", type=int, default=0, help="글자 Y 위치 보정")
    p_patch.add_argument("--stroke-width", type=int, default=0, help="획 두께 보정. 0 권장, 굵게는 1")


    p_auto_csv = sub.add_parser("auto-csv", help="DOL 내부 글자 순서표를 읽어 한자→한글 독음 CSV 자동 생성")
    p_auto_csv.add_argument("--dol", required=True, type=Path, help="원본 main.dol")
    p_auto_csv.add_argument("--out", default=Path("auto_readings.csv"), type=Path, help="자동 생성 CSV 출력 경로")
    p_auto_csv.add_argument("--map", default=None, type=Path, help="추가 독음표 CSV. hanja,hangul 열 사용")
    p_auto_csv.add_argument("--override-map", default=None, type=Path, help="최종 보정 독음표 CSV. hanja,hangul 열 사용")
    p_auto_csv.add_argument("--only-patchable", action="store_true", help="독음이 있는 행만 CSV에 저장")

    p_auto_patch = sub.add_parser("auto-patch-dol", help="DOL 내부 한자 순서표를 읽어 바로 한글 독음 폰트로 패치")
    p_auto_patch.add_argument("--dol", required=True, type=Path, help="원본 main.dol")
    p_auto_patch.add_argument("--out", default=Path("patched_main.dol"), type=Path, help="패치된 main.dol 출력 경로")
    p_auto_patch.add_argument("--csv-out", default=None, type=Path, help="자동 생성 독음 CSV 저장 경로")
    p_auto_patch.add_argument("--map", default=None, type=Path, help="추가 독음표 CSV. hanja,hangul 열 사용")
    p_auto_patch.add_argument("--override-map", default=None, type=Path, help="최종 보정 독음표 CSV. hanja,hangul 열 사용")
    p_auto_patch.add_argument("--font", default=None, help="한글 폰트 경로. 예: C:\\Windows\\Fonts\\malgun.ttf")
    p_auto_patch.add_argument("--preview-dir", default=Path("patched_preview"), type=Path, help="패치 미리보기 PNG 출력 폴더. 끄려면 빈 문자열")
    p_auto_patch.add_argument("--x-offset", type=int, default=0, help="글자 X 위치 보정")
    p_auto_patch.add_argument("--y-offset", type=int, default=0, help="글자 Y 위치 보정")
    p_auto_patch.add_argument("--stroke-width", type=int, default=0, help="획 두께 보정. 0 권장, 굵게는 1")

    p_auto_iso = sub.add_parser("auto-patch-iso", help="GameCube ISO에서 main.dol을 꺼내 한자 독음 패치 후 ISO에 바로 재삽입")
    p_auto_iso.add_argument("--iso", required=True, type=Path, help="원본 GameCube ISO")
    p_auto_iso.add_argument("--out", required=True, type=Path, help="패치된 ISO 출력 경로")
    p_auto_iso.add_argument("--work-dir", default=Path("auto_patch_work"), type=Path, help="중간 파일 출력 폴더")
    p_auto_iso.add_argument("--csv-out", default=None, type=Path, help="자동 생성 독음 CSV 저장 경로")
    p_auto_iso.add_argument("--map", default=None, type=Path, help="추가 독음표 CSV. hanja,hangul 열 사용")
    p_auto_iso.add_argument("--override-map", default=None, type=Path, help="최종 보정 독음표 CSV. hanja,hangul 열 사용")
    p_auto_iso.add_argument("--font", default=None, help="한글 폰트 경로. 예: C:\\Windows\\Fonts\\malgun.ttf")
    p_auto_iso.add_argument("--preview-dir", default=Path("patched_preview"), type=Path, help="패치 미리보기 PNG 출력 폴더. 끄려면 빈 문자열")
    p_auto_iso.add_argument("--x-offset", type=int, default=0, help="글자 X 위치 보정")
    p_auto_iso.add_argument("--y-offset", type=int, default=0, help="글자 Y 위치 보정")
    p_auto_iso.add_argument("--stroke-width", type=int, default=0, help="획 두께 보정. 0 권장, 굵게는 1")

    p_iso = sub.add_parser("patch-iso", help="GameCube ISO 내부 main.dol을 patched_main.dol로 교체")
    p_iso.add_argument("--iso", required=True, type=Path, help="원본 GameCube ISO")
    p_iso.add_argument("--dol", required=True, type=Path, help="패치된 main.dol")
    p_iso.add_argument("--out", required=True, type=Path, help="패치된 ISO 출력 경로")

    args = ap.parse_args()

    try:
        if args.cmd == "template":
            textures = [int(x.strip(), 0) for x in args.textures.split(",") if x.strip()]
            make_template_and_index(args.dol, args.out_dir, textures)
        elif args.cmd == "patch-dol":
            preview_dir = args.preview_dir if str(args.preview_dir).strip() else None
            patch_dol_font(
                dol_in=args.dol,
                dol_out=args.out,
                csv_path=args.csv,
                font_path=args.font,
                preview_dir=preview_dir,
                x_offset=args.x_offset,
                y_offset=args.y_offset,
                stroke_width=args.stroke_width,
            )

        elif args.cmd == "auto-csv":
            generate_auto_csv(
                dol_in=args.dol,
                out_csv=args.out,
                map_path=args.map,
                override_map=args.override_map,
                only_patchable=args.only_patchable,
            )
        elif args.cmd == "auto-patch-dol":
            preview_dir = args.preview_dir if str(args.preview_dir).strip() else None
            auto_patch_dol_command(
                dol_in=args.dol,
                dol_out=args.out,
                csv_out=args.csv_out,
                map_path=args.map,
                override_map=args.override_map,
                font_path=args.font,
                preview_dir=preview_dir,
                x_offset=args.x_offset,
                y_offset=args.y_offset,
                stroke_width=args.stroke_width,
            )
        elif args.cmd == "auto-patch-iso":
            preview_dir = args.preview_dir if str(args.preview_dir).strip() else None
            auto_patch_iso_command(
                iso_in=args.iso,
                iso_out=args.out,
                work_dir=args.work_dir,
                csv_out=args.csv_out,
                map_path=args.map,
                override_map=args.override_map,
                font_path=args.font,
                preview_dir=preview_dir,
                x_offset=args.x_offset,
                y_offset=args.y_offset,
                stroke_width=args.stroke_width,
            )
        elif args.cmd == "patch-iso":
            patch_gamecube_iso(args.iso, args.out, args.dol)
    except Exception as e:
        print("\n[오류]", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
