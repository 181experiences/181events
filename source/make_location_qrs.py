#!/usr/bin/env python3
"""Location QR pieces for 181residents.com, sized for where each one lives.

The Nixplay frames sit on credenzas at walk-up distance, so the bar, lobby,
and Level 7 get 1080 x 1920 JPGs for the screens. The Level 39 landing
credenza and the elevator frames take 8.5 x 11 prints at 300 DPI (PDF + PNG).
Each location scans to its own tracked path, so the dashboard can say which
sign earns its place.

Fonts and palette follow make_qr_signs.py. Run: python source/make_location_qrs.py"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "print", "qr"))
os.makedirs(OUT, exist_ok=True)

INK = "#16161a"; INK_SOFT = "#55555f"
PAPER = "#f7f4ef"; PAPER2 = "#fffdfa"; LINE = "#ddd6cb"
RED = "#c41f26"; STONE = "#7a7266"

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
MARCELLUS = os.path.join(HERE, "marcellus.ttf")
GEORGIA = "C:/Windows/Fonts/georgia.ttf"

def display_font(size):
    path = MARCELLUS if os.path.exists(MARCELLUS) else GEORGIA
    return ImageFont.truetype(path, size)

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

HEADLINE = "Your club calendar"

def render(W, H, label, url, m):
    """One piece at any size; m scales every measure from the 1080-wide base."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    cx = W / 2
    y = int(120 * m)
    tracked(d, cx, y, "181 FREMONT", display_font(int(66 * m)), int(16 * m), INK)
    tracked(d, cx, y + int(100 * m), "THE RESIDENTS\u2019 CLUB", body_font(int(27 * m), 500), int(9 * m), STONE)
    d.rectangle([cx - int(46 * m), y + int(166 * m), cx + int(46 * m), y + int(170 * m)], fill=RED)
    centered(d, cx, y + int(212 * m), HEADLINE, display_font(int(64 * m)), INK)

    code = qr_image(url, int(640 * m))
    pad = int(42 * m)
    w2 = code.width + pad * 2
    x0 = int(cx - w2 / 2); y0 = y + int(340 * m)
    d.rounded_rectangle([x0, y0, x0 + w2, y0 + w2], radius=int(18 * m), fill=PAPER2, outline=LINE, width=max(2, int(3 * m)))
    img.paste(code, (x0 + pad, y0 + pad))
    yy = y0 + w2 + int(60 * m)

    centered(d, cx, yy, "Point your camera at the code, or visit", body_font(int(32 * m), 500), INK)
    centered(d, cx, yy + int(54 * m), "181residents.com", body_font(int(44 * m), 600), INK)
    centered(d, cx, yy + int(126 * m), "Every gathering, dinner, and class, with RSVP built in.",
             body_font(int(26 * m), 400), INK_SOFT)

    tracked(d, cx, H - int(150 * m), label, body_font(int(25 * m), 600), int(7 * m), RED)
    centered(d, cx, H - int(100 * m), "Resident Experiences \u00b7 181 Fremont Residences", body_font(int(21 * m)), STONE)
    return img

# The screens: credenza distance, portrait frames.
NIXPLAY = [
    ("lobby",  "THE LOBBY",    "https://181residents.com/q/lobby/"),
    ("level7", "LEVEL 7",      "https://181residents.com/q/level7/"),
    ("bar",    "LEVEL 39 BAR", "https://181residents.com/q/bar/"),
]
for key, label, url in NIXPLAY:
    img = render(1080, 1920, label, url, 1.0)
    img.save(os.path.join(OUT, f"{key}-nixplay.jpg"), "JPEG", quality=92)
    print(f"{key}: {url} -> print/qr/{key}-nixplay.jpg (1080x1920)")

# The prints: letter portrait at 300 DPI.
PRINTS = [
    ("level39",  "LEVEL 39 LANDING", "https://181residents.com/q/level39/"),
    ("elevator", "THE ELEVATOR",     "https://181residents.com/q/elevator/"),
]
for key, label, url in PRINTS:
    img = render(2550, 3300, label, url, 2550 / 1080 * 0.82)
    img.save(os.path.join(OUT, f"{key}-print.png"))
    img.save(os.path.join(OUT, f"{key}-print.pdf"), "PDF", resolution=300.0)
    print(f"{key}: {url} -> print/qr/{key}-print.pdf (8.5x11 at 300 DPI)")
