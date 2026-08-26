// Shared helpers for the Pages Functions. Cloudflare D1 (the DB binding) is the only store.
// The API speaks the same field names the admin and the build use: Status, Date, Title, ...

export const FIELDS = ["Status","Date","Title","Category","Start","End","Start24","Location","Host",
  "RSVP","Capacity","Price","Series","Description","Cutoff","Marquee","Counted","Moved","Image","Slug"];

// SQL column per field. "End" would collide with the SQL keyword, so it gets its own name.
export const COLS = { Status: "status", Date: "date", Title: "title", Category: "category",
  Start: "start", End: "end_time", Start24: "start24", Location: "location", Host: "host",
  RSVP: "rsvp", Capacity: "capacity", Price: "price", Series: "series", Description: "description",
  Cutoff: "cutoff", Marquee: "marquee", Counted: "counted", Moved: "moved", Image: "image", Slug: "slug" };

export const CREATE_SQL = `CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL DEFAULT 'Draft', date TEXT NOT NULL, title TEXT NOT NULL,
  category TEXT, start TEXT, end_time TEXT, start24 TEXT, location TEXT, host TEXT,
  rsvp TEXT, capacity INTEGER, price TEXT, series TEXT, description TEXT, cutoff TEXT,
  marquee INTEGER DEFAULT 0, counted INTEGER DEFAULT 1, moved INTEGER DEFAULT 0,
  image TEXT, slug TEXT
)`;

// Resident sign-in, RSVPs, and messages. One residents row per PERSON, each with
// their own code, grouped by the unit they belong to. Role accounts (kind 'role',
// e.g. the front desk) have no unit. An optional `ends` date quietly expires a
// temporary occupant's code. epoch signs a person out everywhere when their code
// is rotated or their row disabled.
export const RESIDENT_TABLES = [
  `CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'resident',
    unit TEXT, name TEXT NOT NULL, email TEXT,
    code TEXT NOT NULL, epoch INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'Active', ends TEXT,
    created TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS rsvps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL,
    event_key TEXT NOT NULL, event_date TEXT NOT NULL, event_title TEXT NOT NULL,
    rsvp_type TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 1, names TEXT,
    status TEXT NOT NULL DEFAULT 'Confirmed',
    created TEXT NOT NULL, updated TEXT
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS rsvps_one_per_event ON rsvps(resident_id, event_key)`,
  `CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER, unit TEXT, sender TEXT,
    topic TEXT, body TEXT NOT NULL, name TEXT, email TEXT,
    state TEXT NOT NULL DEFAULT 'New', replied TEXT, created TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS attempts (ip TEXT NOT NULL, ts INTEGER NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    space TEXT NOT NULL, date TEXT NOT NULL,
    start TEXT, end_time TEXT, start24 TEXT,
    note TEXT, created TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stem TEXT NOT NULL, kind TEXT NOT NULL,
    canva TEXT, filename TEXT, size INTEGER, type TEXT, uploaded TEXT
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS assets_one_per_kind ON assets(stem, kind)`,
];

// The six pieces of an event's kit, by slug. The file itself lives in R2 (the
// KIT binding); the row carries what staff need to know about it, plus the
// Canva address where the design is edited.
export const ASSET_KINDS = ["web-hero", "nixplay-still", "nixplay-video",
  "elevator-print", "level39-print", "email-header"];

// "Margaret · 12A" for residents, "Front Desk" for role accounts.
export function labelOf(r) {
  return r.unit ? `${r.name} · ${r.unit}` : r.name;
}

// One shape for a residents row wherever the admin sees it, so a field added
// here reaches the roster and every PATCH response together.
export function residentView(r) {
  return {
    id: r.id, kind: r.kind, unit: r.unit || "", name: r.name, email: r.email || "",
    code: prettyCode(r.code), status: r.status, ends: r.ends || "",
    created: r.created, label: labelOf(r),
    expired: !!(r.ends && r.ends < todayPacific()),
  };
}

// ---------------------------------------------------------------- admin roles
// Cloudflare Access authenticates everyone who reaches /admin and /api/*, and
// stamps the verified address on the request. Roles are read from that stamp,
// never from anything the browser sends by itself.
//   owner  OWNER_EMAILS   everything, including message bodies
//   desk   DESK_EMAILS    residents and codes only
//   staff  anyone else Access admitted: events + residents, messages redacted
function emailList(v) {
  return String(v || "").toLowerCase().split(",").map(s => s.trim()).filter(Boolean);
}
// Access attaches the verified address two ways: a plain header, and the signed
// login token (JWT). On the locked custom domain both are trustworthy: nothing
// reaches /admin or /api there without passing Access, which sets them itself.
// On *.pages.dev preview addresses Access enforces only if the project's
// preview Access policy is switched on, and headers a client sends itself must
// never be believed, so there the token's SIGNATURE is verified against the
// team's published keys before its email is trusted. Forged tokens fail closed.
export const ACCESS_TEAM = "181sf-events.cloudflareaccess.com";

function b64urlJson(seg) {
  try {
    const pad = seg.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((seg.length + 3) % 4);
    return JSON.parse(atob(pad));
  } catch (e) { return null; }
}

