import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail } from "../../_lib.js";

// PUT /api/guide/<place id> -> the house's own line on one place: do we have
// a connection there, who, their number, and a short note. Every tier writes,
// the desk included, since the desk is who makes the calls; each save is
// signed with who and when. An empty save clears the line.
export async function onRequestPut({ request, env, params }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  const id = String(params.id || "").toLowerCase();
  if (!/^[a-z0-9-]{1,80}$/.test(id)) return json({ error: "Unknown place." }, 400);
  await ensureResidentTables(env);
  let b; try { b = await request.json(); } catch (e) { return json({ error: "Nothing to save." }, 400); }
  const clip = (v, n) => String(v == null ? "" : v).trim().slice(0, n);
  const row = { connected: b.connected ? 1 : 0, contact: clip(b.contact, 80), phone: clip(b.phone, 40), note: clip(b.note, 240) };
  if (!row.connected) { row.contact = ""; row.phone = ""; }
  const by = (await accessEmail(request)) || env.DEV_ROLE || role;
  const at = new Date().toISOString();
  if (!row.connected && !row.note) {
    await env.DB.prepare("DELETE FROM guide_notes WHERE place_id = ?").bind(id).run();
    return json({ ok: true, note: null });
  }
  await env.DB.prepare(
    `INSERT INTO guide_notes (place_id, connected, contact, phone, note, updated, updated_by) VALUES (?,?,?,?,?,?,?)
     ON CONFLICT(place_id) DO UPDATE SET connected = excluded.connected, contact = excluded.contact,
       phone = excluded.phone, note = excluded.note, updated = excluded.updated, updated_by = excluded.updated_by`)
    .bind(id, row.connected, row.contact, row.phone, row.note, at, by).run();
  return json({ ok: true, note: { connected: !!row.connected, contact: row.contact, phone: row.phone, note: row.note, updated: at, updated_by: by } });
}
