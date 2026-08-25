import {
  json, noDb, adminRole, forbidden, ensureResidentTables, makeCode, residentView,
} from "../../_lib.js";

// PATCH /api/residents/:id -> rotate a code, disable or restore a person, set an
// end date, or correct name, unit, or email. Rotating and disabling bump the
// epoch, which signs that person out on every device at once.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const body = await request.json();

  const sets = [], vals = [];
  if (body.rotate) { sets.push("code=?", "epoch=epoch+1"); vals.push(makeCode()); }
  if (body.status === "Active" || body.status === "Disabled") {
    sets.push("status=?", "epoch=epoch+1"); vals.push(body.status);
  }
  for (const f of ["name", "unit", "email", "ends"]) {
    if (f in body) {
      sets.push(`${f}=?`);
      const v = String(body[f] || "").trim();
      vals.push(f === "unit" ? (v.toUpperCase() || null) : (v || null));
    }
  }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);

  const row = await env.DB.prepare(
    `UPDATE residents SET ${sets.join(",")} WHERE id=? RETURNING *`)
    .bind(...vals, id).first();
  if (!row) return json({ error: "No such person" }, 404);
  return json(residentView(row));
}
