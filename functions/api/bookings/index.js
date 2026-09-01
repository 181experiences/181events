import { json, noDb, adminRole, forbidden, ensureResidentTables, to24, makeFeedToken } from "../../_lib.js";

// Space reservations for Level 39. Every admin tier may work here, the front desk
// included, since that is where a booking usually starts. Residents see only the
// space, date, and hours on /spaces; the note never leaves the admin.
//
// A reservation can also be a private event with outside guests: give it an
// event name and open registration, and its unguessable /register/{token} page
// lets invitees put their names (and a plus one) on the list the desk and
// security run from. Guest counts ride along with every row here.

export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT * FROM bookings ORDER BY date, start24").all();
  const counts = {};
  try {
    const g = await env.DB.prepare(
      `SELECT booking_id, COUNT(*) AS parties,
              SUM(CASE WHEN plus_one IS NOT NULL AND plus_one != '' THEN 2 ELSE 1 END) AS heads,
              SUM(CASE WHEN arrived IS NOT NULL THEN 1 ELSE 0 END) AS arrived
       FROM guests GROUP BY booking_id`).all();
    for (const r of g.results) counts[r.booking_id] = r;
  } catch (e) {}
  return json({ bookings: results.map(b => ({
    ...b, guest_parties: counts[b.id] ? counts[b.id].parties : 0,
    guest_heads: counts[b.id] ? counts[b.id].heads : 0,
    guest_arrived: counts[b.id] ? counts[b.id].arrived : 0,
  })) });
}

export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const b = await request.json();
  const space = String(b.space || "").trim();
  const date = String(b.date || "").trim();
  if (!space || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return json({ error: "A space and a date are needed." }, 400);
  const start = String(b.start || "").trim(), end = String(b.end || "").trim();
  const cap = b.guest_cap ? Math.max(1, Math.min(1000, Number(b.guest_cap) || 0)) || null : null;
  const row = await env.DB.prepare(
    `INSERT INTO bookings (space, date, start, end_time, start24, note, created,
                           event_name, host, reg_token, reg_open, guest_cap)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?) RETURNING *`)
    .bind(space, date, start, end, to24(start), String(b.note || "").trim(),
      new Date().toISOString(), String(b.event_name || "").trim() || null,
      String(b.host || "").trim() || null, makeFeedToken(), cap).first();
  return json({ booking: { ...row, guest_parties: 0, guest_heads: 0, guest_arrived: 0 } }, 201);
}
