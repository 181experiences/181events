#!/usr/bin/env python3
"""Lights, Camera, Gala: the residents' style and inspiration guide, MOCKUP.

A standalone page in its own skin (not the calendar's), built from the photo
set in img/. Script-free like every resident page: the lightbox is a :target
overlay, the folds are <details>, the reels are scroll-snap strips with
per-slide arrows. Run: python build_gala_mockup.py -> index.html
"""
import html, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
e = html.escape
RSVP = "https://181residents.com/rsvp/2026-12-18_lights-camera-gala"

# ---------------------------------------------------------------- the pictures
# Four sources, one reel each for her and for him: the color set (lady, guys),
# the sepia set (women, men), the new color grids (cw, cm), and the heritage
# looks cut from the portrait grid (hp). Interleaved so the color pops land
# among the sepia, and nobody is filed separately.
LADY = [("lady01", "Satin, a stole, and one great clutch"), ("lady02", "Black velvet, back view, opera gloves"),
        ("lady03", "Draped velvet and three strands of pearls"), ("lady04", "The flapper: beads, bandeau, fur"),
        ("lady05", "Halter satin beside a black tie"), ("lady06", "Off the shoulder, pearls at the throat"),
        ("lady07", "Beaded gown, fur over the arm"), ("lady08", "Dark gloves, dark fur, red lip"),
        ("lady09", "Fringe and a feathered headband")]
WOMEN = [("women01", "Bias-cut satin, open back"), ("women02", "A coupe and long gloves"), ("women03", "Beaded sheath, fur stole"),
         ("women04", "Halter neck, hair pinned"), ("women05", "Velvet with gloves, a brooch"), ("women06", "A hat with a veil"),
         ("women07", "Strapless, one silk flower"), ("women08", "Beaded jacket, pearls, a coupe"), ("women09", "Beaded back, finger waves"),
         ("women10", "Fur and a double strand"), ("women11", "The sleek updo"), ("women12", "Brocade cheongsam and pearls")]
CW = [("cw01", "Red velvet, white fur"), ("cw02", "Black satin, gloves, a coupe"), ("cw03", "Champagne beading, fur stole"),
      ("cw04", "Black halter, bare back"), ("cw05", "Emerald velvet and a brooch"), ("cw06", "A black hat with a veil"),
      ("cw07", "Strapless red with a silk flower"), ("cw08", "Black and gold beading"), ("cw09", "Beaded champagne, fur, a hair comb"),
      ("cw10", "Off the shoulder, pearls"), ("cw11", "Emerald velvet halter"), ("cw12", "Red beading, open back"),
      ("cw13", "Black velvet and a lace shawl"), ("cw14", "Champagne satin, long gloves"), ("cw15", "Navy beading, dark fur"),
      ("cw16", "Champagne beaded gown")]
HP_W = [("hp01", "A beaded cape, back view"), ("hp02", "Burgundy velvet, long gloves"), ("hp03", "Ivory embroidered sari, gold clutch"),
        ("hp04", "Black embroidered sari, pearls"), ("hp05", "Burgundy sari, emeralds"), ("hp06", "Black sari, three strands")]
GUYS = [("guys01", "The black tuxedo, pocket square white"), ("guys02", "The white dinner jacket"), ("guys03", "Pinstripe double-breast and a fedora"),
        ("guys04", "Peak lapels, a watch, a cufflink"), ("guys06", "Shawl collar, drink in hand"), ("guys07", "Tweed three-piece, hat tipped"),
        ("guys10", "Silver hair, black tie, a coupe"), ("guys11", "Suspenders and a loosened tie"), ("guys12", "Cummerbund and a slim bow"),
        ("guys13", "Hat, overcoat, the velvet rope")]
