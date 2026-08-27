import { json, noDb, fromRow, toCols, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/events/:id {fields} -> the updated row. Not for the desk tier.
// RSVPs are addressed by date_slug, so when a date or slug moves, the event's
// RSVPs are re-addressed with it: the sign-ups, the counts, and every calendar
// feed follow the event to its new day instead of pointing at a ghost.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const { cols, vals } = toCols(await request.json());
  if (!cols.length) return json({ error: "Nothing to save" }, 400);
  const before = await env.DB.prepare("SELECT date, slug, title FROM events WHERE id=?").bind(id).first();
  if (!before) return json({ error: "No such event" }, 404);
  const sql = `UPDATE events SET ${cols.map(c => c + "=?").join(",")} WHERE id=? RETURNING *`;
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
  return json(fromRow(row));
}
