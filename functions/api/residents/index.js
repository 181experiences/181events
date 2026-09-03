import {
  json, noDb, adminRole, forbidden, ensureResidentTables, makeCode, residentView, tenureOf,
} from "../../_lib.js";

// The person registry: every admin tier may work here, including the front desk,
// so a 10 pm "I lost my code" has an answer without waiting for the morning.

// GET /api/residents -> everyone, grouped client-side. Seeds the front desk role
// account on first sight of an empty table, so it exists before anyone asks.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
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
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const body = await request.json();
  const now = new Date().toISOString();
  const people = [];

  if (typeof body.bulk === "string") {
    for (const line of body.bulk.split(/\r?\n/)) {
      const parts = line.split(",").map(s => s.trim());
      if (!parts[0] || !parts[1]) continue;
      people.push({ unit: parts[0].toUpperCase(), name: parts[1], email: parts[2] || "",
        tenure: tenureOf(parts[3]), ends: "", kind: "resident" });
    }
    if (!people.length) return json({ error: "No lines matched. Each line: unit, name, email, owner or tenant (the last two optional)." }, 400);
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
      tenure: tenureOf(body.tenure),
    });
  }

  // A bulk paste is a sync, not a batch of strangers: Leo re-pastes the whole
  // building directory, and anyone already listed must keep the code they have.
  // The key is unit + name; a match is skipped (blank email or standing on the
  // existing row is quietly filled from the paste, nothing else touched).
  const keyOf = (unit, name) => `${String(unit || "").toUpperCase()}|${String(name || "").trim().replace(/\s+/g, " ").toLowerCase()}`;
  const isBulk = typeof body.bulk === "string";
  const existing = new Map();
  if (isBulk) {
    const { results } = await env.DB.prepare(
      "SELECT * FROM residents WHERE kind='resident'").all();
    for (const r of results) existing.set(keyOf(r.unit, r.name), r);
  }

  const made = [], updated = [];
  let skipped = 0, disabled = 0;
  const seenInPaste = new Set();
  for (const p of people) {
    if (isBulk) {
      const k = keyOf(p.unit, p.name);
      if (seenInPaste.has(k)) continue;
      seenInPaste.add(k);
      const have = existing.get(k);
      if (have) {
        skipped++;
        if (have.status !== "Active") disabled++;
        const sets = [], vals = [];
        if (p.email && !have.email) { sets.push("email=?"); vals.push(p.email); }
        if (p.tenure && !have.tenure) { sets.push("tenure=?"); vals.push(p.tenure); }
        if (sets.length) {
          const row = await env.DB.prepare(
            `UPDATE residents SET ${sets.join(",")} WHERE id=? RETURNING *`)
            .bind(...vals, have.id).first();
          updated.push(residentView(row));
        }
        continue;
      }
    }
    const row = await env.DB.prepare(
      `INSERT INTO residents (kind, unit, name, email, code, ends, created, tenure)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *`)
      .bind(p.kind, p.unit || null, p.name, p.email || null, makeCode(),
        p.ends || null, now, p.tenure || null).first();
    made.push(residentView(row));
  }
  return json({ residents: made, updated, skipped, disabled }, 201);
}
