import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail, notifyStaff } from "../../_lib.js";

// PATCH /api/guests/:id {arrived?, name?, plus_one?, email?} -> the door
// check-off (stamped with the moment; unchecking clears it), and the desk's
// corrections: a fixed spelling, a plus one added or dropped, a right email.
// Every write stamps who and when; door work stays quiet, real changes to the
// registration earn Leo an email, mirroring the rsvps doctrine.
export async function onRequestPatch(context) {
  const { request, params, env } = context;
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  const sets = [], vals = [];
  if ("arrived" in b) { sets.push("arrived=?"); vals.push(b.arrived ? new Date().toISOString() : null); }
  if ("name" in b) {
    const name = String(b.name || "").trim().slice(0, 80);
    if (!name) return json({ error: "A name is needed." }, 400);
    sets.push("name=?"); vals.push(name);
  }
  if ("plus_one" in b) { sets.push("plus_one=?"); vals.push(String(b.plus_one || "").trim().slice(0, 80) || null); }
  if ("email" in b) { sets.push("email=?"); vals.push(String(b.email || "").trim().slice(0, 120) || null); }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  sets.push("updated=?"); vals.push(new Date().toISOString());
  sets.push("updated_by=?"); vals.push(who);
  const row = await env.DB.prepare(
    `UPDATE guests SET ${sets.join(",")} WHERE id=? RETURNING *`)
    .bind(...vals, id).first();
  if (!row) return json({ error: "No such registration" }, 404);
  if ("name" in b || "plus_one" in b || "email" in b) {
    const bk = await env.DB.prepare("SELECT event_name, date FROM bookings WHERE id=?").bind(row.booking_id).first();
    notifyStaff(context, `Guest changed (staff) · ${row.name} · ${(bk && bk.event_name) || "private event"}`, [
      `${who} changed a registration: ${(bk && bk.event_name) || "private event"}${bk && bk.date ? `, ${bk.date}` : ""}.`,
      `Now: ${row.name}${row.plus_one ? ` and ${row.plus_one}` : ", no plus one"}${row.email ? ` · ${row.email}` : ""}.`,
    ]);
  }
  return json({ guest: row });
}

// DELETE /api/guests/:id -> remove a registration (a duplicate, a typo).
// The removal is the one write the row cannot record, so the email carries it.
export async function onRequestDelete(context) {
  const { request, params, env } = context;
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const row = await env.DB.prepare("SELECT * FROM guests WHERE id=?").bind(id).first();
  if (!row) return json({ error: "No such registration" }, 404);
  await env.DB.prepare("DELETE FROM guests WHERE id=?").bind(id).run();
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const bk = await env.DB.prepare("SELECT event_name, date FROM bookings WHERE id=?").bind(row.booking_id).first();
  notifyStaff(context, `Guest removed (staff) · ${row.name} · ${(bk && bk.event_name) || "private event"}`, [
    `${who} removed a registration: ${(bk && bk.event_name) || "private event"}${bk && bk.date ? `, ${bk.date}` : ""}.`,
    `Removed: ${row.name}${row.plus_one ? ` and ${row.plus_one}` : ""}${row.email ? ` · ${row.email}` : ""}.`,
  ]);
  return json({ ok: true });
}
