"""Local mirror of functions/api/inventory/[[path]].js, route for route.

dev_server.py hands every /api/inventory* request here with a small env of
its helpers, so this module never imports the server (no cycle). State lives
in dev_inv_*.json beside the server. Keep the report builder in lockstep with
buildReport in the Functions module: the two must say the same things."""
import json, html, datetime, re
from urllib.parse import parse_qs

REPORT_FROM = "reports@181residents.com"
PACIFIC = datetime.timezone(datetime.timedelta(hours=-7))  # close enough for a local preview

def esc(s): return html.escape("" if s is None else str(s), quote=True)

def num(v):
    if v is None or v == "": return None
    try: return float(v)
    except (TypeError, ValueError): return None

def name_of(email):
    s = re.sub(r"[._-]+", " ", str(email or "").split("@")[0]).strip()
    return (s[0].upper() + s[1:]) if s else "staff"

def fmt_qty(q):
    if q is None: return ""
    if q == 0.5: return "½"
    if abs(q - round(q)) < 1e-9: return str(int(round(q)))
    return str(q)

def min_text(it):
    if it.get("minimum") is None: return ""
    return fmt_qty(it["minimum"]) + ((" " + it["unit"]) if it.get("unit") else "")

def is_low(it, qty):
    return qty is not None and it.get("minimum") is not None and qty <= it["minimum"]

def pacific(iso=None):
    d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")) if iso else datetime.datetime.now(datetime.timezone.utc)
    d = d.astimezone(PACIFIC)
    t = d.strftime("%I:%M %p").lstrip("0")
    return {"day": d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y"),
            "short": d.strftime("%A, %b ") + str(d.day), "time": t}

S = {
    "body": "font-family:Arial,Helvetica,sans-serif;color:#16161a;font-size:14px;line-height:1.45;max-width:720px",
    "h1": "font-family:Georgia,serif;font-size:22px;color:#c41f26;margin:14px 0 2px;font-weight:normal",
    "rh": "border-bottom:2.5px solid #c41f26;padding-bottom:6px;font-family:Georgia,serif;letter-spacing:.14em;font-size:13px",
    "sub": "color:#55555f;font-size:13px;margin:0 0 14px",
    "h2": "font-family:Georgia,serif;font-size:15px;color:#c41f26;margin:18px 0 4px;border-bottom:1px solid #ddd6cb;padding-bottom:3px;font-weight:normal",
    "tag": "font-family:Arial,sans-serif;font-size:9px;letter-spacing:.14em;color:#7a7266;text-transform:uppercase;margin-left:8px",
    "th": "text-align:left;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#7a7266;border-bottom:2px solid #16161a;padding:4px 8px 4px 0",
    "td": "border-top:1px solid #ddd6cb;padding:5px 8px 5px 0;vertical-align:top;font-size:13px",
    "tdr": "border-top:1px solid #ddd6cb;padding:5px 0 5px 8px;vertical-align:top;font-size:13px;text-align:right;white-space:nowrap",
    "lowc": "color:#c41f26;font-weight:bold",
    "area": "font-family:Georgia,serif;background:#f7f4ef;padding:6px 8px 6px 0;font-size:14px",
    "note": "background:#f7f4ef;border-left:3px solid #c41f26;padding:8px 12px;margin-top:14px;font-size:13px",
    "ftr": "margin-top:18px;border-top:1px solid #ddd6cb;padding-top:6px;font-size:11px;color:#7a7266",
}

