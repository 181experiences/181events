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

def shape_resident(r):
    return dict(id=r["id"], kind=r["kind"], unit=r.get("unit") or "", name=r["name"],
                email=r.get("email") or "", code=pretty_code(r["code"]), status=r["status"],
                ends=r.get("ends") or "", created=r["created"], label=label_of(r),
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
    mx = 6 if rsvp_type == "guest" else 4
    out = ""
    for n in range(1, mx + 1):
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

def rsvp_page(e, key, me):
    rsvp_type = TYPE_OF[e["RSVP"]]
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
    body = cut(body, "CUTOFF", fill(inner(tpl, "CUTOFF"), dict(CUTOFF=esc(e["Cutoff"]))) if e.get("Cutoff") else None)
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
    for name, keep in [("STANDARD", rsvp_type == "standard"), ("GUEST", rsvp_type == "guest"),
                       ("PAID", rsvp_type == "paid"), ("FULLNOTE", full and rsvp_type != "guest")]:
        section = cut(section, name, inner(section, name) if keep else None)
    section = cut(section, "CHIP", chips_html(section, rsvp_type, 1))
    if full and rsvp_type != "guest": btn = "Join the Waitlist"
    elif rsvp_type == "guest": btn = "Register Guests"
    elif rsvp_type == "paid": btn = (f"{esc(e['Price'])} &middot; " if e.get("Price") else "") + "Request Seats"
    else: btn = "Confirm RSVP"
    body = cut(cut(body, "EXISTING", None), "FORM", fill(section, dict(KEY=key,
        COUNTLABEL="Outside guests" if rsvp_type == "guest" else "Your party", BTNTEXT=btn)))
    return shell_page(e["Title"], body, me)

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
    return shell_page("My RSVPs", fill(body, dict(LABEL=esc(me["label"]))), me)

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
            return self._json({"bookings": load_store("bookings", [])})
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
            return self._html(my_page(me))
        if p.path == "/message":
            return self._redirect("/")
        if p.path == "/board":
            return self._html(board_page(me))
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
            if e["RSVP"] not in TYPE_OF:
                return self._html(done_page(me, "No RSVP needed",
                    "This one is drop-in. Just come along; we&rsquo;ll be glad to see you.",
                    "/", "Back to the calendar"))
            if e["Date"] < today():
                return self._html(done_page(me, "That date has passed",
                    "This event has already happened. The calendar has what&rsquo;s coming next.",
                    "/", "Back to the calendar"))
            return self._html(rsvp_page(e, key, me))
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
                                         epoch=1, status="Active", ends=None, created=now_iso()))
                if not made:
                    return self._json({"error": "No lines matched. Each line: unit, name, email (email optional)."}, 400)
            else:
                kind = "role" if body.get("kind") == "role" else "resident"
                name = (body.get("name") or "").strip()
                unit = "" if kind == "role" else (body.get("unit") or "").strip().upper()
                if not name: return self._json({"error": "A name is needed."}, 400)
                if kind == "resident" and not unit: return self._json({"error": "A unit is needed for a resident."}, 400)
                nid += 1
                made.append(dict(id=nid, kind=kind, unit=unit or None, name=name,
                                 email=(body.get("email") or "").strip(), code=make_code(),
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
            mx = 6 if rsvp_type == "guest" else 4
            try: count = max(1, min(mx, int(body.get("count") or 1)))
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
            row = dict(id=max([x["id"] for x in bookings] or [0]) + 1, space=space, date=date,
                       start=(b.get("start") or "").strip(), end_time=(b.get("end") or "").strip(),
                       start24=to24(b.get("start")), note=(b.get("note") or "").strip(), created=now_iso())
            bookings.append(row); save_store("bookings", bookings)
            return self._json({"booking": row}, 201)
        if p.path.startswith("/api/"):
            return self._json({"error": "not found"}, 404)

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
            rsvp_type = TYPE_OF[e["RSVP"]]
            form = self._body_form()
            rsvps = load_store("rsvps", [])
            mine = next((r for r in rsvps if r["resident_id"] == me["id"] and r["event_key"] == key), None)
            if form.get("action") == "cancel":
                if mine: mine["status"] = "Cancelled"; mine["updated"] = now_iso(); save_store("rsvps", rsvps)
                return self._html(done_page(me, "Cancelled",
                    "You&rsquo;re off the list for this one, and always welcome to change your mind while there&rsquo;s room.",
                    "/my", "My RSVPs"))
            mx = 6 if rsvp_type == "guest" else 4
            try: count = max(1, min(mx, int(form.get("count") or 1)))
            except ValueError: count = 1
            names = (form.get("names") or "").strip()[:120]
            cap = int(e["Capacity"]) if e.get("Capacity") else None
            # Mirrors the Cloudflare rules exactly: a confirmed party never
            # forfeits seats by editing, growing must fit or nothing changes,
            # and the queue is honored while anyone waits.
            held = mine if mine and mine["status"] == "Confirmed" else None
            status = "Confirmed"
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

    # ------------------------------------------------------------ PATCH
    def do_PATCH(self):
        p = urlparse(self.path)
        if p.path.startswith("/api/events/"):
            if self._role() == "desk": return self._json({"error": "forbidden"}, 403)
            rid = p.path.rsplit("/", 1)[1]; events = load_events(); body = self._body_json()
            for e in events:
                if e["id"] == rid:
                    e.update({k: v for k, v in body.items() if k != "id"}); save_store("events", events)
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
                    save_store("residents", residents)
                    return self._json(shape_resident(r))
            return self._json({"error": "No such person"}, 404)
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
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)

if __name__ == "__main__":
    load_events(); ensure_front_desk()
    print(f"181residents dev server on http://localhost:{PORT}  (site: {SITE})")
    print("roles: /dev/role/owner  /dev/role/staff  /dev/role/desk")
    ThreadingHTTPServer(("", PORT), H).serve_forever()
