// GET /e/{slug} -> the standing short address for a calendar event, made for
// emails and print: 181residents.com/e/book-club forwards to the NEXT upcoming
// date of that event, so a series link never goes stale. With nothing ahead it
// falls back to the latest passed date (which shows the past treatment), and
// failing that, the calendar.
import { ensureEventTables, todayPacific } from "../_lib.js";

export async function onRequestGet({ env, params }) {
  const home = new Response(null, { status: 302, headers: { location: "https://181residents.com/" } });
  if (!env.DB) return home;
  const slug = String(params.slug || "").toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]{0,80}$/.test(slug)) return home;
  await ensureEventTables(env);
  let row = await env.DB.prepare(
    `SELECT date, slug FROM events WHERE slug=? AND status='Live' AND date >= ?
     ORDER BY date LIMIT 1`).bind(slug, todayPacific()).first();
  if (!row) {
    row = await env.DB.prepare(
      `SELECT date, slug FROM events WHERE slug=? AND status='Live'
       ORDER BY date DESC LIMIT 1`).bind(slug).first();
  }
  if (!row) return home;
  return new Response(null, { status: 302,
    headers: { location: `https://181residents.com/rsvp/${row.date}_${row.slug}`, "cache-control": "no-store" } });
}
