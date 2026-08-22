"""The contract between Airtable and the generator. One row per occurrence.
Column names are the Airtable field names; the order is the CSV order."""
import html

FIELDS = ["Status", "Date", "Title", "Category", "Start", "End", "Start24", "Location",
          "Host", "RSVP", "Capacity", "Price", "Series", "Description", "Cutoff", "Marquee",
          "Counted", "Moved", "Image", "Slug"]

RSVP_LABELS = {None: "None", "guest": "Guest count", "standard": "Seat", "paid": "Paid seat"}
RSVP_KEYS = {v: k for k, v in RSVP_LABELS.items()}

def plain(s):
    """HTML entities -> readable text for Airtable."""
    return html.unescape(s) if isinstance(s, str) else s

def markup(s):
    """Readable text -> safe HTML for the site (page is UTF-8, so accents are fine)."""
    return html.escape(s, quote=False) if isinstance(s, str) else s

def to_row(e):
    return {
        "Status": "Live", "Date": e["on"].isoformat(), "Title": plain(e["title"]),
        "Category": e["cat"], "Start": e["time"], "End": e["end"], "Start24": e["t24"],
        "Location": plain(e["loc"]), "Host": e["host"], "RSVP": RSVP_LABELS[e["rsvp"]],
        "Capacity": e["cap"] or "", "Price": e["price"] or "", "Series": e["series"] or "",
        "Description": "\n\n".join(plain(p) for p in e["desc"]), "Cutoff": e["cutoff"] or "",
        "Marquee": bool(e["marquee"]), "Counted": bool(e["counted"]), "Moved": bool(e["moved"]),
        "Image": e["img"] or "", "Slug": e["slug"],
    }

STATUSES = ["Draft", "Live", "Unpublished", "Archived"]

def from_record(f, month_keys):
    """Airtable field dict -> the event shape build_proto.py expects (id/m/d added by caller)."""
    from datetime import date
    d = date.fromisoformat(f["Date"])
    desc = [markup(p.strip()) for p in (f.get("Description") or "").split("\n\n") if p.strip()]
    return dict(
        on=d, m=month_keys[d.month], d=d.day, slug=f["Slug"], title=markup(f["Title"]),
        cat=f["Category"], t24=f.get("Start24") or "0000", time=f.get("Start", ""), end=f.get("End", ""),
        loc=markup(f.get("Location") or "Level 39, Residents’ Club"),
        host=f.get("Host") or "Resident Experiences", rsvp=RSVP_KEYS.get(f.get("RSVP") or "None"),
        cap=int(f["Capacity"]) if f.get("Capacity") else None, price=f.get("Price") or None,
        series=f.get("Series") or None, desc=desc, cutoff=f.get("Cutoff") or None,
        marquee=bool(f.get("Marquee")), counted=bool(f.get("Counted", True)),
        moved=bool(f.get("Moved")), img=f.get("Image") or None, sub=None,
        status=f.get("Status") or "Draft", rec=f.get("_id"),
    )
