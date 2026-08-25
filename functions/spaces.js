// GET /spaces -> when the Level 39 rooms are spoken for, in advance.
// Anyone can walk into a free room at any hour; this page only marks the hours
// a space is reserved. It shows the room, the date, and the time, and nothing
// else, because a reservation may be a resident's private affair. Read live
// from the database, so the desk removing a booking frees the room here at once.

import { esc, ensureResidentTables, todayPacific } from "./_lib.js";
import { currentResident, template, fill, cut, inner, page, MONTHS_S, DOW, DOW_S } from "./_resident.js";

export async function onRequestGet(context) {
  const { env } = context;
  const me = env.SESSION_SECRET ? await currentResident(context) : null;
  let rows = [];
  if (env.DB) {
    await ensureResidentTables(env);
    const r = await env.DB.prepare(
      "SELECT * FROM bookings WHERE date >= ? ORDER BY date, start24").bind(todayPacific()).all();
    rows = r.results;
  }
  const tpl = await template(context, "spaces");
  const rowTpl = inner(tpl, "ROW");
  let body;
  if (rows.length) {
    const rendered = rows.map(b => {
      const d = new Date(b.date + "T12:00:00");
      return fill(rowTpl, {
        DAY: d.getDate(),
        DOW: DOW_S[d.getDay()],
        SPACE: esc(b.space),
        META: `${DOW[d.getDay()]}, ${MONTHS_S[d.getMonth()]} ${d.getDate()}`
          + (b.start ? ` &middot; ${esc(b.start)}${b.end_time ? " &ndash; " + esc(b.end_time) : ""}` : " &middot; all day"),
      });
    }).join("");
    body = cut(cut(tpl, "EMPTY", null), "ROWS", cut(inner(tpl, "ROWS"), "ROW", rendered));
  } else {
    body = cut(cut(tpl, "ROWS", null), "EMPTY", inner(tpl, "EMPTY"));
  }
  return page(context, "Level 39 Spaces", body, me);
}
