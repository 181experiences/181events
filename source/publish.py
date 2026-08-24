#!/usr/bin/env python3
"""Build the site from the events database, falling back to events_data.py when the
database is not reachable. This is the Cloudflare Pages build command.

Reads the Live rows from D1 over the Cloudflare API. Environment variables, set in the
Pages project settings and never in a file here:
  CF_API_TOKEN     API token with D1 read (the same token the analytics use)
  CF_ACCOUNT_ID    the Cloudflare account id
  D1_DATABASE_ID   the D1 database id (uuid, shown on the database page)"""
import json, os, sys, subprocess, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fields import FIELD_OF_COL

token = os.environ.get("CF_API_TOKEN")
account = os.environ.get("CF_ACCOUNT_ID")
dbid = os.environ.get("D1_DATABASE_ID")
live = os.path.join(HERE, "events_live.json")

def build_from_code(reason):
    print(reason + " Building from events_data.py instead.")
    if os.path.exists(live):
        os.remove(live)
    sys.exit(subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")]).returncode)

if not (token and account and dbid):
    build_from_code("CF_API_TOKEN / CF_ACCOUNT_ID / D1_DATABASE_ID not set.")

url = f"https://api.cloudflare.com/client/v4/accounts/{account}/d1/database/{dbid}/query"
req = urllib.request.Request(url, method="POST",
    data=json.dumps({"sql": "SELECT * FROM events WHERE status='Live' ORDER BY date, start24"}).encode(),
    headers={"Authorization": f"Bearer {token}", "content-type": "application/json"})
try:
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    results = data["result"][0]["results"]
except Exception as ex:
    build_from_code(f"Could not read the events database ({ex}).")

rows = []
for r in results:
    f = {FIELD_OF_COL[k]: v for k, v in r.items() if k in FIELD_OF_COL}
    for k in ("Marquee", "Counted", "Moved"):
        f[k] = bool(f.get(k))
    f["_id"] = str(r.get("id"))
    if f.get("Date") and f.get("Title"):
        rows.append(f)

if not rows:
    build_from_code("The events database is empty (not seeded yet).")

json.dump(rows, open(live, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"{len(rows)} live events pulled from the database")
subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")], check=True)
print("Built. On Cloudflare this deploys automatically; locally, the site/ folder is current.")
