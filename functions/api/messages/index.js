import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// GET /api/messages -> the inbox. Bodies (and reply addresses) leave the server
// only for the owner tier; every other admin sees who wrote, when, on what topic,
// and whether it has been answered. That redaction happens here, not in styling.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = adminRole(request, env);
  if (!role) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT * FROM messages ORDER BY (state='New') DESC, created DESC").all();
  const full = role === "owner";
  return json({
    role,
    messages: results.map(m => ({
      id: m.id, unit: m.unit || "", sender: m.sender || "", topic: m.topic || "",
      state: m.state, replied: m.replied || "", created: m.created,
      name: full ? (m.name || "") : "",
      email: full ? (m.email || "") : "",
      body: full ? m.body : null,
    })),
  });
}
