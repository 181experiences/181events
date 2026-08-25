import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// PATCH /api/messages/:id {state} -> Replied or Archived, with the reply moment
// kept so the dashboard can speak to response times. Owner only: answering
// residents is the one job this inbox exists for, and it is Leo's.
export async function onRequestPatch({ request, params, env }) {
  const err = noDb(env); if (err) return err;
  if (adminRole(request, env) !== "owner") return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const { state } = await request.json();
  if (!["New", "Replied", "Archived"].includes(state)) return json({ error: "Bad state" }, 400);
  const replied = state === "Replied" ? new Date().toISOString() : null;
  const row = await env.DB.prepare(
    "UPDATE messages SET state=?, replied=COALESCE(?, replied) WHERE id=? RETURNING *")
    .bind(state, replied, id).first();
  if (!row) return json({ error: "No such message" }, 404);
  return json({ id: row.id, state: row.state, replied: row.replied || "" });
}
