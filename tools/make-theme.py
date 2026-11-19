#!/usr/bin/env python3
"""Generate Saman OS 2.0's MODERN visual identity (post 13 Nov 2026 order:
the old handmade desktop's look -- teal-green bg, grey window, pixel
font, letter icons -- is REJECTED and must not be copied).

Produces, with only the standard library:
  * rootfs/usr/share/backgrounds/saman-gradient.png -- 1024x768 dark
    aurora gradient (deep navy -> indigo -> teal glow), no flat blue.
  * rootfs/usr/share/icons/hicolor/48x48/apps/saman-logo.png -- white
    bold "S" mark on a Saman-blue disc (the launcher / start mark).
  * rootfs/usr/share/themes/SamanOS/openbox-3/{themerc,*.xbm} -- flat
    dark theme: slate title bars, white text, sky accent.
"""
import math, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOTFS = os.path.join(HERE, "..", "rootfs")

# ---------------------------------------------------------------- PNG ----
def png_rgba(path, pixels):
    h = len(pixels); w = len(pixels[0])
    raw = b"".join(b"\x00" + b"".join(struct.pack("BBBB", *px) for px in row)
                   for row in pixels)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 6))
    data += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

# ------------------------------------------------------------- wallpaper --
W, H = 1024, 768
TOP = (10, 14, 34)        # deep navy
MID = (30, 27, 75)        # indigo
BOT = (13, 84, 84)        # deep teal
GLOW1 = (79, 70, 229)     # indigo glow, upper left
GLOW2 = (34, 211, 238)    # cyan glow, lower right
px = []
for y in range(H):
    t = y / (H - 1)
    base = lerp(lerp(TOP, MID, min(1, t * 1.6)), BOT, max(0, (t - 0.45) / 0.55)) \
        if t < 0.55 else lerp(MID, BOT, (t - 0.45) / 0.55)
    row = []
    for x in range(W):
        r, g, b = base
        d1 = math.hypot((x - 300) / 520, (y - 180) / 340)
        d2 = math.hypot((x - 780) / 560, (y - 620) / 360)
        w1 = max(0.0, 1 - d1) ** 2 * 0.55
        w2 = max(0.0, 1 - d2) ** 2 * 0.45
        r = min(255, int(r + GLOW1[0] * w1 + GLOW2[0] * w2))
        g = min(255, int(g + GLOW1[1] * w1 + GLOW2[1] * w2))
        b = min(255, int(b + GLOW1[2] * w1 + GLOW2[2] * w2))
        row.append((r, g, b, 255))
    px.append(row)
# Faint Saman "S" watermark at the centre (brand presence, no flat logo block).
S = ["01110", "10001", "10000", "01110", "00001", "10001", "01110"]
sc, gw, gh = 34, 5 * 34, 7 * 34
ox, oy = (W - gw) // 2, (H - gh) // 2
for ry, bits in enumerate(S):
    for rx, ch in enumerate(bits):
        if ch != "1":
            continue
        for dy in range(sc):
            for dx in range(sc):
                x, y = ox + rx * sc + dx, oy + ry * sc + dy
                r, g, b, _ = px[y][x]
                px[y][x] = (min(255, r + 26), min(255, g + 26), min(255, b + 26), 255)
png_rgba(os.path.join(ROOTFS, "usr/share/backgrounds/saman-gradient.png"), px)
print("wallpaper written")

# ------------------------------------------------------------------ logo --
# 5x7 bold "S"
S = ["01110", "10001", "10000", "01110", "00001", "10001", "01110"]
SZX, SZY = 48, 48
logo = [[(0, 0, 0, 0) for _ in range(SZX)] for _ in range(SZY)]
for y in range(SZY):
    for x in range(SZX):
        if (x - 24) ** 2 + (y - 24) ** 2 <= 22 ** 2:
            logo[y][x] = (36, 86, 168, 255)
gx, gy, sc = 11, 8, 5  # glyph origin + scale (5 cols * 5 = 25 wide)
for ry, bits in enumerate(S):
    for rx, ch in enumerate(bits):
        if ch == "1":
            for dy in range(sc):
                for dx in range(sc):
                    logo[gy + ry * sc + dy][gx + rx * sc + dx] = (255, 255, 255, 255)
png_rgba(os.path.join(ROOTFS, "usr/share/icons/hicolor/48x48/apps/saman-logo.png"), logo)
print("logo written")

