"""Helpers compartidos para tests de los quality gates PIT-DEV.

``write_real_png`` genera un PNG VÁLIDO (parseable por python-pptx, que lee
IHDR para dimensionar la imagen) con payload incompresible para superar el
mínimo de bytes del gate QA — un fake "magic + padding" rompería el embed del
deck.
"""

from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_real_png(path: Path, *, width: int = 64, height: int = 64) -> Path:
    """PNG RGB válido con píxeles aleatorios (incompresible → >8 KB con 64×64)."""
    rows = bytearray()
    for _ in range(height):
        rows += b"\x00"  # filtro None por scanline
        rows += os.urandom(width * 3)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    payload = (
        PNG_MAGIC
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), 0))
        + _chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path
