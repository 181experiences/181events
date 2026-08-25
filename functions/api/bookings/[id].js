import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// DELETE /api/bookings/:id -> the room shows as open again, at once.
export async function onRequestDelete({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const { meta } = await env.DB.prepare("DELETE FROM bookings WHERE id=?").bind(id).run();
  if (!meta.changes) return json({ error: "No such reservation" }, 404);
  return json({ ok: true });
}
