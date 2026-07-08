# -*- coding: utf-8 -*-
""".vsc 코덱: 파일 전체 바이트역순 + XOR 0xFF <-> 평문."""

def vsc_decode(b: bytes) -> bytes:
    return bytes((c ^ 0xFF) for c in b[::-1])

def vsc_encode(plain: bytes) -> bytes:
    # decode의 완전 역연산 (involution: 역순+XOR 을 다시 적용)
    return bytes((c ^ 0xFF) for c in plain[::-1])
