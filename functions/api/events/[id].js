import { json, noDb, fromRow, toCols, adminRole, forbidden } from "../../_lib.js";

// PATCH /api/events/:id {fields} -> the updated row. Not for the desk tier.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const { cols, vals } = toCols(await request.json());
  if (!cols.length) return json({ error: "Nothing to save" }, 400);
  const sql = `UPDATE events SET ${cols.map(c => c + "=?").join(",")} WHERE id=? RETURNING *`;
  const row = await env.DB.prepare(sql).bind(...vals, id).first();
  if (!row) return json({ error: "No such event" }, 404);
  return json(fromRow(row));
}