MEN = [("men01", "Black tie, peak lapel"), ("men02", "White dinner jacket, whisky"), ("men03", "Pinstripe and a fedora"), ("men04", "Black tie, in profile"),
       ("men05", "Shawl collar, silver at the temples"), ("men06", "Brown three-piece by the car"), ("men07", "Black tie, a coupe, a smile"),
       ("men08", "Grey tweed, a hat"), ("men09", "Suspenders, tie loosened"), ("men10", "Tuxedo, whisky, no hurry"), ("men11", "Spectacles and a double-breast"),
       ("men12", "Silver hair, black tie"), ("men13", "Pinstripe, fedora, night"), ("men14", "Fixing the cuff"), ("men15", "White dinner jacket at the bar"),
       ("men16", "A patterned tie and the flashbulbs")]
CM = [("cm01", "Black tuxedo, whisky"), ("cm02", "White dinner jacket, a coupe"), ("cm03", "Pinstripe and a fedora"), ("cm04", "Burgundy velvet dinner jacket"),
      ("cm05", "Black tie, cummerbund"), ("cm06", "Tweed three-piece, watch chain"), ("cm07", "Black tie, a laugh"), ("cm08", "Grey tweed, red tie, a hat"),
      ("cm09", "White dinner jacket, seated"), ("cm10", "Burgundy velvet, shawl collar"), ("cm11", "Spectacles and black tie"), ("cm12", "Navy pinstripe, paisley tie"),
      ("cm13", "Black tie and a coupe"), ("cm14", "Green velvet dinner jacket"), ("cm15", "White jacket and suspenders"), ("cm16", "Silver hair, black tie, a coupe")]
HP_M = [("hp07", "Black tuxedo"), ("hp08", "White dinner jacket, a coupe"), ("hp09", "Pinstripe three-piece"),
        ("hp10", "Black tie, silver moustache"), ("hp11", "Spectacles and pinstripe"), ("hp12", "White dinner jacket, a beard")]

def interleave(*lists):
    out, i = [], 0
    while True:
        added = False
        for L in lists:
            if i < len(L): out.append(L[i]); added = True
        if not added: break
        i += 1
    return out

HER = interleave(CW, LADY, WOMEN, HP_W)
HIM = interleave(CM, GUYS, MEN, HP_M)
VIBE = [("vibe01", "The red carpet", "Arrive like it is a premiere."), ("vibe02", "Shrimp cocktail", "Stacked on silver, lemon and ice."),
        ("vibe03", "The silent film lounge", "Black and white on the big screen, low lamps, deep chairs."),
        ("vibe04", "The carving station", "Prime rib, a side of salmon, carved to order."), ("vibe05", "Coupes and pearls", "Champagne the old way."),
        ("vibe06", "Live music", "Piano, bass and horn, all night."), ("vibe07", "The Residents’ Club at night", "Lit for the occasion."),
        ("vibe08", "Lights, camera", "A camera, a coupe, a feather.")]
BIG = [("moodboard", "The moodboard: the whole evening on one board"), ("banquet", "The banquet, the bar, the house"),
       ("heromix", "The studio reference sheet"), ("vibe-all", "The scene, all together")]

def fig(stem, cap="", cls=""):
    return (f'<figure class="ph {cls}"><a href="#lb-{stem}"><img src="img/{stem}.jpg" alt="{e(cap)}" loading="lazy"></a>'
            f'{f"<figcaption>{e(cap)}</figcaption>" if cap else ""}</figure>')

def reel(items, key):
    n = len(items)
    slides = []
    for i, (stem, cap) in enumerate(items):
        prev = f"{key}-{(i - 1) % n + 1:02d}"; nxt = f"{key}-{(i + 1) % n + 1:02d}"
        slides.append(f'<figure class="slide" id="{key}-{i + 1:02d}"><div class="pic"><a href="#lb-{stem}"><img src="img/{stem}.jpg" alt="{e(cap)}"></a>'
                      f'<a class="arr l" href="#{prev}" aria-label="Previous">&lsaquo;</a><a class="arr r" href="#{nxt}" aria-label="Next">&rsaquo;</a></div>'
                      f'<figcaption><span>{e(cap)}</span><i>{i + 1} / {n}</i></figcaption></figure>')
    return (f'<div class="reel" id="reel-{key}"><div class="track">{"".join(slides)}</div>'
            f'<div class="reelhint">Use the arrows, or swipe &middot; tap the picture to see it large</div>'
            f'<details class="seeall"><summary>See all {n} looks at once</summary><div class="gal tall">'
            + "".join(fig(s, c) for s, c in items) + '</div></details></div>')

