#!/usr/bin/env python3
"""Location QR pieces for 181residents.com, one per standee spot.

Each location scans to its own tracked path, so the dashboard can say which
sign earns its place. Rendered into ../print/qr/ as PNG + PDF at 300 DPI,
4 x 5 inches: a small brand head, the location's name, the code on its own
card, and the address written out for anyone who would rather type.

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

# 4 x 5 inches at 300 DPI
W, H = 1200, 1500

LOCATIONS = [
    ("lobby",   "THE LOBBY",         "https://181residents.com/q/lobby/"),
    ("level7",  "LEVEL 7",           "https://181residents.com/q/level7/"),
    ("level39", "LEVEL 39 LANDING",  "https://181residents.com/q/level39/"),
    ("bar",     "LEVEL 39 BAR",      "https://181residents.com/q/bar/"),
]

for key, label, url in LOCATIONS:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    cx = W / 2
    tracked(d, cx, 90, "181 FREMONT", display_font(64), 16, INK)
    tracked(d, cx, 186, "THE RESIDENTS\u2019 CLUB", body_font(26, 500), 9, STONE)
    d.rectangle([cx - 46, 250, cx + 46, 254], fill=RED)
    centered(d, cx, 292, "Everything happening here,", display_font(56), INK)
    centered(d, cx, 362, "in one place.", display_font(56), INK)

    code = qr_image(url, 640)
    pad = 40
    w2 = code.width + pad * 2
    x0 = int(cx - w2 / 2); y0 = 480
    d.rounded_rectangle([x0, y0, x0 + w2, y0 + w2], radius=18, fill=PAPER2, outline=LINE, width=3)
    img.paste(code, (x0 + pad, y0 + pad))
    y = y0 + w2 + 54

    centered(d, cx, y, "Point your camera at the code, or visit", body_font(30, 500), INK)
    centered(d, cx, y + 52, "181residents.com", body_font(42, 600), INK)

    tracked(d, cx, H - 120, label, body_font(24, 600), 7, RED)
    centered(d, cx, H - 76, "Resident Experiences \u00b7 181 Fremont Residences", body_font(20), STONE)

    img.save(os.path.join(OUT, f"{key}-qr.png"))
    img.save(os.path.join(OUT, f"{key}-qr.pdf"), "PDF", resolution=300.0)
    print(f"{key}: {url} -> print/qr/{key}-qr.png + .pdf")
