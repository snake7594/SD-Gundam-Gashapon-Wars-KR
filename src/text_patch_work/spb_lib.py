# -*- coding: utf-8 -*-
"""
SD Gundam Gashapon Wars (GGPJB2) - SPB(SPAR) 시나리오 대사 추출/재삽입 라이브러리.

포맷 (리버스엔지니어링 확정):
  파일 헤더:
    +0x00  "SPAR"
    +0x04  u32 LE  version (=4)
    +0x08  u32 LE  file size
    +0x0C  u32 LE  entry/command count
    +0x10~         선형 명령 스트림 (opcode u16 LE + operands)
  텍스트 명령:
    04 00            opcode = 4 (show text)
    <len u16 LE>     문자열 바이트 길이 (마지막 널 종료 포함)
    <sjis bytes>     본문
    00               널 종료
  * 절대 오프셋/점프 테이블 없음 -> 동일 크기 유지 시 완전 안전.
"""
from __future__ import annotations
import struct
from pathlib import Path
from typing import List, Dict

TEXT_OPCODE = b"\x04\x00"


def _valid_string(seg: bytes) -> bool:
    if not seg:
        return False
    try:
        seg.decode("cp932")
    except UnicodeDecodeError:
        return False
    return True


def find_text_commands(data: bytes) -> List[Dict]:
    """모든 텍스트 명령을 찾는다. 반환: [{'str_off','length','raw','text'}]"""
    out: List[Dict] = []
    n = len(data)
    i = 0x10  # 스트림 시작
    while i < n - 4:
        if data[i:i+2] == TEXT_OPCODE:
            length = struct.unpack_from("<H", data, i + 2)[0]
            str_off = i + 4
            if 2 <= length <= 4000 and str_off + length <= n:
                if data[str_off + length - 1] == 0:  # 널 종료 확인
                    body = data[str_off: str_off + length - 1]
                    if _valid_string(body):
                        out.append({
                            "cmd_off": i,
                            "str_off": str_off,
                            "length": length,          # 널 포함 총 바이트
                            "raw": body,               # 널 제외 원본 바이트
                            "text": body.decode("cp932"),
                        })
                        i = str_off + length
                        continue
        i += 1
    return out


def extract_file(path: Path) -> Dict:
    data = path.read_bytes()
    if data[:4] != b"SPAR":
        return {"file": str(path), "ok": False, "cmds": []}
    cmds = find_text_commands(data)
    return {
        "file": str(path),
        "size": len(data),
        "ok": True,
        "cmds": cmds,
    }


def encode_same_size(korean_bytes: bytes, orig_length: int) -> bytes:
    """
    korean_bytes(널 제외) 를 원래 length(널 포함) 슬롯에 맞춰 인코딩.
    -> korean_bytes + 0x00(종료) + 0x00 패딩, 총 orig_length 바이트.
    맞지 않으면 ValueError.
    """
    if len(korean_bytes) + 1 > orig_length:
        raise ValueError(f"too long: {len(korean_bytes)+1} > {orig_length}")
    return korean_bytes + b"\x00" * (orig_length - len(korean_bytes))


def rebuild_file_inplace(data: bytearray, replacements: List[Dict]) -> bytearray:
    """
    replacements: [{'str_off','length','new_raw'}] new_raw = 널 제외 한글 바이트.
    동일 크기(orig length 슬롯)로 제자리 치환. 파일 크기/구조 불변.
    """
    for r in replacements:
        slot = r["length"]
        payload = encode_same_size(r["new_raw"], slot)
        so = r["str_off"]
        data[so: so + slot] = payload
    return data
