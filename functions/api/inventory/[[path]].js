import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail, esc,
         todayPacific, notifyMail } from "../../_lib.js";
import { inventoryRecipients } from "../settings.js";

// Inventory, under the Operations tab. One module answers every route, so
// the dev server's mirror (dev_server.py, "inventory") reads side by side:
//
//   GET    /api/inventory                 areas, items, counts (summaries), recipients
//   POST   /api/inventory/seed            the starting list, only into an empty list
//   POST   /api/inventory/areas           {name, floor}                        staff+
//   PATCH  /api/inventory/areas/:id       {name, floor, ord, active}           staff+
//   POST   /api/inventory/items           {area_id, name, minimum, unit, orderer, hint}
//   PATCH  /api/inventory/items/:id       any of those, ord, active            staff+
//   POST   /api/inventory/counts          {scope: [area ids]} -> a new Open count
//   GET    /api/inventory/counts/:id      the count with its lines and area notes
//   PATCH  /api/inventory/counts/:id      {lines:{item:qty}, notes:{area:text}} autosave,
//                                         or {action: handoff|submit|resend|close}
//   GET    /api/inventory/counts/:id/report[?format=csv]   the printable report
//   GET    /api/inventory/sheet           a blank count sheet of today's list
//
// Every tier counts (the desk does the walking); the item list and the
// recipients belong to staff and owner. A count is never deleted: it is Open,
// Submitted (complete, or still needing finishing), or Closed by staff.

const REPORT_FROM = "reports@181residents.com";

async function who(request, env) {
  return (await accessEmail(request)) || env.DEV_ROLE || "staff";
}
const now = () => new Date().toISOString();
const num = v => (v === "" || v == null || isNaN(Number(v))) ? null : Number(v);

// "krystle@181sf.com" -> "Krystle"; the trail names a person, not an address.
export function nameOf(email) {
  const s = String(email || "").split("@")[0].replace(/[._-]+/g, " ").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "staff";
}

export function fmtQty(q) {
  if (q == null) return "";
  if (q === 0.5) return "½";
  if (Math.abs(q - Math.round(q)) < 1e-9) return String(Math.round(q));
  return String(q);
}
export function minText(it) {
  if (it.minimum == null) return "";
  return fmtQty(it.minimum) + (it.unit ? " " + it.unit : "");
}
export function isLow(it, qty) {
  return qty != null && it.minimum != null && qty <= it.minimum;
}

