import { json } from "../_lib.js";

// POST /api/publish -> asks Cloudflare Pages to rebuild the resident site from the events database.
// DEPLOY_HOOK is the Pages deploy hook URL, stored as an environment variable.
export async function onRequestPost({ env }) {
  if (!env.DEPLOY_HOOK) return json({ error: "No deploy hook configured" }, 503);
  const r = await fetch(env.DEPLOY_HOOK, { method: "POST" });
  return json({ ok: r.ok, status: r.status, note: "The calendar updates in a couple of minutes." }, r.ok ? 200 : 502);
}
