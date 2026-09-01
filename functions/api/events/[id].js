import { json, noDb, fromRow, toCols, adminRole, forbidden, ensureResidentTables,
         ensureEventTables, fieldDiff, logHistory } from "../../_lib.js";

// PATCH /api/events/:id -> the updated row. Not for the desk tier.
//
// Two kinds of body. {__draft: {...}} stores a Live event's working copy in
// draft_json without touching what residents see ({__draft: null} discards it);
// nothing else changes and the site never reads that column. A regular {fields}
// body writes the row itself, clears any working copy (publishing IS the apply),
// and lands in the change history with who, when, and what changed.
//
// RSVPs are addressed by date_slug, so when a date or slug moves, the event's
// RSVPs are re-addressed with it: the sign-ups, the counts, and every calendar
// feed follow the event to its new day instead of pointing at a ghost.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  await ensureEventTables(env);
  const body = await request.json();

  if ("__draft" in body) {
    const stored = body.__draft == null ? null : JSON.stringify(body.__draft);
    const row = await env.DB.prepare(
      "UPDATE events SET draft_json=? WHERE id=? RETURNING *").bind(stored, id).first();
    if (!row) return json({ error: "No such event" }, 404);
    await logHistory(env, request, id, stored ? "Draft saved" : "Draft discarded", null, null);
    return json(fromRow(row));
  }

  const { cols, vals } = toCols(body);
  if (!cols.length) return json({ error: "Nothing to save" }, 400);
  const before = await env.DB.prepare("SELECT * FROM events WHERE id=?").bind(id).first();
  if (!before) return json({ error: "No such event" }, 404);
  const sql = `UPDATE events SET ${cols.map(c => c + "=?").join(",")}, draft_json=NULL WHERE id=? RETURNING *`;
  const row = await env.DB.prepare(sql).bind(...vals, id).first();
  if (!row) return json({ error: "No such event" }, 404);
  const oldKey = `${before.date}_${before.slug}`;
  const newKey = `${row.date}_${row.slug}`;
  if (oldKey !== newKey || before.title !== row.title) {
    await ensureResidentTables(env);
    await env.DB.prepare(
      "UPDATE rsvps SET event_key=?, event_date=?, event_title=? WHERE event_key=?")
      .bind(newKey, row.date, row.title, oldKey).run();
  }
  const changes = fieldDiff(before, row);
  if (Object.keys(changes).length) {
    const action = "Status" in changes ? `Status: ${changes.Status[0] || "Draft"} → ${changes.Status[1]}` : "Edited";
    await logHistory(env, request, id, action, changes, row);
  }
  return json(fromRow(row));
}
