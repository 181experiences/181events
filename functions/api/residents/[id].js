import {
  json, noDb, adminRole, forbidden, ensureResidentTables, makeCode, residentView, tenureOf,
  labelOf, residentDiff, logChange,
} from "../../_lib.js";

// PATCH /api/residents/:id -> rotate a code, disable or restore a person, set an
// end date, or correct name, unit, or email. Rotating and disabling bump the
// epoch, which signs that person out on every device at once.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
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
  if ("tenure" in body) { sets.push("tenure=?"); vals.push(tenureOf(body.tenure) || null); }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);

  const before = await env.DB.prepare("SELECT * FROM residents WHERE id=?").bind(id).first();
  const row = await env.DB.prepare(
    `UPDATE residents SET ${sets.join(",")} WHERE id=? RETURNING *`)
    .bind(...vals, id).first();
  if (!row) return json({ error: "No such person" }, 404);
  // The log line: the verb the desk used, and the fields that moved.
  const changes = residentDiff(before, row);
  const action = body.rotate ? "Code rotated"
    : body.status === "Disabled" ? "Disabled"
    : body.status === "Active" ? "Restored"
    : "Edited";
  if (action !== "Edited" || Object.keys(changes).length) {
    await logChange(env, request, "resident", row.id, labelOf(row), action, changes);
  }
  return json(residentView(row));
}

// DELETE /api/residents/:id -> remove the row entirely, along with any RSVPs it
// made, so nothing orphaned lingers in the counts. For typos, duplicates, and
// test rows. Someone who moved out should be Disabled instead: that keeps
// their history and stays one click from restored.
export async function onRequestDelete({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const before = await env.DB.prepare("SELECT * FROM residents WHERE id=?").bind(id).first();
  await env.DB.prepare("DELETE FROM rsvps WHERE resident_id=?").bind(id).run();
  const { meta } = await env.DB.prepare("DELETE FROM residents WHERE id=?").bind(id).run();
  if (!meta.changes) return json({ error: "No such person" }, 404);
  await logChange(env, request, "resident", id, before ? labelOf(before) : "", "Deleted", null);
  return json({ ok: true });
}
