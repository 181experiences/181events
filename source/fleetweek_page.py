# The Fleet Week page: a static, standalone resident page at /fleetweek.
# Linked from the calendar event's description and the resident email; the
# hero carries what The Residents' Club itself is doing, then a day-by-day
# cheat sheet of the city's week in native <details> folds (no JavaScript,
# per the resident doctrine), fun facts, and where to go.
#
# Schedule facts sourced from fleetweeksf.org, October 6, 2026. Edit here,
# rebuild, publish; never hand-edit site/.

def _day(title, note, items):
    rows = "\n".join(
        f'<div class="ev"><span class="tm">{t}</span><span class="wh">{w}</span></div>'
        for t, w in items)
    note_html = f'<div class="ours"><span class="dot"></span>{note}</div>' if note else ""
    return f"""<details>
<summary><span class="dy">{title}</span><span class="chev">&rsaquo;</span></summary>
<div class="dbody">
{note_html}{rows}
</div>
</details>"""


def page():
    days = [
        _day("Wednesday, October 7", None, [
            ("10:00 AM", "Ship tours begin: Pier 27 until 1:00, Pier 35 until 4:00. Free walk-aboard visits with the sailors and crews."),
            ("2:00 PM", "USAF Band of the Golden West at Ghirardelli Square"),
            ("3:00 PM", "Navy Band Southwest woodwinds at Grace Cathedral"),
            ("5:00 PM", "Military bands at Huntington Park, Japantown, and Pier 39"),
        ]),
        _day("Thursday, October 8", None, [
            ("10:00 AM", "Ship tours at Piers 27 and 35, until 4:00"),
            ("12:00 PM", "Navy Band Southwest at the Ferry Building back plaza"),
            ("6:00 PM", "Honor Our Fallen ceremony at the Marines&rsquo; Memorial"),
            ("7:00 PM", "Heroes Block Party with the Navy Band Destroyers"),
        ]),
        _day("Friday, October 9",
             "The Residents&rsquo; Club &middot; lemonade, water, and snacks for the air show &middot; noon to 4:00", [
            ("11:00 AM", "Parade of Ships along the waterfront, the fleet arriving under the Golden Gate"),
            ("12:00 PM", "Air show over the Bay until 4:00, flown between the Golden Gate Bridge and Alcatraz; the Blue Angels close the show"),
            ("All day", "Neighborhood concerts across the city"),
        ]),
        _day("Saturday, October 10",
             "The Residents&rsquo; Club &middot; lemonade, water, and snacks for the air show &middot; noon to 4:00", [
            ("10:00 AM", "K9 Heroes at Duboce Park, until 11:00"),
            ("10:00 AM", "Fleet Fest at Fisherman&rsquo;s Wharf until 7:00: live music, food, and a beer garden at the SkyStar Wheel, and the Service &amp; Safety Expo at Pier 27"),
            ("10:00 AM", "Ship tours at Piers 27 and 35, until 4:00"),
            ("12:00 PM", "Air show over the Bay until 4:00; the Blue Angels close the show"),
        ]),
        _day("Sunday, October 11",
             "The Residents&rsquo; Club &middot; lemonade, water, and snacks for the air show &middot; noon to 4:00", [
            ("10:00 AM", "Fleet Fest at the SkyStar Wheel, until 5:00"),
            ("10:00 AM", "Ship tours at Piers 27 and 35, until 4:00"),
            ("12:00 PM", "Air show over the Bay until 4:00; the Blue Angels close the final show of the year"),
            ("12:30 PM", "Fleet Week bands march in the Italian Heritage Parade, North Beach"),
        ]),
        _day("Monday, October 12", None, [
            ("9:00 AM", "Last ship tours: Pier 35 until noon"),
            ("9:00 AM", "High School Band Challenge at the Golden Gate Park Bandshell, until noon"),
        ]),
    ]
    days_html = "\n".join(days)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Fleet Week at The Residents&rsquo; Club &middot; 181 Fremont</title>
