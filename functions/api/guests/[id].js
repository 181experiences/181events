import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/guests/:id {arrived: true|false} -> the door check-off, stamped
// with the moment; unchecking clears it (a mistaken tap, not a revolving door).
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  if (!("arrived" in b)) return json({ error: "Nothing to change" }, 400);
  const row = await env.DB.prepare(
    "UPDATE guests SET arrived=? WHERE id=? RETURNING *")
    .bind(b.arrived ? new Date().toISOString() : null, id).first();
  if (!row) return json({ error: "No such registration" }, 404);
  return json({ guest: row });
}

// DELETE /api/guests/:id -> remove a registration (a duplicate, a typo).
export async function onRequestDelete({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const { meta } = await env.DB.prepare("DELETE FROM guests WHERE id=?").bind(id).run();
  if (!meta.changes) return json({ error: "No such registration" }, 404);
  return json({ ok: true });
}
