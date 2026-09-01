import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/bookings/:id -> open or close guest registration, or correct the
// event name, host, cap, or staff note. The registration link itself never
// changes: invitations already sent keep working.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  const sets = [], vals = [];
  if ("reg_open" in b) { sets.push("reg_open=?"); vals.push(b.reg_open ? 1 : 0); }
  for (const f of ["event_name", "host", "note"]) {
    if (f in b) { sets.push(`${f}=?`); vals.push(String(b[f] || "").trim() || null); }
  }
  if ("guest_cap" in b) {
    const cap = b.guest_cap ? Math.max(1, Math.min(1000, Number(b.guest_cap) || 0)) || null : null;
    sets.push("guest_cap=?"); vals.push(cap);
  }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);
  const row = await env.DB.prepare(
    `UPDATE bookings SET ${sets.join(",")} WHERE id=? RETURNING *`).bind(...vals, id).first();
  if (!row) return json({ error: "No such reservation" }, 404);
  return json({ booking: row });
}

// DELETE /api/bookings/:id -> the room shows as open again, at once. Any guest
// registrations go with it, so a cancelled private event leaves no stray list.
export async function onRequestDelete({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  try { await env.DB.prepare("DELETE FROM guests WHERE booking_id=?").bind(id).run(); } catch (e) {}
  const { meta } = await env.DB.prepare("DELETE FROM bookings WHERE id=?").bind(id).run();
  if (!meta.changes) return json({ error: "No such reservation" }, 404);
  return json({ ok: true });
}
