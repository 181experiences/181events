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
