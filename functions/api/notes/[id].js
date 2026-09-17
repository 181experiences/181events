import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail } from "../../_lib.js";

// DELETE /api/notes/:id -> take a note down, any tier, the desk included: at
// 2 AM a quick eye can save the day, and the archive holds everyone to
// account. The note keeps its record (hands too) under Past notes, marked
// with who took it down and when.
export async function onRequestDelete({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  await ensureResidentTables(env);
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const { meta } = await env.DB.prepare(
    "UPDATE notes SET deleted_at=?, deleted_by=? WHERE id=? AND deleted_at IS NULL")
    .bind(new Date().toISOString(), who, id).run();
  if (!meta.changes) return json({ error: "No such note, or it is already down." }, 404);
  return json({ ok: true });
}

// PATCH /api/notes/:id {restore: true} -> put a taken-down note back on the
// board. It keeps its ORIGINAL fade date, so a restore never extends a
// note's life; one already past the fade simply stays in the archive.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  if (!b.restore) return json({ error: "Nothing to change" }, 400);
  await ensureResidentTables(env);
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const { meta } = await env.DB.prepare(
    "UPDATE notes SET deleted_at=NULL, deleted_by=NULL, restored_at=?, restored_by=? WHERE id=? AND deleted_at IS NOT NULL")
    .bind(new Date().toISOString(), who, id).run();
  if (!meta.changes) return json({ error: "No such note, or it is not down." }, 404);
  return json({ ok: true });
}
