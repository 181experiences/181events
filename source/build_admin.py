#!/usr/bin/env python3
"""181 Fremont Resident Experiences admin.
Screens and tabs run on CSS :checked selectors; the data comes from /api/* via admin_app.js,
which is inlined at build time. Staff only, so JavaScript is fine here."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
APP_JS = open(os.path.join(HERE, "admin_app.js"), encoding="utf-8").read()

CATEGORIES = ["Morning Offering", "Happy Hour", "Community Dinner", "Culinary Experience",
              "Enrichment Experience", "Signature Event"]
STATUSES = ["Draft", "Live", "Unpublished", "Archived"]
RSVP_TYPES = ["None", "Guest count only", "Seat", "Paid seat"]

SCREENS = ["dash", "events", "editor", "assets", "msgs", "inst",
           "inst-events", "inst-brand", "inst-email", "inst-screens"]
NAV_OF = {"dash": "dash", "events": "events", "editor": "events", "assets": "assets",
          "msgs": "msgs", "inst": "inst", "inst-events": "inst", "inst-brand": "inst",
          "inst-email": "inst", "inst-screens": "inst"}
NAV = [("dash", "Dashboard"), ("events", "Events"), ("assets", "Assets"),
       ("msgs", "Messages"), ("inst", "Instructions")]

rules = [f'#s-{s}:checked ~ .body #scr-{s}{{display:block}}' for s in SCREENS]
for s, nav in NAV_OF.items():
    rules.append(f'#s-{s}:checked ~ .navbar label[for="s-{nav}"]{{color:var(--ink);border-bottom-color:var(--red)}}')
for f in ["all", "live", "draft", "unpublished", "archived"]:
    rules.append(f'#f-{f}:checked ~ .wrap .tabs label[for="f-{f}"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}')
for f in ["live", "draft", "unpublished", "archived"]:
    rules.append(f'#f-{f}:checked ~ .wrap .evlist .erow:not(.{f}){{display:none}}')
GEN_CSS = "\n  ".join(rules)

def picks(name, options):
    return "".join(f'<label class="pick" for="{name}-{i}">{o}</label>' for i, o in enumerate(options))

def radios(name, options, checked=0):
    return "".join(f'<input class="state" type="radio" name="{name}" id="{name}-{i}"{" checked" if i == checked else ""}>'
                   for i in range(len(options)))

# ---------------------------------------------------------------- page
HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>181 Fremont Resident Experiences Admin</title>
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
  :root{{
    --ink:#16161a; --ink-body:#3a3a43; --ink-soft:#55555f;
    --paper:#f2efe9; --paper-2:#fffdfa; --line:#ddd6cb; --line-2:#eae3d8;
    --red:#c41f26; --stone:#7a7266; --radius:4px;
    --fd:'Marcellus',Georgia,serif;
    --fb:'Hanken Grotesk',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  }}
  *{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
  html,body{{margin:0;padding:0}}
  body{{background:var(--paper);color:var(--ink-body);font-family:var(--fb);font-size:17px;line-height:1.6;-webkit-font-smoothing:antialiased}}
  h1,h2,h3{{font-family:var(--fd);font-weight:400;margin:0;color:var(--ink);letter-spacing:.015em}}
  label{{cursor:pointer}}
  code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em;background:#eae3d8;padding:2px 6px;border-radius:3px;color:#4a4238}}
  .state{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;margin:0}}
  .wrap{{max-width:1080px;margin:0 auto;padding:0 clamp(18px,4vw,34px)}}

  /* ---------- chrome ---------- */
  .topbar{{background:var(--ink);color:#e8e2d8}}
  .topbar .inner{{max-width:1080px;margin:0 auto;padding:15px clamp(18px,4vw,34px);display:flex;align-items:center;justify-content:space-between;gap:16px}}
  .brand{{font-family:var(--fd);font-size:17px;letter-spacing:.2em;text-transform:uppercase;line-height:1.3}}
  .brand small{{display:block;font-family:var(--fb);font-size:10px;letter-spacing:.24em;color:#a49c90;margin-top:4px}}
  .who{{font-size:13px;color:#a49c90;text-align:right;line-height:1.4}}
  .who strong{{display:block;color:#e8e2d8;font-weight:500}}

  .navbar{{background:var(--paper-2);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:30}}
  .navbar .inner{{max-width:1080px;margin:0 auto;padding:0 clamp(18px,4vw,34px);display:flex;gap:4px;overflow-x:auto}}
  .navbar label{{white-space:nowrap;padding:17px 18px;font-size:14px;letter-spacing:.1em;text-transform:uppercase;
    font-weight:500;color:var(--stone);border-bottom:2px solid transparent}}
  .navbar label:hover{{color:var(--ink)}}

  .screen{{display:none;padding:34px 0 90px}}
  {GEN_CSS}

  .phead{{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:6px}}
  .phead h1{{font-size:clamp(28px,4.4vw,38px);line-height:1.1}}
  .psub{{color:var(--stone);font-size:15px;margin:8px 0 26px}}
  .btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:var(--red);color:#fff;
    border:1px solid var(--red);border-radius:var(--radius);padding:14px 22px;font-size:13px;letter-spacing:.14em;
    text-transform:uppercase;font-weight:600;min-height:50px}}
  .btn:hover{{background:#a5171d;border-color:#a5171d}}
  .btn.ghost{{background:transparent;color:var(--ink);border-color:#c9c0b3}}
  .card{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:24px}}
  .sec{{margin-top:34px}}
  .sec h2{{font-size:23px;margin-bottom:4px}}
  .sec .sd{{font-size:15px;color:var(--stone);margin-bottom:16px}}
  .back{{display:inline-block;font-size:15px;color:var(--ink-soft);margin-bottom:16px}}
  .back:hover{{color:var(--red)}}

  /* ---------- kpi tiles ---------- */
  .kpis{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(196px,1fr))}}
  .kpi{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:22px}}
  .kpi .k{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--stone);font-weight:500}}
  .kpi .v{{font-family:var(--fd);font-size:40px;line-height:1.05;color:var(--ink);margin-top:10px}}
  .kpi .n{{font-size:14px;color:var(--ink-soft);margin-top:6px}}

  /* ---------- funnels ---------- */
  .fgrid{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(310px,1fr))}}
  .fcard{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px}}
  .fhead{{font-family:var(--fd);font-size:19px;color:var(--ink);line-height:1.25;margin-bottom:14px;display:flex;
    justify-content:space-between;gap:12px;align-items:baseline}}
  .fhead span{{font-family:var(--fb);font-size:13px;color:var(--stone);white-space:nowrap}}
  .frow{{display:flex;align-items:center;gap:12px;margin-bottom:9px}}
  .fstage{{flex:0 0 76px;font-size:13px;color:var(--ink-soft)}}
  .ftrack{{flex:1;height:14px;background:#eee8de;border-radius:3px;overflow:hidden}}
  .ffill{{display:block;height:100%;border-radius:0 3px 3px 0}}
  .fval{{flex:0 0 34px;text-align:right;font-size:15px;color:var(--ink);font-weight:500}}
  .nodata{{font-size:14px;color:var(--stone);font-style:italic}}

  .srow{{display:flex;align-items:center;gap:14px;padding:9px 0}}
  .slab{{flex:0 0 168px;font-size:15px;color:var(--ink-body)}}
  .strack{{flex:1;height:12px;background:#eee8de;border-radius:3px;overflow:hidden}}
  .sfill{{display:block;height:100%;background:var(--ink);border-radius:0 3px 3px 0}}
  .sval{{flex:0 0 44px;text-align:right;font-size:15px;font-weight:500;color:var(--ink)}}

  /* ---------- events table ---------- */
  .tabs{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}}
  .tabs label{{border:1px solid var(--line);border-radius:100px;padding:9px 18px;font-size:13px;letter-spacing:.1em;
    text-transform:uppercase;font-weight:500;color:var(--stone);background:var(--paper-2);min-height:42px;display:flex;align-items:center}}
  .emptynote{{display:none;background:var(--paper-2);border:1px dashed var(--line);border-radius:var(--radius);
    padding:22px;margin-bottom:12px;font-size:15px;color:var(--stone);line-height:1.5}}
  #f-unpublished:checked ~ .wrap .emptynote{{display:block}}
  .evlist{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}
  .erow{{display:grid;gap:14px;grid-template-columns:2.2fr .8fr 1fr .9fr 1fr;align-items:center;
    padding:18px 22px;border-top:1px solid var(--line-2)}}
  .erow:first-child{{border-top:none}}
  .et{{display:block;font-family:var(--fd);font-size:19px;color:var(--ink);line-height:1.25}}
  .esub{{display:block;font-size:13px;color:var(--stone);margin-top:3px}}
  .lbl{{display:none;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);margin-right:6px}}
  .ecell{{font-size:15px}}
  .pill{{display:inline-block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:600;
    border-radius:100px;padding:5px 12px}}
  .pill.live{{background:#e7f0e8;color:#2c5c37}}
  .pill.draft{{background:#f4ecd9;color:#6d5518}}
  .pill.unpublished{{background:#f0e2e2;color:#8a2b2b}}
  .pill.archived{{background:#eae4da;color:#5c5548}}
  .badge2{{display:inline-block;font-size:10px;letter-spacing:.14em;text-transform:uppercase;font-weight:600;
    border:1px solid var(--line);border-radius:100px;padding:3px 9px;color:var(--stone);vertical-align:middle;
    margin-left:6px;font-family:var(--fb)}}
  .badge2.pay{{background:var(--ink);border-color:var(--ink);color:var(--paper-2)}}
  .badge2.ext{{background:#efe9e0;border-color:#efe9e0;color:#6d6355}}
  .eact{{display:flex;gap:8px;justify-content:flex-end}}
  .mini{{border:1px solid var(--line);border-radius:3px;padding:9px 14px;font-size:12px;letter-spacing:.1em;
    text-transform:uppercase;font-weight:600;color:var(--ink);min-height:40px;display:inline-flex;align-items:center}}
  .mini:hover{{border-color:var(--red);color:var(--red)}}
  .mini.ghost{{color:var(--stone)}}
  @media(max-width:820px){{
    .erow{{grid-template-columns:1fr;gap:8px}}
    .lbl{{display:inline}}
    .eact{{justify-content:flex-start;margin-top:6px}}
  }}

  /* ---------- editor form ---------- */
  .form{{display:grid;gap:18px;grid-template-columns:1fr 1fr}}
  .f-full{{grid-column:1/-1}}
  .field label.fl{{display:block;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);
    margin-bottom:8px;font-weight:500}}
  .inp{{width:100%;padding:14px 16px;font-family:var(--fb);font-size:17px;color:var(--ink);background:var(--paper-2);
    border:1px solid var(--line);border-radius:var(--radius);min-height:52px}}
  textarea.inp{{min-height:120px;resize:vertical;line-height:1.55}}
  .hint{{font-size:13px;color:var(--stone);margin-top:7px}}
  .picks{{display:flex;flex-wrap:wrap;gap:8px}}
  .pick{{border:1px solid var(--line);border-radius:100px;padding:12px 18px;font-size:14px;font-weight:500;
    color:var(--ink-body);background:var(--paper-2);min-height:48px;display:inline-flex;align-items:center}}
  .pick:hover{{border-color:var(--red)}}
#ho-0:checked ~ .form label[for="ho-0"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #ho-1:checked ~ .form label[for="ho-1"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #ho-2:checked ~ .form label[for="ho-2"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #ho-3:checked ~ .form label[for="ho-3"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #co-0:checked ~ .form label[for="co-0"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #co-1:checked ~ .form label[for="co-1"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #cat-0:checked ~ .form label[for="cat-0"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #cat-1:checked ~ .form label[for="cat-1"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #cat-2:checked ~ .form label[for="cat-2"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #cat-3:checked ~ .form label[for="cat-3"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #cat-4:checked ~ .form label[for="cat-4"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #cat-5:checked ~ .form label[for="cat-5"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #st-0:checked ~ .form label[for="st-0"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #st-1:checked ~ .form label[for="st-1"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #st-2:checked ~ .form label[for="st-2"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #st-3:checked ~ .form label[for="st-3"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rep-0:checked ~ .form label[for="rep-0"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rep-1:checked ~ .form label[for="rep-1"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rep-2:checked ~ .form label[for="rep-2"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rt-0:checked ~ .form label[for="rt-0"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rt-1:checked ~ .form label[for="rt-1"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rt-2:checked ~ .form label[for="rt-2"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  #rt-3:checked ~ .form label[for="rt-3"]{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  @media(max-width:700px){{ .form{{grid-template-columns:1fr}} }}
  .chips{{display:flex;flex-wrap:wrap;gap:8px}}
  .chip{{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:100px;
    padding:9px 15px;font-size:13px;font-weight:500}}
  .chip i{{font-style:normal;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-size:11px;font-weight:700}}
  .chip.done{{border-color:#bcd3c0;background:#eef5ef;color:#2c5c37}}
  .chip.done i{{background:#2c5c37;color:#fff}}
  .chip.miss{{color:var(--stone);border-style:dashed}}
  .chip.miss i{{background:#e6ded2;color:#6b6255}}

  /* ---------- assets ---------- */
  .aklist{{border:1px solid var(--line);border-radius:var(--radius);background:var(--paper-2);overflow:hidden}}
  .akrow{{display:grid;grid-template-columns:1.1fr 2fr auto;gap:14px;align-items:center;
    padding:14px 18px;border-top:1px solid var(--line-2)}}
  .akrow:first-child{{border-top:none}}
  .akname{{font-size:15px;font-weight:500;color:var(--ink)}}
  .akname em{{display:block;font-style:normal;font-size:12px;color:var(--stone);font-weight:400;margin-top:3px}}
  .akstate{{font-size:13px;color:var(--stone);overflow-wrap:anywhere}}
  .akstate.done{{color:#2c5c37}}
  .akstate.miss{{font-style:italic}}
  .akact{{display:flex;gap:8px;justify-content:flex-end}}
  @media(max-width:760px){{ .akrow{{grid-template-columns:1fr;gap:8px}} .akact{{justify-content:flex-start}} }}
  .acard{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;margin-bottom:12px}}
  .ahead{{margin-bottom:14px}}
  .at{{display:block;font-family:var(--fd);font-size:20px;color:var(--ink)}}
  .asub{{display:block;font-size:13px;color:var(--stone);margin-top:5px}}

  /* ---------- messages ---------- */
  .mrow{{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;margin-bottom:10px}}
  .mtop{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:9px}}
  .munit{{font-family:var(--fd);font-size:19px;color:var(--ink)}}
  .mkind{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:600;border:1px solid var(--line);
    border-radius:100px;padding:4px 11px;color:var(--stone)}}
  .mstate{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:600;border-radius:100px;padding:4px 11px}}
  .mstate.new{{background:var(--red);color:#fff}}
  .mstate.replied{{background:#eae4da;color:#5c5548}}
  .mwhen{{margin-left:auto;font-size:13px;color:var(--stone)}}
  .mtext{{font-size:16px;color:var(--ink-body)}}

  /* ---------- instructions ---------- */
  .docs{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(255px,1fr))}}
  .doc{{display:block;background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);padding:24px}}
  .doc:hover{{border-color:var(--red)}}
  .doc .dt{{display:block;font-family:var(--fd);font-size:22px;color:var(--ink);line-height:1.2}}
  .doc .dd{{display:block;font-size:14px;color:var(--ink-soft);margin-top:8px;line-height:1.5}}
  .doc .dm{{display:block;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--stone);margin-top:14px;font-weight:500}}

  .prose{{max-width:74ch}}
  .prose h2{{font-size:26px;margin:34px 0 10px}}
  .prose h3{{font-size:20px;margin:26px 0 8px}}
  .prose p{{margin:0 0 14px}}
  .prose ol,.prose ul{{margin:0 0 16px;padding-left:22px}}
  .prose li{{margin-bottom:8px}}
  .prose table{{width:100%;border-collapse:collapse;margin:8px 0 20px;font-size:15px}}
  .prose th{{text-align:left;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--stone);
    padding:10px 12px;border-bottom:1px solid var(--line);font-weight:600}}
  .prose td{{padding:12px;border-bottom:1px solid var(--line-2);vertical-align:top}}
  .tblwrap{{overflow-x:auto}}
  .callout{{background:#f4ecd9;border-radius:var(--radius);padding:18px 20px;margin:18px 0;font-size:15px;color:#5b4a1f;line-height:1.55}}
  .callout strong{{color:#3d3212}}
  .swatches{{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 18px}}
  .sw{{width:110px}}
  .sw .chip2{{height:56px;border-radius:var(--radius);border:1px solid rgba(0,0,0,.08)}}
  .sw .nm{{font-size:12px;color:var(--ink);margin-top:7px}}
  .sw .hx{{font-size:11px;color:var(--stone);font-family:ui-monospace,Menlo,monospace}}
  .toast{{position:fixed;left:50%;bottom:28px;transform:translateX(-50%) translateY(20px);background:var(--ink);color:#f2efe9;
    padding:14px 22px;border-radius:var(--radius);font-size:15px;opacity:0;pointer-events:none;transition:.25s;z-index:90;max-width:92vw}}
  .toast.show{{opacity:1;transform:translateX(-50%)}}
  .toast.warn{{background:#8a2b2b}}
  button{{font-family:var(--fb);cursor:pointer}}
  button.btn,button.mini{{appearance:none}}
  button:disabled{{opacity:.45;cursor:not-allowed}}
  input.inp,select.inp{{appearance:none}}
  input.inp:focus,textarea.inp:focus,select.inp:focus{{outline:none;border-color:var(--red)}}
  select.inp{{background-image:linear-gradient(45deg,transparent 50%,var(--stone) 50%),linear-gradient(135deg,var(--stone) 50%,transparent 50%);
    background-position:calc(100% - 20px) 50%,calc(100% - 14px) 50%;background-size:6px 6px;background-repeat:no-repeat;padding-right:40px}}
  .check{{display:flex;gap:12px;align-items:center;font-size:15px;color:var(--ink-body)}}
  .check input{{width:20px;height:20px;accent-color:var(--red)}}
  .picks .pick.on{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  .fmtbar{{display:flex;gap:6px;margin-bottom:8px}}
  .fmtbar .mini{{min-width:44px;justify-content:center;background:var(--paper-2)}}
  .chart{{width:100%;height:auto;display:block}}
  .chart .bar{{fill:#cfc6b8}} .chart .bar.hot{{fill:var(--ink)}}
  .chart .tick{{font-size:11px;fill:var(--stone);font-family:var(--fb)}}
  .period{{display:flex;gap:6px}}
  .period button{{border:1px solid var(--line);background:var(--paper-2);border-radius:100px;padding:8px 14px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;color:var(--stone)}}
  .period button.on{{background:var(--ink);color:var(--paper-2);border-color:var(--ink)}}
  .sval small{{font-weight:400;color:var(--stone);font-size:12px}}
  .twocol{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}}
  .mocknote{{background:#16161a;color:#c9c2b6;font-size:12px;letter-spacing:.1em;text-align:center;padding:10px 16px;text-transform:uppercase}}
</style>
</head>
<body>

<div class="mocknote" id="sysbar">Connecting&hellip;</div>

<div class="topbar"><div class="inner">
  <div class="brand">181 Fremont<small>Resident Experiences &middot; Admin</small></div>
  <div class="who">Resident Experiences<strong>181 Fremont &middot; Level 39</strong></div>
</div></div>

<input class="state" type="radio" name="scr" id="s-dash" checked>
{"".join(f'<input class="state" type="radio" name="scr" id="s-{s}">' for s in SCREENS if s != "dash")}

<nav class="navbar"><div class="inner">
  {"".join(f'<label for="s-{k}">{v}</label>' for k, v in NAV)}
</div></nav>

<div class="body">

<!-- ================= DASHBOARD ================= -->
<section class="screen" id="scr-dash"><div class="wrap">
  <div class="phead"><h1>Dashboard</h1><div class="period" id="period"><button data-period="7" data-days="7">7 days</button><button data-period="30" data-days="30" class="on">30 days</button><button data-period="90" data-days="90">90 days</button></div></div>
  <div class="psub" id="dash-period">Loading&hellip;</div>
  <div class="callout" id="dash-note" style="display:none;margin:0 0 18px"></div>

  <div class="kpis" id="kpis"></div>

  <div class="sec">
    <h2>Visits by day</h2>
    <div class="sd">One visit is one person opening the calendar, however many pages they look at. Tuesdays and Thursdays are marked darker, since that is when the building gathers.</div>
    <div class="card" id="daychart"></div>
  </div>

  <div class="sec twocol">
    <div>
      <h2>Where the traffic came from</h2>
      <div class="sd">Each QR standee and the weekly email carry their own link, so every scan and click is attributable.</div>
      <div class="card" id="sources"></div>
    </div>
    <div>
      <h2>What residents open it on</h2>
      <div class="sd">Useful for deciding what to design for. The site is built for the iPad first.</div>
      <div class="card" id="devices"></div>
    </div>
  </div>

  <div class="sec twocol">
    <div>
      <h2>Live calendar by category</h2>
      <div class="sd">Upcoming dates, grouped the way the budget lines are.</div>
      <div class="card" id="bycat"></div>
    </div>
    <div>
      <h2>Coming up</h2>
      <div class="sd">The next six dates on the resident calendar.</div>
      <div class="card" id="nextlist"></div>
    </div>
  </div>

  <div class="sec">
    <h2>Reporting note</h2>
    <div class="card" style="font-size:15px;color:var(--ink-soft)">
      With about ten year-round residents, two people is 20%. Every figure here shows a <strong style="color:var(--ink);font-weight:500">count alongside its percentage</strong>,
      and month-to-month swings should be read as noise until there are three months of trend. <strong style="color:var(--ink);font-weight:500">Events hosted by others are listed but not counted.</strong>
      Caf&eacute; 181 appears on the resident calendar and is excluded from engagement figures, so nothing here credits
      Resident Experiences with someone else&rsquo;s attendance. Traffic is measured without cookies and without identifying anyone.
      RSVP and attendance figures join this page once sign-ups open on the site.
    </div>
  </div>
</div></section>

<!-- ================= EVENTS ================= -->
<section class="screen" id="scr-events">
  <input class="state" type="radio" name="filt" id="f-all" checked>
  <input class="state" type="radio" name="filt" id="f-live">
  <input class="state" type="radio" name="filt" id="f-draft">
  <input class="state" type="radio" name="filt" id="f-unpublished">
  <input class="state" type="radio" name="filt" id="f-archived">
  <div class="wrap">
    <div class="phead"><h1>Events</h1><div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn ghost" data-publish title="Rebuild the resident calendar from what is saved">Publish calendar</button><button class="btn" data-new>+ New Event</button></div></div>
    <div class="psub" id="evcount">Loading&hellip;</div>
  </div>
  <div class="wrap"><div class="tabs">
    <label for="f-all">All</label><label for="f-live">Live</label><label for="f-draft">Drafts</label><label for="f-unpublished">Unpublished</label><label for="f-archived">Archived</label>
  </div></div>
  <div class="wrap"><div class="emptynote">Unpublishing pulls an event from the resident calendar and holds its RSVPs, so it can go back up unchanged.</div>
    <div class="evlist" id="evlist"></div></div>
</section>

<!-- ================= EVENT EDITOR ================= -->
<section class="screen" id="scr-editor"><div class="wrap">
  <label class="back" for="s-events">&larr; Back to events</label>
  {radios("cat", CATEGORIES, 4)}
  {radios("st", STATUSES, 0)}
  {radios("co", ["Count it", "List only"], 0)}
  {radios("rt", RSVP_TYPES, 2)}
  <div class="phead"><h1 id="ed-title">Edit event</h1><span class="pill draft" id="ed-pill">Draft</span></div>
  <div class="psub" id="ed-sub"></div>

  <div class="form">
    <div class="field f-full" id="ed-occ" style="display:none"><label class="fl" for="f-occ">Which date of this series</label>
      <select class="inp" id="f-occ"></select>
      <div class="hint">A series is one row per date, so a single week can be moved or skipped without touching the rest.</div></div>
    <div class="field f-full"><label class="fl" for="f-title">Event title</label><input class="inp" id="f-title" autocapitalize="words"></div>
    <div class="field f-full"><label class="fl">Category</label><div class="picks">{picks("cat", CATEGORIES)}</div><div class="hint">Categories match the budget line items, so the monthly report rolls up against what Scott already sees.</div></div>
    <div class="field"><label class="fl">Status</label><div class="picks">{picks("st", STATUSES)}</div><div class="hint">Draft is never published. Unpublished is pulled from the site with RSVPs held, ready to go back up. Archived is over, hidden, and kept for reporting.</div></div>
    <div class="field"><label class="fl" for="f-date">Date</label><input class="inp" type="date" id="f-date"></div>
    <div class="field"><label class="fl" for="f-start">Start time</label><input class="inp" id="f-start" placeholder="5:30 PM" inputmode="text"></div>
    <div class="field"><label class="fl" for="f-end">End time</label><input class="inp" id="f-end" placeholder="7:30 PM"></div>
    <div class="field"><label class="fl" for="f-loc">Location</label><input class="inp" id="f-loc" list="locs"><datalist id="locs"><option value="Level 39, Residents’ Club"><option value="Level 7 Terrace"><option value="Lobby"><option value="Fitness Center"></datalist></div>
    <div class="field"><label class="fl" for="f-host">Hosted by</label><input class="inp" id="f-host" list="hosts" autocapitalize="words"><datalist id="hosts"><option value="Resident Experiences"><option value="Leigh-Ann"><option value="Front desk"></datalist>
      <div class="hint">Shown on the event page so residents know who to ask.</div></div>
    <div class="field"><label class="fl">Count in engagement reporting</label><div class="picks">{picks("co", ["Count it", "List only, don’t count"])}</div>
      <div class="hint">Choose List only whenever the host is not Resident Experiences, so nothing credits you with someone else&rsquo;s attendance.</div></div>
    <div class="field f-full" id="rp-builder"><label class="fl">Repeats</label>
      <div class="picks" id="rp-picks">
        <label class="pick on" data-rp="none">Does not repeat</label>
        <label class="pick" data-rp="daily">Daily</label>
        <label class="pick" data-rp="weekly">Weekly</label>
        <label class="pick" data-rp="monthly">Monthly</label>
      </div>
      <div id="rp-weekly" class="rp-row" style="display:none">
        <span class="fl" style="margin:14px 0 8px">On these days</span>
        <div class="picks" id="rp-days">
          <label class="pick" data-wd="0">Sunday</label><label class="pick" data-wd="1">Monday</label>
          <label class="pick" data-wd="2">Tuesday</label><label class="pick" data-wd="3">Wednesday</label>
          <label class="pick" data-wd="4">Thursday</label><label class="pick" data-wd="5">Friday</label>
          <label class="pick" data-wd="6">Saturday</label>
        </div>
      </div>
      <div id="rp-monthly" class="rp-row" style="display:none">
        <span class="fl" style="margin:14px 0 8px">Which day of the month</span>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <select class="inp" id="rp-ord" style="width:auto"><option>First</option><option>Second</option><option>Third</option><option>Fourth</option><option selected>Last</option></select>
          <select class="inp" id="rp-wd" style="width:auto"><option value="0">Sunday</option><option value="1">Monday</option><option value="2">Tuesday</option><option value="3">Wednesday</option><option value="4">Thursday</option><option value="5">Friday</option><option value="6">Saturday</option></select>
        </div>
      </div>
      <div id="rp-ends" class="rp-row" style="display:none">
        <span class="fl" style="margin:14px 0 8px">Ends</span>
        <div class="picks" id="rp-endpicks">
          <label class="pick on" data-en="cal">End of the calendar</label>
          <label class="pick" data-en="count">After a number of times</label>
          <label class="pick" data-en="date">On a date</label>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px">
          <input class="inp" type="number" id="rp-times" min="2" max="60" value="6" style="width:120px;display:none">
          <input class="inp" type="date" id="rp-until" style="width:auto;display:none">
        </div>
        <div class="hint">The resident calendar runs to a fixed end and is extended season by season, so a series runs to the calendar&rsquo;s end rather than forever. Each date becomes its own entry, so a single week can still be moved or skipped later.</div>
      </div>
      <div class="hint" id="rp-preview" style="margin-top:10px"></div>
    </div>
    <div class="field"><label class="fl" for="f-series">Repeats, as shown to residents</label><input class="inp" id="f-series" placeholder="Writes itself from the rule; edit if you like"></div>
    <div class="field"><label class="fl">RSVP type</label><div class="picks">{picks("rt", RSVP_TYPES)}</div><div class="hint">Guest count collects non-resident numbers only. Paid seat shows the price.</div></div>
    <div class="field"><label class="fl" for="f-cap">Capacity</label><input class="inp" type="number" id="f-cap" inputmode="numeric" placeholder="Leave blank for no limit"></div>
    <div class="field"><label class="fl" for="f-price">Price per person</label><input class="inp" id="f-price" placeholder="$75"></div>
    <div class="field"><label class="fl" for="f-cutoff">RSVP closes</label><input class="inp" id="f-cutoff" placeholder="Monday, Aug 31">
      <div class="hint">Workshops close the Monday of the event week, so materials can be ordered against a firm count.</div></div>
    <div class="field f-full"><label class="fl" for="f-desc">Description</label>
      <div class="fmtbar">
        <button type="button" class="mini" data-fmt="strong" title="Bold the selected text"><strong>B</strong></button>
        <button type="button" class="mini" data-fmt="em" title="Italicise the selected text"><em>I</em></button>
        <button type="button" class="mini" data-fmt="u" title="Underline the selected text"><u>U</u></button>
      </div>
      <textarea class="inp" id="f-desc" rows="7" placeholder="Write it as if the reader knows nothing about the event. A blank line starts a new paragraph."></textarea>
      <div class="hint">Select some text, then B, I, or U. Titles of books and films take italics. A blank line starts a new paragraph; sizes are set by the calendar itself.</div></div>
    <div class="field f-full"><label class="check"><input type="checkbox" id="f-marquee"> Feature this on the home screen as the marquee event</label></div>
    <div class="field f-full" id="ed-scope" style="display:none"><label class="check"><input type="checkbox" id="f-scope" checked> Apply these changes to every upcoming date of this series (<span id="f-scope-n">0</span>)</label>
      <div class="hint">Untick to change only the date chosen above, for example to move or re-time a single week.</div></div>
    <div class="field f-full"><label class="fl" for="f-slug">File name stem, generated from the date and title</label>
      <div class="inp" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><code id="f-stem"></code><input id="f-slug" placeholder="custom slug, optional" style="border:none;background:transparent;font:inherit;flex:1;min-width:160px"></div>
      <div class="hint">Every file in this kit is named from this stem, so it stays identifiable in Canva, on Nixplay, or at the print shop.</div></div>
    <div class="field f-full"><label class="fl">Asset kit</label>
      <div class="aklist" id="ak"></div>
      <div class="hint">Uploads arrive with the next build. A Nixplay still will also email itself to the frames. Specs under Instructions &rarr; Screens &amp; Print.</div></div>
  </div>

  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:30px" id="ed-actions">
    <button class="btn" data-save="keep">Save changes</button>
    <button class="btn ghost" data-save="Draft">Save as draft</button>
    <button class="btn ghost" data-save="Archived">Archive event</button>
    <button class="btn ghost" id="ed-cancel" style="border-color:var(--red);color:var(--red)" disabled>Cancel &amp; notify guests</button>
  </div>
  <div class="hint" id="ed-cancel-note" style="margin-top:10px"></div>
</div></section>

<!-- ================= ASSETS ================= -->
<section class="screen" id="scr-assets"><div class="wrap">
  <div class="phead"><h1>Assets</h1></div>
  <div class="psub">One kit per event. This is the single place every version of an event&rsquo;s artwork lives: web, screens, print, and email. Uploads arrive with the next build; the kits and their file names are ready now.</div>
  <div class="callout" style="margin-bottom:22px">
    <strong>File naming is the whole trick.</strong> Every file in a kit uses the same stem, so a file stays identifiable
    anywhere it ends up. Canva, Nixplay, a print shop, or someone&rsquo;s downloads folder:
    <code>2026-09-25_a-night-in-mexico-city_nixplay-still.jpg</code>
  </div>
  <div id="assets"></div>
</div></section>

<!-- ================= MESSAGES ================= -->
<section class="screen" id="scr-msgs"><div class="wrap">
  <div class="phead"><h1>Messages</h1></div>
  <div class="psub">What residents send from the Message tile, with the promise of a reply within one business day.</div>
  <div class="card" style="font-size:15px;color:var(--ink-soft);line-height:1.6">
    For now the Message tile opens the resident&rsquo;s own mail app addressed to <strong style="color:var(--ink);font-weight:500">leonardo@181sf.com</strong>, with the topic, their note, and optionally their name, unit, and email.
    Replies happen in the inbox, so nothing is lost and nobody needs another login. Once resident sign-in is live, messages will be logged here with their status, and this screen becomes the inbox.
  </div>
</div></section>

<!-- ================= INSTRUCTIONS ================= -->
<section class="screen" id="scr-inst"><div class="wrap">
  <div class="phead"><h1>Instructions</h1></div>
  <div class="psub">The document center. Everything needed to run this without having to remember it, and to hand over to whoever covers for you.</div>
  <div class="docs">
    <label class="doc" for="s-inst-events"><span class="dt">Creating &amp; archiving events</span>
      <span class="dd">The full loop: draft, asset kit, publish, promote, archive.</span><span class="dm">Updated Aug 2026</span></label>
    <label class="doc" for="s-inst-brand"><span class="dt">Brand &amp; Canva templates</span>
      <span class="dd">Colors, type, and the exact template requirements for every asset.</span><span class="dm">Updated Aug 2026</span></label>
    <label class="doc" for="s-inst-screens"><span class="dt">Screens &amp; print</span>
      <span class="dd">Nixplay specs for the bar, lobby, and Level 7, plus the printed signs.</span><span class="dm">Updated Aug 2026</span></label>
    <label class="doc" for="s-inst-email"><span class="dt">Email templates</span>
      <span class="dd">Campaign and automated sequence copy.</span><span class="dm">Awaiting content</span></label>
  </div>
</div></section>

<section class="screen" id="scr-inst-events"><div class="wrap prose">
  <label class="back" for="s-inst">&larr; Instructions</label>
  <h1 style="font-size:34px">Creating &amp; archiving events</h1>

  <h2>The loop</h2>
  <ol>
    <li><strong>Create the draft.</strong> Events &rarr; New Event. Fill in title, category, date, time, location, and capacity. Leave status on <em>Draft</em>, so nothing is visible to residents yet.</li>
    <li><strong>Write both descriptions.</strong> The short one is a single line and appears in the list view. The full one appears on the event page. Write the full one as if the reader knows nothing about the event.</li>
    <li><strong>Build the asset kit.</strong> Six pieces, same six every time. See <em>Brand &amp; Canva templates</em> for sizes.</li>
    <li><strong>Publish.</strong> Change status to <em>Live</em>. It appears on the calendar immediately.</li>
    <li><strong>Promote, in this order:</strong> Mailchimp campaign, then the Nixplay playlist, then the printed signs. All three point at the same event page.</li>
    <li><strong>After it happens:</strong> record actual attendance, then set status to <em>Archived</em>.</li>
  </ol>

  <h2>Pulling an event back down</h2>
  <table>
    <tr><th>State</th><th>What it means</th></tr>
    <tr><td>Draft</td><td>Never published. Still being written; residents have never seen it.</td></tr>
    <tr><td>Live</td><td>On the resident calendar, taking RSVPs.</td></tr>
    <tr><td>Unpublished</td><td>Was live, now pulled. Disappears from the calendar, <strong>RSVPs are held</strong>, and putting it back Live restores it unchanged.</td></tr>
    <tr><td>Archived</td><td>Over. Hidden from residents, kept in full for reporting.</td></tr>
  </table>
  <div class="callout"><strong>Unpublishing is silent. Cancelling is not.</strong> If an event has RSVPs and it truly is
  not happening, use <em>Cancel &amp; notify guests</em>, which emails everyone who signed up. Unpublishing tells nobody,
  which is right when you are re-timing a date and wrong when twelve people have it in their calendar. The difference between
  those two buttons is the difference between a quiet edit and someone arriving on Level 39 to an empty room.</div>

  <div class="callout"><strong>Archive, never delete.</strong> An archived event disappears from the resident calendar but keeps its
  views, RSVPs, and attendance. Delete it and the monthly report loses that history permanently — and a comparison to last
  year&rsquo;s version of the same event is the most useful number you will ever hand the Board.</div>

  <h2>The four categories</h2>
  <p>Every event takes exactly one, and the names match the budget line items so the monthly report rolls up against what Scott already sees.</p>
  <p>The calendar carries <strong>everything happening in the building</strong>, not only what Resident Experiences runs. That is the point of having one place to look. Events hosted by someone else carry their host&rsquo;s name and sit outside the engagement figures.</p>
  <table>
    <tr><th>Category</th><th>What lands here</th></tr>
    <tr><td>Morning Offerings</td><td>Caf&eacute; 181 and anything else that runs before the day starts</td></tr>
    <tr><td>Happy Hours</td><td>The weekly Tuesday and Thursday gatherings</td></tr>
    <tr><td>Community Dinners</td><td>Seated dinners for the building, ticketed or paid</td></tr>
    <tr><td>Culinary Experiences</td><td>Brunch, tastings, dumpling and kimchi classes, wine &amp; cheese</td></tr>
    <tr><td>Enrichment Experiences</td><td>Book club, moss wall, skincare, and everything else that isn&rsquo;t food-led</td></tr>
    <tr><td>Signature Events</td><td>The end-of-year gala and anything else carrying its own approved budget</td></tr>
  </table>
  <div class="callout"><strong>When an event could sit in two, the budget decides.</strong> A dumpling-making class is a
  Culinary Experience even though it is shaped like a workshop, because the culinary line pays for it. That removes the
  judgment call and keeps the report honest. You only ever have to ask who is paying.</div>

  <h2>Capacity and waitlists</h2>
  <p>Capacity is enforced automatically. Once RSVPs reach the number, the button changes to <em>Join the Waitlist</em> and continues collecting names. Raise the capacity number and waitlisted residents are promoted in the order they signed up.</p>

  <h2>Timing</h2>
  <table>
    <tr><th>When</th><th>What</th></tr>
    <tr><td>3 weeks out</td><td>Event goes Live; assets complete</td></tr>
    <tr><td>2 weeks out</td><td>Mailchimp campaign; Nixplay playlist updated</td></tr>
    <tr><td>1 week out</td><td>Elevator prints posted</td></tr>
    <tr><td>Monday of the event week</td><td>RSVP closes on workshops, so materials are ordered against a firm count</td></tr>
    <tr><td>1 day out</td><td>Automated reminder to everyone who RSVP&rsquo;d</td></tr>
    <tr><td>Day after</td><td>Thank-you email; record attendance</td></tr>
    <tr><td>Within a week</td><td>Archive</td></tr>
  </table>
</div></section>

<section class="screen" id="scr-inst-brand"><div class="wrap prose">
  <label class="back" for="s-inst">&larr; Instructions</label>
  <h1 style="font-size:34px">Brand &amp; Canva templates</h1>

  <h2>Palette</h2>
  <div class="swatches">
    <div class="sw"><div class="chip2" style="background:#c41f26"></div><div class="nm">Brand red</div><div class="hx">#C41F26</div></div>
    <div class="sw"><div class="chip2" style="background:#16161a"></div><div class="nm">Ink</div><div class="hx">#16161A</div></div>
    <div class="sw"><div class="chip2" style="background:#f7f4ef"></div><div class="nm">Paper</div><div class="hx">#F7F4EF</div></div>
    <div class="sw"><div class="chip2" style="background:#7a7266"></div><div class="nm">Stone</div><div class="hx">#7A7266</div></div>
  </div>
  <p>Red is an accent only: a rule, a button, a marker. It is never a background for a full panel. Red as a dominant color reads as a warning and cheapens the look.</p>

  <h2>Type</h2>
  <table>
    <tr><th>Role</th><th>Typeface</th><th>Rule</th></tr>
    <tr><td>Display</td><td>Marcellus <span style="color:var(--stone)">(stand-in for Quainton)</span></td><td>Titles and the building name only. Never below 20px.</td></tr>
    <tr><td>Body</td><td>Hanken Grotesk <span style="color:var(--stone)">(stand-in for Sofia Pro)</span></td><td>Everything a person actually reads. Never below 16px.</td></tr>
  </table>
  <div class="callout"><strong>The one rule that governs everything:</strong> the display face carries the glamour at large sizes, and
  a sturdy sans does all the reading. If the building licenses web versions of Quainton and Sofia Pro, swap them in and the
  rule is unchanged.</div>

  <h2>The six assets, every event</h2>
  <div class="tblwrap"><table>
    <tr><th>Asset</th><th>Size</th><th>Format</th><th>Where it goes</th></tr>
    <tr><td>Web hero</td><td>1600 &times; 900 <span style="color:var(--stone)">(16:9)</span></td><td>JPG, under 500 KB</td><td>Event page on 181residents.com</td></tr>
    <tr><td>Nixplay still</td><td>1920 &times; 1080</td><td>JPG or PNG</td><td>Bar, Lobby, Level 7 screens</td></tr>
    <tr><td>Nixplay video <span style="color:var(--stone)">(optional)</span></td><td>1920 &times; 1080, 10&ndash;20 sec</td><td>MP4, H.264</td><td>Same three screens. Manual upload only, see Screens &amp; Print</td></tr>
    <tr><td>Elevator print</td><td>8.5 &times; 11 portrait, 300 DPI</td><td>Print-ready PDF</td><td>Elevator frames</td></tr>
    <tr><td>Level 39 print <span style="color:var(--stone)">(optional)</span></td><td>8.5 &times; 11 portrait, 300 DPI</td><td>Print-ready PDF</td><td>Level 39 landing sign</td></tr>
    <tr><td>Email header</td><td>1200 &times; 600</td><td>JPG, under 200 KB</td><td>Mailchimp campaign</td></tr>
  </table></div>
  <div class="callout"><strong>The two prints are the same design, not the same file.</strong> Both are 8.5 &times; 11
  portrait, but each carries its own QR code so a scan in the elevator and a scan on the Level 39 landing are told apart in
  the dashboard. Export twice from the same Canva page with the QR swapped.<br><br>
  <strong>Still to confirm:</strong> the Nixplay screen orientation at the bar, lobby, and Level 7. Portrait screens
  need a 1080 &times; 1920 variant instead of 1920 &times; 1080.</div>

  <h2>How the Canva side works</h2>
  <ol>
    <li>One Canva <strong>folder per event</strong>, named with the file stem: <code>2026-09-17_skyline-chef-series</code></li>
    <li>Inside it, duplicate the six brand templates rather than starting from blank. Type, logo placement, and margins are locked in the templates so nothing drifts.</li>
    <li>Swap the photo and the title. Nothing else.</li>
    <li>Export all six, named with the stem plus the asset type.</li>
    <li>Upload the kit here under Assets.</li>
  </ol>
  <p>An event image is optional. If there isn&rsquo;t a good photo, the event page falls back to a typographic card automatically — that is by design, so a rushed event never gets a bad stock photo.</p>
</div></section>

<section class="screen" id="scr-inst-screens"><div class="wrap prose">
  <label class="back" for="s-inst">&larr; Instructions</label>
  <h1 style="font-size:34px">Screens &amp; print</h1>

  <h2>The three screens</h2>
  <p>Nixplay drives three Smart Frame 15 inch Touch displays: the <strong>bar</strong>, the <strong>lobby</strong>, and the <strong>Level 7 landing</strong>. Each frame is named and given a location in the Nixplay dashboard, so settings can be checked per screen rather than guessed at. The building is on Nixplay <em>frames</em>, which means there is a shortcut most people never find:</p>

  <div class="callout"><strong>The frames have their own email address.</strong>
  <code>181concierge@mynixplay.com</code>. Anything emailed there lands in the <em>Emailed</em> album, which is already
  assigned to the frames. Send a picture and it appears on the screens. No app, no dashboard, no manual upload.</div>

  <h3>What this makes possible</h3>
  <p>Because it is just an email address, publishing to the screens can be automated. When a Nixplay still is added to an event&rsquo;s asset kit here, a rule emails it straight to the frames. One upload, and the artwork is on the web page and on all three screens.</p>
  <p>It is the closest thing to a real integration Nixplay offers, as there is no developer API, and for this building it is enough.</p>

  <div class="callout"><strong>Treat that address like a password.</strong> Anyone who has it can put an image on the
  lobby, bar, and Level 7 screens. It belongs in this admin and in the automation, and nowhere else. Not on a printed sheet, not in a resident email, and not in a shared Canva folder.</div>

  <h3>The two things email can&rsquo;t do</h3>
  <ol>
    <li><strong>Video.</strong> Email-to-frame carries photos. Whether the frames play video at all depends on the model, and it will not arrive this way. Video goes through the Nixplay app or web dashboard. Worth deciding whether the video asset is worth producing at all, or whether a strong still does the job.</li>
    <li><strong>Expiry.</strong> Everything emailed accumulates in one album with no schedule and no end date. Nothing removes a past event on its own.</li>
  </ol>

  <div class="callout"><strong>So the one manual step that matters is removal, not upload.</strong> A poster for a dinner
  that already happened is worse than no poster. It tells every resident walking through the lobby that nobody is
  paying attention. Clear the Emailed album the morning after each event.</div>

  <h3>Frame settings, as they should be</h3>
  <p>The frames are Smart Frame 15 inch Touch. Four settings matter, and three of them are currently not set the way signage wants.</p>
  <div class="tblwrap"><table>
    <tr><th>Setting</th><th>Set to</th><th>Why</th></tr>
    <tr><td>Playback mode</td><td><strong>All photos</strong>, with a clean account</td><td>See the note below. This is the one real decision.</td></tr>
    <tr><td>Sleep schedule</td><td><strong>On</strong>, roughly 6:00 to 11:00 pm</td><td>A frame glowing at three in the morning in an empty lobby looks like nobody is minding the building. It also saves the panel.</td></tr>
    <tr><td>Motion sensor</td><td><strong>Off</strong></td><td>The frame&rsquo;s own note says a sleep schedule disables motion anyway. In a lobby with steady traffic, motion means residents catch a black screen for a moment before it wakes, which looks broken rather than clever.</td></tr>
    <tr><td>When frame wakes up</td><td>Continue the current album</td><td>Fine as it is. Starting over each morning would mean the same image greets everyone at the same hour.</td></tr>
  </table></div>

  <div class="callout"><strong>The one real decision: All photos, or a playlist.</strong><br><br>
  On <em>All photos</em> the frame plays everything in the account, so an emailed still appears with no further steps. That is
  what makes the email automation worth having. The cost is that nothing expires on its own, so the account has to be kept
  clean by hand.<br><br>
  On a <em>playlist</em> you control exactly what shows and in what order, but emailed images land in the Emailed album rather
  than the playlist, so every image needs moving across. That is a manual step on every event, which is the thing we were
  trying to remove.<br><br>
  <strong>Keep All photos, and treat the account as signage rather than a photo library.</strong> Every image in it should be
  for something that has not happened yet. That makes the discipline simple enough to actually keep: clear the album the
  morning after each event.</div>

  <h3>Publishing an event to the screens</h3>
  <ol>
    <li>Export the Nixplay still from the event&rsquo;s Canva folder.</li>
    <li>Upload it to the Assets kit here. This stays the master copy, and it triggers the email to the frames.</li>
    <li>Confirm it appeared on all three screens. They are cloud-connected, so a screen that&rsquo;s offline silently shows nothing new.</li>
    <li>Remove it from the Emailed album the morning after the event.</li>
  </ol>
  <p>Design for distance. These are read by people walking past, not standing still. One idea, a large title, and the date. If it needs a second read, it is too much.</p>
  <div class="callout"><strong>Do not rely on a QR code on the screens.</strong> A code has to be roughly a tenth of the
  distance it is scanned from, so at four feet it needs to be nearly five inches across. On a fifteen inch frame that is a
  third of the width, and it would dominate the artwork. Let the screens announce and the printed signs carry the code.
  Anyone standing close enough to scan a frame is close enough to read a poster.</div>

  <h2>Prints, in two locations</h2>
  <p>Both are 8.5 &times; 11 portrait: the <strong>elevator frames</strong>, and a second sign on the <strong>Level 39 landing</strong>. The Level 39 sign is used rarely, though it is worth producing whenever the event is on Level 39, which is nearly all of them.</p>
  <ol>
    <li>Export both as print-ready PDFs at 300 DPI.</li>
    <li>Post one week out, and remove them the morning after, the same rule as the screens.</li>
    <li>Each print carries a <strong>different QR code</strong>, even though the artwork is otherwise identical. That is what lets the dashboard tell an elevator scan from a Level 39 scan, and tells you whether the second sign is earning its place.</li>
  </ol>
  <p>Note that Level 39 has a printed sign but no Nixplay screen. The screens are the bar, the lobby, and the Level 7 landing.</p>

  <h2>Why all of it points to one place</h2>
  <p>The screens, the prints, the emails, and the QR standees all lead to the same event page on 181residents.com. That is the whole consolidation strategy: the artwork lives in different places because it has to, but there is only ever one source of truth for what an event is, and one destination for everyone who sees it.</p>
</div></section>

<section class="screen" id="scr-inst-email"><div class="wrap prose">
  <label class="back" for="s-inst">&larr; Instructions</label>
  <h1 style="font-size:34px">Email templates</h1>
  <div class="callout"><strong>Awaiting your templates.</strong> Send them over and they will be formatted into this section, with the merge fields and send timing documented alongside each one.</div>
  <h2>What this section will hold</h2>
  <table>
    <tr><th>Template</th><th>Trigger</th><th>Status</th></tr>
    <tr><td>Weekly resident email</td><td>Manual, weekly</td><td>Awaiting content</td></tr>
    <tr><td>RSVP confirmation</td><td>Automatic, on RSVP</td><td>Awaiting content</td></tr>
    <tr><td>Reminder</td><td>Automatic, 1 day before</td><td>Awaiting content</td></tr>
    <tr><td>Thank-you &amp; feedback</td><td>Automatic, day after</td><td>Awaiting content</td></tr>
    <tr><td>Waitlist promotion</td><td>Automatic, on a spot opening</td><td>Awaiting content</td></tr>
  </table>
</div></section>

</div>
<div class="toast" id="toast"></div>
<script>
{APP_JS}
</script>
</body>
</html>
'''

import os
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "181fremont_admin_prototype.html"), "w", encoding="utf-8").write(HTML)
print("built", len(HTML), "bytes")
