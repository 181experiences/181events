#!/usr/bin/env python3
"""181 Fremont resident site — static, zero-JavaScript prototype.
All navigation, month switching, view toggles, day panels and RSVP states run on
CSS :checked selectors, so it works in any renderer including sandboxed previews."""

from urllib.parse import quote
from events_data import (EVENTS, MONTHS, MONTH_BY_KEY, dow_of, dow_s, month_name,
                         short_month, evs_on, days_with_events)

# picked by slug so ids can be regenerated freely
MY_RSVP_SLUGS = []  # populated once RSVPs are live
NEXT_SLUG = "book-club-inaugural"
GUEST_COUNTS = ["1", "2", "3", "4+"]

def plain(s):
    for a, b in [("&rsquo;", "'"), ("&amp;", "&"), ("&middot;", "-"), ("&mdash;", "-"),
                 ("<em>", ""), ("</em>", ""), ("—", "-")]:
        s = s.replace(a, b)
    return s

def slug(e):
    return plain(e["title"]).lower().replace(" ", "-").replace(":", "").replace("'", "")

def ics_href(e):
    m = MONTH_BY_KEY[e["m"]]["num"]
    eh = e["end"].split(":")[0]
    ehm = e["end"].split(":")[1].split(" ")[0]
    h24 = str((int(eh) % 12) + (12 if "PM" in e["end"] else 0)).zfill(2)
    body = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//181 Fremont//Resident Experiences//EN",
        "BEGIN:VEVENT", f"UID:181fremont-{e['id']}@181residents.com", "DTSTAMP:20260821T170000Z",
        f"DTSTART:2026{m:02d}{e['d']:02d}T{e['t24']}00",
        f"DTEND:2026{m:02d}{e['d']:02d}T{h24}{ehm}00",
        f"SUMMARY:{plain(e['title'])}", f"LOCATION:181 Fremont - {plain(e['loc'])}",
        f"DESCRIPTION:{plain(e['desc'][0])}", "END:VEVENT", "END:VCALENDAR"])
    return "data:text/calendar;charset=utf-8," + quote(body)

def tag_for(e):
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
for s in ["home", "cal", "rsvp", "msg"] + [f"ev{e['id']}" for e in EVENTS]:
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
for e in EVENTS:
    if e["rsvp"]:
        i = e["id"]
        rules.append(f'#rsvp{i}:checked ~ .ebody .rsvpbox{{display:block}}')
        rules.append(f'#rsvp{i}:checked ~ .ebody .rsvpbtn{{background:var(--ink);border-color:var(--ink)}}')
        rules.append(f'#rsvp{i}:checked ~ .ebody .rsvpbtn .s-off{{display:none}}')
        rules.append(f'#rsvp{i}:checked ~ .ebody .rsvpbtn .s-on{{display:inline}}')
        if e["rsvp"] == "guest":
            for gi, _ in enumerate(GUEST_COUNTS):
                rules.append(f'#g{i}-{gi}:checked ~ .ebody label[for="g{i}-{gi}"]'
                             '{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}')
GEN_CSS = "\n  ".join(rules)

