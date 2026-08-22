import { airtable, json, clean } from "../../_lib.js";

// PATCH /api/events/:id {fields} -> the updated row.
export async function onRequestPatch({ request, params, env }) {
  const body = await request.json();
  const r = await airtable(env, "/" + params.id, { method: "PATCH",
    body: JSON.stringify({ fields: clean(body), typecast: true }) });
  if (!r.ok) return json({ error: "Airtable " + r.status, detail: await r.text() }, 502);
  const out = await r.json();
  return json({ id: out.id, ...out.fields });
}
