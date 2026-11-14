import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../_lib.js";

// The Black Book keeps two kinds of knowledge apart. The facts about a place
// (address, hours, phone) ride the admin page from source/guide_places.json,
// checked against each place's own website and shipped with a build. What the
// house itself knows (whether we have someone there, and who) lives here, in
// the database, written by the team and never overwritten by a fact check.
//
// GET /api/guide -> { notes: { <place id>: { connected, contact, phone, note, updated, updated_by } } }
// Every tier reads; the desk is who the book is for.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT place_id, connected, contact, phone, note, updated, updated_by FROM guide_notes").all();
  const notes = {};
  for (const r of results) {
    notes[r.place_id] = { connected: !!r.connected, contact: r.contact || "", phone: r.phone || "",
      note: r.note || "", updated: r.updated || "", updated_by: r.updated_by || "" };
  }
  return json({ notes });
}
