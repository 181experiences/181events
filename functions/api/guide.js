import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail, logChange } from "../_lib.js";

// The Black Book keeps three kinds of knowledge apart, so each can say where
// it came from and when:
//
//   the file    source/guide_places.json rides the admin page. It is what the
//               weekly check found on each place's own website, and it carries
//               its own history of what the system changed. ("Information
//               automatically updated on")
//   the team    a correction typed in by someone at the desk is stored here as
//               an edit laid over the file, field by field, signed and logged.
//               A call to the place stamps who verified it and when.
//               ("Location information last verified on, by")
//   the house   our connection there: who we know, their number, a note.
//
// A fourth kind since: places the team added themselves. Each is a whole
// record kept in guide_added, shaped like an entry of the file, with an id
// that starts "t-" so it can never collide with one. Corrections, the phone
// stamp and the connection work on it exactly as on any other place.
//
// GET  /api/guide -> { notes: { <place id>: {...} }, added: [ place, ... ],
//                      log: [ {place, at, who, action, changes} ] }
// POST /api/guide -> add a place: { fields: { <flat field>: text, latlon: "lat,lon" } }
// Every tier reads and adds; the desk is who the book is for.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    "SELECT place_id, connected, contact, phone, note, updated, updated_by, verified_at, verified_by, edits FROM guide_notes").all();
  const notes = {};
  for (const r of results) notes[r.place_id] = noteView(r);
  const log = (await env.DB.prepare(
    "SELECT label, at, who, action, changes FROM change_log WHERE kind='guide' ORDER BY id DESC LIMIT 2000").all()).results;
  const added = (await env.DB.prepare(
    "SELECT place FROM guide_added WHERE removed IS NULL ORDER BY added").all()).results
    .map(r => { try { return JSON.parse(r.place); } catch (e) { return null; } }).filter(Boolean);
  return json({ notes, added, log: log.map(r => ({ place: r.label || "", at: r.at, who: r.who || "", action: r.action,
    changes: r.changes ? JSON.parse(r.changes) : null })) });
}

export const FIELDS = ["name", "cuisines", "neighborhood", "address", "phone", "website", "email", "book_how", "book_url",
  "price", "michelin", "description", "hours_note", "desk_note", "latlon",
  "hours_mon", "hours_tue", "hours_wed", "hours_thu", "hours_fri", "hours_sat", "hours_sun"];
export const LIMIT = { description: 700, desk_note: 400, hours_note: 300, book_url: 400, website: 300 };
export const clip = (v, n) => String(v == null ? "" : v).trim().slice(0, n);
// "37.789788,-122.395356" -> [lat, lon], or null when it is not a spot in or
// around San Francisco.
export function spot(s) {
  const m = /^\s*(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$/.exec(String(s || ""));
  if (!m) return null;
  const lat = Number(m[1]), lon = Number(m[2]);
  return lat > 37.2 && lat < 38.2 && lon > -123.2 && lon < -121.8 ? [Number(lat.toFixed(6)), Number(lon.toFixed(6))] : null;
}

export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role) return forbidden();
  await ensureResidentTables(env);
  let b; try { b = await request.json(); } catch (e) { return json({ error: "Nothing to add." }, 400); }
  const f = {};
  for (const k of FIELDS) f[k] = clip(b.fields && b.fields[k], LIMIT[k] || 200);
  if (!f.name) return json({ error: "A place needs a name." }, 400);
  if (!f.address) return json({ error: "A place needs an address." }, 400);
  const at = spot(f.latlon);
  if (!at) return json({ error: "Set the place on the map first." }, 400);
  const by = (await accessEmail(request)) || env.DEV_ROLE || role;
  const now = new Date().toISOString();
  const slug = "t-" + (f.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "place");
  let id = slug;
  for (let n = 2; await env.DB.prepare("SELECT 1 FROM guide_added WHERE place_id = ?").bind(id).first(); n++) id = `${slug}-${n}`;
  const days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const place = {
    id, name: f.name, kind: "Restaurant", team: true, added_at: now, added_by: by,
    cuisines: f.cuisines.split(",").map(s => s.trim()).filter(Boolean), neighborhood: f.neighborhood,
    address: f.address, lat: at[0], lon: at[1],
    hours: days.some(d => f["hours_" + d]) ? Object.fromEntries(days.map(d => [d, f["hours_" + d] || null])) : null,
    hours_note: f.hours_note || null, phone: f.phone || null, website: f.website || null, email: f.email || null,
    book: { how: f.book_how || null, url: f.book_url || null }, price: f.price || null, michelin: f.michelin || null,
    good_for: [], description: f.description, desk_note: f.desk_note || null,
  };
  await env.DB.prepare("INSERT INTO guide_added (place_id, place, added, added_by) VALUES (?,?,?,?)")
    .bind(id, JSON.stringify(place), now, by).run();
  const changes = {};
  for (const k of FIELDS) if (f[k] && k !== "latlon") changes[k] = ["", f[k]];
  await logChange(env, request, "guide", null, id, "Added by the team", changes);
  let note = null;
  if (b.verify) {
    await env.DB.prepare("INSERT INTO guide_notes (place_id, verified_at, verified_by, edits) VALUES (?,?,?,'{}')").bind(id, now, by).run();
    await logChange(env, request, "guide", null, id, "Verified by phone", {});
    note = noteView({ verified_at: now, verified_by: by });
  }
  return json({ ok: true, place, note, logged: [{ place: id, at: now, who: by, action: "Added by the team", changes },
    ...(b.verify ? [{ place: id, at: now, who: by, action: "Verified by phone", changes: null }] : [])] }, 201);
}

export function noteView(r) {
  let edits = {};
  try { edits = r.edits ? JSON.parse(r.edits) : {}; } catch (e) { edits = {}; }
  return { connected: !!r.connected, contact: r.contact || "", phone: r.phone || "", note: r.note || "",
    updated: r.updated || "", updated_by: r.updated_by || "",
    verified_at: r.verified_at || "", verified_by: r.verified_by || "", edits };
}