def lightboxes(items):
    seen = set(); items = [it for it in items if not (it[0] in seen or seen.add(it[0]))]
    return "".join(f'<div class="lb" id="lb-{s}"><a class="lbbg" href="#shut" aria-label="Close"></a><a class="lbx" href="#shut" aria-label="Close">&times;</a>'
                   f'<img src="img/{s}.jpg" alt="{e(c)}">{f"<p>{e(c)}</p>" if c else ""}</div>' for s, c in items)

CSS = r'''
:root{--night:#0b0908;--night2:#141008;--ink:#f3e9d6;--soft:#c9b89a;--gold:#d2ab63;--gold2:#a88244;--champ:#efdcb6;--velvet:#8b1e24;--line:rgba(210,171,99,.28)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--night);color:var(--ink);font-family:Georgia,"Times New Roman",serif;font-size:18px;line-height:1.55;
  background-image:radial-gradient(1200px 600px at 50% -10%,rgba(210,171,99,.14),transparent 60%)}
a{color:var(--gold)}
.mocknote{background:#1b3a6b;color:#fff;text-align:center;font-family:Arial,sans-serif;font-size:12px;letter-spacing:.14em;text-transform:uppercase;padding:7px}
.wrap{max-width:1120px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
.eyebrow{font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.32em;text-transform:uppercase;color:var(--gold)}
h1,h2,h3{font-weight:400;margin:0}
h2{font-size:clamp(30px,5vw,48px);line-height:1.05;letter-spacing:.02em;color:var(--champ)}
h3{font-size:clamp(21px,3vw,26px);color:var(--champ)}
p{margin:0 0 16px;color:var(--soft)}
p b,li b{color:var(--ink);font-weight:400}
.bulbs{height:14px;background:radial-gradient(circle at 7px 7px,#ffe9a8 0 3px,#f0b64a 3.5px 4.5px,transparent 5px) 0 0/22px 14px repeat-x;opacity:.9}
nav.chapters{position:sticky;top:0;z-index:20;background:rgba(11,9,8,.92);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
nav.chapters .in{max-width:1120px;margin:0 auto;display:flex;gap:4px;overflow-x:auto;padding:0 12px;scrollbar-width:none}
nav.chapters a{flex:none;display:inline-block;padding:16px 14px;font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--soft);text-decoration:none;border-bottom:2px solid transparent}
nav.chapters a:hover{color:var(--champ);border-bottom-color:var(--gold)}
nav.chapters a.rsvp{margin-left:auto;color:var(--night);background:var(--gold);border-radius:3px;padding:10px 16px;margin-top:9px;margin-bottom:9px;font-weight:700}
.hero{position:relative;width:100%;border-bottom:1px solid var(--line)}
.hero img{display:block;width:100%;height:auto;aspect-ratio:9/16;object-fit:cover;object-position:50% 0}
.hero .veil{display:none}
.hero .copy{padding:30px 0 40px}
@media(min-width:820px){.hero img{aspect-ratio:16/9;max-height:820px}.hero .copy{padding:38px 0 46px}}
@media(max-width:819px){.hero .lede{font-size:clamp(21px,5.6vw,26px)}}
.hero h1{font-size:clamp(14px,2vw,18px);font-family:Arial,Helvetica,sans-serif;letter-spacing:.36em;text-transform:uppercase;color:var(--gold);margin-bottom:14px}
.hero .lede{font-size:clamp(22px,3.4vw,34px);line-height:1.2;color:var(--champ);max-width:22em;margin:0 0 22px}
.facts{display:flex;flex-wrap:wrap;gap:10px 28px;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);margin-bottom:26px}
.facts span b{color:var(--gold);font-weight:400;margin-right:8px}
.btn{display:inline-flex;align-items:center;min-height:54px;padding:0 26px;background:var(--gold);color:var(--night);text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.22em;text-transform:uppercase;font-weight:700;border-radius:3px}
.btn.ghost{background:transparent;color:var(--champ);border:1px solid var(--gold)}
.btnrow{display:flex;gap:12px;flex-wrap:wrap}
section.ch{padding:72px 0 56px;border-bottom:1px solid var(--line)}
.deco{display:flex;align-items:center;gap:18px;margin:0 0 30px}
.deco:before,.deco:after{content:"";flex:1;height:1px;background:linear-gradient(90deg,transparent,var(--gold2),transparent)}
.deco span{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.4em;text-transform:uppercase;color:var(--gold)}
.lead{font-size:clamp(19px,2.4vw,24px);line-height:1.45;color:var(--ink);max-width:34em;margin:14px 0 28px}
.two{display:grid;grid-template-columns:1.1fr .9fr;gap:40px;align-items:start}
.two>*{min-width:0}
@media(max-width:820px){.two{grid-template-columns:1fr}}
.ph{margin:0;background:#1a1510;border:1px solid var(--line);padding:6px;min-width:0;max-width:100%}
.ph img{display:block;width:100%;height:100%;max-width:100%;object-fit:cover;filter:sepia(.08) contrast(1.02);transition:filter .25s}
.ph a{display:block;height:100%}
.ph:hover img{filter:none}
.ph figcaption{font-family:Arial,Helvetica,sans-serif;font-size:11.5px;letter-spacing:.08em;color:var(--soft);padding:8px 4px 4px;line-height:1.4}
.gal{display:grid;gap:14px}
.gal>*{min-width:0}
.gal.tall{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.gal.tall .ph{aspect-ratio:1/1.9;display:flex;flex-direction:column}
.gal.tall .ph a{flex:1;min-height:0}
.gal.wide{grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.gal.wide .ph a{aspect-ratio:4/3;height:auto;width:100%}
/* reels */
.reel{margin:6px auto 10px;max-width:560px}
.track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.track::-webkit-scrollbar{display:none}
.slide{flex:0 0 100%;width:100%;margin:0;scroll-snap-align:start;scroll-margin-top:110px;background:#1a1510;border:1px solid var(--line);padding:8px}
.slide .pic{position:relative}
.slide .pic>a{display:block}
.slide img{display:block;width:100%;aspect-ratio:3/4;object-fit:cover;object-position:50% 10%}
.slide .arr{position:absolute;top:50%;transform:translateY(-50%);width:54px;height:54px;border-radius:50%;background:rgba(11,9,8,.72);border:1px solid var(--gold);color:var(--champ);
  display:flex;align-items:center;justify-content:center;text-decoration:none;font-size:34px;line-height:1;font-family:Georgia,serif}
.slide .arr.l{left:12px}.slide .arr.r{right:12px}
.slide .arr:hover{background:var(--gold);color:var(--night)}
.slide figcaption{display:flex;justify-content:space-between;align-items:center;gap:10px;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.06em;color:var(--champ);padding:12px 6px 4px;line-height:1.35}
.slide figcaption i{font-style:normal;color:var(--gold);letter-spacing:.12em;font-size:11px;flex:none}
.reelhint{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold2);margin:10px 0 8px;text-align:center}
.hairrow{display:flex;gap:14px;margin:8px 0 26px}
.hairrow .ph{flex:1;min-width:0}
.hairrow .ph a{aspect-ratio:3/4;height:auto;width:100%}
details.seeall summary{cursor:pointer;list-style:none;font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);padding:10px 0;min-height:44px;display:flex;align-items:center;gap:10px}
details.seeall summary::-webkit-details-marker{display:none}
details.seeall summary:before{content:"+";font-size:20px;color:var(--gold)}
details.seeall[open] summary:before{content:"\2013"}
details.seeall .gal{margin-bottom:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.card{background:linear-gradient(180deg,#171209,#120e08);border:1px solid var(--line);padding:0 0 14px}
.card img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover}
.card h3{font-size:20px;padding:14px 16px 2px}
.card p{padding:0 16px;font-size:15.5px;margin:0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 24px}
.chip{border:1px solid var(--gold2);color:var(--champ);border-radius:100px;padding:8px 14px;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.06em}
.chip.v{border-color:var(--velvet);background:rgba(139,30,36,.25)}
.sw{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin:16px 0 30px}
.sw div{border:1px solid var(--line);padding:6px}
.sw i{display:block;height:64px}
.sw b{display:block;font-family:Arial,Helvetica,sans-serif;font-weight:400;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);padding:8px 2px 2px}
.ways{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin:10px 0 30px}
.way{border:1px solid var(--line);padding:22px 22px 18px;background:rgba(210,171,99,.04)}
.way .n{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.3em;text-transform:uppercase;color:var(--gold);margin-bottom:8px}
.way h3{margin-bottom:8px}
.way ul{margin:0;padding-left:18px;color:var(--soft);font-size:16px}
.way li{margin-bottom:4px}
.film{height:34px;margin:0;background:
  linear-gradient(90deg,transparent 0 6px,#2a2117 6px 16px,transparent 16px 26px) 0 0/26px 8px repeat-x,
  linear-gradient(90deg,transparent 0 6px,#2a2117 6px 16px,transparent 16px 26px) 0 100%/26px 8px repeat-x,
  linear-gradient(#171209,#171209) 0 8px/100% 18px no-repeat,#0e0b08}
.heritage{border:1px solid var(--line);background:rgba(210,171,99,.05);padding:22px 24px;margin:28px 0 6px}
.heritage h3{margin-bottom:8px}
.heritage p{margin-bottom:0}
details.q{border-top:1px solid var(--line);padding:0}
details.q:last-of-type{border-bottom:1px solid var(--line)}
details.q summary{cursor:pointer;list-style:none;padding:18px 0;font-size:clamp(18px,2.4vw,22px);color:var(--champ);display:flex;justify-content:space-between;gap:16px;min-height:54px;align-items:center}
details.q summary::-webkit-details-marker{display:none}
details.q summary:after{content:"+";color:var(--gold);font-size:26px}
details.q[open] summary:after{content:"\2013"}
details.q .a{padding:0 0 20px;max-width:40em}
.lb{display:none;position:fixed;inset:0;z-index:50;background:rgba(5,4,3,.94);align-items:center;justify-content:center;flex-direction:column;padding:28px 16px}
.lb:target{display:flex}
.lb img{max-width:min(96vw,900px);max-height:84vh;border:1px solid var(--line)}
.lb p{color:var(--champ);margin:14px 0 0;font-size:16px}
.lb .lbbg{position:absolute;inset:0}
.lb img,.lb p{position:relative}
#shut{position:fixed;top:0;left:0;width:1px;height:1px}
.lb .lbx{position:absolute;top:14px;right:18px;color:var(--champ);font-size:44px;text-decoration:none;line-height:1;min-width:54px;min-height:54px;display:flex;align-items:center;justify-content:center}
footer{padding:50px 0 70px;text-align:center;color:var(--soft);font-size:15px}
footer .eyebrow{display:block;margin-bottom:14px}
.tiny{font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--soft)}
@media(max-width:620px){section.ch{padding:48px 0 36px}.hero .copy{padding:40px 0 34px}.gal.tall{grid-template-columns:repeat(2,1fr)}}
'''

