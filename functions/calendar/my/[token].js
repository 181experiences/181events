// GET /calendar/my/{token} -> one resident's RSVPs as a private iCalendar feed.
// The token is a long random address handed out only on that resident's own
// My RSVPs page; there is nothing to guess and nothing to log into, which is
// exactly what a calendar app needs. Subscribed once, their calendar carries
// just the events they said yes to, follows dates when staff move them, and
// lets go of anything cancelled. Disabling the person quiets the feed too.

import { ensureResidentTables, todayPacific, to24, icsStamp } from "../../_lib.js";

export async function onRequestGet({ env, params }) {
  const token = String(params.token || "");
  const empty = ["BEGIN:VCALENDAR", "VERSION:2.0",
    "PRODID:-//181 Fremont//My RSVPs//EN", "X-WR-CALNAME:My 181 Fremont RSVPs"];
  let body = empty.join("\r\n") + "\r\nEND:VCALENDAR\r\n";

  if (env.DB && /^[a-z0-9]{16,32}$/.test(token)) {
    await ensureResidentTables(env);
    const me = await env.DB.prepare(
      "SELECT * FROM residents WHERE feed_token=? AND status='Active' AND (ends IS NULL OR ends='' OR ends >= ?)")
      .bind(token, todayPacific()).first();
    if (me) {
      const { results } = await env.DB.prepare(
        `SELECT r.count, r.status AS rstatus, e.* FROM rsvps r
         JOIN events e ON e.date || '_' || e.slug = r.event_key AND e.status = 'Live'
         WHERE r.resident_id=? AND r.status='Confirmed' AND r.event_date >= ?
         ORDER BY r.event_date`)
        .bind(me.id, todayPacific()).all();
      const { seq, stamp } = icsStamp();
      const out = [...empty];
      for (const ev of results) {
        const d = ev.date.replace(/-/g, "");
        const start = ev.start24 || to24(ev.start);
        const end = ev.end_time ? to24(ev.end_time) : start;
        const title = String(ev.title || "").replace(/[\r\n,;]/g, " ");
        const loc = String(ev.location || "Level 39").replace(/[\r\n,;]/g, " ");
        out.push("BEGIN:VEVENT",
          `UID:181fremont-${ev.slug || "event"}-${d}@181residents.com`,
          `DTSTAMP:${stamp}`, `SEQUENCE:${seq}`,
          `DTSTART:${d}T${start}00`, `DTEND:${d}T${end}00`,
          `SUMMARY:${title}${ev.count > 1 ? ` (party of ${ev.count})` : ""}`,
          `LOCATION:181 Fremont - ${loc}`,
          `URL:https://181residents.com/rsvp/${ev.date}_${ev.slug || ""}`,
          "END:VEVENT");
      }
      body = out.join("\r\n") + "\r\nEND:VCALENDAR\r\n";
    }
  }
  return new Response(body, {
    headers: { "content-type": "text/calendar; charset=utf-8", "cache-control": "no-store" },
  });
}