# ------------------------------------------------------------------ theme --
TD = os.path.join(ROOTFS, "usr/share/themes/SamanOS/openbox-3")
os.makedirs(TD, exist_ok=True)
THEMERC = """! SamanOS -- flat dark modern theme for Saman OS 2.0
! (fresh design; the old handmade desktop's look is not reused)

border.width: 1
padding.width: 4
padding.height: 3
window.handle.width: 2
window.client.padding.width: 0
menu.overlap: 0
*.justify: left

window.active.title.bg: Flat Solid
window.active.title.bg.color: #1E293B
window.active.label.text.color: #F8FAFC
window.inactive.title.bg: Flat Solid
window.inactive.title.bg.color: #334155
window.inactive.label.text.color: #CBD5E1

window.active.handle.bg: Flat Solid
window.active.handle.bg.color: #1E293B
window.inactive.handle.bg: Flat Solid
window.inactive.handle.bg.color: #334155
window.active.grip.bg: Flat Solid
window.active.grip.bg.color: #1E293B
window.inactive.grip.bg: Flat Solid
window.inactive.grip.bg.color: #334155

window.active.border.color: #0F172A
window.inactive.border.color: #1E293B
window.active.client.color: #0F172A
window.inactive.client.color: #1E293B

window.active.button.close.bg: Flat Solid
window.active.button.close.bg.color: #1E293B
window.active.button.close.image.color: #F8FAFC
window.active.button.close.pressed.bg: Flat Solid
window.active.button.close.pressed.bg.color: #DC2626
window.active.button.max.bg: Flat Solid
window.active.button.max.bg.color: #1E293B
window.active.button.max.image.color: #F8FAFC
window.active.button.iconify.bg: Flat Solid
window.active.button.iconify.bg.color: #1E293B
window.active.button.iconify.image.color: #F8FAFC
window.inactive.button.close.bg: Flat Solid
window.inactive.button.close.bg.color: #334155
window.inactive.button.close.image.color: #94A3B8
window.inactive.button.max.bg: Flat Solid
window.inactive.button.max.bg.color: #334155
window.inactive.button.max.image.color: #94A3B8
window.inactive.button.iconify.bg: Flat Solid
window.inactive.button.iconify.bg.color: #334155
window.inactive.button.iconify.image.color: #94A3B8

menu.border.color: #0F172A
menu.border.width: 1
menu.title.bg: Flat Solid
menu.title.bg.color: #1E293B
menu.title.text.color: #F8FAFC
menu.items.bg: Flat Solid
menu.items.bg.color: #1E293B
menu.items.text.color: #F8FAFC
menu.items.disabled.text.color: #64748B
menu.items.active.bg: Flat Solid
menu.items.active.bg.color: #0369A1
menu.items.active.text.color: #FFFFFF
menu.separator.color: #475569
menu.separator.width: 1
"""
with open(os.path.join(TD, "themerc"), "w") as f:
    f.write(THEMERC)

def xbm(name, bitmap):
    # bitmap: 16 strings of 16 chars, '#' = set
    h = len(bitmap); w = len(bitmap[0])
    data = []
    for row in bitmap:
        for bx in range(0, w, 8):
            byte = 0
            for bit in range(8):
                if bx + bit < w and row[bx + bit] == "#":
                    byte |= 1 << bit
            data.append(byte)
    body = ", ".join("0x%02x" % b for b in data)
    with open(os.path.join(TD, name), "w") as f:
        f.write("#define %s_width %d\n#define %s_height %d\n" % (name[:-4], w, name[:-4], h))
        f.write("static unsigned char %s_bits[] = {\n  %s };\n" % (name[:-4], body))

# close: X, 2px thick
close = ["................"] * 16
def draw(bm, pts):
    bm = [list(r) for r in bm]
    for x, y in pts:
        bm[y][x] = "#"
    return ["".join(r) for r in bm]
pts = []
for i in range(3, 13):
    pts += [(i, i), (i + 1, i), (i, i + 1), (15 - i, i), (14 - i, i), (15 - i, i + 1)]
xbm("close.xbm", draw(close, pts))
# max: square outline
mx = ["................"] * 16
pts = [(x, 3) for x in range(3, 13)] + [(x, 12) for x in range(3, 13)] + \
      [(3, y) for y in range(3, 13)] + [(12, y) for y in range(3, 13)]
xbm("max.xbm", draw(mx, pts))
# iconify: bar at the bottom
ic = ["................"] * 16
pts = [(x, y) for x in range(3, 13) for y in (11, 12)]
xbm("iconify.xbm", draw(ic, pts))
print("theme written to", TD)
