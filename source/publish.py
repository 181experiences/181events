#!/usr/bin/env python3
"""Pull published events from Airtable, rebuild the site, report what changed.

Needs two environment variables (never put them in a file in this folder):
  AIRTABLE_TOKEN   a personal access token with data.records:read on the base
  AIRTABLE_BASE    the base id, starts with "app"
Optional: AIRTABLE_TABLE (default "Events").

Then upload the site/ folder in the Cloudflare dashboard, or let the
GitHub Action do it once that is set up."""
import json, os, sys, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
token, base = os.environ.get("AIRTABLE_TOKEN"), os.environ.get("AIRTABLE_BASE")
table = os.environ.get("AIRTABLE_TABLE", "Events")
if not (token and base):
    # First deploys happen before Airtable exists. Build from events_data.py so the site still ships.
    print("AIRTABLE_TOKEN / AIRTABLE_BASE not set. Building from events_data.py instead. See airtable/SETUP.md")
    import subprocess
    live = os.path.join(HERE, "events_live.json")
    if os.path.exists(live): os.remove(live)
    sys.exit(subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")]).returncode)

records, offset = [], None
while True:
    q = {"pageSize": 100, "filterByFormula": "{Status}='Live'"}
    if offset: q["offset"] = offset
    url = f"https://api.airtable.com/v0/{base}/{urllib.parse.quote(table)}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r: page = json.load(r)
    records += page["records"]; offset = page.get("offset")
    if not offset: break

rows = [dict(r["fields"], _id=r["id"]) for r in records if r["fields"].get("Date") and r["fields"].get("Title")]
live = os.path.join(HERE, "events_live.json")
old = json.load(open(live, encoding="utf-8")) if os.path.exists(live) else None
json.dump(rows, open(live, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"{len(rows)} published events pulled from Airtable" + (f" (was {len(old)})" if old else ""))
import subprocess; subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")], check=True)
print("Built. On Cloudflare this deploys automatically; locally, the site/ folder is current.")