<meta name="description" content="Watch the Blue Angels from the Terrace, with lemonade and snacks from The Residents&rsquo; Club, plus a cheat sheet of everything happening across the city.">
<link rel="icon" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
  :root{{
    --ink:#16161a; --ink-body:#3a3a43; --ink-soft:#55555f;
    --paper:#f7f4ef; --paper-2:#fffdfa; --line:#ddd6cb;
    --red:#c41f26; --stone:#7a7266; --radius:4px;
  }}
  *{{box-sizing:border-box}}
  html,body{{margin:0;padding:0}}
  body{{background:var(--paper);color:var(--ink-body);
    font-family:'Hanken Grotesk',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    font-size:19px;line-height:1.6;
    padding:0 max(20px, env(safe-area-inset-left)) 60px max(20px, env(safe-area-inset-right))}}
  .wrap{{max-width:720px;margin:0 auto}}
  a{{color:var(--red)}}
  .back{{display:inline-block;margin:26px 0 8px;font-size:16px;color:var(--stone);text-decoration:none;min-height:54px;line-height:54px}}
  .back:hover{{color:var(--ink)}}

  .eyebrow{{font-size:clamp(11px,2.8vw,12.5px);letter-spacing:.22em;text-transform:uppercase;
    color:var(--stone);font-weight:600;margin:4px 0 10px}}
  h1{{font-family:'Marcellus',Georgia,serif;font-weight:400;color:var(--ink);
    font-size:clamp(32px,8vw,46px);line-height:1.12;margin:0 0 10px}}
  .tick{{width:76px;height:4px;background:var(--red);margin:18px 0 22px}}
  .lede{{font-size:clamp(17px,4.4vw,20px);color:var(--ink-soft);max-width:36em;margin:0 0 30px}}

  .hero{{background:var(--paper-2);border:1px solid var(--line);border-left:4px solid var(--red);
    border-radius:var(--radius);padding:clamp(20px,5vw,30px) clamp(20px,5vw,32px);margin:0 0 44px}}
  .hero h2{{font-family:'Marcellus',Georgia,serif;font-weight:400;color:var(--ink);
    font-size:clamp(23px,5.6vw,28px);margin:0 0 6px}}
  .hero .when{{font-size:clamp(15px,3.8vw,16.5px);letter-spacing:.06em;text-transform:uppercase;
    color:var(--red);font-weight:600;margin:0 0 14px}}
  .hero p{{margin:10px 0}}

  h2.sec{{font-family:'Marcellus',Georgia,serif;font-weight:400;color:var(--ink);
    font-size:clamp(24px,6vw,30px);margin:46px 0 6px;padding-top:26px;border-top:1px solid var(--line)}}
  .sd{{color:var(--ink-soft);margin:0 0 18px}}

  details{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);
    margin:0 0 10px;overflow:hidden}}
  summary{{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;
    gap:12px;min-height:54px;padding:6px 18px;font-family:'Marcellus',Georgia,serif;
    font-size:clamp(18px,4.8vw,21px);color:var(--ink)}}
  summary::-webkit-details-marker{{display:none}}
  summary:hover{{background:var(--paper)}}
  .chev{{color:var(--stone);font-size:26px;line-height:1;transition:transform .15s;flex:none}}
  details[open] .chev{{transform:rotate(90deg)}}
  details[open] summary{{border-bottom:1px solid var(--line)}}
  .dbody{{padding:14px 18px 18px}}
  .ev{{display:flex;gap:14px;padding:9px 0;border-top:1px solid var(--paper)}}
  .ev:first-of-type{{border-top:none}}
  .tm{{flex:none;width:86px;font-weight:600;color:var(--ink);font-size:16px;padding-top:2px}}
  .wh{{font-size:clamp(16px,4.2vw,17.5px)}}
  .ours{{display:flex;gap:10px;align-items:baseline;background:var(--paper);border:1px solid var(--line);
    border-radius:var(--radius);padding:10px 14px;margin:2px 0 12px;color:var(--ink);font-weight:600;
    font-size:clamp(15.5px,4vw,17px)}}
  .ours .dot{{flex:none;width:9px;height:9px;border-radius:50%;background:var(--red);position:relative;top:-1px}}

  ul.facts{{list-style:none;margin:0;padding:0}}
  ul.facts li{{position:relative;padding:7px 0 7px 22px}}
  ul.facts li::before{{content:"";position:absolute;left:0;top:.95em;width:8px;height:8px;background:var(--red)}}

  .place{{padding:14px 0;border-top:1px solid var(--line)}}
  .place:first-of-type{{border-top:none}}
  .place b{{color:var(--ink);font-weight:600}}
  .place .sub{{font-size:clamp(15.5px,4vw,17px);color:var(--ink-soft)}}

  footer{{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
    color:var(--stone);font-size:15px}}
  footer a{{color:var(--stone)}}
