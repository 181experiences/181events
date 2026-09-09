import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// DELETE /api/notes/:id -> the groundskeeper's tool: any note comes down when
// staff say so, no reason recorded, no fuss made. Not for the desk tier.
export async function onRequestDelete({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  await ensureResidentTables(env);
  await env.DB.prepare("DELETE FROM note_hands WHERE note_id=?").bind(id).run();
  await env.DB.prepare("DELETE FROM notes WHERE id=?").bind(id).run();
  return json({ ok: true });
}
