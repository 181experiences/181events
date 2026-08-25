import { json, noDb, adminRole, forbidden, ensureResidentTables, labelOf } from "../_lib.js";
import { liveEvent, seatsTaken, othersWaiting } from "../_resident.js";

const ROW_SQL = `SELECT r.id, r.event_key, r.event_date, r.event_title, r.rsvp_type, r.count,
        r.names, r.status, r.created, r.updated, res.name, res.unit, res.email
 FROM rsvps r JOIN residents res ON res.id = r.resident_id`;

// GET /api/rsvps -> every non-cancelled RSVP with its person, unit, and email
// attached: the dashboard counts, the rollups, the CSV, and the notify drafts.
// Every tier may read and manage RSVPs; the desk handles them in person daily.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    // Waitlist order is creation order; the join names the person and unit.
    `${ROW_SQL} WHERE r.status != 'Cancelled' ORDER BY r.event_date, r.event_key, r.created`).all();
  return json({ rsvps: results });
}

// POST /api/rsvps {resident_id, event_key, count, names} -> an RSVP entered by
// staff, for the resident who asked in passing or phoned the desk. Capacity and
// the waitlist apply exactly as on the site, so one queue stays one queue; if
// the person already had an RSVP for that event, this updates it.
export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const body = await request.json();

  const resident = await env.DB.prepare(
    "SELECT * FROM residents WHERE id=? AND status='Active'").bind(Number(body.resident_id)).first();
  if (!resident) return json({ error: "No such active person." }, 400);
  const key = String(body.event_key || "");
  const ev = await liveEvent(env, key);
  if (!ev) return json({ error: "That event is not on the live calendar." }, 400);
  const TYPE = { "Seat": "standard", "Paid seat": "paid", "Guest count": "guest" };
  const type = TYPE[ev.rsvp];
  if (!type) return json({ error: `${labelOf(resident)} is always welcome: ${ev.title} is drop-in, no RSVP needed.` }, 400);

  const maxCount = type === "guest" ? 6 : 4;
  let count = Math.round(Number(body.count));
  if (!Number.isFinite(count)) count = 1;
  count = Math.max(1, Math.min(maxCount, count));
  const names = String(body.names || "").trim().slice(0, 120);

  let status = "Confirmed";
  if (ev.capacity && type !== "guest") {
    const taken = await seatsTaken(env, key, resident.id);
    const waiting = await othersWaiting(env, key, resident.id);
    if (taken + count > ev.capacity || waiting > 0) status = "Waitlist";
  }

  const now = new Date().toISOString();
  await env.DB.prepare(
    `INSERT INTO rsvps (resident_id, event_key, event_date, event_title, rsvp_type, count, names, status, created, updated)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(resident_id, event_key) DO UPDATE SET
       rsvp_type=excluded.rsvp_type, count=excluded.count, names=excluded.names,
       status=excluded.status, updated=excluded.updated,
       created=CASE WHEN rsvps.status='Cancelled' THEN excluded.created ELSE rsvps.created END`)
    .bind(resident.id, key, ev.date, ev.title, type, count, names, status, now, now).run();

  const row = await env.DB.prepare(
    `${ROW_SQL} WHERE r.resident_id=? AND r.event_key=?`).bind(resident.id, key).first();
  return json({ rsvp: row }, 201);
}
