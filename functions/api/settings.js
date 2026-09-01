import { json, noDb, adminRole, forbidden, ensureEventTables, getWindow } from "../_lib.js";

// The calendar window dials: how many weeks out an event shows its full page
// (RSVP, Add to My Calendar), and how many months out the calendar shows
// anything at all. The build reads these at every rebuild, so the windows
// slide forward on their own, five times a day.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  return json(await getWindow(env));
}

export async function onRequestPut({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  const body = await request.json();
  const weeks = Math.min(12, Math.max(1, Number(body.detail_weeks) || 8));
  const months = Math.min(4, Math.max(1, Number(body.horizon_months) || 4));
  await ensureEventTables(env);
  await env.DB.batch([
    env.DB.prepare("INSERT INTO settings (key, value) VALUES ('detail_weeks', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(String(weeks)),
    env.DB.prepare("INSERT INTO settings (key, value) VALUES ('horizon_months', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(String(months)),
  ]);
  return json({ detail_weeks: weeks, horizon_months: months });
}
