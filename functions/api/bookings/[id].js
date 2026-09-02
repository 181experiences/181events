import { json, noDb, adminRole, forbidden, ensureResidentTables, to24 } from "../../_lib.js";

// PATCH /api/bookings/:id -> edit the reservation (space, date, hours, note),
// its private-event face (event name, host, cap), or the registration switch.
// The registration link itself never changes: invitations already sent keep
// working, and the page they open always shows the current details.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  const sets = [], vals = [];
  if ("space" in b) {
    const v = String(b.space || "").trim();
    if (!v) return json({ error: "A space is needed." }, 400);
    sets.push("space=?"); vals.push(v);
  }
  if ("date" in b) {
    const v = String(b.date || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return json({ error: "Dates read as YYYY-MM-DD." }, 400);
    sets.push("date=?"); vals.push(v);
  }
  if ("start" in b) {
    const v = String(b.start || "").trim();
    sets.push("start=?", "start24=?"); vals.push(v, to24(v));
  }
  if ("end" in b) { sets.push("end_time=?"); vals.push(String(b.end || "").trim()); }
  if ("reg_open" in b) { sets.push("reg_open=?"); vals.push(b.reg_open ? 1 : 0); }
  for (const f of ["event_name", "host", "note"]) {
    if (f in b) { sets.push(`${f}=?`); vals.push(String(b[f] || "").trim() || null); }
  }
  if ("guest_cap" in b) {
    const cap = b.guest_cap ? Math.max(1, Math.min(1000, Number(b.guest_cap) || 0)) || null : null;
    sets.push("guest_cap=?"); vals.push(cap);
  }
  if ("reg_slug" in b) {
    // A written address for the registration page. The token stays valid; this
    // is the face. Lowercase words and hyphens, taken by at most one event.
    const slug = String(b.reg_slug || "").toLowerCase().trim()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
    if (slug) {
      if (slug.length < 3) return json({ error: "A custom address needs at least three characters." }, 400);
      const clash = await env.DB.prepare(
        "SELECT id FROM bookings WHERE reg_slug=? AND id!=?").bind(slug, id).first();
      if (clash) return json({ error: `The address /register/${slug} is already taken by another reservation.` }, 400);
    }
    sets.push("reg_slug=?"); vals.push(slug || null);
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
