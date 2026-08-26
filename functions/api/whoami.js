import { json, adminRole, accessEmail } from "../_lib.js";

// GET /api/whoami -> which admin tier Access signed in, so the UI can shape
// itself, plus the address it decided from, so a wrong tier is diagnosable by
// eye. The real enforcement lives on each endpoint. When role is null the
// email never arrived; report it honestly instead of dressing it as staff.
export async function onRequestGet({ request, env }) {
  const role = await adminRole(request, env);
  return json({ role: role || "none", email: await accessEmail(request) });
}
