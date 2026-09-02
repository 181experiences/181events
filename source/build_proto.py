#!/usr/bin/env python3
"""181 Fremont resident site — static, zero-JavaScript prototype.
All navigation, month switching, view toggles, day panels and RSVP states run on
CSS :checked selectors, so it works in any renderer including sandboxed previews."""

from events_data import (EVENTS, MONTHS, MONTH_BY_KEY, dow_of, dow_s, month_name,
                         short_month, evs_on, days_with_events)

# The Next Event tile aims at the first event that has not started yet at build
# time, Pacific: today's later events still count, and once one begins the tile
# moves on to the next. Each rebuild during the day keeps that honest, so the
# cron schedule decides how quickly the tile turns over. TODAY also drives the
# past-day muting, which stays a whole-day affair on purpose.
from datetime import datetime as _dt
try:
    from zoneinfo import ZoneInfo as _Zone
    _pacific_now = _dt.now(_Zone("America/Los_Angeles"))
except Exception:
    _pacific_now = _dt.utcnow()
TODAY = _pacific_now.date()
NOW_HHMM = _pacific_now.strftime("%H%M")

# ---------------------------------------------------------------- calendar window
# Two dials, set on the admin's Events screen and pulled from the database at
# build time (settings_live.json, written by publish.py): how many weeks out an
# event shows its full page, and how many months out the calendar shows anything
# at all. Inside the detail line, events are themselves. Past it but inside the
# horizon they appear shaded and quiet, like the past: the date is spoken for,
# the details wait, nothing can be RSVP'd or saved to a calendar, so plans can
# still pivot. Past the horizon they stay offstage. Every rebuild slides both
# windows forward; nobody opens anything by hand.
import json as _json, os as _os
from datetime import timedelta as _td
WINDOW = {"detail_weeks": 8, "horizon_months": 4}
try:
    _sl = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                        "settings_live.json"), encoding="utf-8"))
    WINDOW.update({k: int(_sl[k]) for k in WINDOW if k in _sl})
except Exception:
    pass
WINDOW["detail_weeks"] = min(12, max(1, WINDOW["detail_weeks"]))
WINDOW["horizon_months"] = min(4, max(1, WINDOW["horizon_months"]))

DETAIL_END = TODAY + _td(days=WINDOW["detail_weeks"] * 7)
_hy, _hm = TODAY.year, TODAY.month + WINDOW["horizon_months"]
while _hm > 12:
    _hm -= 12; _hy += 1

# In-place, so events_data's own helpers see the same trimmed lists.
_kept = [m for m in MONTHS if (m["yr"], m["num"]) <= (_hy, _hm)]
MONTHS[:] = _kept if _kept else MONTHS[:1]
_mkeys = {m["key"] for m in MONTHS}
EVENTS[:] = [e for e in EVENTS if (e["on"].year, e["on"].month) <= (_hy, _hm) and e["m"] in _mkeys]
for _e in EVENTS:
    _e["far"] = _e["on"] > DETAIL_END

def plain(s):
    for a, b in [("&rsquo;", "'"), ("&amp;", "&"), ("&middot;", "-"), ("&mdash;", "-"),
                 ("<em>", ""), ("</em>", ""), ("<strong>", ""), ("</strong>", ""),
                 ("<u>", ""), ("</u>", ""), ("—", "-")]:
        s = s.replace(a, b)
    return s

def slug(e):
    return plain(e["title"]).lower().replace(" ", "-").replace(":", "").replace("'", "")

ICS_FILES = {}   # filename -> file body; build_site writes these into site/ics/

# Version stamps let a re-added event REPLACE its old entry on the resident's
# calendar instead of duplicating: SEQUENCE grows with every build day, and
# calendar apps treat the higher number as the newer truth.
BUILD_STAMP = _dt.utcnow().strftime("%Y%m%dT%H%M%SZ")
BUILD_SEQ = (_dt.utcnow().date() - _dt(2026, 1, 1).date()).days

def ics_href(e):
    """A real .ics file served from the site. A data: URL looks the same on a laptop
    but does nothing at all on an iPhone, which is most of the audience."""
    eh = e["end"].split(":")[0]
    ehm = e["end"].split(":")[1].split(" ")[0]
    h24 = str((int(eh) % 12) + (12 if "PM" in e["end"] else 0)).zfill(2)
    d = e["on"].strftime("%Y%m%d")
    body = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//181 Fremont//Resident Experiences//EN",
        "BEGIN:VEVENT", f"UID:181fremont-{e['slug']}-{d}@181residents.com",
        f"DTSTAMP:{BUILD_STAMP}",
        f"SEQUENCE:{BUILD_SEQ}",
        f"LAST-MODIFIED:{BUILD_STAMP}",
        f"DTSTART:{d}T{e['t24']}00",
        f"DTEND:{d}T{h24}{ehm}00",
        f"SUMMARY:{plain(e['title'])}", f"LOCATION:181 Fremont - {plain(e['loc'])}",
        f"DESCRIPTION:{plain(e['desc'][0])}", "END:VEVENT", "END:VCALENDAR"]) + "\r\n"
    fname = f"{e['on'].isoformat()}_{e['slug']}.ics"
    ICS_FILES[fname] = body
    return f"/ics/{fname}"

# "RSVP closes" is a date now (the editor picks one); older rows carry text
# like "Monday, Aug 31", which parses to the same thing. Closing means the end
# of that day, Pacific: from the next morning the RSVP button turns into a
# waitlist request that Resident Experiences answers with a yes or a no, via
# the Confirm seats button it already owns.
import re as _re
_MON_NUM = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "june": 6,
            "jul": 7, "july": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