def section(id_, deco, title, body):
    return f'<section class="ch" id="{id_}"><div class="wrap"><div class="deco"><span>{deco}</span></div><h2>{title}</h2>{body}</div></section>'

def chips(items, cls=""):
    return '<div class="chips">' + "".join(f'<span class="chip {cls}">{e(i)}</span>' for i in items) + "</div>"

HERO = f'''<div class="hero" id="top">
<picture><source media="(min-width: 820px)" srcset="img/hero-land.jpg"><img src="img/hero-port.jpg" alt="Lights, Camera, Gala, The Residents&rsquo; Club"></picture>
<div class="veil"></div>
<div class="wrap copy">
  <h1>Friday, December 18 &middot; The holiday gala</h1>
  <p class="lede">Our end-of-year party, and the one evening the whole building comes together. A red-carpet gala in the spirit of Old Hollywood.</p>
  <div class="facts"><span><b>When</b>6:30 to 9:00 PM</span><span><b>Where</b>The Residents&rsquo; Club</span><span><b>Dress</b>Black tie if you have it</span><span><b>RSVP by</b>Monday, December 7</span></div>
  <div class="btnrow"><a class="btn" href="{RSVP}">RSVP on the calendar</a><a class="btn ghost" href="#look">The dress code, decoded</a></div>
</div></div>'''

