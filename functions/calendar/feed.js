// GET /calendar/feed -> the whole resident calendar as a live iCalendar feed.
// Subscribed once (Apple, Google, and Outlook all take a calendar by URL), a
// resident's own calendar refreshes itself: new events appear, cancellations
// vanish, and nothing needs adding one date at a time. This is the calendar in
// machine-readable form; the per-event .ics files remain for one-tap adds.

import { ensureResidentTables, ensureEventTables, todayPacific, to24, icsStamp,
         getWindow, detailEnd, icsHead, logFeedHit } from "../_lib.js";

// The feed honors the calendar window: an event beyond the detail line, or one
// still marked coming-soon, stays out of subscribers' calendars until its
// details settle, so nothing half-formed takes root on a resident's phone.
//
// Removed events are SAID, not just dropped. Google and Outlook are slow to
// notice an entry that silently vanishes from a feed, and Google can keep
// one for weeks, so every event taken off the calendar (unpublished,
// archived, or moved to another date) rides along as STATUS:CANCELLED under
// the UID subscribers already hold, with a SEQUENCE above anything they saw.
// Two sources: rows that were published and since taken down (Unpublished,
// Archived, Cancelled; a Draft never went out), and the (date, slug) pairs an
// event held while Live, read from its change history.
const CANCEL_LOOKBACK_DAYS = 180;
export async function cancelledEntries(env, livePairs, today) {
  const cancelled = new Map();   // uid -> {d, start, title}
  const add = (date, slug, start24, title) => {
    if (!date || date < today) return;
    const key = `${date}_${slug || "event"}`;
    if (livePairs.has(key)) return;
    const d = date.replace(/-/g, "");
    const uid = `181fremont-${slug || "event"}-${d}@181residents.com`;
    if (!cancelled.has(uid)) cancelled.set(uid, { d, start: start24 || "0000", title: String(title || "").replace(/[\r\n,;]/g, " ") });
  };
  const gone = await env.DB.prepare(
    `SELECT date, slug, start24, start, title FROM events
     WHERE status IN ('Unpublished', 'Archived', 'Cancelled') AND (category IS NULL OR category != 'Board Meeting') AND date >= ?`).bind(today).all();
  for (const ev of gone.results) add(ev.date, ev.slug, ev.start24 || to24(ev.start), ev.title);
  const since = new Date(Date.now() - CANCEL_LOOKBACK_DAYS * 86400000).toISOString();
  try {
    const hist = await env.DB.prepare(
      "SELECT snapshot FROM event_history WHERE snapshot IS NOT NULL AND at >= ?").bind(since).all();
    for (const h of hist.results) {
      let s; try { s = JSON.parse(h.snapshot); } catch (e) { continue; }
      // Only dates that were LIVE at the time count: a draft that never went
      // out was never on anyone's calendar, and a public feed does not name it.
      if (!s || s.Category === "Board Meeting" || s.Status !== "Live") continue;
      add(s.Date, s.Slug, s.Start24 || to24(s.Start), s.Title);
    }
  } catch (e) {}
  return cancelled;
}

export async function onRequestGet(context) {
  const { env } = context;
  let rows = [], cancelled = new Map();
  const today = todayPacific();
  if (env.DB) {
    await ensureResidentTables(env);
    await ensureEventTables(env);
    const win = await getWindow(env);
    const r = await env.DB.prepare(
      `SELECT * FROM events WHERE status='Live' AND (category IS NULL OR category != 'Board Meeting')
       AND date >= ? AND (date <= ? OR announce = 1) AND (teaser IS NULL OR teaser = 0) ORDER BY date, start24`)
      .bind(today, detailEnd(win)).all();
    rows = r.results;
    // Every Live row counts as held, even one still beyond the detail line,
    // so a date only waiting its turn is never announced as cancelled.
    const held = await env.DB.prepare(
      "SELECT date, slug FROM events WHERE status='Live' AND date >= ?").bind(today).all();
    const livePairs = new Set(held.results.map(e => `${e.date}_${e.slug || "event"}`));
    try { cancelled = await cancelledEntries(env, livePairs, today); } catch (e) {}
    logFeedHit(context, "calendar");
  }
  const out = icsHead("-//181 Fremont//Resident Events//EN", "181 Fremont Resident Events");
  const { seq, stamp } = icsStamp();
  for (const ev of rows) {
    const d = ev.date.replace(/-/g, "");
    const start = ev.start24 || to24(ev.start);
    const end = ev.end_time ? to24(ev.end_time) : start;
    const title = String(ev.title || "").replace(/[\r\n,;]/g, " ");
    const loc = String(ev.location || "Level 39").replace(/[\r\n,;]/g, " ");
    // A partner event files itself at the venue (street address when given),
    // so a tap on the entry maps to the boutique, never to our lobby.
    const locLine = ev.rsvp === "Partner email"
      ? `LOCATION:${String(ev.address || "").replace(/[\r\n,;]/g, " ") || loc}`
      : `LOCATION:181 Fremont - ${loc}`;
    out.push("BEGIN:VEVENT",
      `UID:181fremont-${ev.slug || "event"}-${d}@181residents.com`,
      `DTSTAMP:${stamp}`, `SEQUENCE:${seq}`,
      `DTSTART:${d}T${start}00`,
      `DTEND:${d}T${end}00`,
      `SUMMARY:${title}`,
      locLine,
      `URL:https://181residents.com/rsvp/${ev.date}_${ev.slug || ""}`,
      "END:VEVENT");
  }
  for (const [uid, c] of cancelled) {
    out.push("BEGIN:VEVENT",
      `UID:${uid}`,
      `DTSTAMP:${stamp}`, `SEQUENCE:${seq + 1000}`,
      "STATUS:CANCELLED",
      `DTSTART:${c.d}T${c.start}00`,
      `SUMMARY:Cancelled: ${c.title}`,
      "END:VEVENT");
  }
  return new Response(out.join("\r\n") + "\r\nEND:VCALENDAR\r\n", {
    headers: { "content-type": "text/calendar; charset=utf-8", "cache-control": "no-store" },
  });
}