# ------------------------------------------------------------------ month grids
def month_block(m):
    k, days, fd = m["key"], m["days"], m["first_dow"]
    cells = ['<div class="cell empty"></div>'] * fd
    for d in range(1, days + 1):
        evs = evs_on(k, d)
        dots = '<span class="dots">' + '<span class="dot"></span>' * min(len(evs), 3) + '</span>'
        if not evs:
            cells.append(f'<div class="cell plain"><span>{d}</span><span class="dots"></span></div>')
        elif len(evs) == 1:
            cells.append(f'<label class="cell has" for="r-ev{evs[0]["id"]}" '
                         f'aria-label="{dow_of(k,d)} {short_month(k)} {d}, 1 event"><span>{d}</span>{dots}</label>')
        else:
            cells.append(f'<label class="cell has" for="d-{k}-{d}" '
                         f'aria-label="{dow_of(k,d)} {short_month(k)} {d}, {len(evs)} events"><span>{d}</span>{dots}</label>')
    panels = []
    for d in days_with_events(k):
        evs = evs_on(k, d)
        if len(evs) < 2:
            continue
        rows = "".join(
            f'<label class="ev" for="r-ev{e["id"]}">'
            f'<span class="ev-time">{e["time"]}</span>'
            f'<span class="ev-body"><span class="ev-title">{e["title"]}</span>'
            f'<span class="ev-meta">{e["loc"]}</span>{tag_for(e)}</span>'
            f'<span class="ev-go">&rarr;</span></label>' for e in evs)
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
            rows.append(
                f'<label class="lrow{" marquee" if e["marquee"] else ""}" for="r-ev{e["id"]}">'
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
        facts += f'<div class="fact"><dt>RSVP by</dt><dd>{e["cutoff"]}</dd></div>'
    if e["series"]:
        facts += f'<div class="fact"><dt>Repeats</dt><dd>{e["series"]}</dd></div>'
    facts += f'<div class="fact"><dt>Hosted by</dt><dd>{e["host"]}</dd></div></dl>'

    checkbox = f'<input type="checkbox" class="state" id="rsvp{i}">' if e["rsvp"] else ''
    guest_radios = ""
    guest_ui = ""
    box = ""
    cta = '<div class="cta">'

    if e["rsvp"] == "guest":
        guest_radios = "".join(
            f'<input class="state" type="radio" name="g{i}" id="g{i}-{gi}"{" checked" if gi==0 else ""}>'
            for gi, _ in enumerate(GUEST_COUNTS))
        chips = "".join(f'<label class="gchip" for="g{i}-{gi}">{c}</label>'
                        for gi, c in enumerate(GUEST_COUNTS))
        guest_ui = ('<div class="guestbox"><div class="gq">Bringing someone from outside the building?</div>'
                    '<div class="gh">You&rsquo;re always welcome on your own, with no RSVP needed. We only ask for a '
                    'count of guests from outside the building, so we can pour and plate for them.</div>'
                    f'<div class="glab">How many guests</div><div class="gchips">{chips}</div></div>')
        cta += (f'<label class="btn rsvpbtn" for="rsvp{i}">'
                '<span class="s-off">Register my guests</span>'
                '<span class="s-on">Guests registered &check;</span></label>')
        box = ('<div class="rsvpbox"><h3>Thank you.</h3>'
               '<p>Your guests are on the list, and a confirmation is on its way to your email. '
               'If the numbers change, simply reply to that email.</p></div>')
    elif e["rsvp"] == "paid":
        cta += (f'<label class="btn rsvpbtn" for="rsvp{i}">'
                f'<span class="s-off">{e["price"]} &middot; Reserve my seat</span>'
                '<span class="s-on">Seat reserved &check;</span></label>')
        box = ('<div class="rsvpbox"><h3>Your seat is held.</h3>'
               '<p>Payment of $75 completes the reservation. You&rsquo;ll be taken to a secure checkout, and a '
               'receipt and confirmation will follow by email. Seats are released if payment isn&rsquo;t '
               'completed within 48 hours.</p></div>')
    elif e["rsvp"] == "standard":
        cta += (f'<label class="btn rsvpbtn" for="rsvp{i}">'
                '<span class="s-off">RSVP for this Event</span>'
                '<span class="s-on">You&rsquo;re going &check;</span></label>')
        cutoff_line = (f' If your plans change, please let us know by {e["cutoff"]}, as that is when we '
                       'order materials.') if e["cutoff"] else ''
        box = ('<div class="rsvpbox"><h3>You&rsquo;re on the list.</h3>'
               '<p>A confirmation is on its way to your email, and we&rsquo;ll send a reminder the day before.'
               + cutoff_line + ' To cancel, simply reply to that email.</p></div>')

    cta += (f'<a class="btn ghost" href="{ics_href(e)}" download="{slug(e)}.ics">Add to My Calendar</a></div>')

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

EVENT_SCREENS = "".join(event_screen(e) for e in EVENTS)

# ------------------------------------------------------------------ my rsvps
rsvp_rows = "".join(
    f'<div class="lgroup"><label class="lrow" for="r-ev{e["id"]}">'
    f'<span class="ldate"><span class="dnum">{e["d"]}</span><span class="dday">{dow_s(e["m"],e["d"])}</span></span>'
    f'<span class="ev-body"><span class="ev-title">{e["title"]}</span>'
    f'<span class="ev-meta">{short_month(e["m"])} {e["d"]} &middot; {e["time"]} &middot; {e["loc"]}</span>'
    f'<span class="tag open">You&rsquo;re going</span></span>'
    f'<span class="ev-go">&rarr;</span></label></div>'
    for e in EVENTS if e["slug"] in MY_RSVP_SLUGS)

NEXT = next(e for e in EVENTS if e["slug"] == NEXT_SLUG)

# ------------------------------------------------------------------ month nav
MONTH_RADIOS = "\n    ".join(
    f'<input class="state" type="radio" name="mon" id="m-{m["key"]}"{" checked" if i == 0 else ""}>'
    for i, m in enumerate(MONTHS))

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

  header.masthead{{border-bottom:1px solid var(--line);background:var(--paper-2)}}
  .masthead-inner{{max-width:940px;margin:0 auto;padding:18px var(--pad);display:flex;align-items:center;justify-content:space-between;gap:16px}}
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
  .quad{{display:grid;grid-template-columns:1fr 1fr;gap:14px;max-width:620px;margin:0 auto;padding-bottom:70px}}
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
  .stickybar{{position:sticky;top:0;z-index:40;background:var(--paper);border-bottom:1px solid var(--line);
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

  .guestbox{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:24px;margin:8px 0 26px}}
  .gq{{font-family:var(--fd);font-size:24px;color:var(--ink);line-height:1.25}}
  .gh{{font-size:17px;color:var(--ink-soft);margin-top:8px}}
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
  #i-idea:checked ~ .msgform .choice[data-k="idea"],
  #i-plan:checked ~ .msgform .choice[data-k="plan"],
  #i-other:checked ~ .msgform .choice[data-k="other"]{{border-color:var(--red);border-left-width:3px;background:#fffaf9}}
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
  .mocknote{{background:#16161a;color:#c9c2b6;font-size:13px;letter-spacing:.1em;text-align:center;padding:11px 16px;text-transform:uppercase}}
</style>
</head>
<body>

<div class="mocknote">Preview &middot; RSVPs open soon, the message button already works</div>

<header class="masthead">
  <div class="masthead-inner">
    <label class="logo" for="r-home">181 Fremont<small>Resident Events</small></label>
    <div class="whoami">Welcome<strong>Residents&rsquo; Club</strong></div>
  </div>
</header>

<input class="state" type="radio" name="scr" id="r-home" checked>
<input class="state" type="radio" name="scr" id="r-cal">
<input class="state" type="radio" name="scr" id="r-rsvp">
<input class="state" type="radio" name="scr" id="r-msg">
{"".join(f'<input class="state" type="radio" name="scr" id="r-ev{e["id"]}">' for e in EVENTS)}

<div class="screens">

  <section class="screen" id="scr-home">
    <div class="wrap">
      <div class="hero">
        <div class="eyebrow">August to December 2026</div>
        <h1>What&rsquo;s happening<br>at 181 Fremont</h1>
        <div class="rule"></div>
        <p>Everything on the calendar, in one place.</p>
      </div>
      <div class="quad">
        <label class="sq dark" for="r-cal">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><circle cx="8.5" cy="14.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="12" cy="14.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="15.5" cy="17.6" r="1.1" fill="currentColor" stroke="none"/></svg></span>
          <span class="label">Calendar</span><span class="sub">Month &amp; list</span>
        </label>
        <label class="sq" for="r-ev{NEXT["id"]}">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5.4l3.4 2"/></svg></span>
          <span class="label">Next Event</span><span class="sub">{dow_s(NEXT["m"],NEXT["d"])}, {short_month(NEXT["m"])} {NEXT["d"]}</span>
        </label>
        <label class="sq" for="r-rsvp">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8.2 12.4l2.6 2.6 5-5.4"/></svg></span>
          <span class="badge">{len(MY_RSVP_SLUGS)}</span>
          <span class="label">My RSVPs</span><span class="sub">{(str(len(MY_RSVP_SLUGS)) + " coming up") if MY_RSVP_SLUGS else "Coming soon"}</span>
        </label>
        <label class="sq" for="r-msg">
          <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/></svg></span>
          <span class="label">Message</span><span class="sub">Ideas &amp; requests</span>
        </label>
      </div>
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

    <div class="listwrap"><div class="wrap">{LIST}<div style="height:70px"></div></div></div>
  </section>

  <section class="screen" id="scr-rsvp">
    <div class="wrap">
      <label class="back" for="r-home">&larr; Back</label>
      <div class="msg-intro"><h2>My RSVPs</h2>
        <p>The events you&rsquo;re signed up for. To cancel, simply reply to your confirmation email.</p></div>
      <div style="height:18px"></div>
      {rsvp_rows or '<p class="prefill">Once RSVPs go live, the events you sign up for will be listed here.</p>'}
      <div style="height:80px"></div>
    </div>
  </section>

  <section class="screen" id="scr-msg">
    <form class="msgform" action="mailto:leonardo@181sf.com?subject=Note%20from%20a%20181%20Fremont%20resident" method="post" enctype="text/plain">
    <input class="state" type="radio" name="Topic" value="Share an idea" id="i-idea" checked>
    <input class="state" type="radio" name="Topic" value="Plan an event with us" id="i-plan">
    <input class="state" type="radio" name="Topic" value="Something else" id="i-other">

    <div class="msgform"><div class="wrap">
      <label class="back" for="r-home">&larr; Back</label>
      <div class="msg-intro">
        <h2>Message Resident Experiences</h2>
        <p>Have an idea for an event? Want to plan something of your own? Tell us here and we&rsquo;ll get back to you within one business day.</p>
      </div>
      <div class="choices">
        <label class="choice" data-k="idea" for="i-idea">
          <span class="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.5.4.8 1 .8 1.6h5.4c0-.6.3-1.2.8-1.6A6 6 0 0 0 12 3z"/></svg></span>
          <span><span class="ct">Share an idea</span><span class="cs">Something you&rsquo;d like to see us host</span></span>
        </label>
        <label class="choice" data-k="plan" for="i-plan">
          <span class="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20"/><circle cx="10" cy="8" r="3.4"/><path d="M17.5 11.5h4M19.5 9.5v4"/></svg></span>
          <span><span class="ct">Plan an event with us</span><span class="cs">Book a one-on-one with Leo to plan your own gathering</span></span>
        </label>
        <label class="choice" data-k="other" for="i-other">
          <span class="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 1 1-3.2-6.4"/><path d="M8 11.5l2.8 2.8L21 5"/></svg></span>
          <span><span class="ct">Something else</span><span class="cs">Feedback on a past event, a question, anything</span></span>
        </label>
      </div>
      <div class="flabel idea">Your idea</div>
      <div class="flabel plan">What would you like to plan?</div>
      <div class="flabel other">Your message</div>
      <textarea name="Message" placeholder="Type here&hellip;"></textarea>
      <div class="fields">
        <label class="field"><span>Your name</span><input type="text" name="Name" autocomplete="name" autocapitalize="words" placeholder="Optional"></label>
        <label class="field"><span>Unit</span><input type="text" name="Unit" autocomplete="off" autocapitalize="characters" inputmode="text" placeholder="Optional"></label>
        <label class="field" style="grid-column:1/-1"><span>Email, if you&rsquo;d like a reply</span><input type="email" name="Email" autocomplete="email" autocapitalize="none" inputmode="email" placeholder="Optional"></label>
      </div>
      <div class="cta"><button class="btn" type="submit">Send to Resident Experiences</button></div>
      <p class="mailnote">Your mail app will open with the note ready to send, so the reply reaches the address you send from. If nothing opens, write to <a href="mailto:leonardo@181sf.com">leonardo@181sf.com</a>.</p>
      <div class="routing"><strong>Building maintenance or a service issue?</strong> Please contact the front desk or Action Life directly. This inbox is monitored during Resident Experiences hours only.</div>
      <div style="height:80px"></div>
    </div></div>
    </form>
  </section>

  {EVENT_SCREENS}

</div>

<footer>181 Fremont Residences &middot; Resident Experiences &middot; Questions? Leo at Level 39</footer>
</body>
</html>
'''

import os
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "181fremont_residents_prototype.html"), "w", encoding="utf-8").write(HTML)
print("built resident site:", len(HTML), "bytes,", len(EVENTS), "events")
