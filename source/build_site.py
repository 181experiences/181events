#!/usr/bin/env python3
"""Assembles the production site from the two builders and adds everything a
deployed site needs: manifest, icons, theme colour, and the save-to-home-screen
prompt. The prompt is progressive enhancement only. With scripts blocked the
calendar still works exactly as it does now."""

import subprocess, shutil, os, json

import sys
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.environ.get("SITE_OUT", os.path.join(HERE, "..", "site"))
os.makedirs(SITE, exist_ok=True)

# Icons (the bay mark, variation 9) and the README are shipped assets, not generated.
# Copy them in so a rebuild into an empty folder is still a complete deploy.
ASSETS = os.path.join(HERE, "assets")
for f in os.listdir(ASSETS):
    src = os.path.join(ASSETS, f)
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(SITE, f), dirs_exist_ok=True)
    else:
        shutil.copy(src, os.path.join(SITE, f))

subprocess.run([sys.executable, "make_seed.py", os.path.join(SITE, "events_seed.json")], check=True, cwd=HERE)
subprocess.run([sys.executable, "build_proto.py"], check=True, cwd=HERE)
subprocess.run([sys.executable, "build_admin.py"], check=True, cwd=HERE)

HEAD = '''<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" href="/favicon-32.png" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<meta name="theme-color" content="#16161a">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="181 Events">
<meta name="description" content="Everything happening at 181 Fremont, in one place.">
<meta name="robots" content="noindex, nofollow">
'''

PROMPT_CSS = '''
  /* ---------- save to home screen ---------- */
  #savecard{position:fixed;left:14px;right:14px;bottom:14px;z-index:900;background:var(--paper-2);
    border:1px solid var(--line);border-radius:8px;padding:22px 20px;display:none;
    box-shadow:0 -10px 34px rgba(0,0,0,.16);animation:rise .3s ease}
  #savecard.show{display:block}
  @keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
  #savecard .sc-t{font-family:var(--fd);font-size:23px;color:var(--ink);line-height:1.2}
  #savecard .sc-p{font-size:16px;color:var(--ink-soft);margin-top:8px;line-height:1.5}
  #savecard ol{margin:16px 0 0;padding:0;list-style:none}
  #savecard li{display:flex;gap:12px;align-items:center;font-size:16px;color:var(--ink);margin-bottom:11px}
  #savecard .n{flex:0 0 26px;height:26px;border-radius:50%;background:var(--ink);color:var(--paper-2);
    display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600}
  #savecard .shareico{display:inline-flex;vertical-align:-5px;color:var(--red);margin:0 4px}
  #savecard .sc-row{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}
  #savecard .sc-b{flex:1 1 auto;text-align:center;border:1px solid var(--line);border-radius:var(--radius);
    padding:16px 12px;font-size:14px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;
    color:var(--ink);background:transparent;min-height:54px;cursor:pointer;font-family:inherit}
  #savecard .sc-b.primary{background:var(--red);border-color:var(--red);color:#fff;flex:1 1 100%}
  #savecard .sc-b.quiet{color:var(--stone);font-size:13px;letter-spacing:.08em}
  #savecard kbd{display:inline-block;border:1px solid #c9c0b3;border-bottom-width:2px;border-radius:4px;
    padding:2px 9px;font-size:14px;background:var(--paper);color:var(--ink);font-weight:600;
    font-family:inherit;margin:0 2px}
  @media(min-width:760px){
    #savecard{left:auto;right:22px;bottom:22px;width:360px}
  }
'''

PROMPT_HTML = '''
<div id="savecard" role="dialog" aria-label="Save this calendar">
  <div class="sc-t">Keep this to hand</div>
  <div class="sc-p" id="sc-sub"></div>
  <ol id="sc-steps"></ol>
  <div class="sc-row">
    <button class="sc-b primary" id="sc-install" hidden>Add to home screen</button>
    <button class="sc-b" id="sc-later">Not now</button>
    <button class="sc-b quiet" id="sc-never">Don&rsquo;t show again</button>
  </div>
</div>
'''

