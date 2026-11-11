import { json, noDb, adminRole, forbidden, ensureResidentTables, todayPacific } from "../_lib.js";

// GET /api/feeds -> how often calendar apps have come back for each feed over
// the last fourteen days, by app family: today's count, the fortnight's, and
// the moment of the latest fetch. Counts only; nothing here names anyone.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureResidentTables(env);
  const since = new Date(Date.now() - 13 * 86400000).toISOString().slice(0, 10);
  const { results } = await env.DB.prepare(
    `SELECT feed, agent, SUM(n) AS total, MAX(last) AS last,
            SUM(CASE WHEN day = ? THEN n ELSE 0 END) AS today
     FROM feed_hits WHERE day >= ? GROUP BY feed, agent ORDER BY feed, total DESC`)
    .bind(todayPacific(), since).all();
  return json({ since, rows: results.map(r => ({ feed: r.feed, agent: r.agent, total: r.total, today: r.today, last: r.last || "" })) });
}
