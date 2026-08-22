#!/usr/bin/env python3
"""Shared event data for 181 Fremont — Resident Experiences.

Months are NOT hand-built. A month is just a window onto the event table:
recurring series generate their own occurrences across the range below, one-offs
are listed explicitly, and any month in range renders whatever falls inside it.
Extending the calendar = moving RANGE_END."""

import calendar
from datetime import date, timedelta

# ---- the window the calendar covers -----------------------------------------
RANGE_START = date(2026, 8, 21)
RANGE_END   = date(2026, 12, 31)

DOW   = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
DOW_S = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
MONTH_KEYS  = {8: "aug", 9: "sep", 10: "oct", 11: "nov", 12: "dec"}
MONTH_SHORT = {8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"}

def _sun_index(d):
    return d.isoweekday() % 7

def _months_in_range():
    out, y, m = [], RANGE_START.year, RANGE_START.month
    while (y, m) <= (RANGE_END.year, RANGE_END.month):
        first = date(y, m, 1)
        out.append(dict(key=MONTH_KEYS[m], name=f"{calendar.month_name[m]} {y}", num=m,
                        first_dow=_sun_index(first), days=calendar.monthrange(y, m)[1]))
        m = 1 if m == 12 else m + 1
        y = y + 1 if m == 1 else y
    return out

MONTHS = _months_in_range()
MONTH_BY_KEY = {m["key"]: m for m in MONTHS}

def _dates_matching(pred):
    d, out = RANGE_START, []
    while d <= RANGE_END:
        if pred(d):
            out.append(d)
        d += timedelta(days=1)
    return out

def _is_last_weekday_of_month(d, iso_wd):
    return d.isoweekday() == iso_wd and (d + timedelta(days=7)).month != d.month

CATEGORIES = ["Morning Offering", "Happy Hour", "Community Dinner",
              "Culinary Experience", "Enrichment Experience", "Signature Event"]

CLUB = "Level 39, Residents&rsquo; Club"

CAFE_DESC = [
    "Leigh-Ann hosts a coffee house on Level 39 on Tuesday and Thursday mornings, from 7:30 to 9:00. Come down for a proper cup before the day gets going.",
    "No sign-up needed. This one is Leigh-Ann&rsquo;s, so please send any questions her way.",
]
WINE_DESC = [
    "Every Tuesday on Level 39, from 5:30 to 7:30. A rotating selection of wine and beer in good company. Come as you are, and stay as long as you like.",
    "You don&rsquo;t need to RSVP to join us on your own. If you&rsquo;re bringing a guest from outside the building, please let us know so we can pour for them.",
]
BITES_DESC = [
    "Thursdays on Level 39, from 5:30 to 7:30. The same easy evening, with something from the kitchen alongside the wine and beer.",
    "You don&rsquo;t need to RSVP to join us on your own. If you&rsquo;re bringing a guest from outside the building, please let us know so we can pour for them.",
]
BRUNCH_DESC = [
    "Brunch on Level 39, from 10:00 to 2:00. A wider window than before, so you can come when it suits you.",
    "If noon to two has been your habit, that time is unchanged. We&rsquo;ve simply opened the morning on either side of it.",
    "Please RSVP so we can set the room properly.",
]
BOOK_DESC_FIRST = [
    "The first meeting of the 181 Fremont book club. We&rsquo;re beginning with <em>London Falling: A Mysterious Death in a Gilded City and a Family&rsquo;s Search for Truth</em> by Patrick Radden Keefe.",
    "Please join us whether or not you&rsquo;ve finished it. This first evening is as much about finding the group&rsquo;s rhythm as it is about the book. Light bites and wine will be served.",
    "From September we&rsquo;ll settle into the last Wednesday of each month at 4:30.",
]
BOOK_DESC = [
    "Our monthly meeting, on the last Wednesday of the month at 4:30 on Level 39.",
    "We&rsquo;re continuing with <em>London Falling</em> by Patrick Radden Keefe. Light bites and wine will be served.",
]
MOSS_DESC = [
    "An evening of hands-on botanical art. You&rsquo;ll build a moss wall to take home, with every material provided and no experience needed.",
    "Light bites and wine will be served throughout.",
]
SCRUB_DESC = [
    "An all-natural skincare workshop. You&rsquo;ll make three sugar scrubs to take home, blended with essential oils of your choosing.",
    "Light bites and wine will be served throughout.",
]
PUMPKIN_DESC = [
    "A succulent-topped pumpkin to carry your home through the autumn. You&rsquo;ll design your own, and learn how to keep the cuttings healthy along the way.",
    "We begin with a demonstration and a proper talk on succulent care, then everyone builds theirs. Mini pumpkins and all materials are provided, so there&rsquo;s nothing to bring.",
    "When the pumpkin has had its run, often many months from now, the cuttings can be replanted and enjoyed for years. Light bites and wine will be served throughout.",
]
KOKEDAMA_DESC = [
    "The Japanese art of moss ball gardening. You&rsquo;ll wrap a living plant in nutrient-rich soil and soft moss to make a kokedama, a sculptural piece that sits on a shelf or hangs by a window.",
    "We begin with a demonstration, then everyone makes their own. All supplies and care instructions are provided, and no experience is needed.",
    "Light bites and wine will be served throughout. You&rsquo;ll take home your kokedama, and everything you need to keep it thriving.",
]
SPEAKEASY_DESC = [
    "A speakeasy on Level 39 for one night only. We&rsquo;d love for you to come in your best spooky speakeasy attire, and there are prizes for the costumes that earn them.",
    "Games and trivia through the evening, signature cocktails from the bar, and spooky bites from the kitchen.",
    "No RSVP needed to join us on your own. If you&rsquo;re bringing a guest from outside the building, please let us know so we can pour for them.",
]
DEMO_DESC = [
    "A cooking demonstration with Leo, our Resident Experience Manager and a chef by training. The subject is holiday appetizers, all of them vegan, and all of them worth putting on your own table.",
    "He&rsquo;ll cook a vegan holiday dish from start to finish, then make two drinks alongside it: a holiday cocktail, and a mocktail.",
    "Everything will be tasted. Please come hungry.",
]
ZEN_DESC = [
    "An evening to slow down before the holiday season begins. A sound bath, guided breathing, and massage work, in a room set for stillness.",
    "Wellness-minded drinks and snacks will be served throughout. Come as you are. There&rsquo;s nothing to bring, and nothing you need to know beforehand.",
    "We begin at 6:00, straight after Book Club, so you&rsquo;re welcome to make an evening of the two.",
]
GALA_DESC = [
    "Our end-of-year party, and the one evening the whole building comes together. A red-carpet gala in the spirit of Old Hollywood. Black tie if you have it, and glamour however you care to define it.",
    "Walk the red carpet on arrival, then join us for an evening of food, drink, and awards, from 6:30 until 9:00 on Level 39.",
    "Open to residents and everyone who lives in your home. This is the one evening we aren&rsquo;t able to include outside guests, as the room only holds so many.",
    "We&rsquo;d love to see you in Old Hollywood glamour.",
]
MEXICO_DESC = [
    "The marquee evening of our season. A tribute to Michelin-level, Latin-inspired cooking, drawing on the techniques of Californios here in San Francisco and the celebrated kitchens of Mexico City.",
    "Twelve seats at one table on Level 39, with the city forty floors below. Courses are served family-style where the food calls for it, and plated where it doesn&rsquo;t. Each one is built around a single idea carried from a particular kitchen.",
    "$75 per person. Seats are released on a first-come basis, and we expect this one to fill quickly.",
]

SERIES = [
    dict(slug="cafe-181", title="Caf&eacute; 181", cat="Morning Offering",
         when=lambda d: d.isoweekday() in (2, 4), label="Every Tuesday and Thursday",
         t24="0730", time="7:30 AM", end="9:00 AM", rsvp=None, cap=None, price=None,
         host="Leigh-Ann", counted=False, desc=CAFE_DESC,
         img="linear-gradient(160deg,#3b2a1c 0%,#7a5636 48%,#c9a377 100%)"),
    dict(slug="wine-beer-happy-hour", title="Wine &amp; Beer Happy Hour", cat="Happy Hour",
         when=lambda d: d.isoweekday() == 2, label="Every Tuesday",
         t24="1730", time="5:30 PM", end="7:30 PM", rsvp="guest", cap=None, price=None,
         desc=WINE_DESC, img="linear-gradient(160deg,#6d2c2f 0%,#a8524a 46%,#dba078 100%)"),
    dict(slug="happy-hour-bites", title="Happy Hour &amp; Bites", cat="Happy Hour",
         when=lambda d: d.isoweekday() == 4, label="Every Thursday",
         t24="1730", time="5:30 PM", end="7:30 PM", rsvp="guest", cap=None, price=None,
         desc=BITES_DESC, img="linear-gradient(160deg,#7d3b1f 0%,#c8632f 45%,#e6a066 100%)"),
    dict(slug="sunday-brunch", title="Sunday Brunch", cat="Culinary Experience",
         when=lambda d: _is_last_weekday_of_month(d, 7), label="Last Sunday of the month",
         t24="1000", time="10:00 AM", end="2:00 PM", rsvp="standard", cap=45, price=None,
         desc=BRUNCH_DESC, img="linear-gradient(155deg,#8a6a34 0%,#c9a15c 48%,#efd9a8 100%)"),
    dict(slug="book-club", title="Book Club", cat="Enrichment Experience",
         when=lambda d: _is_last_weekday_of_month(d, 3) and d >= date(2026, 9, 1),
         label="Last Wednesday of the month",
         t24="1630", time="4:30 PM", end="6:00 PM", rsvp="standard", cap=None, price=None,
         desc=BOOK_DESC, img=None),
]

ONE_OFFS = [
    dict(on=date(2026, 8, 25), slug="book-club-inaugural", title="Book Club: Inaugural Meeting",
         cat="Enrichment Experience", t24="1630", time="4:30 PM", end="6:00 PM",
         rsvp="standard", cap=None, price=None, series="Moves to last Wednesday monthly",
         desc=BOOK_DESC_FIRST, img=None),
    dict(on=date(2026, 9, 2), slug="moss-wall-workshop", title="Moss Wall Workshop",
         cat="Enrichment Experience", t24="1800", time="6:00 PM", end="7:30 PM",
         rsvp="standard", cap=20, cutoff="Monday, Aug 31", price=None,
         desc=MOSS_DESC, img="linear-gradient(155deg,#2c3d2a 0%,#4e6b45 50%,#93b083 100%)"),
    dict(on=date(2026, 9, 16), slug="natural-skincare-sugar-scrubs", title="Natural Skincare: Sugar Scrubs",
         cat="Enrichment Experience", t24="1800", time="6:00 PM", end="7:00 PM",
         rsvp="standard", cap=20, cutoff="Monday, Sept 14", price=None,
         desc=SCRUB_DESC, img=None),
    dict(on=date(2026, 11, 18), slug="a-moment-of-zen", title="A Moment of Zen",
         cat="Enrichment Experience", t24="1800", time="6:00 PM", end="8:00 PM",
         rsvp="standard", cap=25, cutoff="Monday, Nov 16", price=None,
         desc=ZEN_DESC, img="linear-gradient(155deg,#191d2b 0%,#39415e 46%,#7b85a8 74%,#cfd4e2 100%)"),
    dict(on=date(2026, 12, 9), slug="healthy-holiday-appetizers", title="Healthy Holiday Appetizers",
         cat="Culinary Experience", t24="1730", time="5:30 PM", end="7:00 PM",
         rsvp="standard", cap=25, cutoff="Monday, Dec 7", price=None,
         sub="Cooking demonstration", desc=DEMO_DESC,
         img="linear-gradient(150deg,#1e2a1c 0%,#425a34 44%,#9db877 74%,#e6d9a8 100%)"),
    dict(on=date(2026, 12, 18), slug="lights-camera-gala", title="Lights, Camera, Gala",
         cat="Signature Event", t24="1830", time="6:30 PM", end="9:00 PM",
         rsvp="standard", cap=50, cutoff="Monday, Dec 14", price=None, marquee=True,
         sub="Resident End of Year Party", desc=GALA_DESC,
         img="linear-gradient(150deg,#0e0b0e 0%,#3a0f16 38%,#7d1f22 66%,#d8a54e 100%)"),
    dict(on=date(2026, 10, 28), slug="spooky-speakeasy", title="Spooky Speakeasy",
         cat="Happy Hour", t24="1730", time="5:30 PM", end="8:00 PM",
         rsvp="guest", cap=None, price=None, series="A one-night special, not the weekly happy hour",
         desc=SPEAKEASY_DESC,
         img="linear-gradient(150deg,#12101a 0%,#2f1c33 42%,#7a3f2c 76%,#d08a3f 100%)"),
    dict(on=date(2026, 10, 7), slug="succulent-pumpkin-workshop", title="Succulent Pumpkin Workshop",
         cat="Enrichment Experience", t24="1800", time="6:00 PM", end="7:30 PM",
         rsvp="standard", cap=20, cutoff="Monday, Oct 5", price=None,
         desc=PUMPKIN_DESC, img="linear-gradient(150deg,#5a2f14 0%,#a8632a 44%,#e2a95c 74%,#b9c39a 100%)"),
    dict(on=date(2026, 11, 11), slug="kokedama", title="Kokedama",
         cat="Enrichment Experience", t24="1830", time="6:30 PM", end="8:00 PM",
         rsvp="standard", cap=20, cutoff="Monday, Nov 9", price=None,
         desc=KOKEDAMA_DESC, img="linear-gradient(150deg,#3a3f33 0%,#6b7358 48%,#c3c4a5 100%)"),
    dict(on=date(2026, 9, 25), slug="a-night-in-mexico-city", title="A Night in Mexico City",
         cat="Community Dinner", t24="1800", time="6:00 PM", end="8:00 PM",
         rsvp="paid", cap=12, price="$75", marquee=True, desc=MEXICO_DESC,
         img="linear-gradient(145deg,#1d1512 0%,#6b2f22 42%,#c4713a 78%,#e8b06a 100%)"),
]

# One-off changes to a generated series occurrence: move it, or skip it entirely.
# The series itself is untouched — every other occurrence carries on as normal.
SERIES_OVERRIDES = {
    ("book-club", date(2026, 11, 25)): dict(
        move_to=date(2026, 11, 18),
        note="Moved a week early. The last Wednesday of November falls on Thanksgiving eve."),
    # --- December: full programme through the 20th, then a deliberate quiet period ---
    ("book-club", date(2026, 12, 30)): dict(
        move_to=date(2026, 12, 16),
        note="Moved to mid-month. The last Wednesday of December falls between the holidays."),
    ("sunday-brunch", date(2026, 12, 27)): dict(
        move_to=date(2026, 12, 20),
        note="Our last gathering of the year, moved ahead of the holidays."),
    ("wine-beer-happy-hour", date(2026, 12, 22)): dict(skip=True),
    ("wine-beer-happy-hour", date(2026, 12, 29)): dict(skip=True),
    ("happy-hour-bites",    date(2026, 12, 24)): dict(skip=True),
    ("happy-hour-bites",    date(2026, 12, 31)): dict(skip=True),
    ("cafe-181", date(2026, 12, 22)): dict(skip=True),
    ("cafe-181", date(2026, 12, 24)): dict(skip=True),
    ("cafe-181", date(2026, 12, 29)): dict(skip=True),
    ("cafe-181", date(2026, 12, 31)): dict(skip=True),

    ("sunday-brunch", date(2026, 11, 29)): dict(
        move_to=date(2026, 11, 22),
        note="A week early this month, ahead of the Thanksgiving holiday."),
    ("cafe-181", date(2026, 11, 26)): dict(skip=True),
    ("happy-hour-bites", date(2026, 11, 26)): dict(skip=True),
    ("book-club", date(2026, 10, 28)): dict(
        move_to=date(2026, 10, 21),
        note="Moved a week early this month. The Spooky Speakeasy has Level 39 on the 28th, "
             "and we return to the last Wednesday in November."),
}

def _base(**kw):
    e = dict(cap=None, cutoff=None, price=None, series=None, img=None, marquee=False,
             sub=None, host="Resident Experiences", counted=True, loc=CLUB, moved=False,
             status="Live", rec=None)
    e.update(kw)
    return e

EVENTS, _id = [], 1
for s in SERIES:
    for d in _dates_matching(s["when"]):
        ov = SERIES_OVERRIDES.get((s["slug"], d), {})
        if ov.get("skip"):
            continue
        desc = list(s["desc"])
        if ov.get("move_to"):
            d = ov["move_to"]
        if ov.get("note"):
            desc = [ov["note"]] + desc
        EVENTS.append(_base(
            id=_id, m=MONTH_KEYS[d.month], d=d.day, on=d, slug=s["slug"], title=s["title"],
            cat=s["cat"], t24=s["t24"], time=s["time"], end=s["end"], rsvp=s["rsvp"],
            cap=s["cap"], price=s["price"], series=s["label"], desc=desc, img=s["img"],
            host=s.get("host", "Resident Experiences"), counted=s.get("counted", True),
            moved=bool(ov.get("move_to"))))
        _id += 1
for o in ONE_OFFS:
    o = dict(o)
    d = o.pop("on")
    EVENTS.append(_base(id=_id, m=MONTH_KEYS[d.month], d=d.day, on=d, **o))
    _id += 1

EVENTS.sort(key=lambda e: (e["on"], e["t24"]))

# ---- Airtable takes over once publish.py has run -----------------------------
# events_live.json is written by publish.py from the Published rows in Airtable.
# When it exists, it replaces the generated list above. Delete it to fall back
# to the series and one-offs in this file. EVENTS_FROM_CODE=1 forces the fallback.
import os as _os, json as _json
_live = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "events_live.json")
if _os.path.exists(_live) and not _os.environ.get("EVENTS_FROM_CODE"):
    from airtable_fields import from_record as _from_record
    _rows = _json.load(open(_live, encoding="utf-8"))
    EVENTS = [_base(**_from_record(f, MONTH_KEYS)) for f in _rows if (f.get("Status") or "Draft") == "Live"]
    EVENTS = [e for e in EVENTS if RANGE_START <= e["on"] <= RANGE_END]
    EVENTS.sort(key=lambda e: (e["on"], e["t24"]))
    for _i, e in enumerate(EVENTS, 1): e["id"] = _i
    EVENTS_SOURCE = "airtable"
else:
    EVENTS_SOURCE = "code"

def dow_of(mk, d):   return DOW[(MONTH_BY_KEY[mk]["first_dow"] + d - 1) % 7]
def dow_s(mk, d):    return DOW_S[(MONTH_BY_KEY[mk]["first_dow"] + d - 1) % 7]
def month_name(mk):  return MONTH_BY_KEY[mk]["name"]
def short_month(mk): return MONTH_SHORT[MONTH_BY_KEY[mk]["num"]]
def evs_on(mk, d):   return sorted([e for e in EVENTS if e["m"] == mk and e["d"] == d], key=lambda e: e["t24"])
def days_with_events(mk): return sorted({e["d"] for e in EVENTS if e["m"] == mk})

if __name__ == "__main__":
    for m in MONTHS:
        print(m["name"], "-", len([e for e in EVENTS if e["m"] == m["key"]]), "events")
    print("total", len(EVENTS))
