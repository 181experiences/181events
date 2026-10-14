#!/usr/bin/env python3
"""Lights, Camera, Gala: the residents' style and inspiration guide, MOCKUP.

A standalone page in its own skin (not the calendar's), built from the photo
set in img/. Script-free like every resident page: the lightbox is a :target
overlay, the folds are <details>. Run: python build_gala_mockup.py -> index.html
"""
import html, os
HERE = os.path.dirname(os.path.abspath(__file__))
e = html.escape

# ---------------------------------------------------------------- the pictures
LADY = [("lady01", "Satin, a stole, and one great clutch"), ("lady02", "Black velvet, back view, opera gloves"),
        ("lady03", "Draped velvet and three strands of pearls"), ("lady04", "The flapper: beads, bandeau, fur"),
        ("lady05", "Halter satin beside a black tie"), ("lady06", "Off the shoulder, pearls at the throat"),
        ("lady07", "Beaded gown, fur over the arm"), ("lady08", "Dark gloves, dark fur, red lip"),
        ("lady09", "Fringe and a feathered headband")]
WOMEN = [("women01", "Bias-cut satin, open back"), ("women02", "A coupe and long gloves"), ("women03", "Beaded sheath, fur stole"),
         ("women04", "Halter neck, hair pinned"), ("women05", "Velvet with gloves, a brooch"), ("women06", "A hat with a veil"),
         ("women07", "Strapless, one silk flower"), ("women08", "Beaded jacket, pearls, a coupe"), ("women09", "Beaded back, finger waves"),
         ("women10", "Fur and a double strand"), ("women11", "The sleek updo"), ("women12", "Brocade cheongsam and pearls")]
GUYS = [("guys01", "The black tuxedo, pocket square white"), ("guys02", "The white dinner jacket"), ("guys03", "Pinstripe double-breast and a fedora"),
        ("guys04", "Peak lapels, a watch, a cufflink"), ("guys05", "The group at the bar"), ("guys06", "Shawl collar, drink in hand"),
        ("guys07", "Tweed three-piece, hat tipped"), ("guys08", "Bow tie, hand-tied"), ("guys09", "The cuff and the watch"),
        ("guys10", "Silver hair, black tie, a coupe"), ("guys11", "Suspenders and a loosened tie"), ("guys12", "Cummerbund and a slim bow"),
        ("guys13", "Hat, overcoat, the velvet rope")]
MEN = [(f"men{i:02d}", "") for i in range(1, 17)]
VIBE = [("vibe01", "The red carpet", "Arrive like it is a premiere."), ("vibe02", "Shrimp cocktail", "Stacked on silver, lemon and ice."),
        ("vibe03", "The silent film lounge", "Black and white on the big screen, low lamps, deep chairs."),
        ("vibe04", "The prime rib station", "Carved to order."), ("vibe05", "Coupes and pearls", "Champagne the old way."),
        ("vibe06", "Live jazz", "Piano, bass and horn, all night."), ("vibe07", "The Club at night", "Level 39, lit for the occasion."),
        ("vibe08", "Lights, camera", "A camera, a coupe, a feather.")]

def fig(stem, cap="", cls="", lb=True):
    inner = f'<img src="img/{stem}.jpg" alt="{e(cap)}" loading="lazy">'
    if lb:
        inner = f'<a href="#lb-{stem}">{inner}</a>'
    return f'<figure class="ph {cls}">{inner}{f"<figcaption>{e(cap)}</figcaption>" if cap else ""}</figure>'

def lightboxes(items):
    out = []
    for it in items:
        stem, cap = it[0], it[1]
        out.append(f'<div class="lb" id="lb-{stem}"><a class="lbx" href="#top" aria-label="Close">&times;</a>'
                   f'<img src="img/{stem}.jpg" alt="{e(cap)}">{f"<p>{e(cap)}</p>" if cap else ""}</div>')
    return "".join(out)

