#!/usr/bin/env python3
"""Writes ../airtable/events_import.csv from the generated calendar.
Import it once into a new Airtable base; after that Airtable is the source of truth."""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ["EVENTS_FROM_CODE"] = "1"           # ignore events_live.json for this export
from events_data import EVENTS
from airtable_fields import FIELDS, to_row
out = os.path.join(HERE, "..", "airtable", "events_import.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader()
    for e in EVENTS: w.writerow(to_row(e))
print("wrote", out, len(EVENTS), "rows")
