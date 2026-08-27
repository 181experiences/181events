// Resident sign-in, sessions, and page rendering for the resident-facing Functions.
// Sessions are a signed cookie, no server-side session store: rid.epoch.exp.signature,
// HMAC-SHA256 under SESSION_SECRET (a Pages environment variable). Rotating a code
// bumps the row's epoch, which quietly signs that unit out on every device.
//
// Pages served here are HTML templates shipped with the static build (site/_templates/),
// fetched through env.ASSETS and filled in. Copy and styling live in the templates,
// so the resident voice is written in one place: source/build_proto.py.

import { esc, ensureResidentTables, normalizeCode, todayPacific, labelOf, makeFeedToken } from "./_lib.js";

export const COOKIE = "r181s";
const MONTH_SECONDS = 30 * 24 * 60 * 60;

// House date style, shared by every resident-facing page: "Sept", never "Sep".
export const MONTHS_S = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"];
export const DOW = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
export const DOW_S = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const enc = new TextEncoder();

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function issueSession(env, resident) {
  const exp = Math.floor(Date.now() / 1000) + MONTH_SECONDS;
  const body = `${resident.id}.${resident.epoch}.${exp}`;
  return `${body}.${await hmac(env.SESSION_SECRET, body)}`;
}

export function sessionCookie(value) {
  // Max-Age 0 with an empty value clears it on sign-out.
  const age = value ? MONTH_SECONDS : 0;
  return `${COOKIE}=${value}; Max-Age=${age}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

function readCookie(request) {
  const raw = request.headers.get("cookie") || "";
  for (const part of raw.split(/;\s*/)) {
    if (part.startsWith(COOKIE + "=")) return part.slice(COOKIE.length + 1);
  }
  return null;
}

// The signed-in person's row, or null. Checks signature, expiry, then the live row,
// so a rotated code, a disabled account, or a passed end date signs out at once.
export async function currentResident(context) {
  const { request, env } = context;
  if (!env.DB || !env.SESSION_SECRET) return null;
  const token = readCookie(request);
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 4) return null;
  const [rid, epoch, exp, sig] = parts;
  if (!/^\d+$/.test(rid) || !/^\d+$/.test(epoch) || !/^\d+$/.test(exp)) return null;
  if (Number(exp) < Math.floor(Date.now() / 1000)) return null;
  if (await hmac(env.SESSION_SECRET, `${rid}.${epoch}.${exp}`) !== sig) return null;
  await ensureResidentTables(env);
  const row = await env.DB.prepare(
    "SELECT * FROM residents WHERE id=? AND epoch=? AND status='Active' AND (ends IS NULL OR ends='' OR ends >= ?)")
    .bind(Number(rid), Number(epoch), todayPacific()).first();
  if (row) row.label = labelOf(row);
  return row || null;
}

// ---------------------------------------------------------------- sign-in attempts
// A small brake on code guessing: fifteen failures from one address in ten minutes
// earns a pause. The table is pruned as it goes, so it never grows.
export async function tooManyAttempts(env, ip) {
  const cutoff = Date.now() - 10 * 60 * 1000;
  await env.DB.prepare("DELETE FROM attempts WHERE ts < ?").bind(cutoff).run();
  const { c } = await env.DB.prepare(
    "SELECT COUNT(*) AS c FROM attempts WHERE ip=? AND ts >= ?").bind(ip, cutoff).first();
  return c >= 15;
}

export async function recordAttempt(env, ip) {
  await env.DB.prepare("INSERT INTO attempts (ip, ts) VALUES (?, ?)")
    .bind(ip, Date.now()).run();
}

export async function findByCode(env, typed) {
  const code = normalizeCode(typed);
  if (code.length < 6) return null;
  const row = await env.DB.prepare(
    "SELECT * FROM residents WHERE code=? AND status='Active' AND (ends IS NULL OR ends='' OR ends >= ?)")
    .bind(code, todayPacific()).first();
  if (row) row.label = labelOf(row);
  return row;
}

// Where a sign-in may bounce back to. Only our own resident pages, never
// elsewhere, and only event keys the RSVP page will actually recognize.
export function safeReturn(to) {
  if (typeof to === "string" && (to === "/my" || /^\/rsvp\/\d{4}-\d{2}-\d{2}_[a-z0-9-]+$/.test(to))) return to;
  return "/my";
}

// ---------------------------------------------------------------- templates
export async function template(context, name) {
  const res = await context.env.ASSETS.fetch(new URL(`/_templates/${name}.html`, context.request.url));
  if (!res.ok) throw new Error(`template ${name} missing from the build`);
  return await res.text();
}

export function fill(tpl, slots) {
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => (slots && k in slots ? String(slots[k]) : ""));
}

// <!--NAME--> ... <!--/NAME--> marks an optional section. inner() lifts it out,
// cut() replaces it with rendered content, or with nothing.
export function inner(tpl, name) {
  const m = tpl.match(new RegExp(`<!--${name}-->([\\s\\S]*?)<!--/${name}-->`));
  return m ? m[1] : "";
}
export function cut(tpl, name, replacement) {
  // Function replacement, so "$" sequences in user text (names, prices) stay literal.
  return tpl.replace(new RegExp(`<!--${name}-->[\\s\\S]*?<!--/${name}-->`),
    () => (replacement == null ? "" : replacement));
}

export async function page(context, title, content, resident, status = 200) {
  const shell = await template(context, "shell");
  const html = fill(shell, {
    TITLE: esc(title),
    WHO: resident ? esc(resident.label) : "Residents&rsquo; Club",
    CONTENT: content,
  });
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-frame-options": "SAMEORIGIN",
      "x-content-type-options": "nosniff",
      "referrer-policy": "strict-origin-when-cross-origin",
    },
  });
}

export function seeOther(url, cookie) {
  const h = new Headers({ location: url, "cache-control": "no-store" });
  if (cookie) h.set("set-cookie", cookie);
  return new Response(null, { status: 303, headers: h });
}

// The page for "sign-in isn't switched on yet": honest, quiet, and temporary.
export async function notReady(context) {
  const done = await template(context, "done");
  const body = fill(cut(cut(done, "LINK", inner(done, "LINK")), "ICON", null), {
    HEAD: "Sign-in is nearly ready",
    SUB: "This part of the site is being switched on. The calendar works as always, and the front desk is glad to take an RSVP in the meantime.",
    LINKHREF: "/", LINKTEXT: "Back to the calendar",
  });
  return page(context, "One moment", body, null, 503);
}

// ---------------------------------------------------------------- events and rsvps
// An event's stable address is date_slug, the same stem that names its calendar
// file: 2026-09-25_a-night-in-mexico-city.
export function parseEventKey(key) {
  const m = /^(\d{4}-\d{2}-\d{2})_([a-z0-9-]+)$/.exec(String(key || ""));
  return m ? { date: m[1], slug: m[2] } : null;
}

export async function liveEvent(env, key) {
  const k = parseEventKey(key);
  if (!k) return null;
  return await env.DB.prepare(
    "SELECT * FROM events WHERE date=? AND slug=? AND status='Live'")
    .bind(k.date, k.slug).first();
}

// Seats already spoken for, not counting one resident's own row (so a change of
// count is judged against everyone else).
export async function seatsTaken(env, eventKey, excludeResidentId) {
  const { n } = await env.DB.prepare(
    "SELECT COALESCE(SUM(count),0) AS n FROM rsvps WHERE event_key=? AND status='Confirmed' AND resident_id != ?")
    .bind(eventKey, excludeResidentId || 0).first();
  return n;
}

export async function myRsvp(env, residentId, eventKey) {
  return await env.DB.prepare(
    "SELECT * FROM rsvps WHERE resident_id=? AND event_key=?")
    .bind(residentId, eventKey).first();
}

// How many other parties are queued. While anyone waits, a freed seat belongs to
// the queue, not to whoever happens to tap next.
export async function othersWaiting(env, eventKey, excludeResidentId) {
  const { c } = await env.DB.prepare(
    "SELECT COUNT(*) AS c FROM rsvps WHERE event_key=? AND status='Waitlist' AND resident_id != ?")
    .bind(eventKey, excludeResidentId || 0).first();
  return c;
}

export async function confirmedHeads(env, eventKey) {
  const { n } = await env.DB.prepare(
    "SELECT COALESCE(SUM(count),0) AS n FROM rsvps WHERE event_key=? AND status='Confirmed'")
    .bind(eventKey).first();
  return n;
}

export async function upcomingRsvps(env, residentId) {
  const { results } = await env.DB.prepare(
    "SELECT * FROM rsvps WHERE resident_id=? AND status != 'Cancelled' AND event_date >= ? ORDER BY event_date")
    .bind(residentId, todayPacific()).all();
  return results;
}

// The resident's private feed address, minted the first time it is needed.
export async function feedTokenOf(env, me) {
  if (me.feed_token) return me.feed_token;
  const token = makeFeedToken();
  await env.DB.prepare("UPDATE residents SET feed_token=? WHERE id=? AND feed_token IS NULL")
    .bind(token, me.id).run();
  const row = await env.DB.prepare("SELECT feed_token FROM residents WHERE id=?").bind(me.id).first();
  return row.feed_token;
}

// Activity keeps a session alive: each signed-in page view re-issues the cookie,
// so a device in regular use never asks for the code again, while a dormant one
// quietly expires after its month.
export async function slideSession(res, env, me) {
  try { res.headers.append("set-cookie", sessionCookie(await issueSession(env, me))); } catch (e) {}
  return res;
}

// The rest of a unit's picture for one event: who else from the same unit is
// already down, so nobody double-counts the household. Role accounts have no
// unit, so they never see (or appear in) this.
export async function unitMates(env, me, eventKey) {
  if (!me.unit) return [];
  const { results } = await env.DB.prepare(
    `SELECT r.count, r.rsvp_type, r.status, res.name FROM rsvps r
     JOIN residents res ON res.id = r.resident_id
     WHERE res.unit = ? AND r.resident_id != ? AND r.event_key = ? AND r.status != 'Cancelled'
     ORDER BY r.created`)
    .bind(me.unit, me.id, eventKey).all();
  return results;
}

export function clientIp(request) {
  return request.headers.get("cf-connecting-ip") || "unknown";
}
