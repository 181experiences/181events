import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/rsvps/:id {status?, count?, names?} -> staff changes to an RSVP:
// promote a waitlisted party, adjust a party size for someone who asked in
// passing, or cancel outright. Every tier may do this; the desk fields these
// requests all day. The admin opens a pre-written note to the resident after,
// so the person always hears about a change made on their behalf.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const body = await request.json();

  const sets = [], vals = [];
  if ("status" in body) {
    if (!["Confirmed", "Waitlist", "Cancelled"].includes(body.status)) return json({ error: "Bad status" }, 400);
    sets.push("status=?"); vals.push(body.status);
  }
  if ("count" in body) {
    const count = Math.round(Number(body.count));
    if (!Number.isFinite(count) || count < 1 || count > 6) return json({ error: "Party size runs 1 to 6." }, 400);
    sets.push("count=?"); vals.push(count);
  }
  if ("names" in body) { sets.push("names=?"); vals.push(String(body.names || "").trim().slice(0, 120)); }
  if ("arrived" in body) {
    // Attendance mark: null clears, 0-6 records how many of the party came.
    if (body.arrived === null) { sets.push("arrived=NULL", "arrived_at=NULL"); }
    else {
      const n = Math.round(Number(body.arrived));
      if (!Number.isFinite(n) || n < 0 || n > 6) return json({ error: "Arrived runs 0 to 6." }, 400);
      sets.push("arrived=?"); vals.push(n);
      sets.push("arrived_at=?"); vals.push(new Date().toISOString());
    }
  }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);
  sets.push("updated=?"); vals.push(new Date().toISOString());

  const row = await env.DB.prepare(
    `UPDATE rsvps SET ${sets.join(",")} WHERE id=? RETURNING *`).bind(...vals, id).first();
  if (!row) return json({ error: "No such RSVP" }, 404);
  return json({ id: row.id, status: row.status, count: row.count, names: row.names || "",
                arrived: row.arrived ?? null, arrived_at: row.arrived_at || "" });
}
