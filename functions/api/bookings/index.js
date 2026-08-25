import { json, noDb, adminRole, forbidden, ensureResidentTables, to24 } from "../../_lib.js";

// Space reservations for Level 39. Every admin tier may work here, the front desk
// included, since that is where a booking usually starts. Residents see only the
// space, date, and hours on /spaces; the note never leaves the admin.

export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT * FROM bookings ORDER BY date, start24").all();
  return json({ bookings: results });
}

export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const b = await request.json();
  const space = String(b.space || "").trim();
  const date = String(b.date || "").trim();
  if (!space || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return json({ error: "A space and a date are needed." }, 400);
  const start = String(b.start || "").trim(), end = String(b.end || "").trim();
  const row = await env.DB.prepare(
    `INSERT INTO bookings (space, date, start, end_time, start24, note, created)
     VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *`)
    .bind(space, date, start, end, to24(start), String(b.note || "").trim(),
      new Date().toISOString()).first();
  return json({ booking: row }, 201);
}
