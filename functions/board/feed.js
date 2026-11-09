// GET /board/feed -> a live iCalendar feed of upcoming Board meetings.
// Subscribed once (Apple, Google, and Outlook all take a calendar by URL), a
// resident's calendar refreshes this feed on its own schedule, so a cancelled
// meeting quietly leaves their calendar: the notice takes care of itself.

import { plainIcs, icsEvent, icsCancelled } from "./_ics.js";
import { boardMeetings } from "../board.js";
import { todayPacific } from "../_lib.js";

export async function onRequestGet({ env }) {
  const rows = env.DB ? await boardMeetings(env) : [];
  // Meetings taken off the calendar ride along as cancellations, so a
  // subscriber's copy is withdrawn instead of lingering until it is noticed.
  let gone = [];
  if (env.DB) {
    try {
      const r = await env.DB.prepare(
        "SELECT id, date, start24, start, title FROM events WHERE category='Board Meeting' AND status IN ('Unpublished', 'Archived', 'Cancelled') AND date >= ?")
        .bind(todayPacific()).all();
      gone = r.results;
    } catch (e) {}
  }
  const body = plainIcs(rows.map(icsEvent).join("") + gone.map(icsCancelled).join(""), "181 Fremont Board Meetings");
  return new Response(body, {
    headers: {
      "content-type": "text/calendar; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
