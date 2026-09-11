#!/usr/bin/env python3
"""Admin app icons: the bay mark on brand red.

The resident app and the admin app sit side by side on staff phones and
in browser tabs, and the same ink icon on both made them read as one.
This renders the admin's own set, identical mark, red ground, into
source/assets/ next to the resident originals. build_site.py copies
them to the site root and points the admin head and admin.webmanifest
at them.

Filenames deliberately avoid the /admin path prefix: the Access
application locks every path that starts with /admin (that is why the
manifest link carries use-credentials), and an icon fetched anonymously
must get the icon back, never a login page.

Run:  python source/make_admin_icons.py"""

import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets")

RED = "#c41f26"
MARK = "#fffdfa"

# Geometry from icon.svg / icon-maskable.svg, in the 100-unit viewBox:
# the bay mark is a stroked rectangle with one diagonal, stroke centred
# on the path. (box, stroke, diagonal, diagonal stroke)
STANDARD = ((33, 16, 67, 84), 4.5, (35.25, 18.25, 64.75, 81.75), 3.0)
MASKABLE = ((36.74, 23.48, 63.26, 76.52), 3.51, (38.49, 25.23, 61.51, 74.77), 2.34)

def render(size, geom, ss=4):
    (x1, y1, x2, y2), sw, (lx1, ly1, lx2, ly2), lw = geom
    s = size * ss / 100
    img = Image.new("RGB", (size * ss, size * ss), RED)
    d = ImageDraw.Draw(img)
    # Pillow draws a rectangle outline inward from its box, SVG strokes
    # centred on the path: push the box out by half the stroke.
    h = sw / 2
    d.rectangle([round((x1 - h) * s), round((y1 - h) * s),
                 round((x2 + h) * s), round((y2 + h) * s)],
                outline=MARK, width=round(sw * s))
    d.line([round(lx1 * s), round(ly1 * s), round(lx2 * s), round(ly2 * s)],
           fill=MARK, width=round(lw * s))
    return img.resize((size, size), Image.LANCZOS)

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="512" height="512">
  <rect width="100" height="100" fill="{red}"/>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{mark}" stroke-width="{sw}" stroke-linejoin="miter"/>
  <path d="M{lx1} {ly1} L{lx2} {ly2}" fill="none" stroke="{mark}" stroke-width="{lw}" stroke-linecap="butt"/>
</svg>'''

def write_svg(name, geom):
    (x1, y1, x2, y2), sw, (lx1, ly1, lx2, ly2), lw = geom
    body = SVG.format(red=RED, mark=MARK, x=x1, y=y1, w=round(x2 - x1, 2), h=round(y2 - y1, 2),
                      sw=sw, lx1=lx1, ly1=ly1, lx2=lx2, ly2=ly2, lw=lw)
    open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(body)
    print(f"assets/{name}")

PNGS = [
    ("icon-admin-512.png", 512, STANDARD),
    ("icon-admin-192.png", 192, STANDARD),
    ("apple-touch-icon-admin.png", 180, STANDARD),
    ("favicon-admin-32.png", 32, STANDARD),
    ("icon-admin-maskable-512.png", 512, MASKABLE),
]
for name, size, geom in PNGS:
    render(size, geom).save(os.path.join(OUT, name))
    print(f"assets/{name} ({size}x{size})")

write_svg("icon-admin.svg", STANDARD)
write_svg("icon-admin-maskable.svg", MASKABLE)
