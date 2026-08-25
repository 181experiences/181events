import { json, noDb, fromRow, toCols, CREATE_SQL, adminRole, forbidden } from "../../_lib.js";

// The desk tier (front desk) manages people and codes only; events stay with
// Leo, Scott, Leigh Anne, and Carley-Ann.
function noEvents(request, env) {
  const role = adminRole(request, env);
  return !role || role === "desk";
}

// GET /api/events -> every row, every status, for the admin. Reading is open to
// every tier, the desk included: their dashboard and RSVP work needs the list.
// Writing events stays out of the desk's reach below.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await env.DB.prepare(CREATE_SQL).run();
  const { results } = await env.DB.prepare("SELECT * FROM events ORDER BY date, start24").all();
  return json({ events: results.map(fromRow) });
}

// POST /api/events {fields} -> a new row.
export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (noEvents(request, env)) return forbidden();
  const { cols, vals } = toCols(await request.json());
  if (!cols.length) return json({ error: "Nothing to save" }, 400);
  await env.DB.prepare(CREATE_SQL).run();
  const sql = `INSERT INTO events (${cols.join(",")}) VALUES (${cols.map(() => "?").join(",")}) RETURNING *`;
  const row = await env.DB.prepare(sql).bind(...vals).first();
  return json(fromRow(row), 201);
}
