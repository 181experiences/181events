// Shared helpers for the Pages Functions. Airtable is the only store.
export const FIELDS = ["Status","Date","Title","Category","Start","End","Start24","Location","Host",
  "RSVP","Capacity","Price","Series","Description","Cutoff","Marquee","Counted","Moved","Image","Slug"];

export function cfg(env) {
  const table = env.AIRTABLE_TABLE || "Events";
  return { token: env.AIRTABLE_TOKEN, base: env.AIRTABLE_BASE, table,
           url: `https://api.airtable.com/v0/${env.AIRTABLE_BASE}/${encodeURIComponent(table)}` };
}

export async function airtable(env, path, init = {}) {
  const c = cfg(env);
  if (!c.token || !c.base) {
    return new Response(JSON.stringify({ error: "Airtable is not configured" }),
      { status: 503, headers: { "content-type": "application/json" } });
  }
  return fetch(c.url + path, { ...init,
    headers: { "Authorization": `Bearer ${c.token}`, "content-type": "application/json", ...(init.headers || {}) } });
}

export function json(data, status = 200) {
  return new Response(JSON.stringify(data),
    { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

// Only the columns the contract knows about reach Airtable, with the right types.
export function clean(fields) {
  const out = {};
  for (const k of FIELDS) if (k in fields) out[k] = fields[k];
  if ("Capacity" in out) out.Capacity = (out.Capacity === "" || out.Capacity == null) ? null : Number(out.Capacity);
  for (const k of ["Marquee", "Counted", "Moved"]) if (k in out) out[k] = !!out[k];
  return out;
}