NAV = f'''<nav class="chapters"><div class="in">
<a href="#evening">The evening</a><a href="#look">The look</a><a href="#her">For her</a><a href="#him">For him</a><a href="#touches">Finishing touches</a><a href="#questions">Questions</a>
<a class="rsvp" href="{RSVP}">RSVP</a></div></nav>'''

EVENING = section("evening", "Chapter one", "What to expect", '''
<p class="lead">Walk the red carpet on arrival, then join us for an evening of food, drink, and merriment, from 6:30 until 9:00 at The Residents&rsquo; Club. Black tie if you have it, and glamour however you care to define it.</p>
<div class="cards">
  <div class="card"><img src="img/vibe01.jpg" alt=""><h3>The red carpet</h3><p>Arrive like it is a premiere. The rope, the carpet, the flashbulbs.</p></div>
  <div class="card"><img src="img/vibe06.jpg" alt=""><h3>Live music</h3><p>Music of the era, played live, all evening.</p></div>
  <div class="card"><img src="img/vibe05.jpg" alt=""><h3>Cocktails</h3><p>Coupes of champagne and the classics, poured the old way.</p></div>
  <div class="card"><img src="img/vibe04.jpg" alt=""><h3>The table</h3><p>Shrimp cocktail, a prime rib station, a side of salmon carved to order, and more as the evening unfolds.</p></div>
  <div class="card"><img src="img/vibe03.jpg" alt=""><h3>The silent film lounge</h3><p>Black and white on the big screen, low lamps, deep chairs, a place to land between dances.</p></div>
  <div class="card"><img src="img/vibe08.jpg" alt=""><h3>Pictures</h3><p>A photographer on the carpet, and your portrait to keep.</p></div>
</div>
''')

