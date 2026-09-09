import { json, noDb, adminRole, forbidden, ensureResidentTables, labelOf, notesOpen } from "../_lib.js";

// GET /api/notes -> every active note with its raised hands, for the admin's
// oversight card. Every tier may look: the board is resident-visible anyway,
// and the desk hearing the building's plans is the desk doing its job.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const cutoff = new Date(Date.now() - 3 * 86400000).toISOString();
  const { results: notes } = await env.DB.prepare(
    `SELECT n.*, res.name, res.unit FROM notes n JOIN residents res ON res.id = n.resident_id
     WHERE n.created >= ? ORDER BY n.created DESC`).bind(cutoff).all();
  const { results: hands } = await env.DB.prepare(
    `SELECT h.note_id, res.name, res.unit
     FROM note_hands h JOIN residents res ON res.id = h.resident_id ORDER BY h.id`).all();
  return json({
    open: await notesOpen(env),
    notes: notes.map(n => ({
      id: n.id, body: n.body, created: n.created, who: labelOf(n),
      hands: hands.filter(h => h.note_id === n.id).map(labelOf),
    })),
  });
}
