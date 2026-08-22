import { airtable, json, clean } from "../../_lib.js";

// GET /api/events -> every row, every status, for the admin.
export async function onRequestGet({ env }) {
  let records = [], offset;
  do {
    const q = new URLSearchParams({ pageSize: "100", "sort[0][field]": "Date", "sort[0][direction]": "asc" });
    if (offset) q.set("offset", offset);
    const r = await airtable(env, "?" + q.toString());
    if (!r.ok) return json({ error: "Airtable " + r.status, detail: await r.text() }, 502);
    const page = await r.json();
    records = records.concat(page.records);
    offset = page.offset;
  } while (offset);
  return json({ events: records.map(r => ({ id: r.id, ...r.fields })) });
}

// POST /api/events {fields} -> a new row.
export async function onRequestPost({ request, env }) {
  const body = await request.json();
  const r = await airtable(env, "", { method: "POST",
    body: JSON.stringify({ records: [{ fields: clean(body) }], typecast: true }) });
  if (!r.ok) return json({ error: "Airtable " + r.status, detail: await r.text() }, 502);
  const out = await r.json();
  return json({ id: out.records[0].id, ...out.records[0].fields }, 201);
}