let jwksCache = { keys: null, at: 0 };
async function accessKeys() {
  if (jwksCache.keys && Date.now() - jwksCache.at < 6 * 3600 * 1000) return jwksCache.keys;
  const r = await fetch(`https://${ACCESS_TEAM}/cdn-cgi/access/certs`);
  if (!r.ok) return jwksCache.keys || [];
  const d = await r.json();
  jwksCache = { keys: d.keys || [], at: Date.now() };
  return jwksCache.keys;
}

async function verifiedJwtEmail(jwt) {
  const parts = String(jwt || "").split(".");
  if (parts.length !== 3) return "";
  const header = b64urlJson(parts[0]);
  const payload = b64urlJson(parts[1]);
  if (!header || !payload) return "";
  if (payload.iss !== `https://${ACCESS_TEAM}`) return "";
  if (typeof payload.exp !== "number" || payload.exp < Date.now() / 1000) return "";
  const jwk = (await accessKeys()).find(k => k.kid === header.kid);
  if (!jwk) return "";
  try {
    const key = await crypto.subtle.importKey("jwk", jwk,
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const seg = parts[2].replace(/-/g, "+").replace(/_/g, "/") + "===".slice((parts[2].length + 3) % 4);
    const sig = Uint8Array.from(atob(seg), c => c.charCodeAt(0));
    const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, sig,
      new TextEncoder().encode(parts[0] + "." + parts[1]));
    return ok && typeof payload.email === "string" ? payload.email.toLowerCase().trim() : "";
  } catch (e) { return ""; }
}

export async function accessEmail(request) {
  const jwt = request.headers.get("cf-access-jwt-assertion") || "";
  if (new URL(request.url).hostname.endsWith(".pages.dev")) {
    return jwt ? verifiedJwtEmail(jwt) : "";
  }
  const direct = (request.headers.get("cf-access-authenticated-user-email") || "").toLowerCase().trim();
  if (direct) return direct;
  const payload = jwt ? b64urlJson(jwt.split(".")[1] || "") : null;
  return payload && typeof payload.email === "string" ? payload.email.toLowerCase().trim() : "";
}

export async function adminRole(request, env) {
  const email = await accessEmail(request);
  if (!email) return env.DEV_ROLE || null;   // DEV_ROLE is the local dev server's stand-in
  if (emailList(env.OWNER_EMAILS).includes(email)) return "owner";
  if (emailList(env.DESK_EMAILS).includes(email)) return "desk";
  return "staff";
}
export function forbidden() {
  return json({ error: "This part of the admin is not available to this account." }, 403);
}

// The CREATE IF NOT EXISTS batch matters exactly once per database; remembering
// that it ran keeps a six-statement round trip off every later request this
// isolate serves (handlers may call this freely, even twice per request).
let tablesEnsured = false;
export async function ensureResidentTables(env) {
  if (tablesEnsured) return;
  await env.DB.batch(RESIDENT_TABLES.map(s => env.DB.prepare(s)));
  tablesEnsured = true;
}

export function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// Unit codes. The alphabet drops I, L, O, 0 and 1, so a printed card can never
// be misread. Eight characters is about forty bits: not guessable, easy to type.
const CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
export function makeCode() {
  const buf = new Uint8Array(8);
  crypto.getRandomValues(buf);
  let out = "";
  for (const b of buf) out += CODE_ALPHABET[b % CODE_ALPHABET.length];
  return out;
}
export function normalizeCode(s) {
  return String(s || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}
export function prettyCode(c) {
  return c.length === 8 ? c.slice(0, 4) + "-" + c.slice(4) : c;
}

// Today's date where the building is, since "upcoming" means Pacific time.
export function todayPacific() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
}

// "5:30 PM" -> "1730", matching the events table's start24 convention.
// A typed 24-hour time ("14:00") sorts correctly instead of collapsing to 0000.
export function to24(t) {
  const m = /(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?/i.exec(String(t || "").trim());
  if (!m || !m[1]) return "0000";
  let h = Number(m[1]);
  if (m[3]) { h = h % 12; if (/pm/i.test(m[3])) h += 12; }
  if (h > 23) return "0000";
  return String(h).padStart(2, "0") + (m[2] || "00");
}

export function json(data, status = 200) {
  return new Response(JSON.stringify(data),
    { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

export function noDb(env) {
  return env.DB ? null : json({ error: "The events database is not linked yet. Add the D1 binding named DB in the Pages settings." }, 503);
}

// SQL row -> API shape.
export function fromRow(r) {
  const out = { id: String(r.id) };
  for (const f of FIELDS) {
    let v = r[COLS[f]];
    if (["Marquee", "Counted", "Moved"].includes(f)) v = !!v;
    if (v === null) v = f === "Capacity" ? null : "";
    out[f] = v;
  }
  return out;
}

// API fields -> {cols, vals} for SQL, only known fields, typed.
export function toCols(fields) {
  const cols = [], vals = [];
  for (const f of FIELDS) {
    if (!(f in fields)) continue;
    let v = fields[f];
    if (f === "Capacity") v = (v === "" || v == null) ? null : Number(v);
    if (["Marquee", "Counted", "Moved"].includes(f)) v = v ? 1 : 0;
    cols.push(COLS[f]); vals.push(v === undefined ? null : v);
  }
  return { cols, vals };
}
