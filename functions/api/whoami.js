import { json, adminRole } from "../_lib.js";

// GET /api/whoami -> which admin tier Access signed in, so the UI can shape itself.
// The real enforcement lives on each endpoint; this only tells the page what to draw.
export async function onRequestGet({ request, env }) {
  const role = adminRole(request, env);
  return json({ role: role || "staff" });
}
