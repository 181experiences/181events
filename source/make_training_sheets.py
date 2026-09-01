#!/usr/bin/env python3
"""One-page training sheets for 181residents.com, in the site's own look.

Three pieces, written to ../print/training/, each 8.5 x 11 portrait at 300 DPI
as both PDF (for the printer) and PNG (for email and preview):

  desk-cheat-sheet         the front desk: sign-in (and staying signed in), the code
                           rescue, phoned-in RSVPs, and what the desk leaves alone
  leadership-cheat-sheet   Scott, Leigh Anne, Carley-Ann: events, series, waitlists,
                           notices, asset kits, the archive, the dashboard
  residents-welcome        one gracious page for residents, with a QR code on its
                           own tracked path (/q/welcome) like every other standee

Bold runs are marked **like this** in the copy below. Fonts and palette follow
make_qr_signs.py. Run: python source/make_training_sheets.py"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "print", "training"))
os.makedirs(OUT, exist_ok=True)

INK = "#16161a"; INK_BODY = "#3a3a43"; INK_SOFT = "#55555f"
PAPER = "#f7f4ef"; PAPER2 = "#fffdfa"; LINE = "#ddd6cb"
RED = "#c41f26"; STONE = "#7a7266"

def _find_hanken():
    """The brand font lives in the tidemere folder, somewhere above this repo;
    walk upward so reorganizing the folders never breaks the print scripts."""
    d = HERE
    for _ in range(10):
        p = os.path.join(d, "tidemere", "2_Marketing", "brand", "fonts", "HankenGrotesk-Variable.ttf")
        if os.path.exists(p):
            return p
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return "C:/Windows/Fonts/segoeui.ttf"   # last resort, so a render never dies

HANKEN = _find_hanken()
MARCELLUS = os.path.join(HERE, "marcellus.ttf")   # optional upgrade, auto-detected
GEORGIA = "C:/Windows/Fonts/georgia.ttf"

W, H = 2550, 3300          # 8.5 x 11 at 300 DPI
MARGIN = 130
GUTTER = 80
COL_W = (W - MARGIN * 2 - GUTTER) // 2

_fonts = {}
def display_font(size):
    key = ("d", size)
    if key not in _fonts:
        path = MARCELLUS if os.path.exists(MARCELLUS) else GEORGIA
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]

def body_font(size, weight=400):
    key = ("b", size, weight)
    if key not in _fonts:
        f = ImageFont.truetype(HANKEN, size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        _fonts[key] = f
    return _fonts[key]

def tracked(draw, center_x, y, text, font, tracking, fill):
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

# ---------------------------------------------------------------- rich wrapped text
def runs_of(text):
    """Split '**bold** and plain' into (fragment, bold) runs."""
    out, bold = [], False
    for piece in text.split("**"):
        if piece:
            out.append((piece, bold))
        bold = not bold
    return out

def atoms_of(text):
    """Space-separated atoms; an atom is a list of (segment, bold) glued together,
    so punctuation right after a bold run stays attached to it."""
    atoms, atom = [], None
    for frag, bold in runs_of(text):
        for i, part in enumerate(frag.split(" ")):
            if i > 0 and atom:
                atoms.append(atom); atom = None
            if part:
                if atom is None:
                    atom = []
                atom.append((part, bold))
    if atom:
        atoms.append(atom)
    return atoms

def wrap_rich(draw, text, size, max_w, weight=400, bold_weight=600):
    """Greedy word wrap; returns a list of lines, each a list of atoms."""
    reg, bld = body_font(size, weight), body_font(size, bold_weight)
    space = draw.textlength(" ", font=reg)
    def width(atom):
        return sum(draw.textlength(seg, font=bld if bold else reg) for seg, bold in atom)
    lines, line, x = [], [], 0
    for atom in atoms_of(text):
        w = width(atom)
        if line and x + space + w > max_w:
            lines.append(line); line, x = [], 0
        if line:
            x += space
        line.append(atom); x += w
    if line:
        lines.append(line)
    return lines

def draw_rich_line(draw, x, y, line, size, fill, weight=400, bold_weight=600, bold_fill=None):
    reg, bld = body_font(size, weight), body_font(size, bold_weight)
    space = draw.textlength(" ", font=reg)
    for atom in line:
        for seg, bold in atom:
            f = bld if bold else reg
            draw.text((x, y), seg, font=f, fill=(bold_fill or INK) if bold else fill)
            x += draw.textlength(seg, font=f)
        x += space

# ---------------------------------------------------------------- block flow
def flow(draw, blocks, x, y, col_w, body_size, leading, head_size):
    """Render a column of ('h'|'p'|'b'|'gap', ...) blocks; returns the final y."""
    indent = int(body_size * 1.15)
    for block in blocks:
        kind = block[0]
        if kind == "gap":
            y += block[1]
        elif kind == "h":
            y += 26
            draw.rectangle([x, y, x + 64, y + 6], fill=RED)
            y += 30
            draw.text((x, y), block[1], font=display_font(head_size), fill=INK)
            y += int(head_size * 1.42)
        elif kind == "p":
            for line in wrap_rich(draw, block[1], body_size, col_w):
                draw_rich_line(draw, x, y, line, body_size, INK_BODY)
                y += leading
            y += int(leading * 0.35)
        elif kind == "b":
            first = True
            for line in wrap_rich(draw, block[1], body_size, col_w - indent):
                if first:
                    draw.text((x, y - int(body_size * 0.08)), "·",
                              font=body_font(body_size, 700), fill=RED)
                draw_rich_line(draw, x + indent, y, line, body_size, INK_BODY)
                y += leading; first = False
            y += int(leading * 0.28)
    return y

def sheet(eyebrow, title, subtitle):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    cx = W / 2
    tracked(d, cx, 130, "181 FREMONT", display_font(84), 20, INK)
    tracked(d, cx, 254, eyebrow, body_font(34, 500), 12, STONE)
    d.rectangle([cx - 60, 342, cx + 60, 347], fill=RED)
    centered(d, cx, 392, title, display_font(92), INK)
    centered(d, cx, 526, subtitle, body_font(37, 500), INK_SOFT)
    return img, d

def footer(d, text):
    centered(d, W / 2, H - 108, text, body_font(32), STONE)

def save(img, stem):
    img.save(os.path.join(OUT, stem + ".png"))
    img.save(os.path.join(OUT, stem + ".pdf"), "PDF", resolution=300.0)
    print(stem + ":", os.path.join(OUT, stem + ".pdf"))

def dense_sheet(stem, eyebrow, title, subtitle, col1, col2, foot,
                body_size=35, leading=48, head_size=52, top=636, limit=3140):
    img, d = sheet(eyebrow, title, subtitle)
    y1 = flow(d, col1, MARGIN, top, COL_W, body_size, leading, head_size)
    y2 = flow(d, col2, MARGIN + COL_W + GUTTER, top, COL_W, body_size, leading, head_size)
    for name, y in (("left", y1), ("right", y2)):
        if y > limit:
            print(f"  OVERFLOW {stem} {name} column: ends at {y}, limit {limit}")
    footer(d, foot)
    save(img, stem)

# ================================================================ front desk
DESK_COL1 = [
    ("h", "1 · Signing in"),
    ("b", "Go to **181residents.com/admin**. The quiet **Staff** link at the foot of any page of the site lands in the same place."),
    ("b", "Enter **concierge@181sf.com** and ask for the emailed code. It arrives in the desk mailbox; type it in and you are through."),
    ("b", "The first code often comes back \u201calready been used.\u201d That is the mail scanner opening the link before you can, not a mistake of yours. **Request a new code**; the second one works."),
    ("b", "You land on the Dashboard. Your tabs: **Dashboard · Residents · Spaces · Messages**."),
    ("b", "**Stay signed in** on the desk computer; there is no need to sign out between shifts, and each fresh sign-in costs another emailed code."),
    ("h", "2 · The lost code, any hour"),
    ("b", "**Residents** tab. Find the person; the list is grouped by unit."),
    ("b", "**Rotate** issues a fresh code. The old one stops working everywhere, on every device, right away."),
    ("b", "Read the new code over the phone, or press **Email code**: a draft opens in Outlook with the code written out, ready to send."),
    ("b", "One code per person; couples each have their own. Never share a code between people."),
    ("h", "3 · Temporary stays"),
    ("b", "A renter or a visiting family member gets their own row: unit, name, email, and an **Access ends** date. The code simply stops working after it."),
    ("b", "**Ends** on any row sets or clears that date."),
    ("b", "Someone moved out? **Disable** keeps their history. Leave **Delete** alone; it is for typos."),
]

DESK_COL2 = [
    ("h", "4 · RSVPs by phone, or in passing"),
    ("b", "**Dashboard**, RSVPs section, **Add an RSVP for someone**."),
    ("b", "Pick the person, the event, the party size (1 to 6), names if offered, then **Save RSVP**."),
    ("b", "If they already had an RSVP for that event, saving updates theirs."),
    ("b", "If the event is full or others are waiting, the RSVP joins the waitlist, the same queue as the site. Say so kindly; nobody skips the line at the desk."),
    ("h", "5 · Changes and cancellations"),
    ("b", "Every RSVP row has **Edit** for the party size and **Cancel**."),
    ("b", "**Confirm seats** appears on a waitlist row once seats free up. Freed seats are never handed out on their own; pressing it gives them to that party."),
    ("b", "After any change, an email to the resident opens prefilled, ready to send from the desk mailbox. Read it, then send it."),
    ("b", "No email on file? The screen says so. A call, or a word in the lobby, closes the loop."),
    ("h", "6 · What the desk view leaves alone"),
    ("b", "Events, the calendar itself, publishing, and Assets belong to Resident Experiences. If a resident asks about event content, take a note or send them to Leo."),
    ("b", "Message text is private to Leo. You see who wrote and when, never the words."),
    ("b", "The grey bar at the top reports on itself and stays quiet when all is well. If something looks wrong: reload the page; still wrong, call Leo and read him what the bar says."),
]

# ================================================================ leadership
LEAD_COL1 = [
    ("h", "1 · Signing in"),
    ("b", "**181residents.com/admin**, your own email, then the emailed code. The first code may say \u201calready been used\u201d: the mail scanner opened it first. Request another; the second works."),
    ("b", "**Sign out**, top right, on any shared machine."),
    ("h", "2 · Events and the editor"),
    ("b", "**Events** tab: **+ New Event**, or **Edit** on a row. Filters: All · Live · Drafts · Unpublished · Archived."),
    ("b", "**Draft** is never published. **Live** is on the calendar. **Unpublished** is pulled with its RSVPs held, ready to go back up. **Archived** is over, kept for reporting."),
    ("b", "**Publish calendar** rebuilds the resident site from what is saved; a nightly rebuild at 3 AM keeps the dates current on its own."),
    ("h", "3 · Series"),
    ("b", "The Repeats picker writes one row per date, so a single week can be moved or skipped without touching the rest."),
    ("b", "In the editor, **Which date of this series** chooses the week, and the **apply to every upcoming date** box decides the reach. Untick it to change one date only."),
    ("b", "Move a date and its sign-ups follow; nothing is orphaned."),
    ("h", "4 · Capacity and the waitlist"),
    ("b", "Capacity left blank means no limit. A full event queues a waitlist, one queue shared with the site and the desk."),
    ("b", "Freed seats are never given out on their own. **Confirm seats**, on the Dashboard, hands them to the next waiting party, and a note to them opens ready to send."),
    ("b", "A confirmed party never loses seats by editing; a request to grow only goes through if it fits."),
]

LEAD_COL2 = [
    ("h", "5 · Telling residents"),
    ("b", "Change a Live event\u2019s date, time, or place while people are signed up, and one BCC email opens in Outlook to all of them, old and new spelled out. Read it, send it."),
    ("b", "**Cancel & notify guests**, in the editor, pulls the event, holds the RSVPs, and opens the cancellation draft."),
    ("b", "**Link** on any row copies that date\u2019s page address, made for emails and reminders."),
    ("b", "Calendar subscribers update on their own; anyone who used **Add to My Calendar** re-taps it after a change. The drafts say so."),
    ("h", "6 · Asset kits"),
    ("b", "One **master kit** per event or series, under **Assets**; every date inherits it. Per piece, the uploaded file is the final version and the **Canva link** is the living design."),
    ("b", "The editor shows each date\u2019s effective kit. **Override this date** gives one date its own file; **Back to series kit** hands it back."),
    ("b", "Every file is named from the stem, so it stays identifiable in Canva, on Nixplay, or at the print shop."),
    ("h", "7 · The Archive"),
    ("b", "Nothing is filed by hand: a passed or cancelled event drifts in on its own, kit and all, and the downloads and Canva links stay live as templates. Reach it from **Archive · N** atop Events or Assets; restore by setting the status back to **Live**."),
    ("h", "8 · Dashboard and reporting"),
    ("b", "7, 30, or 90 days; **Download CSV** opens in Excel. Every QR standee and the weekly email carry their own link, so each scan is attributable."),
    ("b", "RSVP rollups per event with per-unit detail; a unit appearing twice for one event is worth a glance."),
    ("b", "Counts stand beside their percentages; in a small building, read swings as noise until three months agree. Events hosted by others are listed, not counted."),
    ("h", "9 · Messages"),
    ("b", "The inbox shows who wrote, when, and whether it has been answered. The words themselves are for Leo; residents write to a person, not a department."),
]

# ================================================================ residents
RES_SECTIONS_L = [
    ("The site", "**181residents.com** holds the whole calendar: every gathering, dinner, and class, with the details written out. Nothing to install; it works on an iPad, a phone, or a computer."),
    ("Your resident code", "Sign in once with your personal code and this device stays signed in for a month. No code, or lost it? The front desk can hand you a fresh one, any hour of the day."),
    ("Saying yes", "Open an event and tap RSVP: just you, or your party, up to six. Add names if you like. If an event is full you may join the waitlist, and you will hear from us the moment seats open."),
]
RES_SECTIONS_R = [
    ("Changing your mind", "**My RSVPs** keeps everything saved to your name. Change the party or cancel any time; seats already confirmed stay yours."),
    ("Your own calendar", "**Add to My Calendar** puts any event in your calendar app; if a date or time changes, tap it once more and the entry rights itself. Better still, subscribe once at the foot of the calendar and every event keeps itself current."),
    ("A word to us", "The **Message** tile reaches Resident Experiences directly: an idea, a plan to host, a question, anything. You will hear back within one business day. For building maintenance, please see the front desk or Action Life."),
]

def qr_image(url, target_px):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=0, box_size=10)
    q.add_data(url)
    q.make(fit=True)
    box = max(1, target_px // q.modules_count)
    q.box_size = box
    return q.make_image(fill_color=INK, back_color=PAPER2).get_image().convert("RGB")

def qr_panel(img, draw, center_x, y, url, qr_px, pad):
    code = qr_image(url, qr_px)
    w = code.width + pad * 2
    x0 = int(center_x - w / 2)
    draw.rounded_rectangle([x0, y, x0 + w, y + w], radius=int(pad * 0.4),
                           fill=PAPER2, outline=LINE, width=4)
    img.paste(code, (x0 + pad, y + pad))
    return y + w

def resident_sheet():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    cx = W / 2
    tracked(d, cx, 170, "181 FREMONT", display_font(110), 26, INK)
    tracked(d, cx, 322, "THE RESIDENTS\u2019 CLUB", body_font(40, 500), 14, STONE)
    d.rectangle([cx - 70, 424, cx + 70, 430], fill=RED)
    centered(d, cx, 500, "Everything happening here,", display_font(120), INK)
    centered(d, cx, 650, "in one place.", display_font(120), INK)

    def col(sections, x, y):
        for head, text in sections:
            d.rectangle([x, y, x + 70, y + 6], fill=RED)
            y += 40
            d.text((x, y), head, font=display_font(66), fill=INK)
            y += 112
            for line in wrap_rich(d, text, 44, COL_W):
                draw_rich_line(d, x, y, line, 44, INK_BODY)
                y += 62
            y += 58
        return y

    top = 890
    y1 = col(RES_SECTIONS_L, MARGIN, top)
    y2 = col(RES_SECTIONS_R, MARGIN + COL_W + GUTTER, top)

    qr_top = max(y1, y2) + 50
    bottom = qr_panel(img, d, cx, qr_top, "https://181residents.com/q/welcome/", 440, 48)
    centered(d, cx, bottom + 50, "Point your camera at the code, or visit", body_font(42, 500), INK)
    centered(d, cx, bottom + 122, "181residents.com", body_font(58, 600), INK)
    if bottom + 200 > H - 130:
        print(f"  OVERFLOW residents-welcome: QR block ends at {bottom + 200}, footer at {H - 130}")
    centered(d, cx, H - 108, "181 Fremont Residences  ·  Resident Experiences  ·  The front desk can help, any hour",
             body_font(32), STONE)
    save(img, "residents-welcome")

# ================================================================ run
dense_sheet("desk-cheat-sheet",
            "FRONT DESK · RESIDENT EVENTS ADMIN",
            "Resident events, from the desk",
            "181residents.com/admin  ·  sign in as concierge@181sf.com  ·  keep beside the desk phone",
            DESK_COL1, DESK_COL2,
            "181 Fremont Residences  ·  Resident Experiences  ·  August 2026",
            body_size=42, leading=60, head_size=62, top=680)

dense_sheet("leadership-cheat-sheet",
            "LEADERSHIP · RESIDENT EVENTS ADMIN",
            "Running the calendar",
            "181residents.com/admin  ·  sign in with your own email  ·  the full guides live under Settings",
            LEAD_COL1, LEAD_COL2,
            "181 Fremont Residences  ·  Resident Experiences  ·  August 2026",
            body_size=33, leading=45, head_size=48)

resident_sheet()
