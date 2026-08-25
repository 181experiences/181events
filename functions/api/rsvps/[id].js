import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/rsvps/:id {status} -> promote a waitlisted party to Confirmed (or
// step one back). Freed seats are never given away automatically; this is how
// staff hand them to the queue, in order, and then let the resident know.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const { status } = await request.json();
  if (!["Confirmed", "Waitlist"].includes(status)) return json({ error: "Bad status" }, 400);
  const row = await env.DB.prepare(
    "UPDATE rsvps SET status=?, updated=? WHERE id=? RETURNING *")
    .bind(status, new Date().toISOString(), id).first();
  if (!row) return json({ error: "No such RSVP" }, 404);
  return json({ id: row.id, status: row.status });
}
