#!/usr/bin/env python3
"""Local stand-in for Cloudflare Pages + Functions, so everything can be developed
and tested on this machine before it deploys.

Serves ../site as static files and answers the same routes the Functions do:
  admin api:  /api/status /api/whoami /api/events[...] /api/publish /api/analytics
              /api/residents[...] /api/messages[...] /api/rsvps /api/bookings[...]
  residents:  /signin /signout /my /rsvp/<key> /message /board /board/feed
              /board/ics/<key> /spaces

State lives in dev_*.json files beside this script; delete them to reset.
Roles: /dev/role/owner|staff|desk sets a cookie and reloads the admin as that tier.
Run: python source/dev_server.py  (port 8181, or PORT=...)"""
import json, os, re, sys, subprocess, datetime, random, hmac, hashlib, time, secrets
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote_plus

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "..", "site"))
SEED = os.path.join(SITE, "events_seed.json")
PORT = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else "8181"))
DEV_SECRET = b"local-dev-only-secret"
COOKIE = "r181s"
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

def store_path(name): return os.path.join(HERE, f"dev_{name}.json")

def load_store(name, default):
    p = store_path(name)
    if not os.path.exists(p):
        save_store(name, default)
    return json.load(open(p, encoding="utf-8"))

def save_store(name, data):
    json.dump(data, open(store_path(name), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

def seed_events():
    rows = json.load(open(SEED, encoding="utf-8"))
    for i, r in enumerate(rows, 1):
        r["id"] = f"dev{i:03d}"
    return rows

def load_events():
    events = load_store("events", None)
    if not events:
        events = seed_events()
        save_store("events", events)
    return events
def today(): return datetime.date.today().isoformat()
def now_iso(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def make_code(): return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
def normalize_code(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def pretty_code(c): return c[:4] + "-" + c[4:] if len(c) == 8 else c
def label_of(r): return f"{r['name']} · {r['unit']}" if r.get("unit") else r["name"]

MONTHS_S = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
DOW = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DOW_S = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
sys.path.insert(0, HERE)
from fields import RSVP_KEYS
TYPE_OF = {label: key for label, key in RSVP_KEYS.items() if key}
ASSET_KINDS = ["web-hero", "nixplay-still", "nixplay-video", "elevator-print", "level39-print", "email-header"]
ASSET_DIR = os.path.join(HERE, "dev_assets")

def esc(s):
    return str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# ---------------------------------------------------------------- templates
def template(name):
    return open(os.path.join(SITE, "_templates", name + ".html"), encoding="utf-8").read()

def fill(tpl, slots):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(slots.get(m.group(1), "")), tpl)

def inner(tpl, name):
    m = re.search(f"<!--{name}-->([\\s\\S]*?)<!--/{name}-->", tpl)
    return m.group(1) if m else ""

def cut(tpl, name, replacement):
    return re.sub(f"<!--{name}-->[\\s\\S]*?<!--/{name}-->",
                  lambda m: replacement if replacement is not None else "", tpl, count=1)

# ---------------------------------------------------------------- sessions
def sign(body):
    import base64
    sig = hmac.new(DEV_SECRET, body.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")

def issue_session(resident):
    exp = int(time.time()) + 30 * 24 * 3600
    body = f"{resident['id']}.{resident['epoch']}.{exp}"
    return f"{body}.{sign(body)}"

def session_cookie(value):
    age = 30 * 24 * 3600 if value else 0
    return f"{COOKIE}={value}; Max-Age={age}; Path=/; HttpOnly; SameSite=Lax"

def read_cookie(handler, name):
    raw = handler.headers.get("cookie") or ""
    for part in raw.split(";"):
        part = part.strip()
        if part.startswith(name + "="):
            return part[len(name) + 1:]
    return None

def current_resident(handler):
    token = read_cookie(handler, COOKIE)
    if not token: return None
    parts = token.split(".")
    if len(parts) != 4: return None
    rid, epoch, exp, sig = parts
    if not (rid.isdigit() and epoch.isdigit() and exp.isdigit()): return None
    if int(exp) < time.time(): return None
    if sign(f"{rid}.{epoch}.{exp}") != sig: return None
    for r in load_store("residents", []):
        if r["id"] == int(rid) and r["epoch"] == int(epoch) and r["status"] == "Active" \
           and (not r.get("ends") or r["ends"] >= today()):
            r = dict(r); r["label"] = label_of(r)
            return r
    return None

def find_by_code(typed):
    code = normalize_code(typed)
    if len(code) < 6: return None
    for r in load_store("residents", []):
        if r["code"] == code and r["status"] == "Active" and (not r.get("ends") or r["ends"] >= today()):
            r = dict(r); r["label"] = label_of(r)
            return r
    return None

def safe_return(to):
    if isinstance(to, str) and (to == "/my" or re.match(r"^/rsvp/[A-Za-z0-9._-]+$", to)):
        return to
    return "/my"

# ---------------------------------------------------------------- resident data
def ensure_front_desk():
    residents = load_store("residents", [])
    if not residents:
        residents = [dict(id=1, kind="role", unit=None, name="Front Desk",
                          email="concierge@181sf.com", code=make_code(), epoch=1,
                          status="Active", ends=None, created=now_iso())]
        save_store("residents", residents)
    return residents

def tenure_of(v):
    t = (v or "").strip().lower()
    return t if t in ("tenant", "owner") else ""

def shape_resident(r):
    return dict(id=r["id"], kind=r["kind"], unit=r.get("unit") or "", name=r["name"],
                email=r.get("email") or "", code=pretty_code(r["code"]), status=r["status"],
                ends=r.get("ends") or "", created=r["created"], label=label_of(r),
                tenure=r.get("tenure") or "",
                expired=bool(r.get("ends") and r["ends"] < today()))

def live_event(key):
    m = re.match(r"^(\d{4}-\d{2}-\d{2})_([a-z0-9-]+)$", key or "")
    if not m: return None
    for e in load_events():
        if e.get("Date") == m.group(1) and e.get("Slug") == m.group(2) and e.get("Status") == "Live":
            return e
    return None

def seats_taken(key, exclude_rid):
    return sum(r["count"] for r in load_store("rsvps", [])
               if r["event_key"] == key and r["status"] == "Confirmed" and r["resident_id"] != exclude_rid)

def my_rsvp(rid, key):
    for r in load_store("rsvps", []):
        if r["resident_id"] == rid and r["event_key"] == key:
            return r
    return None

def unit_mates(me, key):
    if not me.get("unit"): return []
    residents = {r["id"]: r for r in load_store("residents", [])}
    out = []
    for r in load_store("rsvps", []):
        res = residents.get(r["resident_id"])
        if res and res.get("unit") == me["unit"] and r["resident_id"] != me["id"] \
           and r["event_key"] == key and r["status"] != "Cancelled":
            out.append(dict(r, name=res["name"]))
    return out

# ---------------------------------------------------------------- page rendering
def shell_page(title, content, resident, status=200):
    html = fill(template("shell"), dict(TITLE=esc(title),
        WHO=esc(resident["label"]) if resident else "Residents&rsquo; Club", CONTENT=content))
    return status, html

def done_page(resident, head, sub, href, text, status=200):
    tpl = template("done")
    body = fill(cut(tpl, "LINK", inner(tpl, "LINK")),
                dict(HEAD=head, SUB=sub, LINKHREF=href, LINKTEXT=text))
    return shell_page(re.sub(r"&[a-z]+;", "'", head), body, resident, status)

def signin_page(to, error, status=200):
    tpl = template("signin")
    body = cut(tpl, "ERROR", fill(inner(tpl, "ERROR"), dict(ERROR=error)) if error else None)
    body = fill(body, dict(TO=safe_return(to)))
    return shell_page("Sign in", body, None, status)

def when_of(e):
    d = datetime.date.fromisoformat(e["Date"])
    day = f"{DOW[(d.weekday() + 1) % 7]}, {MONTHS_S[d.month - 1]} {d.day}"
    if e.get("Start"):
        day += f"<br>{esc(e['Start'])}" + (f" &ndash; {esc(e['End'])}" if e.get("End") else "")
    return day

def chips_html(section, rsvp_type, current):
    chip = inner(section, "CHIP")
    # Three self-serve; the template's contact chip is the doorway for more.
    out = ""
    for n in range(1, 4):
        label = str(n) if rsvp_type == "guest" else ("Just me" if n == 1 else f"+{n - 1}")
        out += fill(chip, dict(N=n, LABEL=label, CHECKED="checked" if n == current else ""))
    return out

def mate_line(m):
    if m["status"] == "Waitlist": return f"{esc(m['name'])} &middot; on the waitlist"
    if m["rsvp_type"] == "guest":
        return f"{esc(m['name'])} &middot; " + ("1 guest" if m["count"] == 1 else f"{m['count']} guests")
    return f"{esc(m['name'])} &middot; " + ("going" if m["count"] == 1 else f"party of {m['count']}")

def state_line(r):
    if r["status"] == "Waitlist": return "You&rsquo;re on the waitlist for this one."
    if r["rsvp_type"] == "guest":
        return "You have 1 outside guest registered." if r["count"] == 1 else f"You have {r['count']} outside guests registered."
    if r["rsvp_type"] == "paid":
        return "You have 1 seat held." if r["count"] == 1 else f"You have {r['count']} seats held."
    return "You&rsquo;re confirmed." if r["count"] == 1 else f"You&rsquo;re confirmed, party of {r['count']}."

# "RSVP closes" enforcement, mirroring functions/rsvp/[key].js exactly: a date
# (or legacy "Monday, Aug 31" text), closed from the morning after, after which
# fresh RSVPs become waitlist requests and held parties may shrink but not grow.
MON_NUM = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "june": 6,
           "jul": 7, "july": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
MON_PRETTY = [None, "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]

def cutoff_iso(e):
    c = (e.get("Cutoff") or "").strip()
    if not c: return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", c): return c
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?$", c)
    if not m: return None
    mon = MON_NUM.get(m.group(1).lower()[:4]) or MON_NUM.get(m.group(1).lower()[:3])
    if not mon: return None
    y = int(e["Date"][:4])
    iso = f"{y}-{mon:02d}-{int(m.group(2)):02d}"
    return f"{y - 1}-{mon:02d}-{int(m.group(2)):02d}" if iso > e["Date"] else iso

def rsvp_closed(e):
    if e.get("Closed"):   # the editor's switch: closed right now, by hand
        return True
    c = cutoff_iso(e)
    return bool(c and today() > c)

def closed_line(e, prefix):
    p = cutoff_pretty(e) if cutoff_iso(e) and not e.get("Closed") else ""
    return f"{prefix} closed {p}" if p else f"{prefix} are closed"

def cutoff_pretty(e):
    c = cutoff_iso(e)
    if not c: return e.get("Cutoff") or ""
    d = datetime.date.fromisoformat(c)
    return f"{DOW[(d.weekday() + 1) % 7]}, {MON_PRETTY[d.month]} {d.day}"

def rsvp_page(e, key, me):
    rsvp_type = TYPE_OF.get(e["RSVP"])   # None for drop-in events: facts, no forms
    tpl = template("rsvp")
    existing = my_rsvp(me["id"], key) if me else None
    active = existing if existing and existing["status"] != "Cancelled" else None
    cap = int(e["Capacity"]) if e.get("Capacity") else None
    taken = seats_taken(key, me["id"] if me else 0) if cap else 0
    full = bool(cap and taken >= cap)

    body = fill(tpl, dict(EYEBROW=esc(e.get("Category") or "On the calendar"),
        TITLE=esc(e["Title"]), WHEN=when_of(e),
        WHERE=esc(e.get("Location") or "Level 39, Residents’ Club")))
    seats_text = None
    if cap:
        seats_text = (f"{cap} at the table &middot; {esc(e['Price'])} per person" if e.get("Price")
                      else f"{cap} places")
    body = cut(body, "SEATS", fill(inner(tpl, "SEATS"), dict(SEATS=seats_text)) if seats_text else None)
    closed = rsvp_closed(e)
    body = cut(body, "CUTOFF", fill(inner(tpl, "CUTOFF"),
        dict(CUTOFF=esc(cutoff_pretty(e)) + (" &middot; now closed" if closed else ""))) if e.get("Cutoff") else None)
    if not rsvp_type:
        body = cut(cut(cut(cut(body, "ALSO", None), "SIGNIN", None), "EXISTING", None), "FORM", None)
        body = cut(body, "DROPIN", inner(tpl, "DROPIN"))
        return shell_page(e["Title"], body, me)
    body = cut(body, "DROPIN", None)

    mates = unit_mates(me, key) if me else []
    body = cut(body, "ALSO", fill(inner(tpl, "ALSO"), dict(MATES="<br>".join(mate_line(m) for m in mates))) if mates else None)

    if not me:
        body = cut(cut(body, "EXISTING", None), "FORM", None)
        body = cut(body, "SIGNIN", fill(inner(tpl, "SIGNIN"), dict(TO=f"/rsvp/{key}")))
        return shell_page(e["Title"], body, None)

    body = cut(body, "SIGNIN", None)
    if active:
        ex = inner(tpl, "EXISTING")
        section = cut(ex, "CHIP", chips_html(ex, rsvp_type, active["count"]))
        body = cut(body, "FORM", None)
        body = cut(body, "EXISTING", fill(section, dict(KEY=key, STATE=state_line(active),
            NAMES=esc(active.get("names") or ""),
            COUNTLABEL="Outside guests" if rsvp_type == "guest" else "Your party")))
        return shell_page(e["Title"], body, me)

    section = inner(tpl, "FORM")
    for name, keep in [("STANDARD", rsvp_type == "standard" and not closed),
                       ("GUEST", rsvp_type == "guest" and not closed),
                       ("PAID", rsvp_type == "paid" and not closed),
                       ("FULLNOTE", full and not closed and rsvp_type != "guest")]:
        section = cut(section, name, inner(section, name) if keep else None)
    section = cut(section, "CLOSEDNOTE",
                  fill(inner(section, "CLOSEDNOTE"), dict(CLOSEDLINE=esc(closed_line(e, "RSVPs for this one")))) if closed else None)
    section = cut(section, "CHIP", chips_html(section, rsvp_type, 1))
    if closed or (full and rsvp_type != "guest"): btn = "Join the Waitlist"
    elif rsvp_type == "guest": btn = "Register Guests"
    elif rsvp_type == "paid": btn = (f"{esc(e['Price'])} &middot; " if e.get("Price") else "") + "Request Seats"
    else: btn = "Confirm RSVP"
    body = cut(cut(body, "EXISTING", None), "FORM", fill(section, dict(KEY=key,
        COUNTLABEL="Outside guests" if rsvp_type == "guest" else "Your party", BTNTEXT=btn)))
    return shell_page(e["Title"], body, me)

def feed_token_of(me):
    if me.get("feed_token"):
        return me["feed_token"]
    token = "".join(secrets.choice(CODE_ALPHABET.lower()) for _ in range(20))
    residents = load_store("residents", [])
    for r in residents:
        if r["id"] == me["id"] and not r.get("feed_token"):
            r["feed_token"] = token
    save_store("residents", residents)
    me["feed_token"] = token
    return token

def my_page(me):
    rows = [r for r in load_store("rsvps", [])
            if r["resident_id"] == me["id"] and r["status"] != "Cancelled" and r["event_date"] >= today()]
    rows.sort(key=lambda r: r["event_date"])
    tpl = template("my")
    if rows:
        rendered = ""
        for r in rows:
            d = datetime.date.fromisoformat(r["event_date"])
            if r["status"] == "Waitlist": tag, tagc = "On the waitlist", ""
            elif r["rsvp_type"] == "guest":
                tag, tagc = ("1 guest registered" if r["count"] == 1 else f"{r['count']} guests registered"), "open"
            elif r["rsvp_type"] == "paid":
                tag, tagc = ("1 seat held" if r["count"] == 1 else f"{r['count']} seats held"), "open"
            else:
                tag, tagc = ("You&rsquo;re going" if r["count"] == 1 else f"You&rsquo;re going &middot; party of {r['count']}"), "open"
            meta = f"{MONTHS_S[d.month - 1]} {d.day}"
            if r.get("names"): meta += f" &middot; with {esc(r['names'])}"
            rendered += fill(inner(tpl, "ROW"), dict(KEY=r["event_key"], DAY=d.day,
                DOW=DOW_S[(d.weekday() + 1) % 7], TITLE=esc(r["event_title"]), META=meta,
                TAG=tag, TAGCLASS=tagc))
        body = cut(cut(tpl, "EMPTY", None), "ROWS", cut(inner(tpl, "ROWS"), "ROW", rendered))
    else:
        body = cut(cut(tpl, "ROWS", None), "EMPTY", inner(tpl, "EMPTY"))
    token = feed_token_of(me)
    return shell_page("My RSVPs", fill(body, dict(
        LABEL=esc(me["label"]),
        FEEDURL=f"http://localhost:{PORT}/calendar/my/{token}",
        FEEDWEBCAL=f"webcal://localhost:{PORT}/calendar/my/{token}")), me)

def board_rows():
    return sorted([e for e in load_events()
                   if e.get("Category") == "Board Meeting" and e.get("Status") == "Live" and e.get("Date", "") >= today()],
                  key=lambda e: (e["Date"], e.get("Start24") or ""))

def board_page(me):
    rows = board_rows()
    tpl = template("board")
    if rows:
        rendered = ""
        for e in rows:
            d = datetime.date.fromisoformat(e["Date"])
            meta = f"{DOW[(d.weekday() + 1) % 7]}, {MONTHS_S[d.month - 1]} {d.day}"
            if e.get("Start"):
                meta += f" &middot; {esc(e['Start'])}" + (f" &ndash; {esc(e['End'])}" if e.get("End") else "")
            meta += f" &middot; {esc(e.get('Location') or 'Level 39')}"
            rendered += fill(inner(tpl, "ROW"), dict(DAY=d.day, DOW=DOW_S[(d.weekday() + 1) % 7],
                TITLE=esc(e["Title"]), META=meta, ICS=f"/board/ics/{e['Date']}_{e.get('Slug') or 'board-meeting'}"))
        body = cut(cut(tpl, "EMPTY", None), "ROWS", cut(inner(tpl, "ROWS"), "ROW", rendered))
    else:
        body = cut(cut(tpl, "ROWS", None), "EMPTY", inner(tpl, "EMPTY"))
    return shell_page("Board Meetings", body, me)

# The private-event registration page, mirroring functions/register/[token].js.
def guest_heads(bid):
    rows = [g for g in load_store("guests", []) if g["booking_id"] == bid]
    return sum(2 if g.get("plus_one") else 1 for g in rows)

def reg_state(b):
    if not b.get("reg_open"):
        return ("Registration for this event is closed. If you are expected, the front desk will have you "
                "on the list; otherwise, kindly check with your host.")
    if b["date"] < today():
        return "This event has passed."
    if b.get("guest_cap") and guest_heads(b["id"]) >= int(b["guest_cap"]):
        return ("The guest list is full. If you were invited, kindly check with your host; there may be room "
                "for adjustments.")
    return None

def register_page(b):
    tpl = template("register")
    d = datetime.date.fromisoformat(b["date"])
    when = f"{DOW[(d.weekday() + 1) % 7]}, {MONTHS_S[d.month - 1]} {d.day}"
    if b.get("start"):
        when += f"<br>{esc(b['start'])}" + (f" &ndash; {esc(b['end_time'])}" if b.get("end_time") else "")
    body = fill(tpl, dict(EVENT=esc(b.get("event_name") or "A private event"), WHEN=when,
                          WHERE=esc(b.get("space") or "Level 39, Residents’ Club")))
    body = cut(body, "HOST", fill(inner(tpl, "HOST"), dict(HOST=esc(b["host"]))) if b.get("host") else None)
    state = reg_state(b)
    if state:
        body = cut(cut(body, "FORM", None), "CLOSED", fill(inner(tpl, "CLOSED"), dict(CLOSEDMSG=state)))
    else:
        body = cut(cut(body, "CLOSED", None), "FORM", fill(inner(tpl, "FORM"), dict(TOKEN=esc(b["reg_token"]))))
    return shell_page(b.get("event_name") or "Private event", body, None)

def spaces_page(me):
    rows = sorted([b for b in load_store("bookings", []) if b["date"] >= today()],
                  key=lambda b: (b["date"], b.get("start24") or ""))
    tpl = template("spaces")
    if rows:
        rendered = ""
        for b in rows:
            d = datetime.date.fromisoformat(b["date"])
            meta = f"{DOW[(d.weekday() + 1) % 7]}, {MONTHS_S[d.month - 1]} {d.day}"
            meta += (f" &middot; {esc(b['start'])}" + (f" &ndash; {esc(b['end_time'])}" if b.get("end_time") else "")) if b.get("start") else " &middot; all day"
            rendered += fill(inner(tpl, "ROW"), dict(DAY=d.day, DOW=DOW_S[(d.weekday() + 1) % 7],
                SPACE=esc(b["space"]), META=meta))
        body = cut(cut(tpl, "EMPTY", None), "ROWS", cut(inner(tpl, "ROWS"), "ROW", rendered))
    else:
        body = cut(cut(tpl, "ROWS", None), "EMPTY", inner(tpl, "EMPTY"))
    return shell_page("Level 39 Spaces", body, me)

def to24(t):
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", (t or "").strip(), re.I)
    if not m or not m.group(1): return "0000"
    h = int(m.group(1))
    if m.group(3):
        h = h % 12 + (12 if m.group(3).upper() == "PM" else 0)
    if h > 23: return "0000"
    return f"{h:02d}" + (m.group(2) or "00")

def board_ics(rows, name):
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//181 Fremont//Board Meetings//EN", f"X-WR-CALNAME:{name}"]
    for e in rows:
        d = e["Date"].replace("-", "")
        start = e.get("Start24") or to24(e.get("Start"))
        end = to24(e.get("End")) if e.get("End") else start
        out += ["BEGIN:VEVENT", f"UID:181fremont-board-{e['id']}@181residents.com",
                f"DTSTAMP:{d}T000000Z", f"DTSTART:{d}T{start}00", f"DTEND:{d}T{end}00",
                f"SUMMARY:{e['Title']}", f"LOCATION:181 Fremont - {e.get('Location') or 'Level 39'}",
                "END:VEVENT"]
    return "\r\n".join(out) + "\r\nEND:VCALENDAR\r\n"

# ---------------------------------------------------------------- misc
# The calendar window dials live in settings_live.json, the same file the real
# build reads, so the local rebuild honors them exactly as production does.
WINDOW_DEFAULTS = {"detail_weeks": 8, "horizon_months": 4}
def load_window():
    out = dict(WINDOW_DEFAULTS)
    try:
        raw = json.load(open(os.path.join(HERE, "settings_live.json"), encoding="utf-8"))
        out.update({k: int(raw[k]) for k in out if k in raw})
    except Exception:
        pass
    out["detail_weeks"] = min(12, max(1, out["detail_weeks"]))
    out["horizon_months"] = min(4, max(1, out["horizon_months"]))
    return out

def detail_end():
    win = load_window()
    return (datetime.date.today() + datetime.timedelta(days=win["detail_weeks"] * 7)).isoformat()

# Locations and hosts ride in the same settings file; the build ignores them,
# the admin's event editor offers them.
LIST_DEFAULTS = {
    "locations": ["Level 39, Residents’ Club", "Level 7 Terrace", "Lobby", "Fitness Center"],
    "hosts": ["Resident Experiences", "181 Fremont Residences Association", "The Board",
              "Leo Ramirez", "Leigh Anne", "Carley-Ann", "Scott"],
}

def clean_list(v, key):
    if not isinstance(v, list):
        return list(LIST_DEFAULTS[key])
    out = []
    for item in v:
        s = str(item or "").strip()[:80]
        if s and s not in out:
            out.append(s)
        if len(out) >= 60:
            break
    return out

def load_all_settings():
    out = dict(load_window(), **{k: list(v) for k, v in LIST_DEFAULTS.items()})
    try:
        raw = json.load(open(os.path.join(HERE, "settings_live.json"), encoding="utf-8"))
        for k in LIST_DEFAULTS:
            if isinstance(raw.get(k), list) and raw[k]:
                out[k] = clean_list(raw[k], k)
    except Exception:
        pass
    return out

def log_history(role, event_id, action, changes=None, snapshot=None):
    rows = load_store("history", [])
    rows.append(dict(id=max([h["id"] for h in rows] or [0]) + 1, event_id=event_id,
                     at=now_iso(), who=f"{role}@local.dev", action=action,
                     changes=changes, snapshot=snapshot))
    save_store("history", rows)

def field_changes(before, after):
    from fields import FIELDS
    out = {}
    for f in FIELDS:
        o, n = (before or {}).get(f), after.get(f)
        if o != n:
            out[f] = [o, n]
    return out

def rebuild():
    events = load_events()
    live = [dict(e, _id=e["id"]) for e in events]
    json.dump(live, open(os.path.join(HERE, "events_live.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")], check=True)

def sample_analytics(days):
    rnd = random.Random(181)
    t = datetime.date.today()
    by_day = []
    for i in range(days):
        d = t - datetime.timedelta(days=days - 1 - i)
        base = 9 if d.weekday() in (1, 3) else 5
        views = base + rnd.randint(0, 7)
        by_day.append({"date": d.isoformat(), "views": views, "visits": max(1, views - rnd.randint(1, 3))})
    visits = sum(d["visits"] for d in by_day)
    src = [("Weekly email", "/q/email/", .44), ("QR, Lobby", "/q/lobby/", .16), ("QR, Coffee Bar", "/q/coffee/", .11),
           ("QR, Fitness Center", "/q/fitness/", .08), ("QR, Leo's Office", "/q/office/", .05),
           ("Direct or saved to home screen", "/", .16)]
    return {"configured": False, "sample": True, "days": days, "since": by_day[0]["date"], "until": by_day[-1]["date"],
            "pageviews": sum(d["views"] for d in by_day), "visits": visits, "byDay": by_day,
            "bySource": [{"label": l, "path": p, "visits": round(visits * f)} for l, p, f in src],
            "byDevice": [{"device": "mobile", "views": 61}, {"device": "tablet", "views": 24}, {"device": "desktop", "views": 15}],
            "byPath": [], "byReferer": []}

ATTEMPTS = []  # (ip, ts) in memory; the real thing keeps these in D1

def too_many_attempts(ip):
    cutoff = time.time() - 600
    ATTEMPTS[:] = [(i, ts) for i, ts in ATTEMPTS if ts >= cutoff]
    return sum(1 for i, _ in ATTEMPTS if i == ip) >= 15

# ---------------------------------------------------------------- handler
class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

    def log_message(self, fmt, *args):
        if args and ("/api/" in str(args[0]) or any(p in str(args[0]) for p in ("/signin", "/my", "/rsvp", "/message", "/board", "/spaces"))):
            super().log_message(fmt, *args)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _html(self, pair, cookie=None):
        status, html = pair
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("cache-control", "no-store")
        if cookie: self.send_header("set-cookie", cookie)
        self.send_header("content-length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _redirect(self, url, cookie=None, status=303):
        self.send_response(status)
        self.send_header("location", url)
        if cookie: self.send_header("set-cookie", cookie)
        self.send_header("content-length", "0")
        self.end_headers()

    def _text(self, body, ctype, status=200, extra=None):
        b = body.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", ctype)
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.send_header("content-length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def _body_json(self):
        n = int(self.headers.get("content-length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _body_form(self):
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n).decode("utf-8")
        out = {}
        for pair in raw.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                out[unquote_plus(k)] = unquote_plus(v)
        return out

    def _role(self):
        return read_cookie(self, "dev_role") or os.environ.get("DEV_ROLE", "owner")

    def end_headers(self):
        self.send_header("cache-control", "no-store")
        super().end_headers()

    # ------------------------------------------------------------ GET
    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        me = current_resident(self)

        if p.path.startswith("/dev/role/"):
            role = p.path.rsplit("/", 1)[1]
            return self._redirect("/admin.html", cookie=f"dev_role={role}; Path=/")
        if p.path == "/admin":   # Pages serves pretty URLs; this plain server does not
            return self._redirect("/admin.html", status=302)

        # ---- admin api
        if p.path == "/api/status":
            return self._json({"db": True, "publish": True, "email": False, "analytics": False,
                               "signin": True, "roles": True, "mode": "local"})
        if p.path == "/api/whoami":
            return self._json({"role": self._role(), "email": f"{self._role()}@local.dev"})
        if p.path == "/cdn-cgi/access/logout":   # Access sign-out is a live-site feature
            return self._redirect("/admin.html", status=302)
        if p.path == "/api/events":
            return self._json({"events": load_events()})   # reading is open to every tier
        if p.path == "/api/settings":
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            return self._json(load_all_settings())
        if p.path == "/api/history":
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            eid = (q.get("event") or [""])[0]
            rows = [h for h in load_store("history", []) if str(h["event_id"]) == str(eid)]
            rows.sort(key=lambda h: h["id"], reverse=True)
            return self._json({"history": rows[:100]})
        if p.path == "/api/analytics":
            days = max(1, min(90, int((q.get("days") or ["30"])[0])))
            return self._json(sample_analytics(days))
        if p.path == "/api/residents":
            return self._json({"residents": [shape_resident(r) for r in ensure_front_desk()]})
        if p.path == "/api/rsvps":
            residents = {r["id"]: r for r in load_store("residents", [])}
            rows = []
            for r in load_store("rsvps", []):
                if r["status"] == "Cancelled": continue
                res = residents.get(r["resident_id"], {})
                rows.append(dict(r, name=res.get("name", "?"), unit=res.get("unit") or "",
                                 email=res.get("email") or ""))
            rows.sort(key=lambda r: (r["event_date"], r["event_key"], r["created"]))
            return self._json({"rsvps": rows})
        if p.path == "/api/messages":
            full = self._role() == "owner"
            out = []
            for m in load_store("messages", []):
                out.append(dict(id=m["id"], unit=m.get("unit") or "", sender=m.get("sender") or "",
                                topic=m.get("topic") or "", state=m["state"], replied=m.get("replied") or "",
                                created=m["created"], name=m.get("name", "") if full else "",
                                email=m.get("email", "") if full else "",
                                body=m["body"] if full else None))
            # New first, then newest first: the same order the SQL gives production.
            out.sort(key=lambda m: m["created"], reverse=True)
            out.sort(key=lambda m: m["state"] != "New")
            return self._json({"role": self._role(), "messages": out})
        if p.path == "/api/bookings":
            guests = load_store("guests", [])
            out = []
            for b in load_store("bookings", []):
                mine = [g for g in guests if g["booking_id"] == b["id"]]
                out.append(dict(b, guest_parties=len(mine),
                                guest_heads=sum(2 if g.get("plus_one") else 1 for g in mine),
                                guest_arrived=sum(1 for g in mine if g.get("arrived"))))
            return self._json({"bookings": out})
        if p.path == "/api/guests":
            bid = int((q.get("booking") or ["0"])[0] or 0)
            return self._json({"guests": [g for g in load_store("guests", []) if g["booking_id"] == bid]})
        if p.path.startswith("/e/"):
            slug = p.path[len("/e/"):].lower()
            live = [e for e in load_events() if e.get("Status") == "Live" and e.get("Slug") == slug]
            ahead = sorted([e for e in live if e["Date"] >= today()], key=lambda e: e["Date"])
            pick = ahead[0] if ahead else (sorted(live, key=lambda e: e["Date"])[-1] if live else None)
            return self._redirect(f"/rsvp/{pick['Date']}_{pick['Slug']}" if pick else "/")
        if p.path.startswith("/register/"):
            token = p.path[len("/register/"):].lower()
            b = next((x for x in load_store("bookings", [])
                      if x.get("reg_token") == token or x.get("reg_slug") == token), None)
            if not b:
                tpl = template("done")
                body = fill(cut(cut(tpl, "LINK", inner(tpl, "LINK")), "ICON", None), dict(
                    HEAD="That page isn&rsquo;t here",
                    SUB="The address may have been mistyped, or the invitation withdrawn. Kindly check with whoever sent it.",
                    LINKHREF="/", LINKTEXT="181 Fremont"))
                return self._html(shell_page("Not found", body, None, 404))
            return self._html(register_page(b))
        if p.path == "/api/assets":
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            return self._json({"storage": True, "assets": load_store("assets", [])})
        if p.path.startswith("/api/assets/"):
            parts = p.path.split("/")
            if len(parts) == 5 and parts[4] in ASSET_KINDS:
                fp = os.path.join(ASSET_DIR, f"{parts[3]}__{parts[4]}")
                row = next((a for a in load_store("assets", [])
                            if a["stem"] == parts[3] and a["kind"] == parts[4] and a.get("uploaded")), None)
                if not row or not os.path.exists(fp):
                    return self._json({"error": "Nothing uploaded here yet."}, 404)
                data = open(fp, "rb").read()
                self.send_response(200)
                self.send_header("content-type", row.get("type") or "application/octet-stream")
                self.send_header("content-disposition", f'attachment; filename="{row.get("filename") or "file"}"')
                self.send_header("content-length", str(len(data)))
                self.end_headers(); self.wfile.write(data)
                return
            return self._json({"error": "Bad asset address"}, 400)
        if p.path.startswith("/api/"):
            return self._json({"error": "not found"}, 404)

        # ---- resident pages
        if p.path == "/signin":
            if me: return self._redirect(safe_return((q.get("to") or [None])[0]))
            return self._html(signin_page((q.get("to") or [None])[0], None))
        if p.path == "/signout":
            return self._redirect("/")
        if p.path == "/my":
            if not me: return self._redirect("/signin?to=/my")
            return self._html(my_page(me), cookie=session_cookie(issue_session(me)))
        if p.path == "/message":
            return self._redirect("/")
        if p.path == "/board":
            return self._html(board_page(me))
        if p.path.startswith("/calendar/my/"):
            token = p.path.rsplit("/", 1)[1]
            me2 = next((r for r in load_store("residents", [])
                        if r.get("feed_token") == token and r["status"] == "Active"
                        and (not r.get("ends") or r["ends"] >= today())), None)
            out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//181 Fremont//My RSVPs//EN",
                   "X-WR-CALNAME:My 181 Fremont RSVPs"]
            if me2:
                by_key = {f"{e['Date']}_{e.get('Slug')}": e for e in load_events() if e.get("Status") == "Live"}
                for r in sorted(load_store("rsvps", []), key=lambda r: r["event_date"]):
                    e = by_key.get(r["event_key"])
                    if not e or r["resident_id"] != me2["id"] or r["status"] != "Confirmed" or r["event_date"] < today():
                        continue
                    d = e["Date"].replace("-", "")
                    start = e.get("Start24") or to24(e.get("Start"))
                    end = to24(e.get("End")) if e.get("End") else start
                    party = f" (party of {r['count']})" if r["count"] > 1 else ""
                    out += ["BEGIN:VEVENT", f"UID:181fremont-{e.get('Slug') or 'event'}-{d}@181residents.com",
                            f"DTSTAMP:{d}T000000Z", f"DTSTART:{d}T{start}00", f"DTEND:{d}T{end}00",
                            f"SUMMARY:{e['Title']}{party}", f"LOCATION:181 Fremont - {e.get('Location') or 'Level 39'}",
                            "END:VEVENT"]
            return self._text("\r\n".join(out) + "\r\n" + "END:VCALENDAR", "text/calendar; charset=utf-8")
        if p.path == "/calendar/feed":
            rows = sorted([e for e in load_events()
                           if e.get("Status") == "Live" and e.get("Category") != "Board Meeting"
                           and today() <= e.get("Date", "") <= detail_end() and not e.get("Teaser")],
                          key=lambda e: (e["Date"], e.get("Start24") or ""))
            out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//181 Fremont//Resident Events//EN",
                   "X-WR-CALNAME:181 Fremont Resident Events"]
            for e in rows:
                d = e["Date"].replace("-", "")
                start = e.get("Start24") or to24(e.get("Start"))
                end = to24(e.get("End")) if e.get("End") else start
                out += ["BEGIN:VEVENT", f"UID:181fremont-{e.get('Slug') or 'event'}-{d}@181residents.com",
                        f"DTSTAMP:{d}T000000Z", f"DTSTART:{d}T{start}00", f"DTEND:{d}T{end}00",
                        f"SUMMARY:{e['Title']}", f"LOCATION:181 Fremont - {e.get('Location') or 'Level 39'}",
                        f"URL:https://181residents.com/rsvp/{e['Date']}_{e.get('Slug') or ''}", "END:VEVENT"]
            return self._text("\r\n".join(out) + "\r\nEND:VCALENDAR\r\n", "text/calendar; charset=utf-8")
        if p.path == "/board/feed":
            return self._text(board_ics(board_rows(), "181 Fremont Board Meetings"),
                              "text/calendar; charset=utf-8")
        if p.path.startswith("/board/ics/"):
            key = p.path.rsplit("/", 1)[1]
            m = re.match(r"^(\d{4}-\d{2}-\d{2})_([a-z0-9-]+)$", key)
            row = None
            if m:
                for e in load_events():
                    if e.get("Category") == "Board Meeting" and e.get("Status") == "Live" \
                       and e["Date"] == m.group(1) and e.get("Slug") == m.group(2):
                        row = e; break
            if not row: return self._text("Not found", "text/plain", 404)
            return self._text(board_ics([row], "181 Fremont Board Meeting"),
                              "text/calendar; charset=utf-8",
                              extra={"content-disposition": f'attachment; filename="{key}.ics"'})
        if p.path == "/spaces":
            return self._html(spaces_page(me))
        if p.path.startswith("/rsvp/"):
            key = p.path[len("/rsvp/"):]
            e = live_event(key)
            if not e:
                return self._html(done_page(me, "That event isn&rsquo;t on the calendar",
                    "It may have moved, or the address was mistyped. The calendar has everything that is on.",
                    "/", "Back to the calendar", 404))
            if e["Date"] < today():
                return self._html(done_page(me, "That date has passed",
                    "This event has already happened. The calendar has what&rsquo;s coming next.",
                    "/", "Back to the calendar"))
            if e.get("Teaser") or e["Date"] > detail_end():
                return self._html(done_page(me, e["Title"],
                    "This one is still coming together. The full details arrive right here, and RSVP opens with them.",
                    "/", "Back to the calendar"))
            return self._html(rsvp_page(e, key, me), cookie=session_cookie(issue_session(me)) if me else None)
        return super().do_GET()

    # ------------------------------------------------------------ POST
    def do_POST(self):
        p = urlparse(self.path)
        me = current_resident(self)
        ip = self.client_address[0]

        # ---- admin api
        if p.path == "/api/events":
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            events = load_events(); body = self._body_json()
            body["id"] = f"dev{len(events) + 1:03d}"
            events.append(body); save_store("events", events)
            log_history(self._role(), body["id"], "Created", field_changes(None, body), dict(body))
            return self._json(body, 201)
        if p.path == "/api/publish":
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            try:
                rebuild()
                return self._json({"ok": True, "status": 200, "note": "Rebuilt locally. Reload the calendar."})
            except subprocess.CalledProcessError as ex:
                return self._json({"ok": False, "error": str(ex)}, 500)
        if p.path == "/api/residents":
            residents = ensure_front_desk()
            body = self._body_json()
            made = []
            nid = max([r["id"] for r in residents] or [0])
            if isinstance(body.get("bulk"), str):
                for line in body["bulk"].splitlines():
                    parts = [s.strip() for s in line.split(",")]
                    if len(parts) >= 2 and parts[0] and parts[1]:
                        nid += 1
                        made.append(dict(id=nid, kind="resident", unit=parts[0].upper(), name=parts[1],
                                         email=parts[2] if len(parts) > 2 else "", code=make_code(),
                                         tenure=tenure_of(parts[3] if len(parts) > 3 else "") or None,
                                         epoch=1, status="Active", ends=None, created=now_iso()))
                if not made:
                    return self._json({"error": "No lines matched. Each line: unit, name, email, owner or tenant (the last two optional)."}, 400)
            else:
                kind = "role" if body.get("kind") == "role" else "resident"
                name = (body.get("name") or "").strip()
                unit = "" if kind == "role" else (body.get("unit") or "").strip().upper()
                if not name: return self._json({"error": "A name is needed."}, 400)
                if kind == "resident" and not unit: return self._json({"error": "A unit is needed for a resident."}, 400)
                nid += 1
                made.append(dict(id=nid, kind=kind, unit=unit or None, name=name,
                                 email=(body.get("email") or "").strip(), code=make_code(),
                                 tenure=tenure_of(body.get("tenure")) or None,
                                 epoch=1, status="Active", ends=(body.get("ends") or "").strip() or None,
                                 created=now_iso()))
            residents += made; save_store("residents", residents)
            return self._json({"residents": [shape_resident(r) for r in made]}, 201)
        if p.path == "/api/rsvps":
            body = self._body_json()
            residents = load_store("residents", [])
            resident = next((r for r in residents if r["id"] == int(body.get("resident_id") or 0)
                             and r["status"] == "Active"), None)
            if not resident: return self._json({"error": "No such active person."}, 400)
            key = str(body.get("event_key") or "")
            e = live_event(key)
            if not e: return self._json({"error": "That event is not on the live calendar."}, 400)
            if e.get("RSVP") not in TYPE_OF:
                return self._json({"error": f"{label_of(resident)} is always welcome: {e['Title']} is drop-in, no RSVP needed."}, 400)
            rsvp_type = TYPE_OF[e["RSVP"]]
            # Staff seat up to six, the fulfillment of the contact chip.
            try: count = max(1, min(6, int(body.get("count") or 1)))
            except ValueError: count = 1
            names = str(body.get("names") or "").strip()[:120]
            rsvps = load_store("rsvps", [])
            cap = int(e["Capacity"]) if e.get("Capacity") else None
            status = "Confirmed"
            if cap and rsvp_type != "guest":
                waiting = sum(1 for r in rsvps if r["event_key"] == key
                              and r["status"] == "Waitlist" and r["resident_id"] != resident["id"])
                if seats_taken(key, resident["id"]) + count > cap or waiting:
                    status = "Waitlist"
            mine = next((r for r in rsvps if r["resident_id"] == resident["id"] and r["event_key"] == key), None)
            if mine:
                if mine["status"] == "Cancelled": mine["created"] = now_iso()
                mine.update(rsvp_type=rsvp_type, count=count, names=names, status=status, updated=now_iso())
                row = mine
            else:
                row = dict(id=max([r["id"] for r in rsvps] or [0]) + 1, resident_id=resident["id"],
                           event_key=key, event_date=e["Date"], event_title=e["Title"],
                           rsvp_type=rsvp_type, count=count, names=names, status=status,
                           created=now_iso(), updated=now_iso())
                rsvps.append(row)
            save_store("rsvps", rsvps)
            return self._json({"rsvp": dict(row, name=resident["name"], unit=resident.get("unit") or "",
                                            email=resident.get("email") or "")}, 201)
        if p.path == "/api/bookings":
            b = self._body_json()
            space = (b.get("space") or "").strip(); date = (b.get("date") or "").strip()
            if not space or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                return self._json({"error": "A space and a date are needed."}, 400)
            bookings = load_store("bookings", [])
            cap = None
            if b.get("guest_cap"):
                try: cap = max(1, min(1000, int(b["guest_cap"])))
                except (TypeError, ValueError): cap = None
            slug = re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", (b.get("reg_slug") or "").lower().strip()))[:60]
            if slug:
                if len(slug) < 3: return self._json({"error": "A custom address needs at least three characters."}, 400)
                if any(x.get("reg_slug") == slug for x in bookings):
                    return self._json({"error": f"The address /register/{slug} is already taken by another reservation."}, 400)
            row = dict(id=max([x["id"] for x in bookings] or [0]) + 1, space=space, date=date,
                       start=(b.get("start") or "").strip(), end_time=(b.get("end") or "").strip(),
                       start24=to24(b.get("start")), note=(b.get("note") or "").strip(), created=now_iso(),
                       event_name=(b.get("event_name") or "").strip() or None,
                       host=(b.get("host") or "").strip() or None,
                       reg_token="".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(20)),
                       reg_open=0, guest_cap=cap, reg_slug=slug or None)
            bookings.append(row); save_store("bookings", bookings)
            return self._json({"booking": dict(row, guest_parties=0, guest_heads=0, guest_arrived=0)}, 201)
        if p.path == "/api/guests":
            b = self._body_json()
            name = (b.get("name") or "").strip()[:80]
            bid = int(b.get("booking_id") or 0)
            if not name or not bid: return self._json({"error": "A booking and a name are needed."}, 400)
            guests = load_store("guests", [])
            row = dict(id=max([g["id"] for g in guests] or [0]) + 1, booking_id=bid, name=name,
                       plus_one=(b.get("plus_one") or "").strip()[:80] or None,
                       created=now_iso(), arrived=None)
            guests.append(row); save_store("guests", guests)
            return self._json({"guest": row}, 201)
        if p.path.startswith("/api/"):
            return self._json({"error": "not found"}, 404)
        if p.path.startswith("/register/"):
            token = p.path[len("/register/"):].lower()
            b = next((x for x in load_store("bookings", [])
                      if x.get("reg_token") == token or x.get("reg_slug") == token), None)
            if not b: return self._redirect("/")
            form = self._body_form()
            name = (form.get("name") or "").strip()[:80]
            plus = (form.get("plus") or "").strip()[:80]
            if reg_state(b) or not name: return self._redirect(f"/register/{token}")
            if not (form.get("website") or "").strip():   # the honeypot stays empty for people
                guests = load_store("guests", [])
                guests.append(dict(id=max([g["id"] for g in guests] or [0]) + 1, booking_id=b["id"],
                                   name=name, plus_one=plus or None, created=now_iso(), arrived=None))
                save_store("guests", guests)
            tpl = template("done")
            body = fill(cut(tpl, "LINK", None), dict(
                HEAD="You&rsquo;re on the list",
                SUB=f"{esc(name)}{' and ' + esc(plus) if plus else ''}, registered for {esc(b.get('event_name') or 'the event')}. "
                    "On the day, come to the 181 Fremont lobby and give the event name; the front desk will be expecting you."))
            return self._html(shell_page("Registered", body, None))

        # ---- resident forms
        if p.path == "/signin":
            form = self._body_form()
            to = form.get("to")
            if too_many_attempts(ip):
                return self._html(signin_page(to, "Quite a few tries in a row. Please pause a few minutes, then try again.", 429))
            resident = find_by_code(form.get("code"))
            if not resident:
                ATTEMPTS.append((ip, time.time()))
                return self._html(signin_page(to, "That code didn&rsquo;t match. Check the card, or ask the front desk for a fresh one."))
            return self._redirect(safe_return(to), cookie=session_cookie(issue_session(resident)))
        if p.path == "/signout":
            return self._redirect("/", cookie=session_cookie(""))
        if p.path == "/message":
            form = self._body_form()
            topics = ["Share an idea", "Plan an event with us", "Something else"]
            fields = dict(topic=form.get("Topic") if form.get("Topic") in topics else topics[2],
                          body=(form.get("Message") or "").strip()[:4000],
                          name=(form.get("Name") or "").strip()[:80],
                          email=(form.get("Email") or "").strip()[:120])
            if not fields["body"]: return self._redirect("/")
            cookie = None
            if not me:
                typed = form.get("code")
                tpl = template("msgstep")
                def step(error):
                    b = cut(tpl, "ERROR", fill(inner(tpl, "ERROR"), dict(ERROR=error)) if error else None)
                    b = fill(b, dict(TOPIC=esc(fields["topic"]), BODY=esc(fields["body"]),
                                     NAME=esc(fields["name"]), EMAIL=esc(fields["email"])))
                    return shell_page("One more step", b, None)
                if not typed: return self._html(step(None))
                if too_many_attempts(ip):
                    return self._html(step("Quite a few tries in a row. Please pause a few minutes, then try again."))
                found = find_by_code(typed)
                if not found:
                    ATTEMPTS.append((ip, time.time()))
                    return self._html(step("That code didn&rsquo;t match. Check the card, or ask the front desk for a fresh one."))
                me = found; cookie = session_cookie(issue_session(found))
            msgs = load_store("messages", [])
            msgs.append(dict(id=max([m["id"] for m in msgs] or [0]) + 1, resident_id=me["id"],
                             unit=me.get("unit") or "", sender=label_of(me), topic=fields["topic"],
                             body=fields["body"], name=fields["name"], email=fields["email"],
                             state="New", replied=None, created=now_iso()))
            save_store("messages", msgs)
            return self._html(done_page(me, "Received",
                "Your note is with Resident Experiences, and we will get back to you within one business day.",
                "/", "Back to the calendar"), cookie=cookie)
        if p.path.startswith("/rsvp/"):
            key = p.path[len("/rsvp/"):]
            e = live_event(key)
            if not e or e["RSVP"] not in TYPE_OF: return self._redirect("/")
            if not me: return self._redirect(f"/rsvp/{key}")
            if e["Date"] < today(): return self._redirect(f"/rsvp/{key}")
            if e.get("Teaser") or e["Date"] > detail_end(): return self._redirect(f"/rsvp/{key}")
            rsvp_type = TYPE_OF[e["RSVP"]]
            form = self._body_form()
            rsvps = load_store("rsvps", [])
            mine = next((r for r in rsvps if r["resident_id"] == me["id"] and r["event_key"] == key), None)
            if form.get("action") == "cancel":
                if mine: mine["status"] = "Cancelled"; mine["updated"] = now_iso(); save_store("rsvps", rsvps)
                return self._html(done_page(me, "Cancelled",
                    "You&rsquo;re off the list for this one, and always welcome to change your mind while there&rsquo;s room.",
                    "/my", "My RSVPs"))
            if (form.get("count") or "") == "contact":
                return self._html(done_page(me, "Let&rsquo;s arrange it together",
                    "For a larger party, send us a note from the Message page, or a word at the front desk does it. Nothing is booked or changed yet.",
                    "/message", "Message Resident Experiences"))
            try: count = max(1, min(3, int(form.get("count"))))
            except (TypeError, ValueError):
                # No chip chosen keeps the party as it stands, so a staff-seated
                # party above three never quietly shrinks on an untouched save.
                count = mine["count"] if mine and mine["status"] != "Cancelled" else 1
            names = (form.get("names") or "").strip()[:120]
            cap = int(e["Capacity"]) if e.get("Capacity") else None
            # Mirrors the Cloudflare rules exactly: a confirmed party never
            # forfeits seats by editing, growing must fit or nothing changes,
            # the queue is honored while anyone waits, and after the close date
            # fresh RSVPs become waitlist requests for staff to answer.
            held = mine if mine and mine["status"] == "Confirmed" else None
            closed = rsvp_closed(e)
            if closed and held and count > held["count"]:
                n = held["count"]
                return self._html(done_page(me, "RSVPs have closed",
                    f"Your {'seat stands' if n == 1 else str(n) + ' seats stand'} exactly as they were. {closed_line(e, 'RSVPs')}, so a larger party takes a word to Resident Experiences: send us a Message or ask the front desk, and we&rsquo;ll try.",
                    "/my", "My RSVPs"))
            status = "Confirmed"
            if closed and not held:
                status = "Waitlist"
            if cap and rsvp_type != "guest":
                if held and count <= held["count"]:
                    status = "Confirmed"
                elif held:
                    if seats_taken(key, me["id"]) + count > cap:
                        seats = "your seat" if held["count"] == 1 else f"your {held['count']} seats"
                        return self._html(done_page(me, "Not enough room to grow",
                            f"There isn&rsquo;t space for the larger party at the moment, so nothing has changed: you still hold {seats}. "
                            "Ask Resident Experiences about the difference; sometimes room opens up.",
                            "/my", "My RSVPs"))
                else:
                    waiting = sum(1 for r in rsvps if r["event_key"] == key
                                  and r["status"] == "Waitlist" and r["resident_id"] != me["id"])
                    if seats_taken(key, me["id"]) + count > cap or waiting:
                        status = "Waitlist"
            if mine:
                if mine["status"] == "Cancelled":
                    mine["created"] = now_iso()   # a revived RSVP queues from now
                mine.update(rsvp_type=rsvp_type, count=count, names=names, status=status, updated=now_iso())
            else:
                rsvps.append(dict(id=max([r["id"] for r in rsvps] or [0]) + 1, resident_id=me["id"],
                                  event_key=key, event_date=e["Date"], event_title=e["Title"],
                                  rsvp_type=rsvp_type, count=count, names=names, status=status,
                                  created=now_iso(), updated=now_iso()))
            if status == "Confirmed" and cap and rsvp_type != "guest":
                total = sum(r["count"] for r in rsvps if r["event_key"] == key and r["status"] == "Confirmed")
                if total > cap:   # two racers can pass the check; step back onto the waitlist
                    row = mine or rsvps[-1]
                    row["status"] = status = "Waitlist"
            save_store("rsvps", rsvps)
            if status == "Waitlist":
                if closed:
                    return self._html(done_page(me, "Your request is in",
                        f"{closed_line(e, 'RSVPs')}, so this went to Resident Experiences as a request rather than a booking. We&rsquo;ll reach out with a yes or a no.",
                        "/my", "My RSVPs"))
                return self._html(done_page(me, "You&rsquo;re on the waitlist",
                    "Every seat is spoken for at the moment. You hold a place in the order requests arrived, and Resident Experiences will reach out if one opens.",
                    "/my", "My RSVPs"))
            if rsvp_type == "guest":
                sub = "Your guest is registered. We&rsquo;ll pour and plate for one more." if count == 1 \
                    else f"Your {count} guests are registered. We&rsquo;ll pour and plate for them."
            elif rsvp_type == "paid":
                sub = "Your seats are requested. Resident Experiences confirms them in the order requests arrive, and payment is arranged with your confirmation."
            else:
                sub = "You&rsquo;re on the list, and it now appears under My RSVPs, where you can change or cancel anytime."
            return self._html(done_page(me, "Request received" if rsvp_type == "paid" else "You&rsquo;re in",
                                        sub, "/my", "My RSVPs"))
        return self._json({"error": "not found"}, 404)

    # ------------------------------------------------------------ PUT
    def do_PUT(self):
        p = urlparse(self.path)
        parts = p.path.split("/")
        if p.path == "/api/settings":
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            body = self._body_json()
            # Only the keys sent are written, so saving one list never
            # disturbs the window dials, and the other way round.
            try:
                stored = json.load(open(os.path.join(HERE, "settings_live.json"), encoding="utf-8"))
            except Exception:
                stored = {}
            if "detail_weeks" in body:
                stored["detail_weeks"] = min(12, max(1, int(body.get("detail_weeks") or 8)))
            if "horizon_months" in body:
                stored["horizon_months"] = min(4, max(1, int(body.get("horizon_months") or 4)))
            for k in LIST_DEFAULTS:
                if k in body:
                    stored[k] = clean_list(body[k], k)
            json.dump(stored, open(os.path.join(HERE, "settings_live.json"), "w", encoding="utf-8"),
                      ensure_ascii=False)
            return self._json(load_all_settings())
        if p.path.startswith("/api/assets/") and len(parts) == 5 and parts[4] in ASSET_KINDS:
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            os.makedirs(ASSET_DIR, exist_ok=True)
            n = int(self.headers.get("content-length") or 0)
            data = self.rfile.read(n)
            open(os.path.join(ASSET_DIR, f"{parts[3]}__{parts[4]}"), "wb").write(data)
            from urllib.parse import unquote
            filename = unquote(self.headers.get("x-filename") or "file")[:160]
            rows = load_store("assets", [])
            row = next((a for a in rows if a["stem"] == parts[3] and a["kind"] == parts[4]), None)
            if not row:
                row = dict(id=max([a["id"] for a in rows] or [0]) + 1, stem=parts[3], kind=parts[4], canva=None)
                rows.append(row)
            row.update(filename=filename, size=n, type=self.headers.get("content-type") or "application/octet-stream",
                       uploaded=now_iso())
            save_store("assets", rows)
            return self._json({"asset": row}, 201)
        return self._json({"error": "not found"}, 404)

    # ------------------------------------------------------------ PATCH
    def do_PATCH(self):
        p = urlparse(self.path)
        if p.path.startswith("/api/events/"):
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            rid = p.path.rsplit("/", 1)[1]; events = load_events(); body = self._body_json()
            for e in events:
                if e["id"] == rid:
                    # {__draft: {...}} stores a working copy beside the row; the
                    # published fields and the resident site stay untouched.
                    if "__draft" in body:
                        e["Draft"] = body["__draft"] or None
                        save_store("events", events)
                        log_history(self._role(), rid, "Draft saved" if e["Draft"] else "Draft discarded")
                        return self._json(e)
                    before = dict(e)
                    old_key = f"{e.get('Date')}_{e.get('Slug')}"; old_title = e.get("Title")
                    e.update({k: v for k, v in body.items() if k != "id"})
                    e["Draft"] = None   # publishing or saving fields IS the apply
                    save_store("events", events)
                    new_key = f"{e.get('Date')}_{e.get('Slug')}"
                    if old_key != new_key or old_title != e.get("Title"):
                        rsvps = load_store("rsvps", [])
                        for r in rsvps:
                            if r["event_key"] == old_key:
                                r.update(event_key=new_key, event_date=e["Date"], event_title=e["Title"])
                        save_store("rsvps", rsvps)
                    ch = field_changes(before, e)
                    if ch:
                        action = (f"Status: {before.get('Status') or 'Draft'} → {e.get('Status')}"
                                  if "Status" in ch else "Edited")
                        log_history(self._role(), rid, action, ch, {k: v for k, v in e.items() if k != "Draft"})
                    return self._json(e)
            return self._json({"error": "no such event"}, 404)
        if p.path.startswith("/api/residents/"):
            rid = p.path.rsplit("/", 1)[1]; body = self._body_json()
            residents = load_store("residents", [])
            for r in residents:
                if str(r["id"]) == rid:
                    if body.get("rotate"): r["code"] = make_code(); r["epoch"] += 1
                    if body.get("status") in ("Active", "Disabled"): r["status"] = body["status"]; r["epoch"] += 1
                    for f in ("name", "unit", "email", "ends"):
                        if f in body:
                            v = (str(body[f] or "")).strip()
                            r[f] = (v.upper() or None) if f == "unit" else (v or None)
                    if "tenure" in body:
                        r["tenure"] = tenure_of(body["tenure"]) or None
                    save_store("residents", residents)
                    return self._json(shape_resident(r))
            return self._json({"error": "No such person"}, 404)
        parts = p.path.split("/")
        if p.path.startswith("/api/assets/") and len(parts) == 5 and parts[4] in ASSET_KINDS:
            body = self._body_json()
            url = str(body.get("canva") or "").strip()[:400]
            if url and not url.startswith("https://"):
                return self._json({"error": "A Canva link starts with https://"}, 400)
            rows = load_store("assets", [])
            row = next((a for a in rows if a["stem"] == parts[3] and a["kind"] == parts[4]), None)
            if not row:
                row = dict(id=max([a["id"] for a in rows] or [0]) + 1, stem=parts[3], kind=parts[4],
                           filename=None, size=None, type=None, uploaded=None)
                rows.append(row)
            row["canva"] = url or None
            save_store("assets", rows)
            return self._json({"asset": row})
        if p.path.startswith("/api/rsvps/"):
            rid = p.path.rsplit("/", 1)[1]; body = self._body_json()
            rsvps = load_store("rsvps", [])
            for r in rsvps:
                if str(r["id"]) == rid:
                    if "status" in body:
                        if body["status"] not in ("Confirmed", "Waitlist", "Cancelled"):
                            return self._json({"error": "Bad status"}, 400)
                        r["status"] = body["status"]
                    if "count" in body:
                        try: n = int(body["count"])
                        except (TypeError, ValueError): n = 0
                        if n < 1 or n > 6: return self._json({"error": "Party size runs 1 to 6."}, 400)
                        r["count"] = n
                    if "names" in body:
                        r["names"] = str(body["names"] or "").strip()[:120]
                    r["updated"] = now_iso()
                    save_store("rsvps", rsvps)
                    return self._json({"id": r["id"], "status": r["status"], "count": r["count"],
                                       "names": r.get("names") or ""})
            return self._json({"error": "No such RSVP"}, 404)
        if p.path.startswith("/api/bookings/"):
            bid = p.path.rsplit("/", 1)[1]; body = self._body_json()
            bookings = load_store("bookings", [])
            for b in bookings:
                if str(b["id"]) == bid:
                    if "space" in body:
                        v = (str(body["space"] or "")).strip()
                        if not v: return self._json({"error": "A space is needed."}, 400)
                        b["space"] = v
                    if "date" in body:
                        v = (str(body["date"] or "")).strip()
                        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                            return self._json({"error": "Dates read as YYYY-MM-DD."}, 400)
                        b["date"] = v
                    if "start" in body:
                        v = (str(body["start"] or "")).strip()
                        b["start"] = v; b["start24"] = to24(v)
                    if "end" in body: b["end_time"] = (str(body["end"] or "")).strip()
                    if "reg_open" in body: b["reg_open"] = 1 if body["reg_open"] else 0
                    for f in ("event_name", "host", "note"):
                        if f in body: b[f] = (str(body[f] or "")).strip() or None
                    if "guest_cap" in body:
                        try: b["guest_cap"] = max(1, min(1000, int(body["guest_cap"]))) if body["guest_cap"] else None
                        except (TypeError, ValueError): b["guest_cap"] = None
                    if "reg_slug" in body:
                        slug = re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", (str(body["reg_slug"] or "")).lower().strip()))[:60]
                        if slug:
                            if len(slug) < 3: return self._json({"error": "A custom address needs at least three characters."}, 400)
                            if any(x.get("reg_slug") == slug and x["id"] != b["id"] for x in bookings):
                                return self._json({"error": f"The address /register/{slug} is already taken by another reservation."}, 400)
                        b["reg_slug"] = slug or None
                    save_store("bookings", bookings)
                    return self._json({"booking": b})
            return self._json({"error": "No such reservation"}, 404)
        if p.path.startswith("/api/guests/"):
            gid = p.path.rsplit("/", 1)[1]; body = self._body_json()
            guests = load_store("guests", [])
            for g in guests:
                if str(g["id"]) == gid and "arrived" in body:
                    g["arrived"] = now_iso() if body["arrived"] else None
                    save_store("guests", guests)
                    return self._json({"guest": g})
            return self._json({"error": "No such registration"}, 404)
        if p.path.startswith("/api/messages/"):
            if self._role() != "owner": return self._json({"error": "forbidden"}, 403)
            mid = p.path.rsplit("/", 1)[1]; body = self._body_json()
            msgs = load_store("messages", [])
            for m in msgs:
                if str(m["id"]) == mid and body.get("state") in ("New", "Replied", "Archived"):
                    m["state"] = body["state"]
                    if body["state"] == "Replied": m["replied"] = now_iso()
                    save_store("messages", msgs)
                    return self._json({"id": m["id"], "state": m["state"], "replied": m.get("replied") or ""})
            return self._json({"error": "No such message"}, 404)
        return self._json({"error": "not found"}, 404)

    # ------------------------------------------------------------ DELETE
    def do_DELETE(self):
        p = urlparse(self.path)
        parts = p.path.split("/")
        if p.path.startswith("/api/assets/") and len(parts) == 5 and parts[4] in ASSET_KINDS:
            fp = os.path.join(ASSET_DIR, f"{parts[3]}__{parts[4]}")
            if os.path.exists(fp): os.remove(fp)
            rows = load_store("assets", [])
            row = next((a for a in rows if a["stem"] == parts[3] and a["kind"] == parts[4]), None)
            if row:
                if row.get("canva"):
                    row.update(filename=None, size=None, type=None, uploaded=None)
                else:
                    rows.remove(row); row = None
            save_store("assets", rows)
            return self._json({"asset": row})
        if p.path.startswith("/api/residents/"):
            rid = p.path.rsplit("/", 1)[1]
            residents = load_store("residents", [])
            kept = [r for r in residents if str(r["id"]) != rid]
            if len(kept) == len(residents): return self._json({"error": "No such person"}, 404)
            save_store("residents", kept)
            save_store("rsvps", [r for r in load_store("rsvps", []) if str(r["resident_id"]) != rid])
            return self._json({"ok": True})
        if p.path.startswith("/api/bookings/"):
            bid = p.path.rsplit("/", 1)[1]
            bookings = load_store("bookings", [])
            kept = [b for b in bookings if str(b["id"]) != bid]
            if len(kept) == len(bookings): return self._json({"error": "No such reservation"}, 404)
            save_store("bookings", kept)
            save_store("guests", [g for g in load_store("guests", []) if str(g["booking_id"]) != bid])
            return self._json({"ok": True})
        if p.path.startswith("/api/guests/"):
            gid = p.path.rsplit("/", 1)[1]
            guests = load_store("guests", [])
            kept = [g for g in guests if str(g["id"]) != gid]
            if len(kept) == len(guests): return self._json({"error": "No such registration"}, 404)
            save_store("guests", kept)
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)

if __name__ == "__main__":
    load_events(); ensure_front_desk()
    print(f"181residents dev server on http://localhost:{PORT}  (site: {SITE})")
    print("roles: /dev/role/owner  /dev/role/staff  /dev/role/desk")
    ThreadingHTTPServer(("", PORT), H).serve_forever()
