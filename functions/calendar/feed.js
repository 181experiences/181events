// GET /calendar/feed -> the whole resident calendar as a live iCalendar feed.
// Subscribed once (Apple, Google, and Outlook all take a calendar by URL), a
// resident's own calendar refreshes itself: new events appear, cancellations
// vanish, and nothing needs adding one date at a time. This is the calendar in
// machine-readable form; the per-event .ics files remain for one-tap adds.

import { ensureResidentTables, todayPacific, to24, icsStamp } from "../_lib.js";

export async function onRequestGet({ env }) {
  let rows = [];
  if (env.DB) {
    await ensureResidentTables(env);
    const r = await env.DB.prepare(
      `SELECT * FROM events WHERE status='Live' AND (category IS NULL OR category != 'Board Meeting')
       AND date >= ? ORDER BY date, start24`).bind(todayPacific()).all();
    rows = r.results;
  }
  const out = ["BEGIN:VCALENDAR", "VERSION:2.0",
    "PRODID:-//181 Fremont//Resident Events//EN",
    "X-WR-CALNAME:181 Fremont Resident Events"];
  const { seq, stamp } = icsStamp();
  for (const ev of rows) {
    const d = ev.date.replace(/-/g, "");
    const start = ev.start24 || to24(ev.start);
    const end = ev.end_time ? to24(ev.end_time) : start;
    const title = String(ev.title || "").replace(/[\r\n,;]/g, " ");
    const loc = String(ev.location || "Level 39").replace(/[\r\n,;]/g, " ");
    out.push("BEGIN:VEVENT",
      `UID:181fremont-${ev.slug || "event"}-${d}@181residents.com`,
      `DTSTAMP:${stamp}`, `SEQUENCE:${seq}`,
      `DTSTART:${d}T${start}00`,
      `DTEND:${d}T${end}00`,
      `SUMMARY:${title}`,
      `LOCATION:181 Fremont - ${loc}`,
      `URL:https://181residents.com/rsvp/${ev.date}_${ev.slug || ""}`,
      "END:VEVENT");
  }
  return new Response(out.join("\r\n") + "\r\nEND:VCALENDAR\r\n", {
    headers: { "content-type": "text/calendar; charset=utf-8", "cache-control": "no-store" },
  });
}
