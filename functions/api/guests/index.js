import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail, notifyStaff } from "../../_lib.js";

// The guest list behind a private event's registration page. Every admin tier
// works here, the desk first among them: this is the list security runs from.

// GET /api/guests?booking=ID -> that reservation's registrations, oldest first.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(new URL(request.url).searchParams.get("booking"));
  if (!Number.isInteger(id)) return json({ error: "Bad booking id" }, 400);
  const { results } = await env.DB.prepare(
    "SELECT * FROM guests WHERE booking_id=? ORDER BY id").bind(id).all();
  return json({ guests: results });
}

// POST /api/guests {booking_id, name, plus_one} -> a registration added at the
// desk, for the invitee who arrives vouched-for but never used the link.
// Stamped with who added it, and Leo hears, same as every list change.
export async function onRequestPost(context) {
  const { request, env } = context;
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const b = await request.json();
  const id = Number(b.booking_id);
  const name = String(b.name || "").trim().slice(0, 80);
  if (!Number.isInteger(id) || !name) return json({ error: "A booking and a name are needed." }, 400);
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const now = new Date().toISOString();
  const row = await env.DB.prepare(
    `INSERT INTO guests (booking_id, name, plus_one, created, updated, updated_by)
     VALUES (?, ?, ?, ?, ?, ?) RETURNING *`)
    .bind(id, name, String(b.plus_one || "").trim().slice(0, 80) || null, now, now, who).first();
  const bk = await env.DB.prepare("SELECT event_name, date FROM bookings WHERE id=?").bind(id).first();
  notifyStaff(context, `Guest added (staff) · ${name}${row.plus_one ? " +1" : ""} · ${(bk && bk.event_name) || "private event"}`, [
    `${who} added a guest at the desk: ${(bk && bk.event_name) || "private event"}${bk && bk.date ? `, ${bk.date}` : ""}.`,
    `${name}${row.plus_one ? ` and ${row.plus_one}` : ""}.`,
  ]);
  return json({ guest: row }, 201);
}