def build_report(count, areas, items, lines, notes, scope_ids, now_iso):
    in_scope = sorted([a for a in areas if a.get("active", 1) and (not scope_ids or a["id"] in scope_ids)],
                      key=lambda a: (a.get("ord", 0), a["id"]))
    qty_of = {l["item_id"]: l for l in lines}
    note_of = {n["area_id"]: n for n in notes}
    total = counted = 0
    low, rows_by_area, counters = [], [], set()
    for a in in_scope:
        its = sorted([i for i in items if i.get("active", 1) and i["area_id"] == a["id"]], key=lambda i: (i.get("ord", 0), i["id"]))
        rows = []
        for it in its:
            total += 1
            l = qty_of.get(it["id"]); qty = l["qty"] if l and l.get("qty") is not None else None
            if qty is not None:
                counted += 1
                if l.get("who"): counters.add(l["who"])
            lw = is_low(it, qty)
            shown = dict(it, name=f"{it['name']} ({l['label']})") if l and l.get("label") else it
            if lw: low.append((shown, a, qty))
            rows.append((shown, qty, lw))
        n = note_of.get(a["id"])
        rows_by_area.append((a, rows, n["body"] if n and n.get("body") else ""))
    when = pacific(count.get("submitted") or now_iso())
    started = pacific(count["started"])
    active_n = len([a for a in areas if a.get("active", 1)])
    scope_name = ", ".join(a["name"] for a in in_scope) if scope_ids and len(scope_ids) < active_n else "Full walk"
    people = []
    for p in [count.get("started_by")] + sorted(counters):
        if p and p not in people: people.append(p)
    people = [name_of(p) for p in people]
    complete = counted == total
    submit_no = (count.get("submits") or 0) + 1
    subject = ("RC Inventory, completes " + started["short"] if submit_no > 1 else "RC Inventory, " + when["short"]) + ": " \
        + (f"{len(low)} item{'' if len(low) == 1 else 's'} below minimum" if low else "nothing below minimum") \
        + ("" if complete else f" ({total - counted} not yet counted)")
    e = esc
    h = [f'<div style="{S["body"]}">',
         f'<div style="{S["rh"]}">181 FREMONT RESIDENCES <span style="float:right;font-family:Arial,sans-serif;letter-spacing:.2em;font-size:9px;color:#7a7266">RESIDENTS&rsquo; CLUB OPERATIONS</span></div>',
         f'<h1 style="{S["h1"]}">Inventory count &middot; {e(when["day"])}</h1>',
         f'<p style="{S["sub"]}">{e(scope_name)}, <b>{counted} of {total}</b> items counted'
         + ("" if complete else f' (<b style="{S["lowc"]}">{total - counted} still to count</b>)') + ". "
         + f'Counted by <b>{e(", ".join(people) or "staff")}</b>, started {e(started["short"])} {e(started["time"])}'
         + (f', submitted {e(when["time"])}' if count.get("submitted") else "") + ". "
         + (f'<b>{len(low)} item{"" if len(low) == 1 else "s"} at or below minimum.</b>' if low else "Nothing at or below its minimum.")
         + " Department heads review and place their own orders; nothing here is an order.</p>",
         f'<h2 style="{S["h2"]}">Below minimum<span style="{S["tag"]}">ORDER THESE, OR DECIDE NOT TO</span></h2>']
    if low:
        h.append(f'<table style="width:100%;border-collapse:collapse"><tr><th style="{S["th"]}">Item</th><th style="{S["th"]}">Where</th><th style="{S["th"]};text-align:right">Minimum</th><th style="{S["th"]};text-align:right">On hand</th><th style="{S["th"]}">Ordered by</th></tr>')
        for it, a, qty in low:
            h.append(f'<tr><td style="{S["td"]}">{e(it["name"])}</td><td style="{S["td"]}">{e(a["name"])}{" &middot; floor " + e(a["floor"]) if a.get("floor") else ""}</td><td style="{S["tdr"]}">{e(min_text(it))}</td><td style="{S["tdr"]};{S["lowc"]}">{e(fmt_qty(qty))}</td><td style="{S["td"]}">{e(it.get("orderer") or "")}</td></tr>')
        h.append("</table>")
    else:
        h.append(f'<p style="{S["sub"]}">Nothing. Every counted item sits above its minimum.</p>')
    noted = [x for x in rows_by_area if x[2]]
    if noted:
        h.append(f'<h2 style="{S["h2"]}">Notes from the walk</h2><table style="width:100%;border-collapse:collapse">')
        for a, _, note in noted:
            h.append(f'<tr><td style="{S["td"]};width:160px;color:#7a7266">{e(a["name"])}</td><td style="{S["td"]}">{e(note)}</td></tr>')
        h.append("</table>")
    h.append(f'<h2 style="{S["h2"]}">Everything counted<span style="{S["tag"]}">BY AREA, IN WALK ORDER</span></h2><table style="width:100%;border-collapse:collapse"><tr><th style="{S["th"]}">Item</th><th style="{S["th"]};text-align:right">Minimum</th><th style="{S["th"]};text-align:right">On hand</th></tr>')
    for a, rows, _ in rows_by_area:
        h.append(f'<tr><td colspan="3" style="{S["area"]}">{e(a["name"])}{" <span style=\"font-family:Arial,sans-serif;font-size:11px;color:#7a7266\">floor " + e(a["floor"]) + "</span>" if a.get("floor") else ""}</td></tr>')
        for it, qty, lw in rows:
            cell = '<span style="color:#7a7266;font-style:italic">not counted</span>' if qty is None else e(fmt_qty(qty))
            h.append(f'<tr><td style="{S["td"]}">{e(it["name"])}</td><td style="{S["tdr"]}">{e(min_text(it))}</td><td style="{S["tdr"]}{";" + S["lowc"] if lw else ""}">{cell}</td></tr>')
    h.append("</table>")
    h.append(f'<div style="{S["note"]}"><b>Counted on 181residents.com &middot; Operations &middot; Inventory.</b> The live record, with who counted what and when, is at the same address. Orders are placed by management from this report.</div>')
    h.append(f'<div style="{S["ftr"]}">Inventory count #{count["id"]} &middot; {"submitted " + e(when["day"]) + ", " + e(when["time"]) if count.get("submitted") else "not yet submitted"} &middot; 181residents.com/admin</div></div>')
    t = [f"INVENTORY COUNT, {when['day']}",
         f"{scope_name}, {counted} of {total} items counted{'' if complete else f' ({total - counted} still to count)'}. Counted by {', '.join(people) or 'staff'}.", "",
         "BELOW MINIMUM" if low else "BELOW MINIMUM: nothing"]
    for it, a, qty in low:
        t.append(f"- {it['name']} ({a['name']}): {fmt_qty(qty)} on hand, minimum {min_text(it)}{', ordered by ' + it['orderer'] if it.get('orderer') else ''}")
    if noted:
        t += ["", "NOTES FROM THE WALK"] + [f"- {a['name']}: {note}" for a, _, note in noted]
    t += ["", "EVERYTHING COUNTED"]
    for a, rows, _ in rows_by_area:
        t.append(a["name"] + (f" (floor {a['floor']})" if a.get("floor") else ""))
        for it, qty, lw in rows:
            t.append(f"  {it['name']}: {'not counted' if qty is None else fmt_qty(qty)}{' (BELOW MINIMUM)' if lw else ''} / min {min_text(it) or 'none'}")
    t += ["", "Orders are placed by management from this report. Live record: https://181residents.com/admin"]
    return {"html": "".join(h), "text": "\n".join(t), "subject": subject, "low": len(low), "counted": counted, "total": total, "complete": complete}

