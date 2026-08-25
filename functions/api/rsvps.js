import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../_lib.js";

// GET /api/rsvps -> every non-cancelled RSVP with its person and unit attached,
// for the dashboard counts, the per-event rollups, and the CSV export.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    // Waitlist order is creation order; the join names the person and unit.
    `SELECT r.id, r.event_key, r.event_date, r.event_title, r.rsvp_type, r.count,
            r.names, r.status, r.created, r.updated, res.name, res.unit
     FROM rsvps r JOIN residents res ON res.id = r.resident_id
     WHERE r.status != 'Cancelled'
     ORDER BY r.event_date, r.event_key, r.created`).all();
  return json({ rsvps: results });
}
