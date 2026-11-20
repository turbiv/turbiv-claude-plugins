"""Test helpers: put the server folder on sys.path and build tiny image files."""
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))


def png_bytes(width=2, height=3):
    """A valid, tiny RGB PNG."""
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def jpeg_bytes(width=5, height=7):
    """A JPEG header with an APP0 segment then SOF0; enough for size parsing."""
    app0 = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = struct.pack(">BHHB", 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    return (b"\xff\xd8"
            + b"\xff\xe0" + struct.pack(">H", len(app0) + 2) + app0
            + b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof
            + b"\xff\xd9")


def webp_bytes(width=9, height=4, kind="VP8X"):
    """A WebP header of the given chunk kind (VP8X, VP8 or VP8L)."""
    if kind == "VP8X":
        payload = b"\x00\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    elif kind == "VP8":
        payload = b"\x00\x00\x00" + b"\x9d\x01\x2a" + struct.pack("<HH", width, height) + b"\x00" * 4
    else:  # VP8L
        bits = (width - 1) | ((height - 1) << 14)
        payload = b"\x2f" + struct.pack("<I", bits) + b"\x00" * 4
    body = b"WEBP" + kind.encode().ljust(4) + struct.pack("<I", len(payload)) + payload
    return b"RIFF" + struct.pack("<I", len(body)) + body