LOOK = section("look", "Chapter two", "The look, decoded", f'''
<p class="lead">Think the studio years, 1934 to 1955. Satin that catches light, black that swallows it, one piece of jewelry that does the talking. Nobody needs a costume; everybody is invited to lean in.</p>
<div class="ways">
  <div class="way"><div class="n">One &middot; Just come</div><h3>A dark suit or a cocktail dress</h3><ul><li>Add one Old Hollywood touch: a bow tie, a red lip, a brooch, a pocket square</li><li>Shoes polished, hair done</li><li>Honestly, this is plenty</li></ul></div>
  <div class="way"><div class="n">Two &middot; Lean in</div><h3>Black tie, or a gown</h3><ul><li>Tuxedo, or a long dress in satin, velvet or sequins</li><li>Long gloves, pearls, cufflinks</li><li>A wave in the hair, a part on the side</li></ul></div>
  <div class="way"><div class="n">Three &middot; The full picture</div><h3>The movie star</h3><ul><li>White dinner jacket, cummerbund, a fedora at the door</li><li>Bias-cut gown, fur stole (faux is perfect), finger waves, a feathered headband</li><li>Arrive on someone&rsquo;s arm</li></ul></div>
</div>
<div class="deco"><span>The palette</span></div>
<div class="sw">
  <div><i style="background:#0a0a0a"></i><b>Midnight black</b></div>
  <div><i style="background:linear-gradient(135deg,#f3e4c4,#d9c396)"></i><b>Champagne</b></div>
  <div><i style="background:linear-gradient(135deg,#e2bf6e,#9c7a35)"></i><b>Old gold</b></div>
  <div><i style="background:#7a1b22"></i><b>Velvet red</b></div>
  <div><i style="background:#1f4a35"></i><b>Emerald</b></div>
  <div><i style="background:linear-gradient(135deg,#e9e9e9,#9b9b9b 50%,#e0e0e0)"></i><b>Silver screen</b></div>
  <div><i style="background:radial-gradient(circle at 35% 35%,#fff,#e6dccb 60%,#cbbfa8)"></i><b>Pearl</b></div>
</div>
<div class="two">
  <div>
    <h3>Hair and makeup</h3>
    {chips(["Soft waves", "Finger waves", "Sleek updo", "Side part", "Pomade, combed back", "Red lip", "Defined eyes", "A single flower in the hair"])}
    <h3>Fabrics that read from across the room</h3>
    {chips(["Satin", "Velvet", "Sequins", "Beading", "Fur, faux is perfect", "Brocade", "Embroidered silk", "Pinstripe wool", "Crisp white cotton"])}
  </div>
  <div>
    <h3>The hair, in pictures</h3>
    <div class="hairrow">{fig("women09", "Finger waves")}{fig("women11", "The sleek updo")}{fig("cw09", "Soft waves and a comb")}</div>
    <div class="hairrow">{fig("cm16", "Combed back, silver")}{fig("cm01", "Pomade and a side part")}{fig("hp12", "A beard, kept neat")}</div>
  </div>
</div>
''')

