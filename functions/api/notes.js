import { json, noDb, adminRole, forbidden, ensureResidentTables, labelOf, notesOpen } from "../_lib.js";

// GET /api/notes -> every active note with its raised hands, for the admin's
// oversight card. Every tier may look: the board is resident-visible anyway,
// and the desk hearing the building's plans is the desk doing its job.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const cutoff = new Date(Date.now() - 3 * 86400000).toISOString();
  const { results: all } = await env.DB.prepare(
    `SELECT n.*, res.name, res.unit FROM notes n JOIN residents res ON res.id = n.resident_id
     ORDER BY n.created DESC LIMIT 200`).all();
  const { results: hands } = await env.DB.prepare(
    `SELECT h.note_id, res.name, res.unit
     FROM note_hands h JOIN residents res ON res.id = h.resident_id ORDER BY h.id`).all();
  const shape = n => ({
    id: n.id, body: n.body, created: n.created, who: labelOf(n),
    hands: hands.filter(h => h.note_id === n.id).map(labelOf),
    deleted_at: n.deleted_at || null, deleted_by: n.deleted_by || null,
    restored_at: n.restored_at || null, restored_by: n.restored_by || null,
  });
  return json({
    open: await notesOpen(env),
    notes: all.filter(n => n.created >= cutoff && !n.deleted_at).map(shape),
    // The archive: faded and taken-down notes with their full account of
    // when each posted, left, came back, and who was joining.
    past: all.filter(n => n.created < cutoff || n.deleted_at).map(shape),
  });
}
