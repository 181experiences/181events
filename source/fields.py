"""The event field contract, shared by the builders, the publish script, and the dev server.
The API and every data file speak these names: Status, Date, Title, ... One record per occurrence.
functions/_lib.js holds the same lists for the Cloudflare side; keep them in step."""
import html

FIELDS = ["Status", "Date", "Title", "Category", "Start", "End", "Start24", "Location",
          "Host", "RSVP", "Capacity", "Price", "Series", "Description", "Cutoff", "Marquee",
          "Counted", "Moved", "Image", "Slug", "Teaser", "Closed", "Announce", "Party", "Partner", "Address", "Potluck"]

# SQL column per field in the D1 events table ("End" would collide with the SQL keyword).
COLS = {f: f.lower() for f in FIELDS}
COLS["End"] = "end_time"
FIELD_OF_COL = {v: k for k, v in COLS.items()}

RSVP_LABELS = {None: "None", "guest": "Guest count", "standard": "Seat", "paid": "Paid seat",
               "partner": "Partner email"}
RSVP_KEYS = {v: k for k, v in RSVP_LABELS.items()}
STATUSES = ["Draft", "Live", "Unpublished", "Archived"]

def plain(s):
    """HTML entities -> readable text for storage."""
    return html.unescape(s) if isinstance(s, str) else s

import re as _re

SITE_HOST = "181residents.com"

def safe_href(url):
    """A link address the page may carry: http(s), mailto, or a path on this site."""
    u = (url or "").strip()
    if _re.match(r"^(https?://|mailto:)[^\s<>\"']+$", u) or _re.match(r"^/[^\s<>\"']*$", u):
        return u
    return ""

def markup(s):
    """Stored text -> safe HTML for the site (the page is UTF-8, so accents stay as they are).
    Everything is escaped except <em>, <strong>, <u>, and <a href="..."> with a
    safe address, the tags the admin's formatting buttons produce. Links off
    the site open in a new tab."""
    if not isinstance(s, str):
        return s
    s = html.escape(s, quote=False)
    for t in ("em", "strong", "u"):
        s = s.replace(f"&lt;{t}&gt;", f"<{t}>").replace(f"&lt;/{t}&gt;", f"</{t}>")
    def _a(m):
        href = safe_href(html.unescape(m.group(1)))
        if not href:
            return m.group(2)
        ext = href.startswith("http") and SITE_HOST not in href.split("/")[2]
        extra = ' target="_blank" rel="noopener"' if ext else ""
        return '<a href="' + html.escape(href) + '"' + extra + '>' + m.group(2) + '</a>'
    s = _re.sub(r'&lt;a href="([^"]*)"&gt;(.*?)&lt;/a&gt;', _a, s, flags=_re.S)
    s = _re.sub(r"&lt;/?a(?: [^&]*)?&gt;", "", s)
    return s

def desc_blocks(raw):
    """Stored description -> a list of HTML blocks. A blank line starts a new
    paragraph; inside a paragraph a return is a line break; lines that begin
    "- " (or "* ") make a bulleted list and lines that begin "1. " a numbered
    one. The calendar file carries every block, paragraphs blank-line apart."""
    raw = (raw or "").replace("\r", "")
    out = []
    for para in raw.split("\n\n"):
        if not para.strip():
            continue
        lines, buf, kind = [l for l in para.split("\n")], [], None
        def flush():
            nonlocal buf, kind
            if not buf:
                return
            if kind == "p":
                out.append("<p>" + "<br>".join(markup(l) for l in buf) + "</p>")
            else:
                out.append(f"<{kind}>" + "".join(f"<li>{markup(l)}</li>" for l in buf) + f"</{kind}>")
            buf, kind = [], None
        for line in lines:
            m = _re.match(r"^\s*(?:[-*\u2022]\s+|(\d+)[.)]\s+)(.*)$", line)
            k = ("ol" if m.group(1) else "ul") if m else "p"
            text = m.group(2) if m else line.strip()
            if k != kind:
                flush(); kind = k
            buf.append(text if k != "p" else line.strip())
        flush()
    return out

def to_record(e):
    """events_data event -> the stored field shape."""
    return {
        "Status": "Live", "Date": e["on"].isoformat(), "Title": plain(e["title"]),
        "Category": e["cat"], "Start": e["time"], "End": e["end"], "Start24": e["t24"],
        "Location": plain(e["loc"]), "Host": e["host"], "RSVP": RSVP_LABELS[e["rsvp"]],
        "Capacity": e["cap"], "Price": e["price"] or "", "Series": e["series"] or "",
        "Description": "\n\n".join(plain(p) for p in e["desc"]), "Cutoff": e["cutoff"] or "",
        "Marquee": bool(e["marquee"]), "Counted": bool(e["counted"]), "Moved": bool(e["moved"]),
        "Image": e["img"] or "", "Slug": e["slug"], "Teaser": bool(e.get("teaser")),
        "Closed": bool(e.get("closed")), "Announce": bool(e.get("announce")),
        "Party": e.get("party") or "", "Partner": e.get("partner") or "", "Address": e.get("address") or "",
        "Potluck": bool(e.get("potluck")),
    }

def from_record(f, month_key):
    """Stored field shape -> the event shape build_proto.py expects (id added by caller)."""
    from datetime import date
    d = date.fromisoformat(f["Date"])
    # A blank line starts a new paragraph; a single return stays a line break,
    # so a menu typed one item per line reads one item per line.
    raw = (f.get("Description") or "").replace("\r", "")
    desc = desc_blocks(raw)
    return dict(
        on=d, m=month_key(d), d=d.day, slug=f["Slug"], title=markup(f["Title"]),
        cat=f["Category"], t24=f.get("Start24") or "0000", time=f.get("Start", ""), end=f.get("End", ""),
        loc=markup(f.get("Location") or "Level 39, Residents’ Club"),
        host=f.get("Host") or "Resident Experiences", rsvp=RSVP_KEYS.get(f.get("RSVP") or "None"),
        cap=int(f["Capacity"]) if f.get("Capacity") else None, price=f.get("Price") or None,
        series=f.get("Series") or None, desc=desc, cutoff=f.get("Cutoff") or None,
        marquee=bool(f.get("Marquee")), counted=bool(f.get("Counted", True)),
        moved=bool(f.get("Moved")), img=f.get("Image") or None, sub=None,
        status=f.get("Status") or "Draft", rec=f.get("_id"), teaser=bool(f.get("Teaser")),
        closed=bool(f.get("Closed")), announce=bool(f.get("Announce")),
        party=int(f["Party"]) if f.get("Party") else None,
        partner=f.get("Partner") or None, address=f.get("Address") or None,
        potluck=bool(f.get("Potluck")),
    )