// Pacific wall-clock pieces for the report's head and the subject line.
export function pacific(iso) {
  const d = iso ? new Date(iso) : new Date();
  const day = d.toLocaleDateString("en-US", { timeZone: "America/Los_Angeles", weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const short = d.toLocaleDateString("en-US", { timeZone: "America/Los_Angeles", weekday: "long", month: "short", day: "numeric" });
  const time = d.toLocaleTimeString("en-US", { timeZone: "America/Los_Angeles", hour: "numeric", minute: "2-digit" });
  return { day, short, time };
}

// --------------------------------------------------------------- the report
// Rendered once at submit. The HTML is inline-styled so it reads in a mail
// client; the printable page wraps the same HTML. Keep in lockstep with
// dev_server.py build_inventory_report.
export function buildReport(count, areas, items, lines, notes, scopeIds) {
  const inScope = areas.filter(a => a.active && (!scopeIds.length || scopeIds.includes(a.id)))
    .sort((a, b) => a.ord - b.ord || a.id - b.id);
  const qtyOf = {}; for (const l of lines) qtyOf[l.item_id] = l;
  const noteOf = {}; for (const n of notes) noteOf[n.area_id] = n;
  let total = 0, counted = 0;
  const low = [], rowsByArea = [], counters = new Set();
  for (const a of inScope) {
    const its = items.filter(i => i.active && i.area_id === a.id).sort((x, y) => x.ord - y.ord || x.id - y.id);
    const rows = [];
    for (const it of its) {
      total++;
      const l = qtyOf[it.id]; const qty = l && l.qty != null ? l.qty : null;
      if (qty != null) { counted++; if (l.who) counters.add(l.who); }
      const lowRow = isLow(it, qty);
      if (lowRow) low.push({ it, a, qty });
      rows.push({ it, qty, low: lowRow });
    }
    rowsByArea.push({ a, rows, note: noteOf[a.id] && noteOf[a.id].body ? noteOf[a.id].body : "" });
  }
  const when = pacific(count.submitted || now());
  const started = pacific(count.started);
  const scopeName = scopeIds.length && scopeIds.length < areas.filter(a => a.active).length
    ? inScope.map(a => a.name).join(", ") : "Full walk";
  const people = [...new Set([count.started_by, ...counters].filter(Boolean))].map(nameOf);
  const complete = counted === total;
  const submitNo = (count.submits || 0) + 1;
  const subject = (submitNo > 1 ? "RC Inventory, completes " + started.short : "RC Inventory, " + when.short)
    + ": " + (low.length ? `${low.length} item${low.length === 1 ? "" : "s"} below minimum` : "nothing below minimum")
    + (complete ? "" : ` (${total - counted} not yet counted)`);

  const S = {
    body: "font-family:Arial,Helvetica,sans-serif;color:#16161a;font-size:14px;line-height:1.45;max-width:720px",
    h1: "font-family:Georgia,serif;font-size:22px;color:#c41f26;margin:14px 0 2px;font-weight:normal",
    rh: "border-bottom:2.5px solid #c41f26;padding-bottom:6px;font-family:Georgia,serif;letter-spacing:.14em;font-size:13px",
    sub: "color:#55555f;font-size:13px;margin:0 0 14px",
    h2: "font-family:Georgia,serif;font-size:15px;color:#c41f26;margin:18px 0 4px;border-bottom:1px solid #ddd6cb;padding-bottom:3px;font-weight:normal",
    tag: "font-family:Arial,sans-serif;font-size:9px;letter-spacing:.14em;color:#7a7266;text-transform:uppercase;margin-left:8px",
    th: "text-align:left;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#7a7266;border-bottom:2px solid #16161a;padding:4px 8px 4px 0",
    td: "border-top:1px solid #ddd6cb;padding:5px 8px 5px 0;vertical-align:top;font-size:13px",
    tdr: "border-top:1px solid #ddd6cb;padding:5px 0 5px 8px;vertical-align:top;font-size:13px;text-align:right;white-space:nowrap",
    lowc: "color:#c41f26;font-weight:bold",
    area: "font-family:Georgia,serif;background:#f7f4ef;padding:6px 8px 6px 0;font-size:14px",
    note: "background:#f7f4ef;border-left:3px solid #c41f26;padding:8px 12px;margin-top:14px;font-size:13px",
    ftr: "margin-top:18px;border-top:1px solid #ddd6cb;padding-top:6px;font-size:11px;color:#7a7266",
  };
  const e = esc;
  let h = `<div style="${S.body}">`
    + `<div style="${S.rh}">181 FREMONT RESIDENCES <span style="float:right;font-family:Arial,sans-serif;letter-spacing:.2em;font-size:9px;color:#7a7266">RESIDENTS&rsquo; CLUB OPERATIONS</span></div>`
    + `<h1 style="${S.h1}">Inventory count &middot; ${e(when.day)}</h1>`
    + `<p style="${S.sub}">${e(scopeName)}, <b>${counted} of ${total}</b> items counted${complete ? "" : ` (<b style="${S.lowc}">${total - counted} still to count</b>)`}. `
    + `Counted by <b>${e(people.join(", ") || "staff")}</b>, started ${e(started.short)} ${e(started.time)}${count.submitted ? `, submitted ${e(when.time)}` : ""}. `
    + (low.length ? `<b>${low.length} item${low.length === 1 ? "" : "s"} at or below minimum.</b>` : "Nothing at or below its minimum.")
    + ` Department heads review and place their own orders; nothing here is an order.</p>`;
  h += `<h2 style="${S.h2}">Below minimum<span style="${S.tag}">ORDER THESE, OR DECIDE NOT TO</span></h2>`;
  if (low.length) {
    h += `<table style="width:100%;border-collapse:collapse"><tr><th style="${S.th}">Item</th><th style="${S.th}">Where</th><th style="${S.th};text-align:right">Minimum</th><th style="${S.th};text-align:right">On hand</th><th style="${S.th}">Ordered by</th></tr>`;
    for (const r of low) h += `<tr><td style="${S.td}">${e(r.it.name)}</td><td style="${S.td}">${e(r.a.name)}${r.a.floor ? ` &middot; floor ${e(r.a.floor)}` : ""}</td><td style="${S.tdr}">${e(minText(r.it))}</td><td style="${S.tdr};${S.lowc}">${e(fmtQty(r.qty))}</td><td style="${S.td}">${e(r.it.orderer || "")}</td></tr>`;
    h += `</table>`;
  } else h += `<p style="${S.sub}">Nothing. Every counted item sits above its minimum.</p>`;
  const noted = rowsByArea.filter(x => x.note);
  if (noted.length) {
    h += `<h2 style="${S.h2}">Notes from the walk</h2><table style="width:100%;border-collapse:collapse">`;
    for (const x of noted) h += `<tr><td style="${S.td};width:160px;color:#7a7266">${e(x.a.name)}</td><td style="${S.td}">${e(x.note)}</td></tr>`;
    h += `</table>`;
  }
  h += `<h2 style="${S.h2}">Everything counted<span style="${S.tag}">BY AREA, IN WALK ORDER</span></h2><table style="width:100%;border-collapse:collapse"><tr><th style="${S.th}">Item</th><th style="${S.th};text-align:right">Minimum</th><th style="${S.th};text-align:right">On hand</th></tr>`;
  for (const x of rowsByArea) {
    h += `<tr><td colspan="3" style="${S.area}">${e(x.a.name)}${x.a.floor ? ` <span style="font-family:Arial,sans-serif;font-size:11px;color:#7a7266">floor ${e(x.a.floor)}</span>` : ""}</td></tr>`;
    for (const r of x.rows) h += `<tr><td style="${S.td}">${e(r.it.name)}</td><td style="${S.tdr}">${e(minText(r.it))}</td><td style="${S.tdr}${r.low ? ";" + S.lowc : ""}">${r.qty == null ? `<span style="color:#7a7266;font-style:italic">not counted</span>` : e(fmtQty(r.qty))}</td></tr>`;
  }
  h += `</table>`
    + `<div style="${S.note}"><b>Counted on 181residents.com &middot; Operations &middot; Inventory.</b> The live record, with who counted what and when, is at the same address. Orders are placed by management from this report.</div>`
    + `<div style="${S.ftr}">Inventory count #${count.id} &middot; ${count.submitted ? "submitted " + e(when.day) + ", " + e(when.time) : "not yet submitted"} &middot; 181residents.com/admin</div></div>`;

  const t = [];
  t.push(`INVENTORY COUNT, ${when.day}`);
  t.push(`${scopeName}, ${counted} of ${total} items counted${complete ? "" : ` (${total - counted} still to count)`}. Counted by ${people.join(", ") || "staff"}.`);
  t.push("");
  t.push(low.length ? "BELOW MINIMUM" : "BELOW MINIMUM: nothing");
  for (const r of low) t.push(`- ${r.it.name} (${r.a.name}): ${fmtQty(r.qty)} on hand, minimum ${minText(r.it)}${r.it.orderer ? ", ordered by " + r.it.orderer : ""}`);
  if (noted.length) { t.push(""); t.push("NOTES FROM THE WALK"); for (const x of noted) t.push(`- ${x.a.name}: ${x.note}`); }
  t.push(""); t.push("EVERYTHING COUNTED");
  for (const x of rowsByArea) {
    t.push(`${x.a.name}${x.a.floor ? " (floor " + x.a.floor + ")" : ""}`);
    for (const r of x.rows) t.push(`  ${r.it.name}: ${r.qty == null ? "not counted" : fmtQty(r.qty)}${r.low ? " (BELOW MINIMUM)" : ""} / min ${minText(r.it) || "none"}`);
  }
  t.push(""); t.push("Orders are placed by management from this report. Live record: https://181residents.com/admin");
  return { html: h, text: t.join("\n"), subject, low: low.length, counted, total, complete };
}

// The printable wrapper: the same HTML, a print stylesheet, a Print button.
function reportPage(title, inner) {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title><style>
  body{margin:0;background:#f2efe9;font-family:Arial,Helvetica,sans-serif}
  .bar{display:flex;gap:10px;align-items:center;padding:12px 20px;background:#16161a;color:#c9c2b6;font-size:12px;letter-spacing:.08em}
  .bar button{background:#c41f26;color:#fff;border:none;border-radius:4px;padding:8px 16px;font-size:13px;font-weight:bold;cursor:pointer}
  .bar a{color:#c9c2b6}
  .sheet{background:#fff;max-width:760px;margin:20px auto;padding:28px 32px;border:1px solid #ddd6cb}
  @media print{body{background:#fff}.bar{display:none}.sheet{border:none;margin:0;padding:0;max-width:none}@page{size:Letter;margin:.6in}}
  @media(max-width:620px){.sheet{margin:0;padding:18px 16px}}
</style></head><body>
<div class="bar"><button onclick="window.print()">Print</button><span>${esc(title)}</span><span style="flex:1"></span><a href="/admin">Back to the admin</a></div>
<div class="sheet">${inner}</div></body></html>`;
}

function blankSheet(areas, items) {
  const act = areas.filter(a => a.active).sort((a, b) => a.ord - b.ord || a.id - b.id);
  const td = "border-bottom:1px solid #ddd6cb;padding:7px 6px;font-size:12.5px;vertical-align:middle";
  const box = "border-bottom:1px solid #ddd6cb;border-left:1px solid #ddd6cb;padding:7px 6px;width:1in";
  const note = "border-bottom:1px solid #ddd6cb;border-left:1px solid #ddd6cb;padding:7px 6px;width:1.9in";
  let h = `<div style="border-bottom:2.5px solid #c41f26;padding-bottom:6px;font-family:Georgia,serif;letter-spacing:.14em;font-size:13px">181 FREMONT RESIDENCES <span style="float:right;font-family:Arial,sans-serif;letter-spacing:.2em;font-size:9px;color:#7a7266">RESIDENTS&rsquo; CLUB OPERATIONS</span></div>
<h1 style="font-family:Georgia,serif;font-size:21px;color:#c41f26;margin:12px 0 2px;font-weight:normal">Inventory Count Sheet</h1>
<p style="color:#55555f;font-size:12.5px;margin:0 0 10px">Walk order, with each item&rsquo;s minimum. Write what is on hand; circle anything at or under its minimum. Nespresso pods by the sealed box only; opened or loose capsules are in circulation. Enter the count on 181residents.com (Operations, Inventory) when you are back at a desk. List as of ${esc(pacific().day)}.</p>
<p style="font-size:12.5px;margin:0 0 12px">Counted by <span style="display:inline-block;border-bottom:1px solid #16161a;width:2.2in"></span> &nbsp; Date <span style="display:inline-block;border-bottom:1px solid #16161a;width:1.2in"></span> &nbsp; Time started <span style="display:inline-block;border-bottom:1px solid #16161a;width:.9in"></span></p>`;
  for (const a of act) {
    const its = items.filter(i => i.active && i.area_id === a.id).sort((x, y) => x.ord - y.ord || x.id - y.id);
    if (!its.length) continue;
    h += `<table style="width:100%;border-collapse:collapse;margin-top:14px;page-break-inside:avoid"><tr><td colspan="4" style="font-family:Georgia,serif;font-size:14px;background:#f7f4ef;padding:6px;border-bottom:1px solid #ddd6cb">${esc(a.name)}${a.floor ? ` <span style="font-family:Arial,sans-serif;font-size:10px;color:#7a7266">floor ${esc(a.floor)}</span>` : ""}</td></tr>
<tr><th style="text-align:left;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7a7266;padding:3px 6px">Item</th><th style="text-align:left;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7a7266;padding:3px 6px">Minimum</th><th style="text-align:left;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7a7266;padding:3px 6px">On hand</th><th style="text-align:left;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7a7266;padding:3px 6px">Note</th></tr>`;
    for (const it of its) h += `<tr><td style="${td}">${esc(it.name)}</td><td style="${td};width:1.1in">${esc(minText(it))}</td><td style="${box}"></td><td style="${note}"></td></tr>`;
    h += `</table>`;
  }
  h += `<div style="background:#f7f4ef;border-left:3px solid #c41f26;padding:7px 11px;margin-top:16px;font-size:12px"><b>Orders are placed by management.</b> Below-minimum items are reported; department heads decide. Machine faults, resident feedback and locked doors go in the Note column.</div>`;
  return h;
}

// --------------------------------------------------------------- data access
async function loadLists(env) {
  const areas = (await env.DB.prepare("SELECT * FROM inv_areas ORDER BY ord, id").all()).results;
  const items = (await env.DB.prepare("SELECT * FROM inv_items ORDER BY ord, id").all()).results;
  return { areas, items };
}
async function loadCount(env, id) {
  const count = await env.DB.prepare("SELECT * FROM inv_counts WHERE id=?").bind(id).first();
  if (!count) return null;
  const lines = (await env.DB.prepare("SELECT * FROM inv_lines WHERE count_id=?").bind(id).all()).results;
  const notes = (await env.DB.prepare("SELECT * FROM inv_area_notes WHERE count_id=?").bind(id).all()).results;
  return { count, lines, notes };
}
function scopeOf(count) {
  try { const s = JSON.parse(count.scope || "[]"); return Array.isArray(s) ? s.map(Number).filter(Number.isInteger) : []; }
  catch (e) { return []; }
}
function editable(count) {
  return count.status === "Open" || (count.status === "Submitted" && !count.complete);
}
// What the list screen needs per count: the summary, never the report body.
function summary(c, lines, areas, items) {
  const scope = scopeOf(c);
  const act = areas.filter(a => a.active && (!scope.length || scope.includes(a.id)));
  const ids = new Set(act.map(a => a.id));
  const its = items.filter(i => i.active && ids.has(i.area_id));
  const q = {}; for (const l of lines) if (l.count_id === c.id) q[l.item_id] = l;
  let counted = 0, low = 0;
  const people = new Set();
  for (const it of its) { const l = q[it.id]; if (l && l.qty != null) { counted++; if (isLow(it, l.qty)) low++; if (l.who) people.add(l.who); } }
  const { report_html, report_text, ...rest } = c;
  let emails = []; try { emails = JSON.parse(c.emails || "[]"); } catch (e) {}
  return { ...rest, emails, scope, total: its.length, counted, low,
    scope_names: scope.length && scope.length < areas.filter(a => a.active).length ? act.map(a => a.name) : [],
    people: [...new Set([c.started_by, ...people].filter(Boolean))] };
}

async function sendReport(context, count, rep, kind) {
  const to = await inventoryRecipients(context.env);
  const by = await who(context.request, context.env);
  notifyMail(context, { subject: rep.subject, text: rep.text, html: reportPage(rep.subject, rep.html), to, from: REPORT_FROM });
  let emails = []; try { emails = JSON.parse(count.emails || "[]"); } catch (e) {}
  emails.push({ at: now(), by, to: to.length ? to : ["(the RSVP list; no recipients set yet)"], kind, subject: rep.subject });
  return JSON.stringify(emails.slice(-20));
}

// --------------------------------------------------------------- the router
export async function onRequest(context) {
  const { request, env, params } = context;
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  const staff = role !== "desk";
  await ensureResidentTables(env);
  const parts = Array.isArray(params.path) ? params.path : (params.path ? [params.path] : []);
  const m = request.method;
  const url = new URL(request.url);
  const by = await who(request, env);

  // ---- the lists and the counts
  if (!parts.length && m === "GET") {
    const { areas, items } = await loadLists(env);
    const counts = (await env.DB.prepare("SELECT * FROM inv_counts ORDER BY id DESC LIMIT 200").all()).results;
    const lines = counts.length ? (await env.DB.prepare(
      `SELECT count_id, item_id, qty, who FROM inv_lines WHERE count_id IN (${counts.map(c => c.id).join(",")})`).all()).results : [];
    return json({ areas, items, counts: counts.map(c => summary(c, lines, areas, items)),
      recipients: staff ? await inventoryRecipients(env) : null, role });
  }

  if (parts[0] === "seed" && m === "POST") {
    if (!staff) return forbidden();
    const have = await env.DB.prepare("SELECT COUNT(*) AS n FROM inv_areas").first();
    if (have && have.n) return json({ error: "The list already has areas; the starting list loads only into an empty one." }, 400);
    const b = await request.json();
    const areas = Array.isArray(b.areas) ? b.areas : [];
    let ai = 0, n = 0;
    for (const a of areas.slice(0, 60)) {
      const name = String(a.name || "").trim().slice(0, 80); if (!name) continue;
      const row = await env.DB.prepare("INSERT INTO inv_areas (name, floor, ord, active, created, updated_by) VALUES (?,?,?,1,?,?) RETURNING id")
        .bind(name, String(a.floor || "").trim().slice(0, 20) || null, ai++, now(), by).first();
      let ii = 0;
      for (const it of (Array.isArray(a.items) ? a.items : []).slice(0, 200)) {
        const iname = String(it.name || "").trim().slice(0, 120); if (!iname) continue;
        await env.DB.prepare("INSERT INTO inv_items (area_id, name, minimum, unit, orderer, hint, ord, active, created, updated_by) VALUES (?,?,?,?,?,?,?,1,?,?)")
          .bind(row.id, iname, num(it.minimum), String(it.unit || "").trim().slice(0, 40) || null,
            String(it.orderer || a.orderer || "").trim().slice(0, 60) || null, String(it.hint || "").trim().slice(0, 160) || null, ii++, now(), by).run();
        n++;
      }
    }
    return json({ ok: true, areas: ai, items: n }, 201);
  }

  // ---- areas
  if (parts[0] === "areas") {
    if (!staff) return forbidden();
    if (parts.length === 1 && m === "POST") {
      const b = await request.json();
      const name = String(b.name || "").trim().slice(0, 80);
      if (!name) return json({ error: "Give the area a name." }, 400);
      const top = await env.DB.prepare("SELECT COALESCE(MAX(ord),-1)+1 AS o FROM inv_areas").first();
      const row = await env.DB.prepare("INSERT INTO inv_areas (name, floor, ord, active, created, updated, updated_by) VALUES (?,?,?,1,?,?,?) RETURNING *")
        .bind(name, String(b.floor || "").trim().slice(0, 20) || null, top.o, now(), now(), by).first();
      return json({ area: row }, 201);
    }
    if (parts.length === 2 && m === "PATCH") {
      const id = Number(parts[1]); if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
      const b = await request.json();
      const sets = [], vals = [];
      if ("name" in b) { const v = String(b.name || "").trim().slice(0, 80); if (!v) return json({ error: "Give the area a name." }, 400); sets.push("name=?"); vals.push(v); }
      if ("floor" in b) { sets.push("floor=?"); vals.push(String(b.floor || "").trim().slice(0, 20) || null); }
      if ("ord" in b) { sets.push("ord=?"); vals.push(Number(b.ord) || 0); }
      if ("active" in b) { sets.push("active=?"); vals.push(b.active ? 1 : 0); }
      if (!sets.length) return json({ error: "Nothing to change" }, 400);
      sets.push("updated=?", "updated_by=?"); vals.push(now(), by);
      const row = await env.DB.prepare(`UPDATE inv_areas SET ${sets.join(",")} WHERE id=? RETURNING *`).bind(...vals, id).first();
      if (!row) return json({ error: "No such area" }, 404);
      return json({ area: row });
    }
  }

  // ---- items
  if (parts[0] === "items") {
    if (!staff) return forbidden();
    const clean = b => ({
      name: "name" in b ? String(b.name || "").trim().slice(0, 120) : undefined,
      minimum: "minimum" in b ? num(b.minimum) : undefined,
      unit: "unit" in b ? (String(b.unit || "").trim().slice(0, 40) || null) : undefined,
      orderer: "orderer" in b ? (String(b.orderer || "").trim().slice(0, 60) || null) : undefined,
      hint: "hint" in b ? (String(b.hint || "").trim().slice(0, 160) || null) : undefined,
    });
    if (parts.length === 1 && m === "POST") {
      const b = await request.json(); const c = clean(b);
      const area = Number(b.area_id);
      if (!c.name) return json({ error: "Give the item a name." }, 400);
      if (!Number.isInteger(area) || !(await env.DB.prepare("SELECT id FROM inv_areas WHERE id=?").bind(area).first())) return json({ error: "Pick an area." }, 400);
      const top = await env.DB.prepare("SELECT COALESCE(MAX(ord),-1)+1 AS o FROM inv_items WHERE area_id=?").bind(area).first();
      const row = await env.DB.prepare("INSERT INTO inv_items (area_id, name, minimum, unit, orderer, hint, ord, active, created, updated, updated_by) VALUES (?,?,?,?,?,?,?,1,?,?,?) RETURNING *")
        .bind(area, c.name, c.minimum == null ? null : c.minimum, c.unit || null, c.orderer || null, c.hint || null, top.o, now(), now(), by).first();
      return json({ item: row }, 201);
    }
    if (parts.length === 2 && m === "PATCH") {
      const id = Number(parts[1]); if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
      const b = await request.json(); const c = clean(b);
      const sets = [], vals = [];
      if (c.name !== undefined) { if (!c.name) return json({ error: "Give the item a name." }, 400); sets.push("name=?"); vals.push(c.name); }
      for (const k of ["minimum", "unit", "orderer", "hint"]) if (c[k] !== undefined) { sets.push(`${k}=?`); vals.push(c[k]); }
      if ("area_id" in b) {
        const area = Number(b.area_id);
        if (!Number.isInteger(area) || !(await env.DB.prepare("SELECT id FROM inv_areas WHERE id=?").bind(area).first())) return json({ error: "Pick an area." }, 400);
        const top = await env.DB.prepare("SELECT COALESCE(MAX(ord),-1)+1 AS o FROM inv_items WHERE area_id=?").bind(area).first();
        sets.push("area_id=?", "ord=?"); vals.push(area, top.o);
      }
      if ("ord" in b) { sets.push("ord=?"); vals.push(Number(b.ord) || 0); }
      if ("active" in b) { sets.push("active=?"); vals.push(b.active ? 1 : 0); }
      if (!sets.length) return json({ error: "Nothing to change" }, 400);
      sets.push("updated=?", "updated_by=?"); vals.push(now(), by);
      const row = await env.DB.prepare(`UPDATE inv_items SET ${sets.join(",")} WHERE id=? RETURNING *`).bind(...vals, id).first();
      if (!row) return json({ error: "No such item" }, 404);
      return json({ item: row });
    }
  }

  // ---- the blank sheet
  if (parts[0] === "sheet" && m === "GET") {
    const { areas, items } = await loadLists(env);
    return new Response(reportPage("Blank inventory count sheet", blankSheet(areas, items)),
      { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
  }

  // ---- counts
  if (parts[0] === "counts") {
    if (parts.length === 1 && m === "POST") {
      const b = await request.json();
      const scope = Array.isArray(b.scope) ? b.scope.map(Number).filter(Number.isInteger) : [];
      const row = await env.DB.prepare("INSERT INTO inv_counts (scope, status, started, started_by, updated, updated_by) VALUES (?,?,?,?,?,?) RETURNING *")
        .bind(JSON.stringify(scope), "Open", now(), by, now(), by).first();
      return json({ count: row }, 201);
    }
    const id = Number(parts[1]); if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
    const got = await loadCount(env, id);
    if (!got) return json({ error: "No such count" }, 404);
    const { count, lines, notes } = got;

    if (parts.length === 2 && m === "GET") {
      const { areas, items } = await loadLists(env);
      const { report_html, report_text, ...rest } = count;
      let emails = []; try { emails = JSON.parse(count.emails || "[]"); } catch (e) {}
      return json({ count: { ...rest, emails, scope: scopeOf(count), editable: editable(count) }, lines, notes, areas, items });
    }

    if (parts.length === 3 && parts[2] === "report" && m === "GET") {
      const { areas, items } = await loadLists(env);
      if (url.searchParams.get("format") === "csv") {
        const scope = scopeOf(count);
        const q = {}; for (const l of lines) q[l.item_id] = l;
        const out = [["Area", "Floor", "Item", "Minimum", "Unit", "On hand", "Below minimum", "Ordered by", "Counted by", "At"]];
        for (const a of areas.filter(x => x.active && (!scope.length || scope.includes(x.id))).sort((x, y) => x.ord - y.ord)) {
          for (const it of items.filter(i => i.active && i.area_id === a.id).sort((x, y) => x.ord - y.ord)) {
            const l = q[it.id] || {};
            out.push([a.name, a.floor || "", it.name, it.minimum == null ? "" : it.minimum, it.unit || "", l.qty == null ? "" : l.qty,
              isLow(it, l.qty == null ? null : l.qty) ? "yes" : "", it.orderer || "", l.who ? nameOf(l.who) : "", l.at || ""]);
          }
        }
        const csv = out.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
        return new Response("﻿" + csv, { headers: { "content-type": "text/csv; charset=utf-8",
          "content-disposition": `attachment; filename="inventory-count-${id}.csv"`, "cache-control": "no-store" } });
      }
      // A submitted count prints its stored report; an open one prints a live rendering, marked as such.
      const inner = count.report_html || buildReport(count, areas, items, lines, notes, scopeOf(count)).html;
      return new Response(reportPage(`Inventory count #${id}`, inner),
        { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
    }

    if (parts.length === 2 && m === "PATCH") {
      const b = await request.json();
      const action = b.action || "";
      if (action === "close") {
        if (!staff) return forbidden();
        if (count.status === "Closed" || (count.status === "Submitted" && count.complete)) return json({ error: "This count is already finished." }, 400);
        const row = await env.DB.prepare("UPDATE inv_counts SET status='Closed', closed=?, closed_by=?, updated=?, updated_by=? WHERE id=? RETURNING *")
          .bind(now(), by, now(), by, id).first();
        return json({ count: row });
      }
      if (action === "resend") {
        if (!count.report_html) return json({ error: "Nothing has been submitted yet." }, 400);
        const rep = { subject: count.report_text.split("\n")[0].replace(/^INVENTORY COUNT, /, "RC Inventory, "), text: count.report_text, html: count.report_html };
        const emails = await sendReport(context, count, rep, "resend");
        const row = await env.DB.prepare("UPDATE inv_counts SET emails=?, updated=?, updated_by=? WHERE id=? RETURNING *").bind(emails, now(), by, id).first();
        return json({ count: { ...row, report_html: undefined, report_text: undefined, emails: JSON.parse(emails) } });
      }
      if (!editable(count)) return json({ error: "This count is finished; start a new one." }, 400);
      if (action === "handoff") {
        const note = String(b.note || "").trim().slice(0, 300);
        const row = await env.DB.prepare("UPDATE inv_counts SET handoff_note=?, handoff_by=?, handoff_at=?, updated=?, updated_by=? WHERE id=? RETURNING *")
          .bind(note || null, by, now(), now(), by, id).first();
        return json({ count: row });
      }
      if (action === "submit") {
        const { areas, items } = await loadLists(env);
        const rep = buildReport({ ...count, submitted: now() }, areas, items, lines, notes, scopeOf(count));
        const emails = await sendReport(context, count, rep, count.submits ? "completion" : "first");
        const row = await env.DB.prepare(
          `UPDATE inv_counts SET status='Submitted', complete=?, submitted=?, submitted_by=?, submits=submits+1,
           report_html=?, report_text=?, emails=?, handoff_note=NULL, updated=?, updated_by=? WHERE id=? RETURNING *`)
          .bind(rep.complete ? 1 : 0, now(), by, rep.html, rep.text, emails, now(), by, id).first();
        const { report_html, report_text, ...rest } = row;
        return json({ count: { ...rest, emails: JSON.parse(emails) }, low: rep.low, counted: rep.counted, total: rep.total, complete: rep.complete });
      }
      // autosave: lines and area notes, each stamped with who typed it
      const writes = [];
      if (b.lines && typeof b.lines === "object") {
        for (const [k, v] of Object.entries(b.lines).slice(0, 200)) {
          const item = Number(k); if (!Number.isInteger(item)) continue;
          const qty = num(v);
          writes.push(env.DB.prepare(
            `INSERT INTO inv_lines (count_id, item_id, qty, who, at) VALUES (?,?,?,?,?)
             ON CONFLICT(count_id, item_id) DO UPDATE SET qty=excluded.qty, who=excluded.who, at=excluded.at`)
            .bind(id, item, qty, by, now()));
        }
      }
      if (b.notes && typeof b.notes === "object") {
        for (const [k, v] of Object.entries(b.notes).slice(0, 60)) {
          const area = Number(k); if (!Number.isInteger(area)) continue;
          writes.push(env.DB.prepare(
            `INSERT INTO inv_area_notes (count_id, area_id, body, who, at) VALUES (?,?,?,?,?)
             ON CONFLICT(count_id, area_id) DO UPDATE SET body=excluded.body, who=excluded.who, at=excluded.at`)
            .bind(id, area, String(v || "").trim().slice(0, 600) || null, by, now()));
        }
      }
      if (!writes.length) return json({ error: "Nothing to save" }, 400);
      writes.push(env.DB.prepare("UPDATE inv_counts SET updated=?, updated_by=? WHERE id=?").bind(now(), by, id));
      await env.DB.batch(writes);
      return json({ ok: true, saved: writes.length - 1 });
    }
  }
  return json({ error: "Not found" }, 404);
}