_MON_PRETTY = [None, "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]

def cutoff_date(e):
    from datetime import date as _date
    c = (e.get("cutoff") or "").strip()
    if not c:
        return None
    if _re.match(r"^\d{4}-\d{2}-\d{2}$", c):
        try:
            return _date.fromisoformat(c)
        except ValueError:
            return None
    m = _re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?$", c)
    if not m:
        return None
    mon = _MON_NUM.get(m.group(1).lower()[:4]) or _MON_NUM.get(m.group(1).lower()[:3])
    if not mon:
        return None
    try:
        d = _date(e["on"].year, mon, int(m.group(2)))
        return _date(e["on"].year - 1, mon, int(m.group(2))) if d > e["on"] else d
    except ValueError:
        return None

def cutoff_pretty(e):
    d = cutoff_date(e)
    if not d:
        return e.get("cutoff") or ""
    return f'{d.strftime("%A")}, {_MON_PRETTY[d.month]} {d.day}'

def rsvp_closed(e):
    if e.get("closed"):   # the editor's switch: closed right now, by hand
        return True
    d = cutoff_date(e)
    return bool(d and TODAY > d)

def closed_line(e):
    p = cutoff_pretty(e) if cutoff_date(e) and not e.get("closed") else ""
    return f"RSVPs closed {p}" if p else "RSVPs are closed for this one"

def tag_for(e):
    if e.get("far"):
        return '<span class="tag">Details to come</span>'
    if e.get("teaser"):
        return '<span class="tag">Coming soon</span>'
    if e["rsvp"] == "guest":
        return '<span class="tag">Drop in &middot; guests welcome</span>'
    if e["rsvp"] == "paid":
        return f'<span class="tag paid">{e["cap"]} seats &middot; {e["price"]}</span>'
    if e["rsvp"] == "standard":
        if e["cap"]:
            return f'<span class="tag open">RSVP &middot; {e["cap"]} places</span>'
        return '<span class="tag open">RSVP requested</span>'
    return '<span class="tag">No RSVP needed</span>'

# ------------------------------------------------------------------ generated CSS
rules = []
for s in ["home", "cal", "msg"] + [f"ev{e['id']}" for e in EVENTS if not e.get("far")]:
    rules.append(f'#r-{s}:checked ~ .screens #scr-{s}{{display:block}}')
for m in MONTHS:
    k = m["key"]
    rules.append(f'#m-{k}:checked ~ .stickybar .mname[data-m="{k}"]{{display:block}}')
    rules.append(f'#m-{k}:checked ~ .monthwrap[data-m="{k}"]{{display:block}}')
    rules.append(f'#m-{k}:checked ~ .stickybar .navpair[data-m="{k}"]{{display:flex}}')
    for d in days_with_events(k):
        if len(evs_on(k, d)) > 1:
            rules.append(f'#d-{k}-{d}:checked ~ .monthwrap[data-m="{k}"] .daypanel[data-d="{d}"]{{display:block}}')
            rules.append(f'#d-{k}-{d}:checked ~ .monthwrap[data-m="{k}"] label[for="d-{k}-{d}"]'
                         '{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}')
            rules.append(f'#d-{k}-{d}:checked ~ .monthwrap[data-m="{k}"] label[for="d-{k}-{d}"] .dot'
                         '{background:var(--paper-2)}')
GEN_CSS = "\n  ".join(rules)

# ------------------------------------------------------------------ month grids
def day_is_past(m, d):
    year = int(m["name"].split()[-1])
    return _dt(year, m["num"], d).date() < TODAY

def month_block(m):
    k, days, fd = m["key"], m["days"], m["first_dow"]
    cells = ['<div class="cell empty"></div>'] * fd
    for d in range(1, days + 1):
        evs = evs_on(k, d)
        gone = " past" if day_is_past(m, d) else ""
        dots = '<span class="dots">' + '<span class="dot"></span>' * min(len(evs), 3) + '</span>'
        if not evs:
            cells.append(f'<div class="cell plain{gone}"><span>{d}</span><span class="dots"></span></div>')
        elif all(e.get("far") for e in evs):
            # Beyond the detail window the date is visibly spoken for, but there
            # is nowhere to go yet: a quiet cell, not a doorway.
            cells.append(f'<div class="cell has far" '
                         f'aria-label="{dow_of(k,d)} {short_month(k)} {d}, details to come"><span>{d}</span>{dots}</div>')
        elif len(evs) == 1:
            cells.append(f'<label class="cell has{gone}" for="r-ev{evs[0]["id"]}" '
                         f'aria-label="{dow_of(k,d)} {short_month(k)} {d}, 1 event"><span>{d}</span>{dots}</label>')
        else:
            cells.append(f'<label class="cell has{gone}" for="d-{k}-{d}" '
                         f'aria-label="{dow_of(k,d)} {short_month(k)} {d}, {len(evs)} events"><span>{d}</span>{dots}</label>')
    panels = []
    for d in days_with_events(k):
        evs = evs_on(k, d)
        if len(evs) < 2:
            continue
        gone = " past" if day_is_past(m, d) else ""
        rows = "".join(
            (f'<div class="ev far">'
             f'<span class="ev-time">{e["time"]}</span>'
             f'<span class="ev-body"><span class="ev-title">{e["title"]}</span>'
             f'<span class="ev-meta">{e["loc"]}</span>{tag_for(e)}</span></div>')
            if e.get("far") else
            (f'<label class="ev{gone}" for="r-ev{e["id"]}">'
             f'<span class="ev-time">{e["time"]}</span>'
             f'<span class="ev-body"><span class="ev-title">{e["title"]}</span>'
             f'<span class="ev-meta">{e["loc"]}</span>{tag_for(e)}</span>'
             f'<span class="ev-go">&rarr;</span></label>') for e in evs)
        panels.append(f'<div class="daypanel" data-d="{d}">'
                      f'<div class="d-date">{dow_of(k,d)}, {short_month(k)} {d}</div>'
                      f'<div class="d-count">{len(evs)} events</div>{rows}</div>')
    return (f'<div class="monthwrap" data-m="{k}"><div class="wrap">'
            '<div class="dow"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span>'
            '<span>Thu</span><span>Fri</span><span>Sat</span></div>'
            f'<div class="grid">{"".join(cells)}</div>{"".join(panels)}'
            '<div style="height:70px"></div></div></div>')

MONTH_BLOCKS = "".join(month_block(m) for m in MONTHS)

# ------------------------------------------------------------------ list view
list_html = []
for m in MONTHS:
    k = m["key"]
    list_html.append(f'<div class="month-label">{m["name"]}</div>')
    for d in days_with_events(k):
        rows = []
        for i, e in enumerate(evs_on(k, d)):
            datecell = (f'<span class="dnum">{d}</span><span class="dday">{dow_s(k,d)}</span>'
                        if i == 0 else '')
            if e.get("far"):
                rows.append(
                    f'<div class="lrow far">'
                    f'<span class="ldate">{datecell}</span>'
                    f'<span class="ev-body"><span class="ev-title">{e["title"]}</span>'
                    f'<span class="ev-meta">{e["time"]} &middot; {e["loc"]}</span>{tag_for(e)}</span></div>')
                continue
            rows.append(
                f'<label class="lrow{" marquee" if e["marquee"] else ""}{" past" if day_is_past(m, d) else ""}" for="r-ev{e["id"]}">'
                f'<span class="ldate">{datecell}</span>'
                f'<span class="ev-body"><span class="ev-title">{e["title"]}</span>'
                f'<span class="ev-meta">{e["time"]} &middot; {e["loc"]}</span>{tag_for(e)}</span>'
                f'<span class="ev-go">&rarr;</span></label>')
        list_html.append('<div class="lgroup">' + "".join(rows) + '</div>')
LIST = "".join(list_html)

# ------------------------------------------------------------------ event screens
def event_screen(e):
    i = e["id"]
    if e["img"]:
        hero = f'<div class="ehero photo{" tall" if e["marquee"] else ""}" style="background-image:{e["img"]}"></div>'
    else:
        hero = ('<div class="ehero fallback"><div><div class="fb-line"></div>'
                f'<div class="fb-title">{e["title"]}</div><div class="fb-sub">181 Fremont</div></div></div>')

    facts = ('<dl class="e-facts">'
             f'<div class="fact"><dt>When</dt><dd>{dow_of(e["m"],e["d"])}, {short_month(e["m"])} {e["d"]}<br>'
             f'{e["time"]} &ndash; {e["end"]}</dd></div>'
             f'<div class="fact"><dt>Where</dt><dd>{e["loc"]}</dd></div>')
    if e["cap"] and e["price"]:
        facts += f'<div class="fact"><dt>Seats</dt><dd>{e["cap"]} &middot; {e["price"]} per person</dd></div>'
    elif e["cap"]:
        facts += f'<div class="fact"><dt>Capacity</dt><dd>{e["cap"]} places</dd></div>'
    if e["cutoff"]:
        facts += (f'<div class="fact"><dt>RSVP by</dt><dd>{cutoff_pretty(e)}'
                  f'{" &middot; now closed" if rsvp_closed(e) else ""}</dd></div>')
    if e["series"]:
        facts += f'<div class="fact"><dt>Repeats</dt><dd>{e["series"]}</dd></div>'
    facts += f'<div class="fact"><dt>Hosted by</dt><dd>{e["host"]}</dd></div></dl>'

    # RSVPs happen on the site: each button leads to /rsvp/{date}_{slug}, a live page
    # that knows who is signed in, what the unit already said, and how many seats
    # remain. The calendar itself stays static and script-free.
    checkbox = ""
    guest_radios = ""
    guest_ui = ""
    box = ""
    cta = '<div class="cta">'
    note = ""
    rsvp_href = f"/rsvp/{e['on'].isoformat()}_{e['slug']}"
    gone = e["on"] < TODAY

    if gone:
        # A passed event stays readable, an enticement for the next one, but
        # nothing invites an RSVP or a calendar entry for what already happened.
        label = ("Registration Closed" if e["rsvp"] == "guest"
                 else "Seats Closed" if e["rsvp"] == "paid"
                 else "RSVP Closed" if e["rsvp"] == "standard" else "")
        if label:
            cta += f'<span class="btn off">{label}</span>'
        cta += '<span class="btn ghost off">Add to My Calendar</span></div>'
        ics_href(e)   # the calendar file still builds; subscribers' feeds manage themselves
        note = "This one has passed. The calendar has what&rsquo;s coming next; we&rsquo;d love to see you there."
        box = f'<div class="note" style="margin-top:14px">{note}</div>'
        eyebrow = e["sub"] or e["cat"]
        return f'''<section class="screen" id="scr-ev{e["id"]}">
    <div class="wrap">
      <label class="back" for="r-cal">&larr; Back to calendar</label>
      <div class="ebody">
        {hero}
        <div class="e-eyebrow">{eyebrow} &middot; Past event</div>
        <h1 class="e-title">{e["title"]}</h1>
        {facts}
        <div class="e-copy">{"".join(f"<p>{p}</p>" for p in e["desc"])}</div>
        {box}
        {cta}
      </div>
    </div>
  </section>'''

    if e.get("teaser"):
        # Published on purpose before it is fully formed: the date is claimed and
        # the anticipation is real, but nothing can be RSVP'd or saved to a
        # calendar until the details settle, so plans can still pivot cleanly.
        if e["rsvp"] in ("guest", "paid", "standard"):
            cta += '<span class="btn off">RSVP Opens Soon</span>'
        cta += '<span class="btn ghost off">Add to My Calendar</span></div>'
        box = ('<div class="note" style="margin-top:14px">We&rsquo;re still putting this one together. '
               'The full details arrive right here, and RSVP and Add to My Calendar open with them.</div>')
        return f'''<section class="screen" id="scr-ev{i}">
    <div class="wrap">
      <label class="back" for="r-cal">&larr; Back to calendar</label>
      <div class="ebody">
        {hero}
        <div class="e-eyebrow">{e["sub"] or e["cat"]} &middot; Coming soon</div>
        <h1 class="e-title">{e["title"]}</h1>
        {facts}
        <div class="e-copy">{"".join(f"<p>{p}</p>" for p in e["desc"])}</div>
        {box}
        {cta}
      </div>
    </div>
  </section>'''

    if e["rsvp"] in ("guest", "paid", "standard") and rsvp_closed(e):
        # Closed is not a wall; it is a change of channel. The button asks
        # instead of books: the request lands on the waitlist, Resident
        # Experiences sees it, and Confirm seats (or a call) is the answer.
        cta += f'<a class="btn" href="{rsvp_href}">Join the Waitlist</a>'
        note = (f"{closed_line(e)}. You can still ask: a request joins the waitlist, "
                "lands with Resident Experiences, and we reach out with a yes or a no.")
    elif e["rsvp"] == "guest":
        guest_ui = ('<div class="guestbox"><div class="gq">Bringing someone from outside the building?</div>'
                    '<div class="gh">You&rsquo;re always welcome on your own, with no RSVP needed. We only ask for a '
                    'count of guests from outside the building, so we can pour and plate for them.</div></div>')
        cta += f'<a class="btn" href="{rsvp_href}">Register Guests</a>'
        note = ("Takes a moment, right here on the site. Sign in once with your resident code, "
                "and your guest count saves to your name.")
    elif e["rsvp"] == "paid":
        cta += f'<a class="btn" href="{rsvp_href}">{e["price"]} &middot; Request Seats</a>'
        note = ("Seats are confirmed in the order requests arrive, and payment is arranged with "
                "your confirmation. Sign in once with your resident code.")
    elif e["rsvp"] == "standard":
        cutoff_line = (f" Kindly update your RSVP with any change of plans by {cutoff_pretty(e)}, as that is when we order materials."
                       if e["cutoff"] else "")
        cta += f'<a class="btn" href="{rsvp_href}">RSVP</a>'
        note = ("Sign in once with your resident code, and your RSVP saves under My RSVPs, "
                "where you can change or cancel anytime." + cutoff_line)

    cta += (f'<a class="btn ghost" href="{ics_href(e)}" download="{e["on"].isoformat()}_{e["slug"]}.ics">'
            'Add to My Calendar</a></div>')
    if note:
        box = f'<div class="note" style="margin-top:14px">{note}</div>' 

    eyebrow = e["sub"] or e["cat"]
    return f'''<section class="screen" id="scr-ev{i}">
    <div class="wrap">
      <label class="back" for="r-cal">&larr; Back to calendar</label>
      {checkbox}{guest_radios}
      <div class="ebody">
        {hero}
        <div class="e-eyebrow">{eyebrow}</div>
        <h1 class="e-title">{e["title"]}</h1>
        {facts}
        <div class="e-copy">{"".join(f"<p>{p}</p>" for p in e["desc"])}</div>
        {guest_ui}
        {box}
        {cta}
        <div class="note">Adding to your calendar works with Apple, Google, and Outlook.</div>
      </div>
    </div>
  </section>'''

EVENT_SCREENS = "".join(event_screen(e) for e in EVENTS if not e.get("far"))

# ------------------------------------------------------------------ next event tile
# EVENTS arrives ordered by date then start time, so the first not-yet-started
# entry inside the detail window is the tile. A day with several events hands
# the tile from one to the next as each begins. If nothing detailed is ahead
# (a very short window over a quiet stretch), the tile points at the calendar
# itself rather than at a page that does not exist.
NEXT = next((e for e in EVENTS if not e.get("far")
             and (e["on"] > TODAY or (e["on"] == TODAY and e.get("t24", "2359") > NOW_HHMM))), None)
if NEXT is None:
    NEXT = next((e for e in reversed(EVENTS) if not e.get("far")), None)
NEXT_FOR = f'r-ev{NEXT["id"]}' if NEXT else "r-cal"
NEXT_SUB = f'{dow_s(NEXT["m"], NEXT["d"])}, {short_month(NEXT["m"])} {NEXT["d"]}' if NEXT else "See the calendar"

# ------------------------------------------------------------------ month nav
# The calendar opens on the month the building is living in, clamped to the
# published range, and the home eyebrow reads from that month to the last one
# published. Both re-settle at every rebuild, so the turn of a month needs
# nobody's hands.
def _open_month():
    ym = (TODAY.year, TODAY.month)
    if ym <= (MONTHS[0]["yr"], MONTHS[0]["num"]):
        return MONTHS[0]
    for m in MONTHS:
        if (m["yr"], m["num"]) == ym:
            return m
    return MONTHS[-1]

OPEN_MONTH = _open_month()

def _eyebrow_range():
    a, b = OPEN_MONTH, MONTHS[-1]
    if a is b:
        return a["name"]
    a_name, a_yr = a["name"].rsplit(" ", 1)
    if a_yr == b["name"].rsplit(" ", 1)[1]:
        return f"{a_name} to {b['name']}"
    return f"{a['name']} to {b['name']}"

EYEBROW_RANGE = _eyebrow_range()

MONTH_RADIOS = "\n    ".join(
    f'<input class="state" type="radio" name="mon" id="m-{m["key"]}"{" checked" if m is OPEN_MONTH else ""}>'
    for m in MONTHS)

MONTH_NAMES = "\n        ".join(
    f'<div class="mname" data-m="{m["key"]}">{m["name"]}</div>' for m in MONTHS)

def _nav_for(i):
    k = MONTHS[i]["key"]
    prev = (f'<label class="navbtn" for="m-{MONTHS[i-1]["key"]}" aria-label="{MONTHS[i-1]["name"]}">&lsaquo;</label>'
            if i > 0 else '<span class="navbtn off">&lsaquo;</span>')
    nxt = (f'<label class="navbtn" for="m-{MONTHS[i+1]["key"]}" aria-label="{MONTHS[i+1]["name"]}">&rsaquo;</label>'
           if i < len(MONTHS) - 1 else '<span class="navbtn off">&rsaquo;</span>')
    return f'<span class="navpair" data-m="{k}">{prev}{nxt}</span>'

MONTH_NAV = "\n        ".join(_nav_for(i) for i in range(len(MONTHS)))

DAY_RADIOS = "".join(
    f'<input class="state" type="radio" name="day" id="d-{m["key"]}-{d}">'
    for m in MONTHS for d in days_with_events(m["key"]) if len(evs_on(m["key"], d)) > 1)

# ------------------------------------------------------------------ page
HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>181 Fremont Resident Events</title>
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
  :root{{
    --ink:#16161a; --ink-body:#3a3a43; --ink-soft:#55555f;
    --paper:#f7f4ef; --paper-2:#fffdfa; --line:#ddd6cb;
    --red:#c41f26; --stone:#7a7266; --radius:4px;
    --pad:clamp(20px,5vw,44px);
    --fd:'Marcellus',Georgia,serif;
    --fb:'Hanken Grotesk',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  }}
  *{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
  html,body{{margin:0;padding:0}}
  body{{background:var(--paper);color:var(--ink-body);font-family:var(--fb);
    font-weight:400;font-size:19px;line-height:1.6;-webkit-font-smoothing:antialiased}}
  h1,h2,h3{{font-family:var(--fd);font-weight:400;letter-spacing:.015em;margin:0;color:var(--ink)}}
  a{{color:inherit;text-decoration:none}}
  label{{cursor:pointer}}
  em{{font-style:italic}}
  .wrap{{max-width:940px;margin:0 auto;padding:0 var(--pad)}}
  .state{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;margin:0}}

  /* Saved to an iPhone home screen the page runs edge to edge, so the status bar
     (clock, battery) overlays the top. The inset pushes the header below it. */
  header.masthead{{border-bottom:1px solid var(--line);background:var(--paper-2);padding-top:env(safe-area-inset-top);
    position:sticky;top:0;z-index:50}}
  .masthead-inner{{max-width:940px;margin:0 auto;padding:12px var(--pad);display:flex;align-items:center;justify-content:space-between;gap:16px}}
  .logo{{display:block;font-family:var(--fd);font-size:25px;letter-spacing:.2em;text-transform:uppercase;line-height:1;color:var(--ink)}}
  .logo:hover{{color:var(--red)}}
  .logo small{{display:block;font-family:var(--fb);font-size:11px;letter-spacing:.26em;color:var(--stone);margin-top:7px}}
  .whoami{{font-size:15px;color:var(--stone);text-align:right;line-height:1.35}}
  .whoami strong{{color:var(--ink);font-weight:500;display:block}}

  .screen{{display:none}}
  {GEN_CSS}

  /* ---------- landing ---------- */
  .hero{{padding:clamp(38px,7vw,68px) 0 clamp(26px,5vw,40px);text-align:center}}
  .hero .eyebrow{{font-size:13px;letter-spacing:.28em;text-transform:uppercase;color:var(--stone);margin-bottom:20px}}
  .hero h1{{font-size:clamp(34px,7.5vw,56px);line-height:1.12}}
  .hero p{{max-width:28em;margin:20px auto 0;color:var(--ink-soft)}}
  .rule{{width:52px;height:1px;background:var(--red);margin:26px auto}}
  .quad{{display:grid;grid-template-columns:1fr 1fr;gap:14px;max-width:620px;margin:0 auto;padding-bottom:30px}}
  /* two quiet lines under the quad: real pages, not tiles. position:relative
     matters: on phones the calendar's .ev-go arrows go absolute, and without an
     anchor here they would escape the line and float behind the tiles. */
  .homelines{{max-width:620px;margin:0 auto;padding-bottom:70px}}
  .hline{{position:relative;display:flex;align-items:center;gap:18px;padding:22px 6px;border-top:1px solid var(--line);min-height:64px}}
  @media(max-width:620px){{ .hline{{padding-right:38px}} }}
  .hline:last-child{{border-bottom:1px solid var(--line)}}
  .hline:hover .hl-t{{color:var(--red)}}
  .hl-body{{flex:1}}
  .hl-t{{display:block;font-family:var(--fd);font-size:23px;color:var(--ink);line-height:1.2}}
  .hl-s{{display:block;font-size:15px;color:var(--ink-soft);margin-top:4px;line-height:1.4}}
  .sq{{position:relative;aspect-ratio:1/1;background:var(--paper-2);border:1px solid var(--line);
    border-radius:var(--radius);display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-end;
    padding:clamp(16px,4.4vw,26px);transition:border-color .18s,transform .18s}}
  .sq:hover{{border-color:var(--red);transform:translateY(-2px)}}
  .sq .ico{{position:absolute;top:clamp(16px,4.4vw,26px);left:clamp(16px,4.4vw,26px);color:var(--red)}}
  .sq .ico svg{{width:clamp(28px,7vw,34px);height:clamp(28px,7vw,34px);display:block}}
  .sq .label{{display:block;font-family:var(--fd);font-size:clamp(21px,5.4vw,28px);line-height:1.15;color:var(--ink)}}
  .sq .sub{{display:block;font-size:clamp(13px,3.4vw,15px);color:var(--ink-soft);margin-top:6px;line-height:1.35}}
  .sq.dark{{background:var(--ink);border-color:var(--ink)}}
  .sq.dark .label{{color:var(--paper)}} .sq.dark .sub{{color:#b7b0a5}} .sq.dark .ico{{color:#e8a0a3}}
  .sq .badge{{position:absolute;top:clamp(16px,4.4vw,26px);right:clamp(16px,4.4vw,26px);background:var(--red);
    color:#fff;font-size:12px;font-weight:600;min-width:26px;height:26px;border-radius:100px;
    display:flex;align-items:center;justify-content:center;padding:0 8px}}

  /* ---------- calendar ---------- */
  /* sits directly under the frozen masthead (68px of content plus the phone status bar) */
  .stickybar{{position:sticky;top:calc(env(safe-area-inset-top) + 68px);z-index:40;background:var(--paper);border-bottom:1px solid var(--line);
    padding:16px 0 14px;margin-bottom:18px}}
  .stickybar .inner{{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}}
  .mname{{display:none;font-family:var(--fd);font-size:clamp(26px,5.6vw,36px);line-height:1;color:var(--ink)}}
  .ctrl{{display:flex;align-items:center;gap:8px}}
  .navpair{{display:none;gap:8px}}
  .navbtn{{width:54px;height:54px;border:1px solid var(--line);border-radius:var(--radius);background:var(--paper-2);
    font-size:22px;display:flex;align-items:center;justify-content:center;color:var(--ink)}}
  .navbtn:hover{{border-color:var(--red)}}
  .navbtn.off{{color:#cdc5b9;border-color:#eae3d8}}
  .toggle{{display:inline-flex;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:var(--paper-2)}}
  .toggle label{{padding:14px 22px;font-size:14px;letter-spacing:.12em;text-transform:uppercase;
    min-height:54px;display:flex;align-items:center;color:var(--stone);font-weight:500}}
  #v-month:checked ~ .stickybar .toggle label[for="v-month"],
  #v-list:checked ~ .stickybar .toggle label[for="v-list"]{{background:var(--ink);color:var(--paper-2)}}
  #v-list:checked ~ .stickybar .ctrl .navpair,
  #v-list:checked ~ .stickybar .mname{{display:none !important}}
  #v-list:checked ~ .stickybar .allmonths{{display:block}}
  .allmonths{{display:none;font-family:var(--fd);font-size:clamp(26px,5.6vw,36px);line-height:1;color:var(--ink)}}
  .monthwrap{{display:none}}
  #v-list:checked ~ .monthwrap{{display:none !important}}
  .listwrap{{display:none}}
  #v-list:checked ~ .listwrap{{display:block}}

  .dow{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;margin-bottom:6px}}
  .dow span{{text-align:center;font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--stone);
    padding:6px 0;overflow:hidden;font-weight:500}}
  .grid{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}}
  .cell{{position:relative;background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);
    aspect-ratio:1/1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;
    font-size:21px;min-height:56px;color:var(--ink)}}
  .cell.empty{{background:transparent;border-color:transparent}}
  .cell.has{{font-weight:500}}
  .cell.has:hover{{border-color:var(--red)}}
  .cell.plain{{color:#a9a196}}
  .dots{{display:flex;gap:5px;height:8px}}
  .dot{{width:8px;height:8px;border-radius:50%;background:var(--red)}}
  @media(min-width:720px){{
    .cell{{aspect-ratio:auto;min-height:104px;justify-content:flex-start;align-items:flex-start;padding:12px 14px;gap:9px}}
    .dots{{margin-top:auto}}
  }}
  @media(max-width:620px){{ .dow span{{font-size:11px;letter-spacing:.02em}} .grid,.dow{{gap:5px}} }}

  .daypanel{{background:var(--paper-2);border:1px solid var(--line);border-left:3px solid var(--red);
    border-radius:var(--radius);margin-top:18px;padding:26px 24px;display:none}}
  .d-date{{font-family:var(--fd);font-size:27px;margin-bottom:4px;color:var(--ink)}}
  .d-count{{font-size:14px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);margin-bottom:18px;font-weight:500}}

  .ev{{display:flex;gap:18px;align-items:flex-start;width:100%;padding:20px 4px;border-top:1px solid var(--line);min-height:64px}}
  .ev:first-of-type{{border-top:none}}
  .ev:hover .ev-title{{color:var(--red)}}
  .ev-time{{flex:0 0 100px;font-size:16px;color:var(--stone);padding-top:4px;font-weight:500}}
  .ev-body{{flex:1;display:block}}
  .ev-title{{display:block;font-family:var(--fd);font-size:25px;line-height:1.25;color:var(--ink)}}
  .ev-meta{{display:block;font-size:17px;color:var(--ink-soft);margin-top:5px}}
  .ev-go{{color:var(--red);font-size:24px;padding-top:2px}}
  @media(max-width:620px){{
    .ev{{flex-wrap:wrap;gap:0 14px;position:relative;padding-right:34px}}
    .ev-time{{flex:0 0 100%;padding-top:0;margin-bottom:6px;font-size:14px;letter-spacing:.12em;text-transform:uppercase}}
    .ev-body{{flex:1 1 100%}}
    .ev-go{{position:absolute;right:2px;top:50%;transform:translateY(-50%);padding-top:0}}
  }}
  .tag{{display:inline-block;font-size:13px;letter-spacing:.1em;text-transform:uppercase;font-weight:500;
    border:1px solid var(--line);border-radius:100px;padding:5px 13px;color:var(--stone);margin-top:10px}}
  .tag.open{{border-color:var(--red);color:var(--red)}}
  .tag.paid{{background:var(--ink);border-color:var(--ink);color:var(--paper-2)}}

  .month-label{{font-size:13px;letter-spacing:.26em;text-transform:uppercase;color:var(--stone);
    padding:26px 0 12px;border-bottom:1px solid var(--line);font-weight:500}}
  .month-label:first-child{{padding-top:6px}}
  .lgroup{{border-bottom:1px solid var(--line)}}
  .lrow{{position:relative;display:flex;gap:22px;width:100%;padding:24px 4px;align-items:flex-start;min-height:72px}}
  .lrow:not(:first-child)::before{{content:'';position:absolute;left:var(--datecol,90px);right:4px;top:0;height:1px;background:#e6ded2}}
  .lrow:hover .ev-title{{color:var(--red)}}
  .lrow.marquee{{background:linear-gradient(90deg,rgba(196,31,38,.05),transparent 60%);
    border-left:3px solid var(--red);padding-left:14px}}
  .ldate{{flex:0 0 68px;text-align:center;padding-top:2px}}
  .ldate .dnum{{display:block;font-family:var(--fd);font-size:34px;line-height:1;color:var(--ink)}}
  .ldate .dday{{display:block;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--stone);margin-top:5px;font-weight:500}}
  @media(max-width:620px){{ .lrow{{gap:16px;--datecol:70px;padding-right:36px}} .ldate{{flex:0 0 54px}} }}

  /* ---------- event ---------- */
  .back{{display:inline-flex;align-items:center;gap:10px;margin:24px 0 4px;font-size:17px;color:var(--ink-soft);min-height:50px}}
  .back:hover{{color:var(--red)}}
  .ehero{{border-radius:var(--radius);overflow:hidden;margin:12px 0 32px;aspect-ratio:16/9;
    display:flex;align-items:center;justify-content:center;text-align:center;padding:30px}}
  .ehero.tall{{aspect-ratio:4/3}}
  .ehero.photo{{background-size:cover;background-position:center}}
  .ehero.fallback{{background:var(--ink);color:var(--paper)}}
  .fb-line{{width:44px;height:1px;background:var(--red);margin:0 auto 18px}}
  .fb-title{{font-family:var(--fd);font-size:clamp(26px,5.5vw,44px);line-height:1.15}}
  .fb-sub{{font-size:12px;letter-spacing:.3em;text-transform:uppercase;color:#a8a094;margin-top:16px}}
  .e-eyebrow{{font-size:13px;letter-spacing:.26em;text-transform:uppercase;color:var(--red);font-weight:500}}
  .e-title{{font-size:clamp(32px,6.6vw,52px);line-height:1.12;margin:14px 0 0}}
  .e-facts{{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:30px 0;padding:6px 0}}
  .fact{{display:flex;gap:20px;padding:16px 0;border-top:1px solid var(--line)}}
  .fact:first-child{{border-top:none}}
  .fact dt{{flex:0 0 112px;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);padding-top:5px;margin:0;font-weight:500}}
  .fact dd{{margin:0;flex:1;font-size:20px;color:var(--ink)}}
  .e-copy p{{color:var(--ink-body);font-size:20px;line-height:1.65;margin:0 0 18px}}

  .rlink{{display:inline-flex;align-items:center;min-height:54px;font-size:14px;letter-spacing:.1em;
    text-transform:uppercase;font-weight:600;color:var(--red);border-bottom:1px solid currentColor;padding-bottom:2px}}
  .rlink:hover{{color:#a5171d}}
  .urlline{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:15px;background:var(--paper);
    border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;margin-top:12px;overflow-wrap:anywhere}}
  .guestbox{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:24px;margin:8px 0 26px}}
  .gq{{font-family:var(--fd);font-size:clamp(19px,4.8vw,24px);color:var(--ink);line-height:1.25}}
  .gh{{font-size:clamp(16px,4.2vw,17px);color:var(--ink-soft);margin-top:8px}}
  .gh .rlink{{min-height:0;margin:0}}   /* inline in a paragraph: the tap-target floor would stretch its line */
  .glab{{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);font-weight:500;margin:20px 0 10px}}
  .gchips{{display:flex;gap:10px;flex-wrap:wrap}}
  .gchip{{min-width:62px;min-height:56px;display:flex;align-items:center;justify-content:center;
    border:1px solid var(--line);border-radius:var(--radius);background:var(--paper);font-size:19px;font-weight:500;color:var(--ink)}}
  .gchip:hover{{border-color:var(--red)}}

  .cta{{display:flex;flex-wrap:wrap;gap:14px;margin:30px 0 14px}}
  .btn{{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:20px 30px;min-height:62px;
    border-radius:var(--radius);font-size:16px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;
    background:var(--red);color:#fff;border:1px solid var(--red);flex:1 1 auto;text-align:center}}
  .btn:hover{{background:#a5171d;border-color:#a5171d}}
  .btn.ghost{{background:transparent;color:var(--ink);border-color:#c9c0b3}}
  .btn.ghost:hover{{border-color:var(--ink);background:transparent}}
  /* passed events: readable, never actionable */
  .btn.off{{background:#cdc5b9;border-color:#cdc5b9;color:#fffdfa;cursor:default;pointer-events:none}}
  .btn.ghost.off{{background:transparent;color:#b8b0a4;border-color:#e0d9cd;cursor:default;pointer-events:none}}
  .cell.past{{background:#f2eee7;border-color:#e7e0d5;color:#c3bbae}}
  .cell.past .dot{{background:#d9b3b5}}
  .cell.has.past:hover{{border-color:#c9c0b3}}
  .ev.past .ev-title,.lrow.past .ev-title{{color:#a9a196}}
  .ev.past .ev-meta,.lrow.past .ev-meta,.lrow.past .ldate .dnum{{color:#b8b0a4}}
  .ev.past .tag,.lrow.past .tag{{opacity:.55}}
  .lrow.past.marquee{{background:none;border-left-color:#d9b3b5}}
  /* Beyond the detail window: present, spoken for, and quiet. The translucency
     says "not yet" the way the muting says "already was". */
  .cell.far{{background:#f2eee7;border-color:#e7e0d5;color:#c3bbae;cursor:default;opacity:.8}}
  .cell.far .dot{{background:#d9b3b5}}
  .ev.far,.lrow.far{{cursor:default;opacity:.75}}
  .ev.far .ev-title,.lrow.far .ev-title{{color:#a9a196}}
  .ev.far .ev-meta,.lrow.far .ev-meta,.lrow.far .ldate .dnum{{color:#b8b0a4}}
  .ev.far .tag,.lrow.far .tag{{opacity:.7}}
  .rsvpbtn .s-on{{display:none}}
  .note{{font-size:16px;color:var(--stone);margin:0 0 80px}}
  .rsvpbox{{background:var(--paper-2);border:1px solid var(--line);border-left:3px solid var(--red);
    border-radius:var(--radius);padding:24px;margin:0 0 4px;display:none}}
  .rsvpbox h3{{font-size:25px;margin-bottom:8px}}
  .rsvpbox p{{margin:0;color:var(--ink-soft);font-size:18px}}

  /* ---------- message ---------- */
  .msg-intro{{padding:22px 0 6px}}
  .msg-intro h2{{font-size:clamp(28px,6vw,42px);line-height:1.12}}
  .msg-intro p{{font-size:19px;color:var(--ink-soft);max-width:36em;margin:16px 0 0}}
  .choices{{display:grid;gap:12px;margin:30px 0 26px}}
  .choice{{display:flex;gap:18px;align-items:flex-start;width:100%;background:var(--paper-2);
    border:1px solid var(--line);border-radius:var(--radius);padding:22px;min-height:76px}}
  .choice:hover{{border-color:#b9afa1}}
  #i-idea:checked ~ .msgform .msq[data-k="idea"],
  #i-plan:checked ~ .msgform .msq[data-k="plan"],
  #i-other:checked ~ .msgform .msq[data-k="other"]{{border-color:var(--red);background:#fffaf9;box-shadow:inset 0 0 0 1px var(--red)}}
  .msgquad{{grid-template-columns:repeat(3,1fr);gap:10px;max-width:none;margin:22px 0 4px;padding-bottom:0}}
  .msq .label{{font-size:clamp(15px,4.2vw,21px)}}
  .msq .sub{{font-size:clamp(11px,3vw,14px);margin-top:4px}}
  .msq .ico svg{{width:clamp(22px,6vw,28px);height:clamp(22px,6vw,28px)}}
  .choice .cico{{color:var(--red);flex:0 0 auto;padding-top:2px}}
  .choice .cico svg{{width:26px;height:26px;display:block}}
  .choice .ct{{display:block;font-family:var(--fd);font-size:23px;line-height:1.2;color:var(--ink)}}
  .choice .cs{{display:block;font-size:16px;color:var(--ink-soft);margin-top:5px;line-height:1.45}}
  .flabel{{display:none;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);margin-bottom:10px;font-weight:500}}
  #i-idea:checked ~ .msgform .flabel.idea,
  #i-plan:checked ~ .msgform .flabel.plan,
  #i-other:checked ~ .msgform .flabel.other{{display:block}}
  textarea{{width:100%;min-height:170px;padding:18px;font-family:var(--fb);font-size:19px;line-height:1.55;
    color:var(--ink);background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);resize:vertical}}
  textarea:focus{{outline:none;border-color:var(--red)}}
  .prefill{{font-size:16px;color:var(--stone);margin:14px 0 0}}
  .routing{{background:#efe9e0;border-radius:var(--radius);padding:18px 20px;margin:26px 0 0;font-size:16px;color:#5c5548;line-height:1.5}}
  .routing strong{{color:var(--ink);font-weight:600}}
  .fields{{display:grid;gap:14px;margin:22px 0 0}}
  @media(min-width:640px){{.fields{{grid-template-columns:1fr 1fr}}}}
  .field{{display:block}}
  .field span{{display:block;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);margin-bottom:8px;font-weight:500}}
  .field input{{width:100%;min-height:54px;padding:0 16px;font-family:var(--fb);font-size:19px;color:var(--ink);
    background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius)}}
  .field input:focus{{outline:none;border-color:var(--red)}}
  button.btn{{font-family:var(--fb);cursor:pointer;width:100%}}
  .mailnote{{font-size:16px;color:var(--stone);margin:12px 0 0;line-height:1.5}}
  .mailnote a{{color:var(--ink);border-bottom:1px solid var(--line);text-decoration:none}}
  .msgsent{{text-align:center;padding:50px 0 90px}}
  .check{{width:70px;height:70px;border-radius:50%;background:var(--red);color:#fff;
    display:flex;align-items:center;justify-content:center;margin:0 auto 26px}}
  .msgsent h2{{font-size:34px}}
  .msgsent p{{font-size:19px;color:var(--ink-soft);max-width:30em;margin:16px auto 0}}

  footer{{border-top:1px solid var(--line);padding:34px 0 60px;color:var(--stone);font-size:15px;text-align:center}}
  .stafflink{{color:var(--stone);border-bottom:1px solid var(--line);padding:14px 2px}}
  .stafflink:hover{{color:var(--ink)}}
  .mocknote{{background:#16161a;color:#c9c2b6;font-size:13px;letter-spacing:.1em;text-align:center;padding:11px 16px;text-transform:uppercase}}
</style>
</head>
<body>



<header class="masthead">
  <div class="masthead-inner">
    <label class="logo" for="r-home">181 Fremont<small>Resident Events</small></label>
    <div class="whoami">Welcome<strong>Residents&rsquo; Club</strong></div>
  </div>
</header>

<input class="state" type="radio" name="scr" id="r-home" checked>
<input class="state" type="radio" name="scr" id="r-cal">
<input class="state" type="radio" name="scr" id="r-msg">
{"".join(f'<input class="state" type="radio" name="scr" id="r-ev{e["id"]}">' for e in EVENTS if not e.get("far"))}

<div class="screens">

  <section class="screen" id="scr-home">
    <div class="wrap">
      <div class="hero">
        <div class="eyebrow">{EYEBROW_RANGE}</div>
        <h1>What&rsquo;s happening at<br>The Residents&rsquo; Club</h1>
        <div class="rule"></div>
        <p>Everything on the calendar, in one place.</p>
      </div>
      <div class="quad">
        <label class="sq dark" for="r-cal">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><circle cx="8.5" cy="14.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="12" cy="14.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="15.5" cy="17.6" r="1.1" fill="currentColor" stroke="none"/></svg></span>
          <span class="label">Calendar</span><span class="sub">Month &amp; list</span>
        </label>
        <label class="sq" for="{NEXT_FOR}">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5.4l3.4 2"/></svg></span>
          <span class="label">Next Event</span><span class="sub">{NEXT_SUB}</span>
        </label>
        <a class="sq" href="/my">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8.2 12.4l2.6 2.6 5-5.4"/></svg></span>
          <span class="label">My RSVPs</span><span class="sub">Saved to your name</span>
        </a>
        <label class="sq" for="r-msg">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/></svg></span>
          <span class="label">Message</span><span class="sub">Ideas &amp; requests</span>
        </label>
      </div>
      <div class="homelines">
        <a class="hline" href="/board">
          <span class="hl-body"><span class="hl-t">Board Meetings</span>
          <span class="hl-s">Board business, on its own page, with Add to My Calendar</span></span>
          <span class="ev-go">&rarr;</span>
        </a>
      </div>
      <!-- The Level 39 Spaces line is resting at the Board's request (Aug 2026).
           The /spaces page and the admin's Spaces screen stay live; restore the
           line by putting the anchor back here.
        <a class="hline" href="/spaces"> ... </a> -->
    </div>
  </section>

  <section class="screen" id="scr-cal">
    <input class="state" type="radio" name="view" id="v-month" checked>
    <input class="state" type="radio" name="view" id="v-list">
    {MONTH_RADIOS}
    {DAY_RADIOS}

    <div class="stickybar"><div class="wrap"><div class="inner">
      <div>
        {MONTH_NAMES}
        <div class="allmonths">Coming up</div>
      </div>
      <div class="ctrl">
        <div class="toggle"><label for="v-month">Month</label><label for="v-list">List</label></div>
        {MONTH_NAV}
      </div>
    </div></div></div>

    {MONTH_BLOCKS}

    <div class="listwrap"><div class="wrap">{LIST}<div style="height:24px"></div></div></div>

    <div class="wrap"><div class="guestbox" style="margin:14px 0 70px">
      <div class="gq">Keep the whole calendar in your pocket</div>
      <div class="gh">Subscribe once, and every event lives in your own calendar and keeps itself current:
      new dates appear, changes follow along, and anything cancelled slips away on its own. On an iPhone or iPad,
      <a class="rlink" href="webcal://181residents.com/calendar/feed">tap here to subscribe</a>.
      In Google Calendar or Outlook, add a calendar from this address:</div>
      <div class="urlline">https://181residents.com/calendar/feed</div>
    </div></div>
  </section>

  <section class="screen" id="scr-msg">
    <form class="msgform" action="/message" method="post">
    <input class="state" type="radio" name="Topic" value="Share an idea" id="i-idea" checked>
    <input class="state" type="radio" name="Topic" value="Plan an event with us" id="i-plan">
    <input class="state" type="radio" name="Topic" value="Something else" id="i-other">

    <div class="msgform"><div class="wrap">
      <label class="back" for="r-home">&larr; Back</label>
      <div class="msg-intro">
        <h2>Contact Us</h2>
        <p>Message Resident Experiences for any of the following. We will get back to you within one business day.</p>
      </div>
      <div class="quad msgquad">
        <label class="sq msq" data-k="idea" for="i-idea">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.5.4.8 1 .8 1.6h5.4c0-.6.3-1.2.8-1.6A6 6 0 0 0 12 3z"/></svg></span>
          <span class="label">Share</span><span class="sub">An idea for the calendar</span>
        </label>
        <label class="sq msq" data-k="plan" for="i-plan">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20"/><circle cx="10" cy="8" r="3.4"/><path d="M17.5 11.5h4M19.5 9.5v4"/></svg></span>
          <span class="label">Plan</span><span class="sub">Host your own event</span>
        </label>
        <label class="sq msq" data-k="other" for="i-other">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M9.6 9.2a2.5 2.5 0 0 1 4.9.7c0 1.6-2.4 2-2.4 3.4"/><circle cx="12" cy="16.8" r=".9" fill="currentColor" stroke="none"/></svg></span>
          <span class="label">Ask</span><span class="sub">A question, a note, anything</span>
        </label>
      </div>
      <div class="flabel idea">Your idea</div>
      <div class="flabel plan">What would you like to plan?</div>
      <div class="flabel other">Your message</div>
      <textarea name="Message" placeholder="Type here&hellip;" required></textarea>
      <div class="fields">
        <label class="field"><span>Your name</span><input type="text" name="Name" autocomplete="name" autocapitalize="words" placeholder="Optional"></label>
        <label class="field"><span>Email, if you&rsquo;d like a reply</span><input type="email" name="Email" autocomplete="email" autocapitalize="none" inputmode="email" placeholder="Optional"></label>
      </div>
      <div class="cta"><button class="btn" type="submit">Send to Resident Experiences</button></div>
      <p class="mailnote">Sends right from this page and lands with Resident Experiences under your name and unit.
      Not signed in yet? We&rsquo;ll ask for your resident code first, and nothing you&rsquo;ve typed is lost.</p>
      <div class="routing"><strong>Building maintenance or a service issue?</strong> Please contact the front desk or Action Life directly. This inbox is monitored during Resident Experiences hours only.</div>
      <div style="height:80px"></div>
    </div></div>
    </form>
  </section>

  {EVENT_SCREENS}

</div>

<footer>181 Fremont Residences &middot; Resident Experiences &middot; <a class="stafflink" href="/admin">Staff</a></footer>
</body>
</html>
'''

# ------------------------------------------------------------------ dynamic page templates
# The signed-in pages (/signin, /my, /rsvp/..., /message) are rendered by Pages
# Functions from these templates, which ship with the static build in /_templates/.
# All resident-facing copy and styling for those pages lives HERE, in one voice
# with the calendar; the Functions only compute the values that fill the slots.
# {{NAME}} is a slot; <!--NAME--> ... <!--/NAME--> is a section kept or dropped.

SHELL_CSS = '''
  :root{
    --ink:#16161a; --ink-body:#3a3a43; --ink-soft:#55555f;
    --paper:#f7f4ef; --paper-2:#fffdfa; --line:#ddd6cb;
    --red:#c41f26; --stone:#7a7266; --radius:4px;
    --pad:clamp(20px,5vw,44px);
    --fd:'Marcellus',Georgia,serif;
    --fb:'Hanken Grotesk',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;padding:0}
  body{background:var(--paper);color:var(--ink-body);font-family:var(--fb);
    font-weight:400;font-size:19px;line-height:1.6;-webkit-font-smoothing:antialiased}
  h1,h2{font-family:var(--fd);font-weight:400;letter-spacing:.015em;margin:0;color:var(--ink)}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:720px;margin:0 auto;padding:0 var(--pad) 90px}
  header.masthead{border-bottom:1px solid var(--line);background:var(--paper-2);padding-top:env(safe-area-inset-top);
    position:sticky;top:0;z-index:50}
  .masthead-inner{max-width:940px;margin:0 auto;padding:12px var(--pad);display:flex;align-items:center;justify-content:space-between;gap:16px}
  .logo{display:block;font-family:var(--fd);font-size:25px;letter-spacing:.2em;text-transform:uppercase;line-height:1;color:var(--ink)}
  .logo:hover{color:var(--red)}
  .logo small{display:block;font-family:var(--fb);font-size:11px;letter-spacing:.26em;color:var(--stone);margin-top:7px}
  .whoami{font-size:15px;color:var(--stone);text-align:right;line-height:1.35}
  .whoami strong{color:var(--ink);font-weight:500;display:block}
  .back{display:inline-flex;align-items:center;gap:10px;margin:24px 0 4px;font-size:17px;color:var(--ink-soft);min-height:50px}
  .back:hover{color:var(--red)}
  .pagehead{padding:14px 0 6px}
  .pagehead h1{font-size:clamp(30px,6.4vw,44px);line-height:1.12}
  .pagehead h2{font-size:clamp(25px,5.4vw,32px);line-height:1.18}
  .pagehead p{font-size:19px;color:var(--ink-soft);max-width:34em;margin:14px 0 0}
  .e-eyebrow{font-size:13px;letter-spacing:.26em;text-transform:uppercase;color:var(--red);font-weight:500;margin-top:22px}
  .e-title{font-size:clamp(30px,6.4vw,44px);line-height:1.12;margin:12px 0 0}
  .e-facts{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:26px 0;padding:6px 0}
  .fact{display:flex;gap:20px;padding:16px 0;border-top:1px solid var(--line)}
  .fact:first-child{border-top:none}
  .fact dt{flex:0 0 112px;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);padding-top:5px;margin:0;font-weight:500}
  .fact dd{margin:0;flex:1;font-size:20px;color:var(--ink)}
  .pageform{margin:26px 0 0;display:grid;gap:16px;max-width:30em}
  .field{display:block}
  .field span{display:block;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);margin-bottom:8px;font-weight:500}
  .field input{width:100%;min-height:54px;padding:0 16px;font-family:var(--fb);font-size:19px;color:var(--ink);
    background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius)}
  .field input:focus{outline:none;border-color:var(--red)}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:20px 30px;min-height:62px;
    border-radius:var(--radius);font-size:16px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;
    background:var(--red);color:#fff;border:1px solid var(--red);text-align:center;cursor:pointer;font-family:var(--fb)}
  .btn:hover{background:#a5171d;border-color:#a5171d}
  .btn.ghost{background:transparent;color:var(--ink);border-color:#c9c0b3}
  .btn.ghost:hover{border-color:var(--ink);background:transparent}
  .note{font-size:16px;color:var(--stone);margin:22px 0 0;max-width:34em}
  .note a{border-bottom:1px solid var(--line)}
  .formerror{background:#f7e9e9;border:1px solid #d8b4b4;border-left:3px solid var(--red);border-radius:var(--radius);
    padding:16px 18px;margin:22px 0 0;font-size:17px;color:#7a2a2a;max-width:30em}
  .state{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;margin:0}
  .flabel2{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);font-weight:500}
  .gchips{display:flex;gap:10px;flex-wrap:wrap}
  .gchip{min-width:62px;min-height:56px;display:flex;align-items:center;justify-content:center;
    border:1px solid var(--line);border-radius:var(--radius);background:var(--paper-2);font-size:18px;font-weight:500;
    color:var(--ink);padding:0 18px;cursor:pointer}
  .gchip:hover{border-color:var(--red)}
  .state:checked + .gchip{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}
  .guestbox,.statebox{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:24px;margin:26px 0 0}
  .statebox{border-left:3px solid var(--red)}
  .gq,.statebox h2{font-family:var(--fd);font-size:clamp(19px,4.8vw,24px);color:var(--ink);line-height:1.25}
  .gh,.statebox p{font-size:clamp(16px,4.2vw,17px);color:var(--ink-soft);margin:8px 0 0}
  .gh .rlink{min-height:0;margin:0}
  .alsobox{background:#efe9e0;border-radius:var(--radius);padding:20px 22px;margin:26px 0 0;max-width:34em}
  .alsobox .al-t{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#6d6355;font-weight:600;margin-bottom:8px}
  .alsobox p{margin:0;font-size:18px;color:var(--ink)}
  .alsobox .al-s{font-size:15px;color:#6d6355;margin-top:10px}
  .fullnote{background:#f4ecd9;border-radius:var(--radius);padding:18px 20px;margin:26px 0 0;font-size:17px;color:#5b4a1f;line-height:1.55;max-width:34em}
  .cancelform{margin:14px 0 0;max-width:30em;display:grid}
  .lgroup{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:26px}
  .lrow{position:relative;display:flex;gap:22px;width:100%;padding:24px 4px;align-items:flex-start;min-height:72px}
  .lrow:not(:first-child){border-top:1px solid #e6ded2}
  .lrow:hover .ev-title{color:var(--red)}
  .ldate{flex:0 0 68px;text-align:center;padding-top:2px}
  .ldate .dnum{display:block;font-family:var(--fd);font-size:34px;line-height:1;color:var(--ink)}
  .ldate .dday{display:block;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--stone);margin-top:5px;font-weight:500}
  .ev-body{flex:1;display:block}
  .ev-title{display:block;font-family:var(--fd);font-size:25px;line-height:1.25;color:var(--ink)}
  .ev-meta{display:block;font-size:17px;color:var(--ink-soft);margin-top:5px}
  .ev-go{color:var(--red);font-size:24px;padding-top:2px}
  .tag{display:inline-block;font-size:13px;letter-spacing:.1em;text-transform:uppercase;font-weight:500;
    border:1px solid var(--line);border-radius:100px;padding:5px 13px;color:var(--stone);margin-top:10px}
  .tag.open{border-color:var(--red);color:var(--red)}
  .emptybox{background:var(--paper-2);border:1px dashed var(--line);border-radius:var(--radius);padding:30px 26px;margin-top:26px;max-width:34em}
  .emptybox p{margin:0 0 20px;color:var(--ink-soft)}
  .signoutform{margin-top:44px}
  .signoutform button{background:none;border:none;padding:14px 4px;min-height:54px;font-family:var(--fb);font-size:16px;
    color:var(--stone);cursor:pointer;border-bottom:1px solid var(--line)}
  .signoutform button:hover{color:var(--red);border-color:var(--red)}
  .rlink{display:inline-flex;align-items:center;min-height:54px;margin-top:2px;font-size:14px;letter-spacing:.1em;
    text-transform:uppercase;font-weight:600;color:var(--red);border-bottom:1px solid currentColor;padding-bottom:2px}
  .rlink:hover{color:#a5171d}
  .urlline{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:15px;background:var(--paper-2);
    border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;margin-top:12px;overflow-wrap:anywhere}
  .msgsent{text-align:center;padding:60px 0 20px}
  .check2{width:70px;height:70px;border-radius:50%;background:var(--red);color:#fff;
    display:flex;align-items:center;justify-content:center;margin:0 auto 26px}
  .msgsent h1{font-size:clamp(30px,6.4vw,40px)}
  .msgsent p{font-size:19px;color:var(--ink-soft);max-width:30em;margin:16px auto 0}
  .cta2{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin-top:32px}
  footer{border-top:1px solid var(--line);padding:34px 0 60px;color:var(--stone);font-size:15px;text-align:center}
  .stafflink{color:var(--stone);border-bottom:1px solid var(--line);padding:14px 2px}
  .stafflink:hover{color:var(--ink)}
'''

SHELL = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{TITLE}} &middot; 181 Fremont</title>
<link rel="stylesheet" href="/fonts/fonts.css">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#16161a">
<style>''' + SHELL_CSS + '''</style>
</head>
<body>
<header class="masthead">
  <div class="masthead-inner">
    <a class="logo" href="/">181 Fremont<small>Resident Events</small></a>
    <div class="whoami">Welcome<strong>{{WHO}}</strong></div>
  </div>
</header>
<main class="wrap">
{{CONTENT}}
</main>
<footer>181 Fremont Residences &middot; Resident Experiences &middot; <a class="stafflink" href="/admin">Staff</a></footer>
</body>
</html>
'''

SIGNIN_FORM = '''<form method="post" action="/signin" class="pageform">
<input type="hidden" name="to" value="{{TO}}">
<label class="field"><span>Resident code</span>
<input type="text" name="code" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="XXXX-XXXX" required></label>
<button class="btn" type="submit">Sign In</button>
</form>
<p class="note">No code yet, or lost it? The front desk can hand you a fresh one any hour of the day.</p>'''

T_SIGNIN = '''<a class="back" href="/">&larr; Back to the calendar</a>
<div class="pagehead"><h1>Sign in</h1>
<p>Enter your resident code, the one on your card or in your note from Resident Experiences.
One sign-in lasts a month on this device.</p></div>
<!--ERROR--><div class="formerror">{{ERROR}}</div><!--/ERROR-->
''' + SIGNIN_FORM

T_MY = '''<a class="back" href="/">&larr; Back to the calendar</a>
<div class="pagehead"><h1>My RSVPs</h1>
<p>Signed in as {{LABEL}}.</p></div>
<!--EMPTY--><div class="emptybox">
<p>Nothing on the books yet. Tap RSVP on any event, and it appears here.</p>
<a class="btn" href="/">See the Calendar</a>
</div><!--/EMPTY-->
<!--ROWS--><div class="lgroup">
<!--ROW--><a class="lrow" href="/rsvp/{{KEY}}">
<span class="ldate"><span class="dnum">{{DAY}}</span><span class="dday">{{DOW}}</span></span>
<span class="ev-body"><span class="ev-title">{{TITLE}}</span><span class="ev-meta">{{META}}</span>
<span class="tag {{TAGCLASS}}">{{TAG}}</span></span>
<span class="ev-go">&rarr;</span></a><!--/ROW-->
</div>
<p class="note">Tap any RSVP to change your party or cancel.</p><!--/ROWS-->
<div class="guestbox"><div class="gq">Your RSVPs, living in your own calendar</div>
<div class="gh">Subscribe once, and this page follows you: every event you say yes to appears in your
calendar by itself, moves when a date moves, and slips away if it is cancelled. On an iPhone or iPad,
<a class="rlink" style="min-height:0;margin:0" href="{{FEEDWEBCAL}}">tap here to subscribe</a>.
In Google Calendar or Outlook, add a calendar from this address. It is yours alone, so keep it to yourself:</div>
<div class="urlline">{{FEEDURL}}</div></div>
<form method="post" action="/signout" class="signoutform"><button type="submit">Sign out of this device</button></form>'''

RSVP_CHIPS = '''<div class="flabel2">{{COUNTLABEL}}</div>
<div class="gchips"><!--CHIP--><input class="state" type="radio" name="count" id="c{{N}}" value="{{N}}" {{CHECKED}}><label class="gchip" for="c{{N}}">{{LABEL}}</label><!--/CHIP--></div>
<label class="field"><span>Their names, if you&rsquo;d like us to know</span>
<input type="text" name="names" value="{{NAMES}}" autocomplete="off" autocapitalize="words" placeholder="Optional"></label>'''

T_RSVP = '''<a class="back" href="/">&larr; Back to the calendar</a>
<div class="e-eyebrow">{{EYEBROW}}</div>
<h1 class="e-title">{{TITLE}}</h1>
<dl class="e-facts">
<div class="fact"><dt>When</dt><dd>{{WHEN}}</dd></div>
<div class="fact"><dt>Where</dt><dd>{{WHERE}}</dd></div>
<!--SEATS--><div class="fact"><dt>Seats</dt><dd>{{SEATS}}</dd></div><!--/SEATS-->
<!--CUTOFF--><div class="fact"><dt>RSVP by</dt><dd>{{CUTOFF}}</dd></div><!--/CUTOFF-->
</dl>
<!--ALSO--><div class="alsobox"><div class="al-t">Also from your unit</div>
<p>{{MATES}}</p>
<p class="al-s">Shown so a household never counts itself twice. If they already have you covered, you&rsquo;re all set.</p>
</div><!--/ALSO-->
<!--DROPIN--><div class="pagehead"><h2>No RSVP needed</h2>
<p>This one is drop-in. Just come along; we&rsquo;ll be glad to see you.</p></div><!--/DROPIN-->
<!--SIGNIN--><div class="pagehead"><h2>Sign in to RSVP</h2>
<p>Enter your resident code, and you&rsquo;ll come straight back to this page. One sign-in lasts a month on this device.</p></div>
''' + SIGNIN_FORM + '''<!--/SIGNIN-->
<!--EXISTING--><div class="statebox"><h2>{{STATE}}</h2>
<p>Change your party below, or cancel. Kindly keep us posted; the kitchen sets by the count.</p></div>
<form method="post" action="/rsvp/{{KEY}}" class="pageform">
<input type="hidden" name="action" value="rsvp">
''' + RSVP_CHIPS + '''
<button class="btn" type="submit">Save Changes</button>
</form>
<form method="post" action="/rsvp/{{KEY}}" class="cancelform">
<input type="hidden" name="action" value="cancel">
<button class="btn ghost" type="submit">Cancel This RSVP</button>
</form><!--/EXISTING-->
<!--FORM--><!--STANDARD--><div class="pagehead"><h2>Will you join us?</h2>
<p>Count yourself and anyone coming with you: your household, or a guest staying with you.</p></div><!--/STANDARD-->
<!--GUEST--><div class="guestbox"><div class="gq">Bringing someone from outside the building?</div>
<div class="gh">You&rsquo;re always welcome on your own, with no RSVP needed. We only ask for a count of
guests from outside the building, so we can pour and plate for them.</div></div><!--/GUEST-->
<!--PAID--><div class="pagehead"><h2>Request your seats</h2>
<p>Seats are confirmed by Resident Experiences in the order requests arrive. Payment is arranged
with your confirmation, never on this site.</p></div><!--/PAID-->
<!--FULLNOTE--><div class="fullnote">Every seat is spoken for at the moment. Join the waitlist and
you hold a place in line, in the order requests arrived.</div><!--/FULLNOTE-->
<!--CLOSEDNOTE--><div class="fullnote">{{CLOSEDLINE}}. You can still ask:
your request joins the waitlist, lands with Resident Experiences, and we reach out with a yes or a no.</div><!--/CLOSEDNOTE-->
<form method="post" action="/rsvp/{{KEY}}" class="pageform">
<input type="hidden" name="action" value="rsvp">
''' + RSVP_CHIPS + '''
<button class="btn" type="submit">{{BTNTEXT}}</button>
</form><!--/FORM-->
<p class="note">Full details for this event are on <a href="/">the calendar</a>.</p>'''

T_REGISTER = '''<div class="e-eyebrow">Private event &middot; 181 Fremont</div>
<h1 class="e-title">{{EVENT}}</h1>
<dl class="e-facts">
<div class="fact"><dt>When</dt><dd>{{WHEN}}</dd></div>
<div class="fact"><dt>Where</dt><dd>{{WHERE}}, 181 Fremont, San Francisco</dd></div>
<!--HOST--><div class="fact"><dt>Hosted by</dt><dd>{{HOST}}</dd></div><!--/HOST-->
</dl>
<!--FORM--><div class="pagehead"><h2>May we have your name?</h2>
<p>Register below and the front desk will be expecting you. Bringing someone?
Add their name as your plus one, and you&rsquo;re both on the list.</p></div>
<form method="post" action="/register/{{TOKEN}}" class="pageform">
<label class="field"><span>Your name</span>
<input type="text" name="name" autocomplete="name" autocapitalize="words" maxlength="80" required></label>
<label class="field"><span>Plus one, if you&rsquo;re bringing someone</span>
<input type="text" name="plus" autocomplete="off" autocapitalize="words" maxlength="80" placeholder="Optional"></label>
<div style="position:absolute;left:-9999px" aria-hidden="true"><input type="text" name="website" tabindex="-1" autocomplete="off"></div>
<button class="btn" type="submit">Register</button>
</form><!--/FORM-->
<!--CLOSED--><div class="fullnote">{{CLOSEDMSG}}</div><!--/CLOSED-->
<p class="note">On the day: come to the 181 Fremont lobby and give the event name. Questions go to your host,
or to the front desk at 181 Fremont.</p>'''

T_DONE = '''<div class="msgsent">
<!--ICON--><div class="check2"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12.8l5 5 10-11"/></svg></div><!--/ICON-->
<h1>{{HEAD}}</h1>
<p>{{SUB}}</p>
<div class="cta2"><!--LINK--><a class="btn" href="{{LINKHREF}}">{{LINKTEXT}}</a><!--/LINK--></div>
</div>'''

T_MSGSTEP = '''<a class="back" href="/">&larr; Back to the calendar</a>
<div class="pagehead"><h1>One more step</h1>
<p>Your note is written and ready. Enter your resident code to send it, and you&rsquo;ll stay
signed in for a month on this device.</p></div>
<!--ERROR--><div class="formerror">{{ERROR}}</div><!--/ERROR-->
<form method="post" action="/message" class="pageform">
<input type="hidden" name="Topic" value="{{TOPIC}}">
<input type="hidden" name="Message" value="{{BODY}}">
<input type="hidden" name="Name" value="{{NAME}}">
<input type="hidden" name="Email" value="{{EMAIL}}">
<label class="field"><span>Resident code</span>
<input type="text" name="code" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="XXXX-XXXX" required></label>
<button class="btn" type="submit">Send to Resident Experiences</button>
</form>
<p class="note">No code yet, or lost it? The front desk can hand you a fresh one any hour of the day.</p>'''

T_BOARD = '''<a class="back" href="/">&larr; Back to the calendar</a>
<div class="pagehead"><h1>Board Meetings</h1>
<p>Board business, kept apart from the events calendar. Dates and times are set by the Board,
and questions about them go to the Board or building management rather than Resident Experiences.</p></div>
<!--EMPTY--><div class="emptybox">
<p>Nothing is scheduled at the moment. When the Board sets a date, it appears here.</p>
<a class="btn ghost" href="/">Back to the Calendar</a>
</div><!--/EMPTY-->
<!--ROWS--><div class="lgroup">
<!--ROW--><div class="lrow">
<span class="ldate"><span class="dnum">{{DAY}}</span><span class="dday">{{DOW}}</span></span>
<span class="ev-body"><span class="ev-title">{{TITLE}}</span><span class="ev-meta">{{META}}</span>
<a class="rlink" href="{{ICS}}">Add to My Calendar</a></span>
</div><!--/ROW-->
</div>
<div class="guestbox"><div class="gq">Keep these in your calendar on their own</div>
<div class="gh">Add the Board calendar once, and every change reaches you by itself: a cancelled meeting
leaves your calendar without anyone sending a notice. On an iPhone or iPad,
<a class="rlink" style="margin:0" href="webcal://181residents.com/board/feed">tap here to subscribe</a>.
In Google Calendar or Outlook, add a calendar from this address:</div>
<div class="urlline">https://181residents.com/board/feed</div></div><!--/ROWS-->'''

T_SPACES = '''<a class="back" href="/">&larr; Back to the calendar</a>
<div class="pagehead"><h1>Level 39 Spaces</h1>
<p>The conference room, the dining room, and the Club are yours to walk into whenever they&rsquo;re
free, any hour of the day. The hours below are spoken for; everything else is open.</p></div>
<!--EMPTY--><div class="emptybox">
<p>Nothing is reserved ahead. Every space is open; come on up.</p>
<a class="btn ghost" href="/">Back to the Calendar</a>
</div><!--/EMPTY-->
<!--ROWS--><div class="lgroup">
<!--ROW--><div class="lrow">
<span class="ldate"><span class="dnum">{{DAY}}</span><span class="dday">{{DOW}}</span></span>
<span class="ev-body"><span class="ev-title">{{SPACE}}</span><span class="ev-meta">{{META}}</span>
<span class="tag">Reserved</span></span>
</div><!--/ROW-->
</div><!--/ROWS-->
<p class="note">Reservations show the space and hours only. To reserve a space for yourself,
contact Leo in Resident Experiences.</p>'''

TEMPLATES = {
    "shell": SHELL,
    "signin": T_SIGNIN,
    "my": T_MY,
    "rsvp": T_RSVP,
    "register": T_REGISTER,
    "done": T_DONE,
    "msgstep": T_MSGSTEP,
    "board": T_BOARD,
    "spaces": T_SPACES,
}

import os
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "181fremont_residents_prototype.html"), "w", encoding="utf-8").write(HTML)
print("built resident site:", len(HTML), "bytes,", len(EVENTS), "events")