SEC_HER = section("her", "Chapter three", "For her", f'''
<p class="lead">A long line, a bare back or a bare shoulder, something that shines. Gloves if you have them. Pearls always. Red, emerald and gold belong here as much as black.</p>
{chips(["Silk or satin gown", "Velvet, draped", "Sequins and beading", "A fur stole", "Opera gloves", "Statement earrings", "Three strands of pearls", "A small beaded clutch", "A brooch", "A sari or lehenga in silk and zari", "A cheongsam in brocade", "A hat with a veil, for the bold"])}
{reel(HER, "her")}
<div class="heritage"><h3>Glamour, however you define it</h3>
<p>The dress code speaks every language. A sari in silk and zari, a lehenga, a cheongsam in brocade, a sherwani: dressed to the nines in the 1940s was never only a tuxedo, and the evening is richer for every tradition in the room. Jewelry, the family pieces especially, is very much the point. You will find these looks all through the reels, where they belong.</p></div>
''')

SEC_HIM = section("him", "Chapter four", "For him", f'''
<p class="lead">A tuxedo is the easy answer and the right one. A dark suit with a bow tie is the next easiest. A dinner jacket in white, burgundy or green velvet is the one people remember.</p>
{chips(["Black tuxedo, peak or shawl lapel", "White dinner jacket", "Velvet dinner jacket, burgundy or green", "Dark suit, double-breasted if you have it", "A sherwani or bandhgala", "Bow tie, hand-tied", "Cummerbund or waistcoat", "White pocket square", "Cufflinks", "Suspenders", "Polished black oxfords", "A fedora, left at the door"])}
{reel(HIM, "him")}
''')

TOUCHES = section("touches", "Chapter five", "Finishing touches", f'''
<p class="lead">The details are the costume. One or two of these turn a good outfit into a scene.</p>
<div>
    <h3>Her</h3>{chips(["Red lipstick, one shade bluer than you think", "Long gloves, past the elbow", "A hair comb or a jeweled clip", "A maang tikka or a feather", "A beaded clutch no bigger than a hand", "Stockings with a seam"])}
    <h3>Him</h3>{chips(["A real bow tie, slightly imperfect", "Pomade and a comb in the pocket", "A watch with a leather strap", "A boutonniere, white", "A silk pocket square, folded flat", "Shoes shined that afternoon"])}
    <h3>Both</h3>{chips(["A coupe, not a flute", "An arm to arrive on", "A good exit line"], "v")}
</div>
''')

