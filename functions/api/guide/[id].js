import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail, logChange } from "../../_lib.js";
import { noteView, FIELDS, LIMIT, clip, spot } from "../guide.js";

// PUT /api/guide/<place id> -> one of four acts on one place, each signed and
// written to the change log (kind 'guide', label = the place id). Every tier
// may do all four; the desk is who makes the calls.
//
//   { action: "edit", edits: { <field>: { v, base } }, verify? }
//       A correction from the team. v is the new value, base is what the
//       file said when it was made. The edit lies over the file from then
//       on; if v equals base the edit is simply dropped. verify also stamps
//       the listing as verified by phone in the same save.
//   { action: "verify" }
//       "I called, and the card is right": stamps who and when.
//   { action: "resolve", field, take, base }
//       After the weekly check changes a field the team had corrected:
//       take = true drops our edit for the file's value; false keeps ours
//       and remembers the file's new value as seen.
//   { action: "connection", connected, contact, phone, note }
//       The house's own line: do we know someone there.
// latlon is the dot on the map, "lat,lon": moved by hand when an address
// changes, and an edit like any other.
//
// DELETE /api/guide/<place id> -> takes a place the team added out of the
// book. Only "t-" places; one from the file leaves through the weekly check.

export async function onRequestPut({ request, env, params }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  const id = String(params.id || "").toLowerCase();
  if (!/^[a-z0-9-]{1,80}$/.test(id)) return json({ error: "Unknown place." }, 400);
  await ensureResidentTables(env);
  let b; try { b = await request.json(); } catch (e) { return json({ error: "Nothing to save." }, 400); }
  const by = (await accessEmail(request)) || env.DEV_ROLE || role;
  const at = new Date().toISOString();
  const have = await env.DB.prepare(
    "SELECT place_id, connected, contact, phone, note, updated, updated_by, verified_at, verified_by, edits FROM guide_notes WHERE place_id = ?").bind(id).first();
  const row = noteView(have || {});
  const logs = [];

  if (b.action === "connection") {
    const next = { connected: !!b.connected, contact: clip(b.contact, 80), phone: clip(b.phone, 40), note: clip(b.note, 240) };
    if (!next.connected) { next.contact = ""; next.phone = ""; }
    const ch = {};
    const was = `${row.connected ? "Yes" : "No"}${row.contact ? ", " + row.contact : ""}${row.phone ? ", " + row.phone : ""}`;
    const now = `${next.connected ? "Yes" : "No"}${next.contact ? ", " + next.contact : ""}${next.phone ? ", " + next.phone : ""}`;
    if (was !== now) ch.connection = [was, now];
    if (row.note !== next.note) ch.connection_note = [row.note, next.note];
    Object.assign(row, next);
    if (Object.keys(ch).length) logs.push(["Connection saved", ch]);
  } else if (b.action === "edit") {
    const ch = {};
    for (const f of FIELDS) {
      const e = b.edits && b.edits[f]; if (!e) continue;
      const v = clip(e.v, LIMIT[f] || 200), base = clip(e.base, LIMIT[f] || 200);
      if (f === "latlon" && !spot(v)) continue;
      const before = row.edits[f] ? row.edits[f].v : base;
      if (v === before) continue;
      if (v === base) delete row.edits[f]; else row.edits[f] = { v, base };
      ch[f] = [before, v];
    }
    if (Object.keys(ch).length) { logs.push(["Edited", ch]); row.updated = at; row.updated_by = by; }
    if (b.verify) { row.verified_at = at; row.verified_by = by; logs.push(["Verified by phone", null]); }
    if (!logs.length) return json({ ok: true, note: have ? row : null, unchanged: true });
  } else if (b.action === "verify") {
    row.verified_at = at; row.verified_by = by; logs.push(["Verified by phone", null]);
  } else if (b.action === "resolve") {
    const f = String(b.field || ""), e = row.edits[f];
    if (!FIELDS.includes(f) || !e) return json({ error: "Nothing to settle on that field." }, 400);
    const base = clip(b.base, LIMIT[f] || 200);
    if (b.take) { delete row.edits[f]; logs.push(["Took the weekly check's value", { [f]: [e.v, base] }]); }
    else { e.base = base; logs.push(["Kept the team's entry over the weekly check", { [f]: [base, e.v] }]); }
  } else return json({ error: "Unknown action." }, 400);

  await env.DB.prepare(
    `INSERT INTO guide_notes (place_id, connected, contact, phone, note, updated, updated_by, verified_at, verified_by, edits)
     VALUES (?,?,?,?,?,?,?,?,?,?)
     ON CONFLICT(place_id) DO UPDATE SET connected = excluded.connected, contact = excluded.contact, phone = excluded.phone,
       note = excluded.note, updated = excluded.updated, updated_by = excluded.updated_by,
       verified_at = excluded.verified_at, verified_by = excluded.verified_by, edits = excluded.edits`)
    .bind(id, row.connected ? 1 : 0, row.contact, row.phone, row.note, row.updated, row.updated_by,
      row.verified_at, row.verified_by, JSON.stringify(row.edits)).run();
  for (const [action, changes] of logs) await logChange(env, request, "guide", null, id, action, changes || {});
  return json({ ok: true, note: row, logged: logs.map(([action, changes]) => ({ place: id, at, who: by, action, changes: changes || null })) });
}

export async function onRequestDelete({ request, env, params }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  const id = String(params.id || "").toLowerCase();
  await ensureResidentTables(env);
  const have = /^t-[a-z0-9-]{1,80}$/.test(id)
    ? await env.DB.prepare("SELECT place FROM guide_added WHERE place_id = ? AND removed IS NULL").bind(id).first() : null;
  if (!have) return json({ error: "Only a place the team added can be removed here." }, 400);
  const by = (await accessEmail(request)) || env.DEV_ROLE || role;
  const at = new Date().toISOString();
  let name = id; try { name = JSON.parse(have.place).name || id; } catch (e) {}
  await env.DB.prepare("UPDATE guide_added SET removed = ?, removed_by = ? WHERE place_id = ?").bind(at, by, id).run();
  await logChange(env, request, "guide", null, id, "Removed from the book", { name: [name, ""] });
  return json({ ok: true });
}
