// GET /calendar/my/{token} -> one resident's RSVPs as a private iCalendar feed.
// The token is a long random address handed out only on that resident's own
// My RSVPs page; there is nothing to guess and nothing to log into, which is
// exactly what a calendar app needs. Subscribed once, their calendar carries
// just the events they said yes to, follows dates when staff move them, and
// lets go of anything cancelled. Disabling the person quiets the feed too.
//
// Letting go is SAID, not just done: an RSVP they cancelled, an event taken
// off the calendar, or a date the event held before it moved rides along as
// STATUS:CANCELLED under the UID their calendar already holds, since Google
// and Outlook are slow to notice an entry that silently disappears.

import { ensureResidentTables, todayPacific, to24, icsStamp, icsHead, logFeedHit } from "../../_lib.js";

export async function onRequestGet(context) {
  const { env, params } = context;
  const token = String(params.token || "");
  const empty = icsHead("-//181 Fremont//My RSVPs//EN", "My 181 Fremont RSVPs");
  let body = empty.join("\r\n") + "\r\nEND:VCALENDAR\r\n";

  if (env.DB && /^[a-z0-9]{16,32}$/.test(token)) {
    await ensureResidentTables(env);
    const me = await env.DB.prepare(
      "SELECT * FROM residents WHERE feed_token=? AND status='Active' AND (ends IS NULL OR ends='' OR ends >= ?)")
      .bind(token, todayPacific()).first();
    if (me) {
      logFeedHit(context, "my");
      const { results } = await env.DB.prepare(
        `SELECT r.count, r.status AS rstatus, e.* FROM rsvps r
         JOIN events e ON e.date || '_' || e.slug = r.event_key AND e.status = 'Live'
         WHERE r.resident_id=? AND r.status='Confirmed' AND r.event_date >= ?
         ORDER BY r.event_date`)
        .bind(me.id, todayPacific()).all();
      const { seq, stamp } = icsStamp();
      const out = [...empty];
      const livePairs = new Set(results.map(ev => `${ev.date}_${ev.slug}`));
      // Everything they RSVP'd to from today on, whatever became of it.
      const cancelled = new Map();
      const cancel = (date, slug, start24, start, title) => {
        if (!date || date < todayPacific() || livePairs.has(`${date}_${slug}`)) return;
        const d = date.replace(/-/g, "");
        const uid = `181fremont-${slug || "event"}-${d}@181residents.com`;
        if (!cancelled.has(uid)) cancelled.set(uid, { d, start: start24 || to24(start) || "0000", title: String(title || "").replace(/[\r\n,;]/g, " ") });
      };
      try {
        const all = await env.DB.prepare(
          `SELECT r.event_key, r.event_date, r.event_title, r.status AS rstatus, e.id AS eid, e.status AS estatus,
                  e.date AS edate, e.slug AS eslug, e.start24, e.start
           FROM rsvps r LEFT JOIN events e ON e.date || '_' || e.slug = r.event_key
           WHERE r.resident_id=? AND r.event_date >= ?`).bind(me.id, todayPacific()).all();
        const ids = [];
        for (const r of all.results) {
          const [kd, ...ks] = r.event_key.split("_");
          if (r.rstatus === "Cancelled" || !r.eid || r.estatus !== "Live") cancel(kd, ks.join("_"), r.start24, r.start, r.event_title);
          if (r.eid) ids.push(r.eid);
        }
        if (ids.length) {
          const since = new Date(Date.now() - 180 * 86400000).toISOString();
          const hist = await env.DB.prepare(
            `SELECT snapshot FROM event_history WHERE snapshot IS NOT NULL AND at >= ?
             AND event_id IN (${ids.map(() => "?").join(",")})`).bind(since, ...ids).all();
          for (const h of hist.results) {
            let s; try { s = JSON.parse(h.snapshot); } catch (e) { continue; }
            if (s && s.Status === "Live") cancel(s.Date, s.Slug, s.Start24, s.Start, s.Title);
          }
        }
      } catch (e) {}
      for (const ev of results) {
        const d = ev.date.replace(/-/g, "");
        const start = ev.start24 || to24(ev.start);
        const end = ev.end_time ? to24(ev.end_time) : start;
        const title = String(ev.title || "").replace(/[\r\n,;]/g, " ");
        const loc = String(ev.location || "Level 39").replace(/[\r\n,;]/g, " ");
        const locLine = ev.rsvp === "Partner email"
          ? `LOCATION:${String(ev.address || "").replace(/[\r\n,;]/g, " ") || loc}`
          : `LOCATION:181 Fremont - ${loc}`;
        out.push("BEGIN:VEVENT",
          `UID:181fremont-${ev.slug || "event"}-${d}@181residents.com`,
          `DTSTAMP:${stamp}`, `SEQUENCE:${seq}`,
          `DTSTART:${d}T${start}00`, `DTEND:${d}T${end}00`,
          `SUMMARY:${title}${ev.count > 1 ? ` (party of ${ev.count})` : ""}`,
          locLine,
          `URL:https://181residents.com/rsvp/${ev.date}_${ev.slug || ""}`,
          "END:VEVENT");
      }
      for (const [uid, c] of cancelled) {
        out.push("BEGIN:VEVENT", `UID:${uid}`, `DTSTAMP:${stamp}`, `SEQUENCE:${seq + 1000}`, "STATUS:CANCELLED",
          `DTSTART:${c.d}T${c.start}00`, `SUMMARY:Cancelled: ${c.title}`, "END:VEVENT");
      }
      body = out.join("\r\n") + "\r\nEND:VCALENDAR\r\n";
    }
  }
  return new Response(body, {
    headers: { "content-type": "text/calendar; charset=utf-8", "cache-control": "no-store" },
  });
}
