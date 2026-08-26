import { json } from "../_lib.js";

// GET /api/status -> which pieces are wired up, so the admin can say so honestly.
export async function onRequestGet({ env }) {
  return json({
    db: !!env.DB,
    publish: !!env.DEPLOY_HOOK,
    email: !!env.EMAIL_API_KEY,
    analytics: !!(env.CF_API_TOKEN && env.CF_ACCOUNT_ID && env.CF_SITE_TAG),
    signin: !!env.SESSION_SECRET,
    roles: !!(env.OWNER_EMAILS || env.DESK_EMAILS),
    assets: !!env.KIT,
    mode: "cloudflare",
  });
}