BIG = [("moodboard", "The moodboard: the whole evening on one board"), ("portraits", "Glamour, however you define it"),
       ("banquet", "The banquet, the bar, the house"), ("heromix", "The studio reference sheet"),
       ("lady-all", ""), ("women-all", ""), ("guys-all", ""), ("men-all", ""), ("vibe-all", "")]

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
.gl{color:var(--gold)}
/* marquee bulbs */
.bulbs{height:14px;background:radial-gradient(circle at 7px 7px,#ffe9a8 0 3px,#f0b64a 3.5px 4.5px,transparent 5px) 0 0/22px 14px repeat-x;opacity:.9}
/* nav */
nav.chapters{position:sticky;top:0;z-index:20;background:rgba(11,9,8,.92);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
nav.chapters .in{max-width:1120px;margin:0 auto;display:flex;gap:4px;overflow-x:auto;padding:0 12px;scrollbar-width:none}
nav.chapters a{flex:none;display:inline-block;padding:16px 14px;font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--soft);text-decoration:none;border-bottom:2px solid transparent}
nav.chapters a:hover{color:var(--champ);border-bottom-color:var(--gold)}
nav.chapters a.rsvp{margin-left:auto;color:var(--night);background:var(--gold);border-radius:3px;padding:10px 16px;margin-top:9px;margin-bottom:9px;font-weight:700}
/* hero */
.hero{position:relative;min-height:min(92vh,980px);display:grid;grid-template-columns:1fr;align-items:end;overflow:hidden;border-bottom:1px solid var(--line)}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%}
.hero .veil{position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,9,8,.15) 0,rgba(11,9,8,0) 30%,rgba(11,9,8,.92) 100%)}
.hero .copy{position:relative;padding:60px 0 48px}
.hero h1{font-size:clamp(14px,2vw,18px);font-family:Arial,Helvetica,sans-serif;letter-spacing:.36em;text-transform:uppercase;color:var(--gold);margin-bottom:14px}
.hero .lede{font-size:clamp(22px,3.4vw,34px);line-height:1.2;color:var(--champ);max-width:22em;margin:0 0 22px}
.facts{display:flex;flex-wrap:wrap;gap:10px 28px;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);margin-bottom:26px}
.facts span b{color:var(--gold);font-weight:400;margin-right:8px}
.btn{display:inline-flex;align-items:center;min-height:54px;padding:0 26px;background:var(--gold);color:var(--night);text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.22em;text-transform:uppercase;font-weight:700;border-radius:3px}
.btn.ghost{background:transparent;color:var(--champ);border:1px solid var(--gold)}
.btnrow{display:flex;gap:12px;flex-wrap:wrap}
/* sections */
section.ch{padding:72px 0 56px;border-bottom:1px solid var(--line)}
.deco{display:flex;align-items:center;gap:18px;margin:0 0 30px}
.deco:before,.deco:after{content:"";flex:1;height:1px;background:linear-gradient(90deg,transparent,var(--gold2),transparent)}
.deco span{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.4em;text-transform:uppercase;color:var(--gold)}
.lead{font-size:clamp(19px,2.4vw,24px);line-height:1.45;color:var(--ink);max-width:34em;margin:14px 0 28px}
.two{display:grid;grid-template-columns:1.1fr .9fr;gap:40px;align-items:start}
@media(max-width:820px){.two{grid-template-columns:1fr}}
/* photos */
.ph{margin:0;background:#1a1510;border:1px solid var(--line);padding:6px;min-width:0;max-width:100%}
.ph img{max-width:100%}
.gal>*{min-width:0}
.two>*{min-width:0}
.ph img{display:block;width:100%;height:100%;object-fit:cover;filter:sepia(.08) contrast(1.02);transition:filter .25s}
.ph a{display:block;height:100%}
.ph:hover img{filter:none}
.ph figcaption{font-family:Arial,Helvetica,sans-serif;font-size:11.5px;letter-spacing:.08em;color:var(--soft);padding:8px 4px 4px;line-height:1.4}
.gal{display:grid;gap:14px}
.gal.tall{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.gal.tall .ph{aspect-ratio:1/1.9;display:flex;flex-direction:column}
.gal.tall .ph a{flex:1;min-height:0}
.gal.sq{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}
.gal.sq .ph a{aspect-ratio:1/1.1;height:auto;width:100%}
.gal.wide{grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.gal.wide .ph a{aspect-ratio:4/3;height:auto;width:100%}
.big .ph img{aspect-ratio:auto}
/* program cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.card{background:linear-gradient(180deg,#171209,#120e08);border:1px solid var(--line);padding:0 0 14px}
.card img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover}
.card h3{font-size:20px;padding:14px 16px 2px}
.card p{padding:0 16px;font-size:15.5px;margin:0}
/* chips, swatches */
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 24px}
.chip{border:1px solid var(--gold2);color:var(--champ);border-radius:100px;padding:8px 14px;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.06em}
.chip.v{border-color:var(--velvet);background:rgba(139,30,36,.25)}
.sw{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin:16px 0 30px}
.sw div{border:1px solid var(--line);padding:6px}
.sw i{display:block;height:64px}
.sw b{display:block;font-family:Arial,Helvetica,sans-serif;font-weight:400;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);padding:8px 2px 2px}
/* three ways in */
.ways{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin:10px 0 30px}
.way{border:1px solid var(--line);padding:22px 22px 18px;background:rgba(210,171,99,.04)}
.way .n{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.3em;text-transform:uppercase;color:var(--gold);margin-bottom:8px}
.way h3{margin-bottom:8px}
.way ul{margin:0;padding-left:18px;color:var(--soft);font-size:16px}
.way li{margin-bottom:4px}
/* film strip divider */
.film{height:34px;margin:0;background:
  linear-gradient(90deg,transparent 0 6px,#2a2117 6px 16px,transparent 16px 26px) 0 0/26px 8px repeat-x,
  linear-gradient(90deg,transparent 0 6px,#2a2117 6px 16px,transparent 16px 26px) 0 100%/26px 8px repeat-x,
  linear-gradient(#171209,#171209) 0 8px/100% 18px no-repeat,#0e0b08}
/* faq */
details.q{border-top:1px solid var(--line);padding:0}
details.q:last-of-type{border-bottom:1px solid var(--line)}
details.q summary{cursor:pointer;list-style:none;padding:18px 0;font-size:clamp(18px,2.4vw,22px);color:var(--champ);display:flex;justify-content:space-between;gap:16px;min-height:54px;align-items:center}
details.q summary::-webkit-details-marker{display:none}
details.q summary:after{content:"+";color:var(--gold);font-size:26px}
details.q[open] summary:after{content:"\2013"}
details.q .a{padding:0 0 20px;max-width:40em}
/* lightbox */
.lb{display:none;position:fixed;inset:0;z-index:50;background:rgba(5,4,3,.94);align-items:center;justify-content:center;flex-direction:column;padding:28px 16px}
.lb:target{display:flex}
.lb img{max-width:min(96vw,900px);max-height:84vh;border:1px solid var(--line)}
.lb p{color:var(--champ);margin:14px 0 0;font-size:16px}
.lb .lbx{position:absolute;top:14px;right:18px;color:var(--champ);font-size:44px;text-decoration:none;line-height:1;min-width:54px;min-height:54px;display:flex;align-items:center;justify-content:center}
footer{padding:50px 0 70px;text-align:center;color:var(--soft);font-size:15px}
footer .eyebrow{display:block;margin-bottom:14px}
.note{border-left:3px solid var(--velvet);background:rgba(139,30,36,.12);padding:12px 16px;color:var(--ink);font-size:16px;margin:0 0 20px}
.tiny{font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--soft)}
@media(max-width:620px){section.ch{padding:48px 0 36px}.hero .copy{padding:40px 0 34px}.gal.tall{grid-template-columns:repeat(2,1fr)}}
'''

def section(id_, deco, title, body):
    return f'<section class="ch" id="{id_}"><div class="wrap"><div class="deco"><span>{deco}</span></div><h2>{title}</h2>{body}</div></section>'

def chips(items, cls=""):
    return '<div class="chips">' + "".join(f'<span class="chip {cls}">{e(i)}</span>' for i in items) + "</div>"

HERO = '''<div class="hero" id="top">
<img src="img/hero.jpg" alt="Lights, Camera, Gala">
<div class="veil"></div>
<div class="wrap copy">
  <h1>The Residents&rsquo; Club &middot; Friday, December 18</h1>
  <p class="lede">Our end-of-year party, and the one evening the whole building comes together. A red-carpet gala in the spirit of Old Hollywood.</p>
  <div class="facts"><span><b>When</b>6:30 to 9:00 PM</span><span><b>Where</b>Level 39</span><span><b>Dress</b>Black tie if you have it</span><span><b>RSVP by</b>Monday, December 14</span></div>
  <div class="btnrow"><a class="btn" href="https://181residents.com/rsvp/2026-12-18_lights-camera-gala">RSVP on the calendar</a><a class="btn ghost" href="#look">The dress code, decoded</a></div>
</div></div>'''

NAV = '''<nav class="chapters"><div class="in">
<a href="#evening">The evening</a><a href="#look">The look</a><a href="#her">For her</a><a href="#him">For him</a><a href="#touches">Finishing touches</a><a href="#scene">The scene</a><a href="#questions">Questions</a>
<a class="rsvp" href="https://181residents.com/rsvp/2026-12-18_lights-camera-gala">RSVP</a></div></nav>'''

EVENING = section("evening", "Chapter one", "What to expect", f'''
<p class="lead">Walk the red carpet on arrival, then join us for an evening of food, drink, and merriment, from 6:30 until 9:00 on Level 39. Black tie if you have it, and glamour however you care to define it.</p>
<div class="cards">
  <div class="card"><img src="img/vibe01.jpg" alt=""><h3>The red carpet</h3><p>Arrive like it is a premiere. The rope, the carpet, the flashbulbs.</p></div>
  <div class="card"><img src="img/vibe06.jpg" alt=""><h3>Live jazz</h3><p>Piano, bass and horn, playing the standards all evening.</p></div>
  <div class="card"><img src="img/vibe02.jpg" alt=""><h3>Cocktails and the raw bar</h3><p>Coupes of champagne, classic cocktails, shrimp cocktail on silver.</p></div>
  <div class="card"><img src="img/vibe04.jpg" alt=""><h3>The prime rib station</h3><p>Carved to order, with the sides a banquet deserves.</p></div>
  <div class="card"><img src="img/vibe03.jpg" alt=""><h3>The silent film lounge</h3><p>Black and white on the big screen, low lamps, deep chairs, a place to land between dances.</p></div>
  <div class="card"><img src="img/vibe08.jpg" alt=""><h3>Pictures</h3><p>A photographer on the carpet, and your portrait to keep.</p></div>
</div>
<div class="note" style="margin-top:22px"><span class="tiny">Mockup note</span><br>The program above is read off the moodboards (jazz, cocktails, prime rib, shrimp cocktail, silent films). Swap, cut or add before this goes to residents; the page is only as true as this list.</div>
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
    {chips(["Satin", "Velvet", "Sequins", "Beading", "Fur, faux is perfect", "Brocade", "Pinstripe wool", "Crisp white cotton"])}
  </div>
  {fig("moodboard", "The moodboard, the whole evening on one board", "big")}
</div>
''')

HER = section("her", "Chapter three", "For her", f'''
<p class="lead">A long line, a bare back or a bare shoulder, something that shines. Gloves if you have them. Pearls always.</p>
{chips(["Silk or satin gown", "Velvet, draped", "Sequins and beading", "A fur stole", "Opera gloves", "Statement earrings", "Three strands of pearls", "A small beaded clutch", "A brooch", "A hat with a veil, for the bold"])}
<div class="gal tall">{"".join(fig(s, c) for s, c in LADY)}</div>
<div style="height:28px"></div>
<h3>In sepia: twelve more looks</h3>
<p>Cut from the same cloth, photographed in the Club&rsquo;s own light.</p>
<div class="gal tall">{"".join(fig(s, c) for s, c in WOMEN)}</div>
<div style="height:36px"></div>
<div class="deco"><span>Glamour, however you define it</span></div>
<div class="two">
  <div>
    <h3>Your own heritage, at its most glamorous</h3>
    <p>The dress code speaks every language. A sari in silk and zari, a lehenga, a cheongsam in brocade, a sherwani: dressed to the nines in the 1940s was never only a tuxedo, and the evening is richer for every tradition in the room. Jewelry, the family pieces especially, is very much the point.</p>
    <p class="tiny">More looks are on their way for this board.</p>
  </div>
  {fig("portraits", "The portrait grid", "big")}
</div>
''')

HIM = section("him", "Chapter four", "For him", f'''
<p class="lead">A tuxedo is the easy answer and the right one. A dark suit with a bow tie is the next easiest. A white dinner jacket is the one people remember.</p>
{chips(["Black tuxedo, peak or shawl lapel", "White dinner jacket", "Dark suit, double-breasted if you have it", "Bow tie, hand-tied", "Cummerbund or waistcoat", "White pocket square", "Cufflinks", "Suspenders", "Polished black oxfords", "A fedora, left at the door"])}
<div class="gal tall">{"".join(fig(s, c) for s, c in GUYS[:4] + GUYS[5:7] + GUYS[9:13])}</div>
<div style="height:28px"></div>
<div class="gal wide">{fig("guys05", "The group at the bar")}{fig("guys08", "Bow tie, hand-tied")}{fig("guys09", "The cuff and the watch")}</div>
<div style="height:36px"></div>
<h3>In sepia: sixteen more</h3>
<div class="gal tall">{"".join(fig(s, c, lb=True) for s, c in MEN)}</div>
''')

TOUCHES = section("touches", "Chapter five", "Finishing touches", f'''
<p class="lead">The details are the costume. One or two of these turn a good outfit into a scene.</p>
<div class="two">
  <div>
    <h3>Her</h3>{chips(["Red lipstick, one shade bluer than you think", "Long gloves, past the elbow", "A hair comb or a jeweled clip", "A feather, worn once in a lifetime", "A beaded clutch no bigger than a hand", "Stockings with a seam"])}
    <h3>Him</h3>{chips(["A real bow tie, slightly imperfect", "Pomade and a comb in the pocket", "A watch with a leather strap", "A boutonniere, white", "A silk pocket square, folded flat", "Shoes shined that afternoon"])}
    <h3>Both</h3>{chips(["A coupe, not a flute", "An arm to arrive on", "A good exit line"], "v")}
  </div>
  {fig("heromix", "The studio reference sheet", "big")}
</div>
''')

SCENE = section("scene", "Chapter six", "The scene", f'''
<p class="lead">Level 39, lit for the occasion. This is the room you are dressing for.</p>
<div class="gal wide">{"".join(f'<figure class="ph"><a href="#lb-{s}"><img src="img/{s}.jpg" alt="{e(t)}" loading="lazy"></a><figcaption><b style="color:var(--champ)">{e(t)}</b><br>{e(c)}</figcaption></figure>' for s, t, c in VIBE)}</div>
<div style="height:28px"></div>
<div class="gal wide">{fig("banquet", "The banquet, the bar, the house")}{fig("vibe-all", "The scene, all together")}</div>
''')

QUESTIONS = section("questions", "Chapter seven", "Questions, answered", '''
<details class="q"><summary>Do I have to dress up?</summary><div class="a"><p>No. Come as you are and you will be welcome. The evening rewards a little effort, and a single Old Hollywood touch is all it takes to join in.</p></div></details>
<details class="q"><summary>Where do I find a tuxedo, or a gown, in time?</summary><div class="a"><p>Rental is the easy road for black tie, and most houses deliver within the week. For gowns, rental and vintage both work, and the city&rsquo;s vintage shops are made for this brief. <span class="tiny">Mockup note: Leo to add the places he trusts.</span></p></div></details>
<details class="q"><summary>Can I bring a guest?</summary><div class="a"><p>Yes. Your RSVP on the calendar takes your party size, and your guest walks the carpet with you. Seats are limited, so RSVP by Monday, December 14.</p></div></details>
<details class="q"><summary>Will there be photographs?</summary><div class="a"><p>On the red carpet, yes, and you will get yours. Inside, the evening is for the people in it; take all the pictures you like, and ask before you post someone else&rsquo;s.</p></div></details>
<details class="q"><summary>Is there anything I should not wear?</summary><div class="a"><p>Costumes in the Halloween sense. This is glamour, not fancy dress: no plastic cigarette holders, no gangster props. A feather boa, on the other hand, is allowed.</p></div></details>
<details class="q"><summary>What about the kids?</summary><div class="a"><p><span class="tiny">Mockup note: Leo to rule. The calendar entry will carry the answer; this page points to it.</span></p></div></details>
''')

FOOT = '''<footer><div class="wrap">
<span class="eyebrow">Friday, December 18 &middot; 6:30 to 9:00 PM &middot; The Residents&rsquo; Club</span>
<div class="btnrow" style="justify-content:center;margin-bottom:22px"><a class="btn" href="https://181residents.com/rsvp/2026-12-18_lights-camera-gala">RSVP on the calendar</a><a class="btn ghost" href="https://181residents.com/ics/2026-12-18_lights-camera-gala.ics">Add to my calendar</a></div>
<p>Questions, or a dress you are not sure about? Resident Experiences, Level 39, is happy to be asked.</p>
<p class="tiny">181 Fremont Residences &middot; Resident Experiences</p>
</div></footer>'''

ALL_LB = lightboxes(LADY + WOMEN + GUYS + MEN + [(s, t) for s, t, c in VIBE] + BIG)

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
<div class="mocknote">Mockup &middot; a resident style and inspiration guide for the holiday gala &middot; nothing here is published</div>
<div class="bulbs"></div>
{HERO}
{NAV}
{EVENING}
<div class="film"></div>
{LOOK}
{HER}
<div class="film"></div>
{HIM}
{TOUCHES}
<div class="film"></div>
{SCENE}
{QUESTIONS}
<div class="bulbs"></div>
{FOOT}
{ALL_LB}
</body>
</html>'''

with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(HTML)
print("built index.html", len(HTML), "bytes")
