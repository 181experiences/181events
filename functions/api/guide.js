import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../_lib.js";

// The Black Book keeps three kinds of knowledge apart, so each can say where
// it came from and when:
//
//   the file    source/guide_places.json rides the admin page. It is what the
//               weekly check found on each place's own website, and it carries
//               its own history of what the system changed. ("Information
//               automatically updated on")
//   the team    a correction typed in by someone at the desk is stored here as
//               an edit laid over the file, field by field, signed and logged.
//               A call to the place stamps who verified it and when.
//               ("Location information last verified on, by")
//   the house   our connection there: who we know, their number, a note.
//
// GET /api/guide -> { notes: { <place id>: {...} }, log: [ {place, at, who, action, changes} ] }
// Every tier reads; the desk is who the book is for.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT place_id, connected, contact, phone, note, updated, updated_by, verified_at, verified_by, edits FROM guide_notes").all();
  const notes = {};
  for (const r of results) notes[r.place_id] = noteView(r);
  const log = (await env.DB.prepare(
    "SELECT label, at, who, action, changes FROM change_log WHERE kind='guide' ORDER BY id DESC LIMIT 2000").all()).results;
  return json({ notes, log: log.map(r => ({ place: r.label || "", at: r.at, who: r.who || "", action: r.action,
    changes: r.changes ? JSON.parse(r.changes) : null })) });
}

export function noteView(r) {
  let edits = {};
  try { edits = r.edits ? JSON.parse(r.edits) : {}; } catch (e) { edits = {}; }
  return { connected: !!r.connected, contact: r.contact || "", phone: r.phone || "", note: r.note || "",
    updated: r.updated || "", updated_by: r.updated_by || "",
    verified_at: r.verified_at || "", verified_by: r.verified_by || "", edits };
}
