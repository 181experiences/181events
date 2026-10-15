#!/usr/bin/env python3
"""Friendsgiving Potluck: the residents' page for the evening, MOCKUP.

One screen. The photograph, the facts, one paragraph, the four kinds of
dish, one button. The sign-up itself lives on the calendar RSVP page (the
potluck board), so the button points there. Script-free, nothing to run.
Run: python build_fg_mockup.py -> index.html
"""
import html, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
e = html.escape
RSVP = "https://181residents.com/e/friendsgiving-happy-hour"
ICS = "https://181residents.com/ics/2026-11-19_friendsgiving-happy-hour.ics"

CSS = r'''
:root{--bark:#2a170c;--cream:#f6ead8;--parch:#efdcc1;--soft:#d9c3a3;--rust:#c9742b;--ember:#e28a2d;--line:rgba(226,138,45,.3)}
*{box-sizing:border-box}
body{margin:0;background:var(--bark);color:var(--cream);font-family:Georgia,"Times New Roman",serif;font-size:19px;line-height:1.55}
a{color:var(--ember)}
.mocknote{background:#1b3a6b;color:#fff;text-align:center;font-family:Arial,sans-serif;font-size:12px;letter-spacing:.14em;text-transform:uppercase;padding:7px}
.hero img{display:block;width:100%;height:auto;aspect-ratio:9/16;object-fit:cover}
@media(min-width:820px){.hero img{aspect-ratio:16/9;max-height:620px}}
.wrap{max-width:720px;margin:0 auto;padding:36px clamp(16px,4vw,40px) 60px}
h1{font-weight:400;margin:0 0 6px;font-size:clamp(34px,6vw,52px);line-height:1.05;color:var(--parch)}
.facts{font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:var(--ember);margin:0 0 26px;line-height:1.9}
p{margin:0 0 18px;color:var(--soft)}
p b{color:var(--cream);font-weight:400}
.kinds{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:6px 0 30px}
@media(max-width:520px){.kinds{grid-template-columns:repeat(2,1fr)}}
.kinds div{border:1px solid var(--line);padding:14px 8px;text-align:center}
.kinds b{display:block;font-weight:400;font-size:21px;color:var(--parch)}
.kinds span{display:block;font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.06em;color:var(--soft);margin-top:4px}
.btn{display:inline-flex;align-items:center;min-height:54px;padding:0 26px;background:var(--rust);color:#fff;text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.22em;text-transform:uppercase;font-weight:700;border-radius:3px}
.btn.ghost{background:transparent;color:var(--parch);border:1px solid var(--ember)}
.btnrow{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:30px}
.small{font-size:16px;color:var(--soft)}
.tiny{font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--soft);margin-top:40px}
'''

BODY = f'''<div class="hero">
<picture><source media="(min-width: 820px)" srcset="img/hero-land.jpg"><img src="img/hero-port.jpg" alt="The Friendsgiving table at The Residents&rsquo; Club"></picture>
</div>
<div class="wrap">
  <h1>Friendsgiving Potluck</h1>
  <div class="facts">Thursday, November 19 &middot; 5:30 to 7:30 PM<br>The Residents&rsquo; Club<br>RSVP by Monday, November 16</div>
  <p><b>The Club brings the turkey and the ham.</b> You bring one dish to share, in one of four kinds, and we set the table together. No dish? Come anyway.</p>
  <div class="kinds">
    <div><b>Main</b><span>a second centerpiece</span></div>
    <div><b>Side</b><span>stuffing, potatoes, greens</span></div>
    <div><b>Dessert</b><span>pie, or what beats pie</span></div>
    <div><b>Drink</b><span>a bottle or a pitcher</span></div>
  </div>
  <div class="btnrow"><a class="btn" href="{RSVP}">RSVP and sign up your dish</a><a class="btn ghost" href="{ICS}">Add to my calendar</a></div>
  <p class="small">When you RSVP, pick the kind and name the dish. The page shows what neighbors have signed up so far, so no two tables bring the same thing. Bring it ready to serve, in its own dish with its own spoon, enough for eight to ten.</p>
  <p class="tiny">181 Fremont Residences &middot; Resident Experiences</p>
</div>'''

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Friendsgiving Potluck &middot; 181 Fremont</title>
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#2a170c">
<style>{CSS}</style>
</head>
<body>
__MOCKNOTE__
{BODY}
</body>
</html>'''

MOCKNOTE = '<div class="mocknote">Mockup &middot; nothing here is published</div>'

def render(live=False):
    """The page as HTML. live=True drops the mock banner; img/ paths stay relative."""
    return HTML.replace("__MOCKNOTE__", "" if live else MOCKNOTE)

IMAGES = sorted(set(re.findall(r"img/([a-z0-9-]+[.]jpg)", HTML)))

if __name__ == "__main__":
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(render(False))
    print("built index.html", len(HTML), "bytes;", len(IMAGES), "images")
