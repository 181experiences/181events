#!/usr/bin/env python3
"""Writes the seed file: the calendar from events_data.py in the stored field shape.
build_site.py runs this so /events_seed.json ships with every deploy; /api/seed loads it
into an empty database, and the dev server uses it as its starting store.
Always built from the code calendar, never from a database pull."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ["EVENTS_FROM_CODE"] = "1"
from events_data import EVENTS
from fields import to_record
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "site", "events_seed.json")
rows = [to_record(e) for e in EVENTS]
json.dump(rows, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("seed:", out, len(rows), "events")
