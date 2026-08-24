#!/usr/bin/env python3
"""Local stand-in for Cloudflare Pages + Functions, so the admin can be developed and
demonstrated on this machine before the accounts exist.

Serves ../site as static files and answers the same /api routes the Functions do:
  GET  /api/status
  GET  /api/events, POST /api/events, PATCH /api/events/:id   (backed by dev_events.json)
  POST /api/publish                                            (rebuilds ../site from dev_events.json)
  GET  /api/analytics                                          (sample figures, clearly marked)

dev_events.json is seeded from site/events_seed.json on first run. Delete it to reseed.
Run: python source/dev_server.py  (port 8181)"""
import json, os, sys, subprocess, datetime, random
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "..", "site"))
STORE = os.path.join(HERE, "dev_events.json")
SEED = os.path.join(HERE, "..", "site", "events_seed.json")
PORT = int(os.environ.get("PORT", "8181"))

def seed():
    rows = json.load(open(SEED, encoding="utf-8"))
    for i, r in enumerate(rows, 1):
        r["id"] = f"dev{i:03d}"
    return rows

def load():
    if not os.path.exists(STORE):
        save(seed())
    return json.load(open(STORE, encoding="utf-8"))

def save(events):
    json.dump(events, open(STORE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

def rebuild():
    events = load()
    live = [dict(e, _id=e["id"]) for e in events]
    json.dump(live, open(os.path.join(HERE, "events_live.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")], check=True)

def sample_analytics(days):
    """Shaped like the real endpoint, flagged as sample. Deterministic so the demo is stable."""
    rnd = random.Random(181)
    today = datetime.date.today()
    by_day = []
    for i in range(days):
        d = today - datetime.timedelta(days=days - 1 - i)
        base = 9 if d.weekday() in (1, 3) else 5          # Tuesdays and Thursdays are busier
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

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            super().log_message(fmt, *args)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("content-length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/api/status":
            return self._json({"db": True, "publish": True, "email": False, "analytics": False, "mode": "local"})
        if p.path == "/api/events":
            return self._json({"events": load()})
        if p.path == "/api/analytics":
            days = 30
            for kv in p.query.split("&"):
                if kv.startswith("days="): days = max(1, min(90, int(kv[5:] or 30)))
            return self._json(sample_analytics(days))
        if p.path.startswith("/api/"):
            return self._json({"error": "not found"}, 404)
        return super().do_GET()

    def end_headers(self):
        self.send_header("cache-control", "no-store")
        super().end_headers()

    def do_POST(self):
        p = urlparse(self.path)
        if p.path == "/api/events":
            events = load(); body = self._body()
            body["id"] = f"dev{len(events) + 1:03d}"
            events.append(body); save(events)
            return self._json(body, 201)
        if p.path == "/api/publish":
            try:
                rebuild()
                return self._json({"ok": True, "status": 200, "note": "Rebuilt locally. Reload the calendar."})
            except subprocess.CalledProcessError as ex:
                return self._json({"ok": False, "error": str(ex)}, 500)
        return self._json({"error": "not found"}, 404)

    def do_PATCH(self):
        p = urlparse(self.path)
        if p.path.startswith("/api/events/"):
            rid = p.path.rsplit("/", 1)[1]; events = load(); body = self._body()
            for e in events:
                if e["id"] == rid:
                    e.update({k: v for k, v in body.items() if k != "id"}); save(events)
                    return self._json(e)
            return self._json({"error": "no such event"}, 404)
        return self._json({"error": "not found"}, 404)

if __name__ == "__main__":
    load()
    print(f"181residents dev server on http://localhost:{PORT}  (site: {SITE})")
    ThreadingHTTPServer(("", PORT), H).serve_forever()