def report_page(title, inner):
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>
  body{{margin:0;background:#f2efe9;font-family:Arial,Helvetica,sans-serif}}
  .bar{{display:flex;gap:10px;align-items:center;padding:12px 20px;background:#16161a;color:#c9c2b6;font-size:12px;letter-spacing:.08em}}
  .bar button{{background:#c41f26;color:#fff;border:none;border-radius:4px;padding:8px 16px;font-size:13px;font-weight:bold;cursor:pointer}}
  .bar a{{color:#c9c2b6}}
  .sheet{{background:#fff;max-width:760px;margin:20px auto;padding:28px 32px;border:1px solid #ddd6cb}}
  @media print{{body{{background:#fff}}.bar{{display:none}}.sheet{{border:none;margin:0;padding:0;max-width:none}}@page{{size:Letter;margin:.6in}}}}
  @media(max-width:620px){{.sheet{{margin:0;padding:18px 16px}}}}
</style></head><body>
<div class="bar"><button onclick="window.print()">Print</button><span>{esc(title)}</span><span style="flex:1"></span><a href="/admin">Back to the admin</a></div>
<div class="sheet">{inner}</div></body></html>'''

def blank_sheet(areas, items):
    act = sorted([a for a in areas if a.get("active", 1)], key=lambda a: (a.get("ord", 0), a["id"]))
    td = "border-bottom:1px solid #ddd6cb;padding:7px 6px;font-size:12.5px;vertical-align:middle"
    box = "border-bottom:1px solid #ddd6cb;border-left:1px solid #ddd6cb;padding:7px 6px;width:1in"
    note = "border-bottom:1px solid #ddd6cb;border-left:1px solid #ddd6cb;padding:7px 6px;width:1.9in"
    th = "text-align:left;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7a7266;padding:3px 6px"
    h = [f'<div style="border-bottom:2.5px solid #c41f26;padding-bottom:6px;font-family:Georgia,serif;letter-spacing:.14em;font-size:13px">181 FREMONT RESIDENCES <span style="float:right;font-family:Arial,sans-serif;letter-spacing:.2em;font-size:9px;color:#7a7266">RESIDENTS&rsquo; CLUB OPERATIONS</span></div>',
         '<h1 style="font-family:Georgia,serif;font-size:21px;color:#c41f26;margin:12px 0 2px;font-weight:normal">Inventory Count Sheet</h1>',
         f'<p style="color:#55555f;font-size:12.5px;margin:0 0 10px">Walk order, with each item&rsquo;s minimum. Write what is on hand; circle anything at or under its minimum. Nespresso pods by the sealed box only; opened or loose capsules are in circulation. Enter the count on 181residents.com (Operations, Inventory) when you are back at a desk. List as of {esc(pacific()["day"])}.</p>',
         '<p style="font-size:12.5px;margin:0 0 12px">Counted by <span style="display:inline-block;border-bottom:1px solid #16161a;width:2.2in"></span> &nbsp; Date <span style="display:inline-block;border-bottom:1px solid #16161a;width:1.2in"></span> &nbsp; Time started <span style="display:inline-block;border-bottom:1px solid #16161a;width:.9in"></span></p>']
    for a in act:
        its = sorted([i for i in items if i.get("active", 1) and i["area_id"] == a["id"]], key=lambda i: (i.get("ord", 0), i["id"]))
        if not its: continue
        h.append(f'<table style="width:100%;border-collapse:collapse;margin-top:14px;page-break-inside:avoid"><tr><td colspan="4" style="font-family:Georgia,serif;font-size:14px;background:#f7f4ef;padding:6px;border-bottom:1px solid #ddd6cb">{esc(a["name"])}{" <span style=\"font-family:Arial,sans-serif;font-size:10px;color:#7a7266\">floor " + esc(a["floor"]) + "</span>" if a.get("floor") else ""}</td></tr>'
                 f'<tr><th style="{th}">Item</th><th style="{th}">Minimum</th><th style="{th}">On hand</th><th style="{th}">Note</th></tr>')
        for it in its:
            h.append(f'<tr><td style="{td}">{esc(it["name"])}</td><td style="{td};width:1.1in">{esc(min_text(it))}</td><td style="{box}"></td><td style="{note}"></td></tr>')
        h.append("</table>")
    h.append('<div style="background:#f7f4ef;border-left:3px solid #c41f26;padding:7px 11px;margin-top:16px;font-size:12px"><b>Orders are placed by management.</b> Below-minimum items are reported; department heads decide. Machine faults, resident feedback and locked doors go in the Note column.</div>')
    return "".join(h)

# ----------------------------------------------------------------- the router
def scope_of(c):
    try:
        s = json.loads(c.get("scope") or "[]")
        return [int(x) for x in s] if isinstance(s, list) else []
    except (ValueError, TypeError):
        return []

def editable(c):
    return c.get("status") == "Open" or (c.get("status") == "Submitted" and not c.get("complete"))

def summary(c, lines, areas, items):
    scope = scope_of(c)
    act = [a for a in areas if a.get("active", 1) and (not scope or a["id"] in scope)]
    ids = {a["id"] for a in act}
    its = [i for i in items if i.get("active", 1) and i["area_id"] in ids]
    q = {l["item_id"]: l for l in lines if l["count_id"] == c["id"]}
    counted = low = 0; people = set()
    for it in its:
        l = q.get(it["id"])
        if l and l.get("qty") is not None:
            counted += 1
            if is_low(it, l["qty"]): low += 1
            if l.get("who"): people.add(l["who"])
    out = {k: v for k, v in c.items() if k not in ("report_html", "report_text")}
    try: out["emails"] = json.loads(c.get("emails") or "[]")
    except ValueError: out["emails"] = []
    ppl = []
    for p in [c.get("started_by")] + sorted(people):
        if p and p not in ppl: ppl.append(p)
    active_n = len([a for a in areas if a.get("active", 1)])
    out.update(scope=scope, total=len(its), counted=counted, low=low, people=ppl,
               scope_names=[a["name"] for a in act] if scope and len(scope) < active_n else [])
    return out

def _next_id(rows): return max([r["id"] for r in rows] or [0]) + 1

def handle(h, method, p, env):
    """h = the request handler; env = dict(load_store, save_store, notify, now_iso, recipients)."""
    load, save, now = env["load_store"], env["save_store"], env["now_iso"]
    role = h._role(); staff = role != "desk"; by = f"{role}@local.dev"
    parts = [x for x in p.path[len("/api/inventory"):].split("/") if x]
    q = parse_qs(p.query)
    areas = load("inv_areas", []); items = load("inv_items", [])

    if not parts and method == "GET":
        counts = sorted(load("inv_counts", []), key=lambda c: c["id"], reverse=True)[:200]
        lines = load("inv_lines", [])
        return h._json({"areas": areas, "items": items, "counts": [summary(c, lines, areas, items) for c in counts],
                        "recipients": env["recipients"]() if staff else None, "role": role})

    if parts == ["seed"] and method == "POST":
        if not staff: return h._json({"error": "forbidden"}, 403)
        if areas: return h._json({"error": "The list already has areas; the starting list loads only into an empty one."}, 400)
        b = h._body_json(); n = 0
        for ai, a in enumerate((b.get("areas") or [])[:60]):
            name = str(a.get("name") or "").strip()[:80]
            if not name: continue
            row = dict(id=_next_id(areas), name=name, floor=(str(a.get("floor") or "").strip()[:20] or None), ord=ai, active=1,
                       created=now(), updated=None, updated_by=by)
            areas.append(row)
            for ii, it in enumerate((a.get("items") or [])[:200]):
                iname = str(it.get("name") or "").strip()[:120]
                if not iname: continue
                items.append(dict(id=_next_id(items), area_id=row["id"], name=iname, minimum=num(it.get("minimum")),
                                  unit=(str(it.get("unit") or "").strip()[:40] or None),
                                  orderer=(str(it.get("orderer") or a.get("orderer") or "").strip()[:60] or None),
                                  hint=(str(it.get("hint") or "").strip()[:160] or None), variant=1 if it.get("variant") else 0, ord=ii, active=1,
                                  created=now(), updated=None, updated_by=by))
                n += 1
        save("inv_areas", areas); save("inv_items", items)
        return h._json({"ok": True, "areas": len(areas), "items": n}, 201)

    if parts and parts[0] == "areas":
        if not staff: return h._json({"error": "forbidden"}, 403)
        if len(parts) == 1 and method == "POST":
            b = h._body_json(); name = str(b.get("name") or "").strip()[:80]
            if not name: return h._json({"error": "Give the area a name."}, 400)
            row = dict(id=_next_id(areas), name=name, floor=(str(b.get("floor") or "").strip()[:20] or None),
                       ord=max([a["ord"] for a in areas] or [-1]) + 1, active=1, created=now(), updated=now(), updated_by=by)
            areas.append(row); save("inv_areas", areas)
            return h._json({"area": row}, 201)
        if len(parts) == 2 and method == "PATCH":
            b = h._body_json()
            for a in areas:
                if str(a["id"]) == parts[1]:
                    if "name" in b:
                        v = str(b["name"] or "").strip()[:80]
                        if not v: return h._json({"error": "Give the area a name."}, 400)
                        a["name"] = v
                    if "floor" in b: a["floor"] = str(b["floor"] or "").strip()[:20] or None
                    if "ord" in b: a["ord"] = int(b["ord"] or 0)
                    if "active" in b: a["active"] = 1 if b["active"] else 0
                    a["updated"] = now(); a["updated_by"] = by
                    save("inv_areas", areas)
                    return h._json({"area": a})
            return h._json({"error": "No such area"}, 404)

    if parts and parts[0] == "items":
        if not staff: return h._json({"error": "forbidden"}, 403)
        def clean(b):
            return dict(name=str(b["name"] or "").strip()[:120] if "name" in b else None,
                        minimum=num(b.get("minimum")) if "minimum" in b else "skip",
                        unit=(str(b["unit"] or "").strip()[:40] or None) if "unit" in b else "skip",
                        orderer=(str(b["orderer"] or "").strip()[:60] or None) if "orderer" in b else "skip",
                        hint=(str(b["hint"] or "").strip()[:160] or None) if "hint" in b else "skip",
                        variant=(1 if b["variant"] else 0) if "variant" in b else "skip")
        if len(parts) == 1 and method == "POST":
            b = h._body_json(); c = clean(b)
            if not c["name"]: return h._json({"error": "Give the item a name."}, 400)
            try: area = int(b.get("area_id"))
            except (TypeError, ValueError): area = None
            if area is None or not any(a["id"] == area for a in areas): return h._json({"error": "Pick an area."}, 400)
            row = dict(id=_next_id(items), area_id=area, name=c["name"],
                       minimum=None if c["minimum"] == "skip" else c["minimum"],
                       unit=None if c["unit"] == "skip" else c["unit"], orderer=None if c["orderer"] == "skip" else c["orderer"],
                       hint=None if c["hint"] == "skip" else c["hint"], variant=0 if c["variant"] == "skip" else c["variant"],
                       ord=max([i["ord"] for i in items if i["area_id"] == area] or [-1]) + 1, active=1,
                       created=now(), updated=now(), updated_by=by)
            items.append(row); save("inv_items", items)
            return h._json({"item": row}, 201)
        if len(parts) == 2 and method == "PATCH":
            b = h._body_json(); c = clean(b)
            for it in items:
                if str(it["id"]) == parts[1]:
                    if c["name"] is not None:
                        if not c["name"]: return h._json({"error": "Give the item a name."}, 400)
                        it["name"] = c["name"]
                    for k in ("minimum", "unit", "orderer", "hint", "variant"):
                        if c[k] != "skip": it[k] = c[k]
                    if "area_id" in b:
                        try: area = int(b["area_id"])
                        except (TypeError, ValueError): area = None
                        if area is None or not any(a["id"] == area for a in areas): return h._json({"error": "Pick an area."}, 400)
                        it["area_id"] = area; it["ord"] = max([i["ord"] for i in items if i["area_id"] == area and i is not it] or [-1]) + 1
                    if "ord" in b: it["ord"] = int(b["ord"] or 0)
                    if "active" in b: it["active"] = 1 if b["active"] else 0
                    it["updated"] = now(); it["updated_by"] = by
                    save("inv_items", items)
                    return h._json({"item": it})
            return h._json({"error": "No such item"}, 404)

    if parts == ["sheet"] and method == "GET":
        return h._text(report_page("Blank inventory count sheet", blank_sheet(areas, items)), "text/html; charset=utf-8")

    if parts and parts[0] == "counts":
        counts = load("inv_counts", []); lines = load("inv_lines", []); notes = load("inv_notes", [])
        if len(parts) == 1 and method == "POST":
            b = h._body_json()
            scope = [int(x) for x in (b.get("scope") or []) if str(x).lstrip("-").isdigit()]
            row = dict(id=_next_id(counts), scope=json.dumps(scope), status="Open", complete=0, started=now(), started_by=by,
                       handoff_note=None, handoff_by=None, handoff_at=None, submitted=None, submitted_by=None, submits=0,
                       closed=None, closed_by=None, report_html=None, report_text=None, emails=None, updated=now(), updated_by=by)
            counts.append(row); save("inv_counts", counts)
            return h._json({"count": row}, 201)
        c = next((x for x in counts if str(x["id"]) == parts[1]), None)
        if not c: return h._json({"error": "No such count"}, 404)
        my_lines = [l for l in lines if l["count_id"] == c["id"]]
        my_notes = [n for n in notes if n["count_id"] == c["id"]]
        def public(row):
            out = {k: v for k, v in row.items() if k not in ("report_html", "report_text")}
            try: out["emails"] = json.loads(row.get("emails") or "[]")
            except ValueError: out["emails"] = []
            out["scope"] = scope_of(row); out["editable"] = editable(row)
            return out

        if len(parts) == 2 and method == "GET":
            return h._json({"count": public(c), "lines": my_lines, "notes": my_notes, "areas": areas, "items": items})

        if len(parts) == 3 and parts[2] == "report" and method == "GET":
            if (q.get("format") or [""])[0] == "csv":
                scope = scope_of(c); ql = {l["item_id"]: l for l in my_lines}
                out = [["Area", "Floor", "Item", "Minimum", "Unit", "On hand", "Below minimum", "Ordered by", "Counted by", "At"]]
                for a in sorted([x for x in areas if x.get("active", 1) and (not scope or x["id"] in scope)], key=lambda x: x["ord"]):
                    for it in sorted([i for i in items if i.get("active", 1) and i["area_id"] == a["id"]], key=lambda i: i["ord"]):
                        l = ql.get(it["id"], {})
                        out.append([a["name"], a.get("floor") or "", it["name"] + (f" ({l['label']})" if l.get("label") else ""), "" if it.get("minimum") is None else it["minimum"], it.get("unit") or "",
                                    "" if l.get("qty") is None else l["qty"], "yes" if is_low(it, l.get("qty")) else "", it.get("orderer") or "",
                                    name_of(l["who"]) if l.get("who") else "", l.get("at") or ""])
                csv = "\r\n".join(",".join('"' + str(v).replace('"', '""') + '"' for v in r) for r in out)
                return h._text("﻿" + csv, "text/csv; charset=utf-8", extra={"content-disposition": f'attachment; filename="inventory-count-{c["id"]}.csv"'})
            inner = c.get("report_html") or build_report(c, areas, items, my_lines, my_notes, scope_of(c), now)["html"]
            return h._text(report_page(f"Inventory count #{c['id']}", inner), "text/html; charset=utf-8")

        if len(parts) == 2 and method == "PATCH":
            b = h._body_json(); action = b.get("action") or ""
            def send(rep, kind):
                to = env["recipients"]()
                env["notify"](rep["subject"], [f"to: {', '.join(to) or '(the RSVP list; no recipients set yet)'}", f"from: {REPORT_FROM}", rep["text"][:160].replace("\n", " | ")])
                try: emails = json.loads(c.get("emails") or "[]")
                except ValueError: emails = []
                emails.append(dict(at=now(), by=by, to=to or ["(the RSVP list; no recipients set yet)"], kind=kind, subject=rep["subject"]))
                return json.dumps(emails[-20:])
            if action == "close":
                if not staff: return h._json({"error": "forbidden"}, 403)
                if c["status"] == "Closed" or (c["status"] == "Submitted" and c.get("complete")):
                    return h._json({"error": "This count is already finished."}, 400)
                c.update(status="Closed", closed=now(), closed_by=by, updated=now(), updated_by=by)
                save("inv_counts", counts); return h._json({"count": public(c)})
            if action == "resend":
                if not c.get("report_html"): return h._json({"error": "Nothing has been submitted yet."}, 400)
                rep = {"subject": c["report_text"].split("\n")[0].replace("INVENTORY COUNT, ", "RC Inventory, ", 1), "text": c["report_text"], "html": c["report_html"]}
                c["emails"] = send(rep, "resend"); c["updated"] = now(); c["updated_by"] = by
                save("inv_counts", counts); return h._json({"count": public(c)})
            if not editable(c): return h._json({"error": "This count is finished; start a new one."}, 400)
            if action == "handoff":
                c.update(handoff_note=(str(b.get("note") or "").strip()[:300] or None), handoff_by=by, handoff_at=now(), updated=now(), updated_by=by)
                save("inv_counts", counts); return h._json({"count": public(c)})
            if action == "submit":
                rep = build_report(dict(c, submitted=now()), areas, items, my_lines, my_notes, scope_of(c), now)
                c["emails"] = send(rep, "completion" if c.get("submits") else "first")
                c.update(status="Submitted", complete=1 if rep["complete"] else 0, submitted=now(), submitted_by=by,
                         submits=(c.get("submits") or 0) + 1, report_html=rep["html"], report_text=rep["text"],
                         handoff_note=None, updated=now(), updated_by=by)
                save("inv_counts", counts)
                return h._json({"count": public(c), "low": rep["low"], "counted": rep["counted"], "total": rep["total"], "complete": rep["complete"]})
            saved = 0
            for k, v in list((b.get("lines") or {}).items())[:200]:
                if not str(k).isdigit(): continue
                item = int(k); qty = num(v)
                l = next((x for x in lines if x["count_id"] == c["id"] and x["item_id"] == item), None)
                if l: l.update(qty=qty, who=by, at=now())
                else: lines.append(dict(id=_next_id(lines), count_id=c["id"], item_id=item, qty=qty, who=by, at=now()))
                saved += 1
            for k, v in list((b.get("labels") or {}).items())[:200]:
                if not str(k).isdigit(): continue
                item = int(k); label = str(v or "").strip()[:60] or None
                l = next((x for x in lines if x["count_id"] == c["id"] and x["item_id"] == item), None)
                if l: l.update(label=label, who=by, at=now())
                else: lines.append(dict(id=_next_id(lines), count_id=c["id"], item_id=item, qty=None, label=label, who=by, at=now()))
                saved += 1
            for k, v in list((b.get("notes") or {}).items())[:60]:
                if not str(k).isdigit(): continue
                area = int(k); body = str(v or "").strip()[:600] or None
                n = next((x for x in notes if x["count_id"] == c["id"] and x["area_id"] == area), None)
                if n: n.update(body=body, who=by, at=now())
                else: notes.append(dict(id=_next_id(notes), count_id=c["id"], area_id=area, body=body, who=by, at=now()))
                saved += 1
            if not saved: return h._json({"error": "Nothing to save"}, 400)
            c["updated"] = now(); c["updated_by"] = by
            save("inv_lines", lines); save("inv_notes", notes); save("inv_counts", counts)
            return h._json({"ok": True, "saved": saved})
    return h._json({"error": "Not found"}, 404)
