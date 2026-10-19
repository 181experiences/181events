import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// GET /api/residents/history[?person=ID] -> the roster change log, newest
// first: who did what to whom, when, and which fields moved. Owner and staff
// read it; the desk tier does not. The log is append-only: nothing here is
// ever edited or removed through the site.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureResidentTables(env);
  const person = Number(new URL(request.url).searchParams.get("person"));
  const { results } = Number.isInteger(person) && person > 0
    ? await env.DB.prepare(
        "SELECT id, ref_id, label, at, who, action, changes FROM change_log WHERE kind='resident' AND ref_id=? ORDER BY id DESC LIMIT 1000")
        .bind(person).all()
    : await env.DB.prepare(
        "SELECT id, ref_id, label, at, who, action, changes FROM change_log WHERE kind='resident' ORDER BY id DESC LIMIT 1000").all();
  return json({ log: results.map(r => ({
    id: r.id, person: r.ref_id, label: r.label || "", at: r.at, who: r.who || "",
    action: r.action, changes: r.changes ? JSON.parse(r.changes) : null,
  })) });
}
