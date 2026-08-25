// GET /board -> upcoming Board meetings, on their own page and never on the
// resident events calendar. Board meetings are entered in the admin like any
// event, under the category "Board Meeting"; this page reads them live from the
// database, so a cancellation disappears here the moment it is saved, with no
// rebuild in between. Each meeting offers Add to My Calendar, and the page
// offers a subscription feed, which is how a cancellation actually reaches
// the people who cared: their calendar app refreshes the feed on its own.

import { esc, ensureResidentTables, todayPacific } from "./_lib.js";
import { currentResident, template, fill, cut, inner, page, MONTHS_S, DOW, DOW_S } from "./_resident.js";

export async function boardMeetings(env) {
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare(
    `SELECT * FROM events WHERE category='Board Meeting' AND status='Live' AND date >= ?
     ORDER BY date, start24`).bind(todayPacific()).all();
  return results;
}

export async function onRequestGet(context) {
  const { env } = context;
  const me = env.SESSION_SECRET ? await currentResident(context) : null;
  const rows = env.DB ? await boardMeetings(env) : [];
  const tpl = await template(context, "board");
  const rowTpl = inner(tpl, "ROW");
  let body;
  if (rows.length) {
    const rendered = rows.map(ev => {
      const d = new Date(ev.date + "T12:00:00");
      return fill(rowTpl, {
        DAY: d.getDate(),
        DOW: DOW_S[d.getDay()],
        TITLE: esc(ev.title),
        META: `${DOW[d.getDay()]}, ${MONTHS_S[d.getMonth()]} ${d.getDate()}`
          + (ev.start ? ` &middot; ${esc(ev.start)}${ev.end_time ? " &ndash; " + esc(ev.end_time) : ""}` : "")
          + ` &middot; ${esc(ev.location || "Level 39")}`,
        ICS: `/board/ics/${ev.date}_${esc(ev.slug || "board-meeting")}`,
      });
    }).join("");
    body = cut(cut(tpl, "EMPTY", null), "ROWS", cut(inner(tpl, "ROWS"), "ROW", rendered));
  } else {
    body = cut(cut(tpl, "ROWS", null), "EMPTY", inner(tpl, "EMPTY"));
  }
  return page(context, "Board Meetings", body, me);
}
