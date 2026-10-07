# Renders a Pages-builder page (a D1 row: title, slug, eyebrow, lede, blocks
# JSON) into the same standalone house template Fleet Week proved: no
# JavaScript, 19px body, Marcellus display, native <details> folds, clamps for
# phones. The builder decides words and order; everything visual is fixed here.
#
# Block kinds the publisher knows (anything else is skipped, so an unknown
# kind can never break a build):
#   text     {body}                     paragraphs; blank line starts a new one
#   feature  {heading, when, body}      the red-edged hero card
#   heading  {heading, sub}             a section heading with a small line
#   fold     {title, lines, ours}       a tap-to-open day; lines "time : what",
#                                       one per line; ours = an optional lead
#                                       red-dot Residents' Club row
#   bullets  {lines}                    the red-square fact list, one per line
#   links    {lines}                    place rows "Title : small line", the
#                                       title linking when a URL is given as
#                                       "Title : https://... : small line"
#   image    {stem}                     a kit web hero, served from /hero/{stem}

import html as _html
import json
import re


def _esc(s):
    return _html.escape(str(s or ""), quote=True)


def _paras(s):
    out = []
    for para in re.split(r"\n\s*\n", str(s or "").strip()):
        if para.strip():
            out.append("<p>" + _esc(para).replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def _split_line(line):
    # "Noon : what happens" — the first separator splits time from text. A
    # middot works too, since that is how staff see times everywhere else.
    for sep in (" : ", " · ", " · "):
        if sep in line:
            a, b = line.split(sep, 1)
            return a.strip(), b.strip()
    return "", line.strip()


def _fold(b):
    rows = []
    for line in str(b.get("lines") or "").split("\n"):
        if not line.strip():
            continue
        t, w = _split_line(line)
        rows.append(f'<div class="ev"><span class="tm">{_esc(t)}</span><span class="wh">{_esc(w)}</span></div>')
    ours = str(b.get("ours") or "").strip()
    ours_html = f'<div class="ours"><span class="dot"></span>{_esc(ours)}</div>' if ours else ""
    return (f'<details><summary><span class="dy">{_esc(b.get("title"))}</span>'
            f'<span class="chev">&rsaquo;</span></summary>'
            f'<div class="dbody">{ours_html}{"".join(rows)}</div></details>')


def _links(b):
    out = []
    for line in str(b.get("lines") or "").split("\n"):
        if not line.strip():
            continue
        parts = [p.strip() for p in re.split(r" : | · ", line, maxsplit=2)]
        title, url, sub = parts[0], "", ""
        rest = parts[1:]
        for p in rest:
            if p.startswith("http://") or p.startswith("https://"):
                url = p
            else:
                sub = p
        head = (f'<a href="{_esc(url)}" target="_blank" rel="noopener">{_esc(title)}</a>'
                if url else _esc(title))
        sub_html = f'<br><span class="sub">{_esc(sub)}</span>' if sub else ""
        out.append(f'<div class="place"><b>{head}</b>{sub_html}</div>')
    return "\n".join(out)


def _block(b):
    kind = b.get("kind")
    if kind == "text":
        return _paras(b.get("body"))
    if kind == "feature":
        when = f'<div class="when">{_esc(b.get("when"))}</div>' if str(b.get("when") or "").strip() else ""
        return (f'<div class="hero"><h2>{_esc(b.get("heading"))}</h2>{when}'
                f'{_paras(b.get("body"))}</div>')
    if kind == "heading":
        sub = f'<p class="sd">{_esc(b.get("sub"))}</p>' if str(b.get("sub") or "").strip() else ""
        return f'<h2 class="sec">{_esc(b.get("heading"))}</h2>{sub}'
    if kind == "fold":
        return _fold(b)
    if kind == "bullets":
        items = "".join(f"<li>{_esc(l.strip())}</li>"
                        for l in str(b.get("lines") or "").split("\n") if l.strip())
        return f'<ul class="facts">{items}</ul>' if items else ""
    if kind == "links":
        return _links(b)
    if kind == "image":
        stem = re.sub(r"[^A-Za-z0-9_.-]", "", str(b.get("stem") or ""))
        return (f'<div class="pimg"><img src="/hero/{_esc(stem)}" alt=""></div>') if stem else ""
    return ""


CSS = """
  :root{
    --ink:#16161a; --ink-body:#3a3a43; --ink-soft:#55555f;
    --paper:#f7f4ef; --paper-2:#fffdfa; --line:#ddd6cb;
    --red:#c41f26; --stone:#7a7266; --radius:4px;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{background:var(--paper);color:var(--ink-body);
    font-family:'Hanken Grotesk',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    font-size:19px;line-height:1.6;
    padding:0 max(20px, env(safe-area-inset-left)) 60px max(20px, env(safe-area-inset-right))}
  .wrap{max-width:720px;margin:0 auto}
  a{color:var(--red)}
  .back{display:inline-block;margin:26px 0 8px;font-size:16px;color:var(--stone);text-decoration:none;min-height:54px;line-height:54px}
  .back:hover{color:var(--ink)}
  .eyebrow{font-size:clamp(11px,2.8vw,12.5px);letter-spacing:.22em;text-transform:uppercase;
    color:var(--stone);font-weight:600;margin:4px 0 10px}
  h1{font-family:'Marcellus',Georgia,serif;font-weight:400;color:var(--ink);
    font-size:clamp(32px,8vw,46px);line-height:1.12;margin:0 0 10px}
  .tick{width:76px;height:4px;background:var(--red);margin:18px 0 22px}
  .lede{font-size:clamp(17px,4.4vw,20px);color:var(--ink-soft);max-width:36em;margin:0 0 30px}
  .hero{background:var(--paper-2);border:1px solid var(--line);border-left:4px solid var(--red);
    border-radius:var(--radius);padding:clamp(20px,5vw,30px) clamp(20px,5vw,32px);margin:0 0 34px}
  .hero h2{font-family:'Marcellus',Georgia,serif;font-weight:400;color:var(--ink);
    font-size:clamp(23px,5.6vw,28px);margin:0 0 6px}
  .hero .when{font-size:clamp(15px,3.8vw,16.5px);letter-spacing:.06em;text-transform:uppercase;
    color:var(--red);font-weight:600;margin:0 0 14px}
  .hero p{margin:10px 0}
  h2.sec{font-family:'Marcellus',Georgia,serif;font-weight:400;color:var(--ink);
    font-size:clamp(24px,6vw,30px);margin:46px 0 6px;padding-top:26px;border-top:1px solid var(--line)}
  .sd{color:var(--ink-soft);margin:0 0 18px}
  details{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);
    margin:0 0 10px;overflow:hidden}
  summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;
    gap:12px;min-height:54px;padding:6px 18px;font-family:'Marcellus',Georgia,serif;
    font-size:clamp(18px,4.8vw,21px);color:var(--ink)}
  summary::-webkit-details-marker{display:none}
  summary:hover{background:var(--paper)}
  .chev{color:var(--stone);font-size:26px;line-height:1;transition:transform .15s;flex:none}
  details[open] .chev{transform:rotate(90deg)}
  details[open] summary{border-bottom:1px solid var(--line)}
  .dbody{padding:14px 18px 18px}
  .ev{display:flex;gap:14px;padding:9px 0;border-top:1px solid var(--paper)}
  .ev:first-of-type{border-top:none}
  .tm{flex:none;width:86px;font-weight:600;color:var(--ink);font-size:16px;padding-top:2px}
  .tm:empty{display:none}
  .wh{font-size:clamp(16px,4.2vw,17.5px)}
  .ours{display:flex;gap:10px;align-items:baseline;background:var(--paper);border:1px solid var(--line);
    border-radius:var(--radius);padding:10px 14px;margin:2px 0 12px;color:var(--ink);font-weight:600;
    font-size:clamp(15.5px,4vw,17px)}
  .ours .dot{flex:none;width:9px;height:9px;border-radius:50%;background:var(--red);position:relative;top:-1px}
  ul.facts{list-style:none;margin:0 0 10px;padding:0}
  ul.facts li{position:relative;padding:7px 0 7px 22px}
  ul.facts li::before{content:"";position:absolute;left:0;top:.95em;width:8px;height:8px;background:var(--red)}
  .place{padding:14px 0;border-top:1px solid var(--line)}
  .place:first-of-type{border-top:none}
  .place b{color:var(--ink);font-weight:600}
  .place .sub{font-size:clamp(15.5px,4vw,17px);color:var(--ink-soft)}
  .pimg{margin:6px 0 26px}
  .pimg img{width:100%;border-radius:var(--radius);display:block;aspect-ratio:16/9;object-fit:cover}
  footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
    color:var(--stone);font-size:15px}
  footer a{color:var(--stone)}
"""


def render(page):
    blocks = page.get("blocks")
    if isinstance(blocks, str):
        try:
            blocks = json.loads(blocks)
        except ValueError:
            blocks = []
    if not isinstance(blocks, list):
        blocks = []
    body = "\n\n".join(h for h in (_block(b) for b in blocks if isinstance(b, dict)) if h)
    eyebrow = f'<div class="eyebrow">{_esc(page.get("eyebrow"))}</div>' if str(page.get("eyebrow") or "").strip() else ""
    lede = f'<p class="lede">{_esc(page.get("lede"))}</p>' if str(page.get("lede") or "").strip() else ""
    title = _esc(page.get("title"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} &middot; 181 Fremont</title>
<link rel="icon" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fonts/fonts.css">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<a class="back" href="/">&larr; Back to the calendar</a>

{eyebrow}
<h1>{title}</h1>
<div class="tick"></div>
{lede}

{body}

<footer>The Residents&rsquo; Club &middot; 181 Fremont &middot; questions, write to us through the
<a href="/">calendar&rsquo;s</a> Message page</footer>

</div>
</body>
</html>
"""
