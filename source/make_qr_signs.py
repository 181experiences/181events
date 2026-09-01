#!/usr/bin/env python3
"""QR signage pointing residents at 181residents.com, in the site's own look.

Two pieces, written to ../print/:
  bar-sign.pdf / bar-sign.png   8.5 x 11 portrait at 300 DPI, for the Level 39 bar
  nixplay-qr.png                1080 x 1920 portrait, for the Nixplay frames

Each carries its own tracked address (/q/bar, /q/screens), so the dashboard can
tell a bar scan from a screen scan, same as every other standee.

Fonts: Hanken Grotesk comes from the Tidemere brand kit's variable TTF. The
display face falls back to Georgia (the site's own declared fallback) unless a
marcellus.ttf is dropped beside this script, in which case it is picked up
automatically. Run: python source/make_qr_signs.py"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "print"))
os.makedirs(OUT, exist_ok=True)

INK = "#16161a"; INK_BODY = "#3a3a43"; INK_SOFT = "#55555f"
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
MARCELLUS = os.path.join(HERE, "marcellus.ttf")   # optional upgrade, auto-detected
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

def tracked(draw, center_x, y, text, font, tracking, fill):
    """Uppercase letterspaced text, centered; tracking in px between characters."""
    widths = [draw.textlength(c, font=font) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = center_x - total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill)
        x += w + tracking
    return total

def centered(draw, center_x, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text((center_x - w / 2, y), text, font=font, fill=fill)
    return w

def qr_image(url, target_px):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=0, box_size=10)
    q.add_data(url)
    q.make(fit=True)
    modules = q.modules_count
    box = max(1, target_px // modules)
    q.box_size = box
    img = q.make_image(fill_color=INK, back_color=PAPER2).get_image().convert("RGB")
    return img

def qr_panel(img, draw, center_x, y, url, qr_px, pad):
    """White card with a hairline border; the quiet zone the code needs to scan."""
    code = qr_image(url, qr_px)
    w = code.width + pad * 2
    x0 = int(center_x - w / 2)
    draw.rounded_rectangle([x0, y, x0 + w, y + w], radius=int(pad * 0.4),
                           fill=PAPER2, outline=LINE, width=4)
    img.paste(code, (x0 + pad, y + pad))
    return y + w

# ---------------------------------------------------------------- bar sign, 8.5 x 11 at 300 DPI
W, H = 2550, 3300
img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)
cx = W / 2

tracked(d, cx, 300, "181 FREMONT", display_font(150), 34, INK)
tracked(d, cx, 500, "RESIDENT EVENTS", body_font(52, 500), 18, STONE)
d.rectangle([cx - 80, 660, cx + 80, 666], fill=RED)

centered(d, cx, 780, "Everything happening here,", display_font(160), INK)
centered(d, cx, 980, "in one place.", display_font(160), INK)

bottom = qr_panel(img, d, cx, 1260, "https://181residents.com/q/bar/", 1150, 90)

centered(d, cx, bottom + 80, "Point your camera at the code,", body_font(62, 500), INK)
centered(d, cx, bottom + 168, "or visit", body_font(52), INK_SOFT)
centered(d, cx, bottom + 250, "181residents.com", body_font(84, 600), INK)

centered(d, cx, bottom + 405, "See the calendar, RSVP to events, and message Resident Experiences.",
         body_font(44), INK_BODY)
centered(d, cx, bottom + 470, "Sign in once with your resident code, from the front desk.",
         body_font(44), INK_BODY)

centered(d, cx, H - 130, "181 Fremont Residences  Â·  Resident Experiences  Â·  Questions? Leo at Level 39",
         body_font(38), STONE)

img.save(os.path.join(OUT, "bar-sign.png"))
img.save(os.path.join(OUT, "bar-sign.pdf"), "PDF", resolution=300.0)
print("bar sign:", os.path.join(OUT, "bar-sign.pdf"))

# ---------------------------------------------------------------- nixplay still, 1080 x 1920
W, H = 1080, 1920
img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)
cx = W / 2

tracked(d, cx, 210, "181 FREMONT", display_font(76), 17, INK)
tracked(d, cx, 312, "RESIDENT EVENTS", body_font(28, 500), 10, STONE)
d.rectangle([cx - 40, 392, cx + 40, 396], fill=RED)

centered(d, cx, 460, "Everything happening here,", display_font(76), INK)
centered(d, cx, 558, "in one place.", display_font(76), INK)

bottom = qr_panel(img, d, cx, 720, "https://181residents.com/q/screens/", 640, 50)

centered(d, cx, bottom + 90, "Point your camera at the code", body_font(42, 500), INK)
centered(d, cx, bottom + 165, "181residents.com", body_font(54, 600), INK)

centered(d, cx, H - 130, "Resident Experiences  Â·  Level 39", body_font(28), STONE)

img.save(os.path.join(OUT, "nixplay-qr.png"))
print("nixplay still:", os.path.join(OUT, "nixplay-qr.png"))
