import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/guests/:id {arrived?, name?, plus_one?, email?} -> the door
// check-off (stamped with the moment; unchecking clears it), and the desk's
// corrections: a fixed spelling, a plus one added or dropped, a right email.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  const sets = [], vals = [];
  if ("arrived" in b) { sets.push("arrived=?"); vals.push(b.arrived ? new Date().toISOString() : null); }
  if ("name" in b) {
    const name = String(b.name || "").trim().slice(0, 80);
    if (!name) return json({ error: "A name is needed." }, 400);
    sets.push("name=?"); vals.push(name);
  }
  if ("plus_one" in b) { sets.push("plus_one=?"); vals.push(String(b.plus_one || "").trim().slice(0, 80) || null); }
  if ("email" in b) { sets.push("email=?"); vals.push(String(b.email || "").trim().slice(0, 120) || null); }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);
  const row = await env.DB.prepare(
    `UPDATE guests SET ${sets.join(",")} WHERE id=? RETURNING *`)
    .bind(...vals, id).first();
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