PROMPT_JS = '''
<script>
(function () {
  var K = { seen: "f181-visits", off: "f181-nosave" };
  function get(k){ try { return localStorage.getItem(k); } catch(e) { return null; } }
  function set(k,v){ try { localStorage.setItem(k,v); } catch(e) {} }

  // Already using the saved version? Then never ask.
  var standalone = window.matchMedia("(display-mode: standalone)").matches
                || window.navigator.standalone === true;
  if (standalone) return;
  if (get(K.off) === "1") return;

  var visits = parseInt(get(K.seen) || "0", 10) + 1;
  set(K.seen, String(visits));

  var ua = navigator.userAgent || "";
  var isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var isTouch = isIOS || /Android/.test(ua);
  var deferred = null;

  var card    = document.getElementById("savecard");
  var sub     = document.getElementById("sc-sub");
  var steps   = document.getElementById("sc-steps");
  var install = document.getElementById("sc-install");

  var SHARE = '<span class="shareico"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" '
    + 'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    + '<path d="M12 15V3"/><path d="M8 7l4-4 4 4"/>'
    + '<path d="M4 13v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6"/></svg></span>';

  function render() {
    if (isIOS) {
      sub.textContent = "Two taps, and the calendar sits with your apps. No password, no app store.";
      steps.innerHTML =
        '<li><span class="n">1</span><span>Tap ' + SHARE + ' at the bottom of the screen</span></li>' +
        '<li><span class="n">2</span><span>Choose <strong>Add to Home Screen</strong></span></li>';
    } else if (deferred) {
      sub.textContent = isTouch
        ? "One tap, and the calendar sits with your apps. No password, no app store."
        : "Install it once, and the calendar opens in its own window.";
      steps.innerHTML = "";
      install.hidden = false;
    } else {
      var mac = /Mac/.test(navigator.platform);
      sub.innerHTML = "Bookmark the calendar so it is always a click away.";
      steps.innerHTML = '<li><span>Press <kbd>' + (mac ? "\\u2318" : "Ctrl") + '</kbd> <kbd>D</kbd></span></li>';
    }
    card.classList.add("show");
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    if (visits >= 2) render();
  });

  install.addEventListener("click", function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.then(function () { card.classList.remove("show"); deferred = null; });
  });
  document.getElementById("sc-later").addEventListener("click", function () {
    card.classList.remove("show");
  });
  document.getElementById("sc-never").addEventListener("click", function () {
    set(K.off, "1");
    card.classList.remove("show");
  });
  window.addEventListener("appinstalled", function () { set(K.off, "1"); card.classList.remove("show"); });

  // Second visit onward. iOS and desktop never fire beforeinstallprompt, so show on a short delay.
  if (visits >= 2 && (isIOS || !isTouch)) setTimeout(render, 1200);
})();
</script>
'''

# ---------------------------------------------------------------- resident site
html = open(os.path.join(HERE, "181fremont_residents_prototype.html"), encoding="utf-8").read()

# calendar files: build_proto collects them while rendering, we place them
sys.path.insert(0, HERE)
import build_proto as _bp
os.makedirs(f"{SITE}/ics", exist_ok=True)
for _old in os.listdir(f"{SITE}/ics"):
    os.remove(os.path.join(f"{SITE}/ics", _old))
for _fname, _body in _bp.ICS_FILES.items():
    open(os.path.join(f"{SITE}/ics", _fname), "w", encoding="utf-8", newline="").write(_body)
print("ics files:", len(_bp.ICS_FILES))
html = html.replace('<div class="mocknote">Prototype &middot; real calendar, nothing here is live yet</div>\n\n', "")
html = html.replace("</head>", HEAD + "</head>")
html = html.replace("</style>", PROMPT_CSS + "</style>", 1)
html = html.replace("</body>", PROMPT_HTML + PROMPT_JS + "</body>")
open(f"{SITE}/index.html", "w", encoding="utf-8").write(html)

# Each QR standee and the weekly email land on their own copy of the calendar, so Cloudflare
# Web Analytics can count them separately. Keep in step with SOURCES in functions/api/analytics.js.
QR_PATHS = ["lobby", "coffee", "fitness", "office", "email"]
for q in QR_PATHS:
    os.makedirs(f"{SITE}/q/{q}", exist_ok=True)
    open(f"{SITE}/q/{q}/index.html", "w", encoding="utf-8").write(html)

# ---------------------------------------------------------------- admin
admin = open(os.path.join(HERE, "181fremont_admin_prototype.html"), encoding="utf-8").read()
admin = admin.replace('<div class="mocknote">Admin prototype — sample data, nothing here saves</div>\n\n', "")
admin = admin.replace("</head>", HEAD.replace('href="/manifest.webmanifest"', 'href="/manifest.webmanifest"') + "</head>")
open(f"{SITE}/admin.html", "w", encoding="utf-8").write(admin)

# ---------------------------------------------------------------- manifest
manifest = {
    "name": "181 Fremont Resident Events",
    "short_name": "181 Events",
    "description": "Everything happening at 181 Fremont, in one place.",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f7f4ef",
    "theme_color": "#16161a",
    "orientation": "portrait",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
    ],
}
open(f"{SITE}/manifest.webmanifest", "w", encoding="utf-8").write(json.dumps(manifest, indent=2))

# keep robots honest while it is a private resident site
open(f"{SITE}/robots.txt", "w", encoding="utf-8").write("User-agent: *\nDisallow: /\n")
open(f"{SITE}/_headers", "w", encoding="utf-8").write(
    "/*\n  X-Frame-Options: SAMEORIGIN\n  X-Content-Type-Options: nosniff\n"
    "  Referrer-Policy: strict-origin-when-cross-origin\n"
    # Pages labels .ics as text/html by default; iPhones only open calendar files
    # in Calendar when the label is right.
    "/ics/*\n  Content-Type: text/calendar; charset=utf-8\n")

size = sum(os.path.getsize(os.path.join(SITE, f)) for f in os.listdir(SITE))
print("site built:", len(os.listdir(SITE)), "files,", round(size / 1024), "KB")
