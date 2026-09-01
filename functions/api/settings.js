import { json, noDb, adminRole, forbidden, ensureEventTables, getWindow } from "../_lib.js";

// The working dials and lists. The calendar window (weeks of full detail,
// months of visibility) feeds the build; locations and hosts feed the event
// editor's dropdowns, so the names of the club are typed once and offered
// everywhere after. PUT writes only the keys it is sent, so saving one list
// never disturbs the others.
const DEFAULTS = {
  locations: ["Level 39, Residents’ Club", "Level 7 Terrace", "Lobby", "Fitness Center"],
  hosts: ["Resident Experiences", "181 Fremont Residences Association", "The Board",
          "Leo Ramirez", "Leigh Anne", "Carley-Ann", "Scott"],
};

function cleanList(v, fallback) {
  if (!Array.isArray(v)) return fallback.slice();
  const out = [];
  for (const item of v) {
    const s = String(item || "").trim().slice(0, 80);
    if (s && !out.includes(s)) out.push(s);
    if (out.length >= 60) break;
  }
  return out;
}

async function readLists(env) {
  const out = { locations: DEFAULTS.locations.slice(), hosts: DEFAULTS.hosts.slice() };
  try {
    const { results } = await env.DB.prepare(
      "SELECT key, value FROM settings WHERE key IN ('locations','hosts')").all();
    for (const r of results) {
      try {
        const v = JSON.parse(r.value);
        if (Array.isArray(v) && v.length) out[r.key] = cleanList(v, DEFAULTS[r.key]);
      } catch (e) {}
    }
  } catch (e) {}
  return out;
}

export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureEventTables(env);
  return json({ ...(await getWindow(env)), ...(await readLists(env)) });
}

export async function onRequestPut({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const body = await request.json();
  await ensureEventTables(env);
  const writes = [];
  const put = (key, value) => writes.push(env.DB.prepare(
    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value")
    .bind(key, value));
  if ("detail_weeks" in body) put("detail_weeks", String(Math.min(12, Math.max(1, Number(body.detail_weeks) || 8))));
  if ("horizon_months" in body) put("horizon_months", String(Math.min(4, Math.max(1, Number(body.horizon_months) || 4))));
  if ("locations" in body) put("locations", JSON.stringify(cleanList(body.locations, DEFAULTS.locations)));
  if ("hosts" in body) put("hosts", JSON.stringify(cleanList(body.hosts, DEFAULTS.hosts)));
  if (!writes.length) return json({ error: "Nothing to save" }, 400);
  await env.DB.batch(writes);
  return json({ ...(await getWindow(env)), ...(await readLists(env)) });
}
