// GET /board/feed -> a live iCalendar feed of upcoming Board meetings.
// Subscribed once (Apple, Google, and Outlook all take a calendar by URL), a
// resident's calendar refreshes this feed on its own schedule, so a cancelled
// meeting quietly leaves their calendar: the notice takes care of itself.

import { plainIcs, icsEvent } from "./_ics.js";
import { boardMeetings } from "../board.js";

export async function onRequestGet({ env }) {
  const rows = env.DB ? await boardMeetings(env) : [];
  const body = plainIcs(rows.map(icsEvent).join(""), "181 Fremont Board Meetings");
  return new Response(body, {
    headers: {
      "content-type": "text/calendar; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
