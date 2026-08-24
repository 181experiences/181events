"""The event field contract, shared by the builders, the publish script, and the dev server.
The API and every data file speak these names: Status, Date, Title, ... One record per occurrence.
functions/_lib.js holds the same lists for the Cloudflare side; keep them in step."""
import html

FIELDS = ["Status", "Date", "Title", "Category", "Start", "End", "Start24", "Location",
          "Host", "RSVP", "Capacity", "Price", "Series", "Description", "Cutoff", "Marquee",
          "Counted", "Moved", "Image", "Slug"]

# SQL column per field in the D1 events table ("End" would collide with the SQL keyword).
COLS = {f: f.lower() for f in FIELDS}
COLS["End"] = "end_time"
FIELD_OF_COL = {v: k for k, v in COLS.items()}

RSVP_LABELS = {None: "None", "guest": "Guest count", "standard": "Seat", "paid": "Paid seat"}
RSVP_KEYS = {v: k for k, v in RSVP_LABELS.items()}
STATUSES = ["Draft", "Live", "Unpublished", "Archived"]

def plain(s):
    """HTML entities -> readable text for storage."""
    return html.unescape(s) if isinstance(s, str) else s

def markup(s):
    """Stored text -> safe HTML for the site (the page is UTF-8, so accents stay as they are)."""
    return html.escape(s, quote=False) if isinstance(s, str) else s

def to_record(e):
    """events_data event -> the stored field shape."""
    return {
        "Status": "Live", "Date": e["on"].isoformat(), "Title": plain(e["title"]),
        "Category": e["cat"], "Start": e["time"], "End": e["end"], "Start24": e["t24"],
        "Location": plain(e["loc"]), "Host": e["host"], "RSVP": RSVP_LABELS[e["rsvp"]],
        "Capacity": e["cap"], "Price": e["price"] or "", "Series": e["series"] or "",
        "Description": "\n\n".join(plain(p) for p in e["desc"]), "Cutoff": e["cutoff"] or "",
        "Marquee": bool(e["marquee"]), "Counted": bool(e["counted"]), "Moved": bool(e["moved"]),
        "Image": e["img"] or "", "Slug": e["slug"],
    }

def from_record(f, month_keys):
    """Stored field shape -> the event shape build_proto.py expects (id added by caller)."""
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
