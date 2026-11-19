#!/usr/bin/env python3
"""Generate the two Saman OS launcher icons (About / Power-off) as 48x48
PNGs with only the standard library, into the overlay tree so tint2's
hicolor lookup finds them. No image editor needed on this VM."""
import os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "rootfs", "usr", "share", "icons", "hicolor", "48x48", "apps")
os.makedirs(OUT, exist_ok=True)

def png_rgb(path, pixels, w, h):
    # pixels: list of rows of (r,g,b,a)
    raw = b""
    for row in pixels:
        raw += b"\x00" + b"".join(struct.pack("BBBB", *px) for px in row)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9))
    data += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)

def blank(w, h, color):
    return [[color for _ in range(w)] for _ in range(h)]

def circle(px, cx, cy, r, color):
    for y in range(len(px)):
        for x in range(len(px[0])):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px[y][x] = color

def rect(px, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(len(px), y1)):
        for x in range(max(0, x0), min(len(px[0]), x1)):
            px[y][x] = color

# About: Saman blue disc, white "i" (dot + stem).
W = H = 48
px = blank(W, H, (0, 0, 0, 0))
circle(px, 24, 24, 22, (36, 86, 168, 255))
rect(px, 22, 20, 26, 38, (255, 255, 255, 255))
circle(px, 24, 13, 3, (255, 255, 255, 255))
png_rgb(os.path.join(OUT, "saman-about.png"), px, W, H)

# Power-off: dark red disc, white power symbol (ring + bar).
px = blank(W, H, (0, 0, 0, 0))
circle(px, 24, 25, 22, (178, 34, 34, 255))
# ring: white circle minus inner disc
circle(px, 24, 25, 13, (255, 255, 255, 255))
circle(px, 24, 25, 9, (178, 34, 34, 255))
# bar on top (cuts the ring)
rect(px, 22, 6, 26, 20, (255, 255, 255, 255))
png_rgb(os.path.join(OUT, "saman-poweroff.png"), px, W, H)

print("icons written to", OUT)
