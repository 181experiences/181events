#!/usr/bin/env python3
"""Per-event RSVP QR tile for 181residents.com.

Renders a compact QR card that points at the standing short link
/e/{slug}, which redirects every scan to the next upcoming date of
that event (else the latest passed date, else home). Nothing but the
slug is baked into the code, so a tile composited onto a Nixplay
video or a flyer never goes stale as dates roll forward.

The tile is deliberately small and quiet: the video or flyer carries
the artwork and the date; this card carries only the code, a scan
line, and the typed-out short link as a fallback.

Fonts and palette follow make_location_qrs.py.

Run:  python source/make_event_qr.py sunday-brunch
      python source/make_event_qr.py sunday-brunch --caption "SCAN TO RSVP"
"""

import os
import re
import sys
import qrcode
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "print", "qr", "events"))

INK = "#16161a"
PAPER = "#f7f4ef"; PAPER2 = "#fffdfa"; LINE = "#ddd6cb"
RED = "#c41f26"

def _find_hanken():
    d = HERE
    for _ in range(10):
        p = os.path.join(d, "tidemere", "2_Marketing", "brand", "fonts", "HankenGrotesk-Variable.ttf")
        if os.path.exists(p):
            return p
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return "C:/Windows/Fonts/segoeui.ttf"

HANKEN = _find_hanken()

def body_font(size, weight=400):
    f = ImageFont.truetype(HANKEN, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f

def tracked(draw, cx, y, text, font, tracking, fill):
    widths = [draw.textlength(c, font=font) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill)
        x += w + tracking

def centered(draw, cx, y, text, font, fill):
    draw.text((cx - draw.textlength(text, font=font) / 2, y), text, font=font, fill=fill)

def qr_image(url, target_px):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=0, box_size=10)
    q.add_data(url)
    q.make(fit=True)
    q.box_size = max(1, target_px // q.modules_count)
    return q.make_image(fill_color=INK, back_color=PAPER2).get_image().convert("RGB")

def render_tile(slug, caption):
    url = f"https://181residents.com/e/{slug}"
    short = f"181residents.com/e/{slug}"

    code = qr_image(url, 560)
    pad = 52          # card padding around the code
    margin = 56       # paper margin around the card

    d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    cap_f = body_font(30, 600)
    url_f = body_font(27, 500)
    url_w = d0.textlength(short, font=url_f)

    card_w = max(code.width + pad * 2, int(url_w) + pad * 2)
    card_h = pad + code.height + 44 + 38 + 14 + 36 + pad
    W = card_w + margin * 2
    H = card_h + margin * 2

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    cx = W / 2
    x0, y0 = margin, margin
    d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=18,
                        fill=PAPER2, outline=LINE, width=3)
    img.paste(code, (int(cx - code.width / 2), y0 + pad))

    yy = y0 + pad + code.height + 44
    tracked(d, cx, yy, caption, cap_f, 7, RED)
    centered(d, cx, yy + 52, short, url_f, INK)
    return img, url

def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("Usage: python source/make_event_qr.py <event-slug> [--caption TEXT]")
        return 2
    slug = args[0].strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        print(f"That does not look like an event slug: {slug}")
        return 2
    caption = "SCAN TO RSVP"
    if "--caption" in argv:
        i = argv.index("--caption")
        if i + 1 < len(argv):
            caption = argv[i + 1]

    os.makedirs(OUT, exist_ok=True)
    img, url = render_tile(slug, caption.upper())
    jpg = os.path.join(OUT, f"{slug}-qr.jpg")
    png = os.path.join(OUT, f"{slug}-qr.png")
    img.save(jpg, "JPEG", quality=92)
    img.save(png)
    print(f"{slug}: {url}")
    print(f"  -> print/qr/events/{slug}-qr.jpg ({img.width}x{img.height})")
    print(f"  -> print/qr/events/{slug}-qr.png")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
