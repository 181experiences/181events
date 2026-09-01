import { json, noDb, adminRole, forbidden, ensureEventTables } from "../_lib.js";

// GET /api/history?event=ID -> that event's change history, newest first.
// Each row: who, when, action, {field: [old, new]}, and the full snapshot
// after the change, which the editor's "Load this version" reads back.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const id = Number(new URL(request.url).searchParams.get("event"));
  if (!Number.isInteger(id)) return json({ error: "Bad event id" }, 400);
  await ensureEventTables(env);
  const { results } = await env.DB.prepare(
    "SELECT id, at, who, action, changes, snapshot FROM event_history WHERE event_id=? ORDER BY id DESC LIMIT 100")
    .bind(id).all();
  return json({ history: results.map(r => ({
    id: r.id, at: r.at, who: r.who || "", action: r.action,
    changes: r.changes ? JSON.parse(r.changes) : null,
    snapshot: r.snapshot ? JSON.parse(r.snapshot) : null,
  })) });
}
