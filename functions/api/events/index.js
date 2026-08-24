import { json, noDb, fromRow, toCols, CREATE_SQL } from "../../_lib.js";

// GET /api/events -> every row, every status, for the admin.
export async function onRequestGet({ env }) {
  const err = noDb(env); if (err) return err;
  await env.DB.prepare(CREATE_SQL).run();
  const { results } = await env.DB.prepare("SELECT * FROM events ORDER BY date, start24").all();
  return json({ events: results.map(fromRow) });
}

// POST /api/events {fields} -> a new row.
export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  const { cols, vals } = toCols(await request.json());
  if (!cols.length) return json({ error: "Nothing to save" }, 400);
  await env.DB.prepare(CREATE_SQL).run();
  const sql = `INSERT INTO events (${cols.join(",")}) VALUES (${cols.map(() => "?").join(",")}) RETURNING *`;
  const row = await env.DB.prepare(sql).bind(...vals).first();
  return json(fromRow(row), 201);
}