SCENE = section("scene", "Chapter six", "The scene", f'''
<p class="lead">The Residents&rsquo; Club, lit for the occasion. This is the room you are dressing for.</p>
<div class="gal wide">{"".join(f'<figure class="ph"><a href="#lb-{s}"><img src="img/{s}.jpg" alt="{e(t)}" loading="lazy"></a><figcaption><b style="color:var(--champ)">{e(t)}</b><br>{e(c)}</figcaption></figure>' for s, t, c in VIBE)}</div>
<div style="height:28px"></div>
<div class="gal wide">{fig("banquet", "The banquet, the bar, the house")}{fig("vibe-all", "The scene, all together")}</div>
''')

QUESTIONS = section("questions", "Chapter seven", "Questions, answered", '''
<details class="q"><summary>Do I have to dress up?</summary><div class="a"><p>No. Come as you are and you will be welcome. The evening rewards a little effort, and a single Old Hollywood touch is all it takes to join in.</p></div></details>
<details class="q"><summary>Can I bring a guest?</summary><div class="a"><p>This one is residents only, with no outside guests. The building&rsquo;s own children are residents too, and welcome. Seats are limited, so RSVP by Monday, December 7.</p></div></details>
<details class="q"><summary>Where do I find a tuxedo, or a gown, in time?</summary><div class="a"><p>Rental is the easy road for black tie, and most houses deliver within the week. For gowns, rental and vintage both work, and the city&rsquo;s vintage shops are made for this brief.</p></div></details>
<details class="q"><summary>Will there be photographs?</summary><div class="a"><p>On the red carpet, yes, and you will get yours. Inside, the evening is for the people in it; take all the pictures you like, and ask before you post someone else&rsquo;s.</p></div></details>
<details class="q"><summary>Is there anything I should not wear?</summary><div class="a"><p>Costumes in the Halloween sense. This is glamour, not fancy dress: no plastic cigarette holders, no gangster props. A feather boa, on the other hand, is allowed.</p></div></details>
''')

FOOT = f'''<footer><div class="wrap">
<span class="eyebrow">Friday, December 18 &middot; 6:30 to 9:00 PM &middot; The Residents&rsquo; Club</span>
<div class="btnrow" style="justify-content:center;margin-bottom:22px"><a class="btn" href="{RSVP}">RSVP on the calendar</a><a class="btn ghost" href="https://181residents.com/ics/2026-12-18_lights-camera-gala.ics">Add to my calendar</a></div>
<p>Questions, or a dress you are not sure about? Resident Experiences at The Residents&rsquo; Club is happy to be asked.</p>
<p class="tiny">181 Fremont Residences &middot; Resident Experiences</p>
</div></footer>'''

ALL_LB = lightboxes(HER + HIM + [("cw09", "Soft waves and a comb"), ("cm16", "Combed back, silver"), ("cm01", "Pomade and a side part"), ("hp12", "A beard, kept neat")])

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Lights, Camera, Gala &middot; the style guide &middot; 181 Fremont</title>
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0b0908">
<style>{CSS}</style>
</head>
<body>
<div id="shut"></div>
__MOCKNOTE__
<div class="bulbs"></div>
{HERO}
{NAV}
{EVENING}
<div class="film"></div>
{LOOK}
{SEC_HER}
<div class="film"></div>
{SEC_HIM}
{TOUCHES}
<div class="film"></div>
{QUESTIONS}
<div class="bulbs"></div>
{FOOT}
{ALL_LB}
</body>
</html>'''

MOCKNOTE = '<div class="mocknote">Mockup &middot; a resident style and inspiration guide for the holiday gala &middot; nothing here is published</div>'

def render(live=False):
    """The page as HTML. live=True drops the mock banner; img/ paths stay relative."""
    return HTML.replace("__MOCKNOTE__", "" if live else MOCKNOTE)

IMAGES = sorted(set(re.findall(r"img/([a-z0-9-]+[.]jpg)", HTML)))

if __name__ == "__main__":
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(render(False))
    print("built index.html", len(HTML), "bytes;", len(HER), "looks for her,", len(HIM), "for him;", len(IMAGES), "images")