</style>
</head>
<body>
<div class="wrap">

<a class="back" href="/">&larr; Back to the calendar</a>

<div class="eyebrow">The Residents&rsquo; Club &middot; October 4 to 12</div>
<h1>Fleet Week 2026</h1>
<div class="tick"></div>
<p class="lede">The fleet is in, the bands are out, and the Blue Angels are back over the Bay.
Here is our plan for the show, and a resident&rsquo;s cheat sheet to the whole week.</p>

<div class="hero">
<h2>Watch the air show from the Terrace</h2>
<div class="when">Friday, October 9 to Sunday, October 11 &middot; Noon to 4:00 PM</div>
<p>The air show flies over the Bay from noon to 4:00 each day, and the Terrace looks right at it.
The Residents&rsquo; Club will be pouring <b>lemonade and ice water</b> through the show, with
<b>popcorn, chips, and snacks</b> set out alongside.</p>
<p>The <b>Blue Angels close the show each afternoon</b>, flying roughly 3:00 to 4:00; if you only
come up for one hour, that is the hour. No sign-up needed; just come up.</p>
</div>

<h2 class="sec">Your Fleet Week cheat sheet</h2>
<p class="sd">The week at a glance, from the city&rsquo;s official program. Tap a day to open it.</p>
{days_html}

<h2 class="sec">Worth knowing</h2>
<ul class="facts">
<li>San Francisco has hosted Fleet Week since 1981, and today it is one of the largest in the country.</li>
<li>The air show is flown over the water between the Golden Gate Bridge and Alcatraz, which is exactly the stretch the Terrace faces.</li>
<li>This year&rsquo;s lineup includes the U.S. Navy Blue Angels, the Air Force F-22 Raptor, the Marine Corps F-35B, the Patriots Jet Team, and a United Airlines 777 flying a fully choreographed demonstration.</li>
<li>Watching from Marina Green is free; so are the ship tours and nearly every event of the week.</li>
<li>Navy ships open their decks at Piers 27 and 35 every day from Wednesday through Monday; you can walk aboard and meet the crews.</li>
</ul>

<h2 class="sec">Where to go in the city</h2>
<div class="place"><b>Marina Green</b><br>
<span class="sub">The air show&rsquo;s festival center, Friday through Sunday. Free general admission, food, and the loudest seat in the house.</span></div>
<div class="place"><b>Fisherman&rsquo;s Wharf and the SkyStar Wheel</b><br>
<span class="sub">Fleet Fest on Saturday (10 to 7) and Sunday (10 to 5): live music, food, a beer garden, classic and military vehicles, and family activities.</span></div>
<div class="place"><b>Pier 27</b><br>
<span class="sub">The Service &amp; Safety Expo, Saturday and Sunday: first responders, live demonstrations, and equipment up close.</span></div>
<div class="place"><b>Piers 27 and 35</b><br>
<span class="sub">Ship tours, Wednesday through Monday. Lines move best in the morning.</span></div>
<div class="place"><b>A resident&rsquo;s tip</b><br>
<span class="sub">The waterfront is one long walk from the Ferry Building to the Wharf; skip the parking and take Muni or your feet. Afternoons turn cool when the fog comes to watch too, so bring a layer.</span></div>

<p style="margin-top:26px">Maps, the full program, and air show tickets:
<a href="https://fleetweeksf.org/" target="_blank" rel="noopener">fleetweeksf.org</a></p>

<footer>The Residents&rsquo; Club &middot; 181 Fremont &middot; questions, write to us through the
<a href="/">calendar&rsquo;s</a> Message page</footer>

</div>
</body>
</html>
"""
