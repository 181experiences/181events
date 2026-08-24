import { json } from "../_lib.js";

// GET /api/status -> which pieces are wired up, so the admin can say so honestly.
export async function onRequestGet({ env }) {
  return json({
    airtable: !!(env.AIRTABLE_TOKEN && env.AIRTABLE_BASE),
    publish: !!env.DEPLOY_HOOK,
    email: !!env.EMAIL_API_KEY,
    analytics: !!(env.CF_API_TOKEN && env.CF_ACCOUNT_ID && env.CF_SITE_TAG),
    mode: "cloudflare",
  });
}
