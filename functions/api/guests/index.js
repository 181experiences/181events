import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// The guest list behind a private event's registration page. Every admin tier
// works here, the desk first among them: this is the list security runs from.

// GET /api/guests?booking=ID -> that reservation's registrations, oldest first.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const id = Number(new URL(request.url).searchParams.get("booking"));
  if (!Number.isInteger(id)) return json({ error: "Bad booking id" }, 400);
  const { results } = await env.DB.prepare(
    "SELECT * FROM guests WHERE booking_id=? ORDER BY id").bind(id).all();
  return json({ guests: results });
}

// POST /api/guests {booking_id, name, plus_one} -> a registration added at the
// desk, for the invitee who arrives vouched-for but never used the link.
export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const b = await request.json();
  const id = Number(b.booking_id);
  const name = String(b.name || "").trim().slice(0, 80);
  if (!Number.isInteger(id) || !name) return json({ error: "A booking and a name are needed." }, 400);
  const row = await env.DB.prepare(
    `INSERT INTO guests (booking_id, name, plus_one, created) VALUES (?, ?, ?, ?) RETURNING *`)
    .bind(id, name, String(b.plus_one || "").trim().slice(0, 80) || null,
      new Date().toISOString()).first();
  return json({ guest: row }, 201);
}
