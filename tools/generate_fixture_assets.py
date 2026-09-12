"""Generate tiny original PNG fixtures without third-party dependencies."""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def png(path: Path, color: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    width, height = 480, 300
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            use_accent = abs((height - 1 - y) - int((x / width) * height)) < 6
            row.extend(accent if use_accent else color)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(raw, 9))
    payload += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    fixtures = ROOT / "tests" / "fixtures" / "basic"
    old = fixtures / "old"
    new = fixtures / "new"
    png(old / "changed.png", (236, 241, 255), (190, 40, 40))
    png(new / "changed.png", (236, 255, 241), (30, 90, 210))
    png(old / "same-old-name.png", (245, 245, 245), (80, 80, 80))
    (new / "same-new-name.png").write_bytes((old / "same-old-name.png").read_bytes())
    png(old / "removed.png", (255, 238, 238), (180, 20, 20))
    png(new / "added.png", (238, 245, 255), (20, 80, 190))
    png(old / "panel-a.png", (245, 245, 245), (40, 40, 40))
    (new / "panel-a.png").write_bytes((old / "panel-a.png").read_bytes())
    png(old / "panel-b.png", (255, 245, 220), (170, 90, 10))
    png(new / "panel-b.png", (235, 250, 255), (0, 120, 150))
    png(new / "panel-c.png", (244, 236, 255), (100, 40, 180))


if __name__ == "__main__":
    main()
