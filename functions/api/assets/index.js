import { json, noDb, adminRole, forbidden, ensureResidentTables } from "../../_lib.js";

// GET /api/assets -> every kit row: what's uploaded, and each piece's Canva
// address. `storage` says whether the R2 bucket (binding KIT) is linked yet;
// Canva links work either way. Events staff only.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT * FROM assets ORDER BY stem, kind").all();
  return json({ storage: !!env.KIT, assets: results });
}
