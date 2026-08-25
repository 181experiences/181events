import {
  json, noDb, adminRole, forbidden, ensureResidentTables, makeCode, residentView,
} from "../../_lib.js";

// The person registry: every admin tier may work here, including the front desk,
// so a 10 pm "I lost my code" has an answer without waiting for the morning.

// GET /api/residents -> everyone, grouped client-side. Seeds the front desk role
// account on first sight of an empty table, so it exists before anyone asks.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const { c } = await env.DB.prepare("SELECT COUNT(*) AS c FROM residents").first();
  if (c === 0) {
    await env.DB.prepare(
      `INSERT INTO residents (kind, unit, name, email, code, created)
       VALUES ('role', NULL, 'Front Desk', 'concierge@181sf.com', ?, ?)`)
      .bind(makeCode(), new Date().toISOString()).run();
  }
  const { results } = await env.DB.prepare(
    "SELECT * FROM residents ORDER BY kind DESC, unit, name").all();
  return json({ residents: results.map(residentView) });
}

// POST /api/residents -> add people. Accepts one person {unit, name, email, ends, kind}
// or {bulk: "12A, Margaret, margaret@..."} with one person per line.
export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!adminRole(request, env)) return forbidden();
  await ensureResidentTables(env);
  const body = await request.json();
  const now = new Date().toISOString();
  const people = [];

  if (typeof body.bulk === "string") {
    for (const line of body.bulk.split(/\r?\n/)) {
      const parts = line.split(",").map(s => s.trim());
      if (!parts[0] || !parts[1]) continue;
      people.push({ unit: parts[0].toUpperCase(), name: parts[1], email: parts[2] || "", ends: "", kind: "resident" });
    }
    if (!people.length) return json({ error: "No lines matched. Each line: unit, name, email (email optional)." }, 400);
  } else {
    const kind = body.kind === "role" ? "role" : "resident";
    const name = String(body.name || "").trim();
    const unit = kind === "role" ? "" : String(body.unit || "").trim().toUpperCase();
    if (!name) return json({ error: "A name is needed." }, 400);
    if (kind === "resident" && !unit) return json({ error: "A unit is needed for a resident." }, 400);
    people.push({
      unit, name, kind,
      email: String(body.email || "").trim(),
      ends: String(body.ends || "").trim(),
    });
  }

  const made = [];
  for (const p of people) {
    const row = await env.DB.prepare(
      `INSERT INTO residents (kind, unit, name, email, code, ends, created)
       VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *`)
      .bind(p.kind, p.unit || null, p.name, p.email || null, makeCode(),
        p.ends || null, now).first();
    made.push(residentView(row));
  }
  return json({ residents: made }, 201);
}
