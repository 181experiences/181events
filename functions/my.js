// GET /my -> the signed-in person's upcoming RSVPs, or the sign-in page when signed out.
import { esc } from "./_lib.js";
import {
  currentResident, upcomingRsvps, template, fill, cut, inner, page, seeOther, notReady,
  feedTokenOf, feedState, slideSession, MONTHS_S, DOW_S,
} from "./_resident.js";

function rowSlots(r) {
  const d = new Date(r.event_date + "T12:00:00");
  let tag, tagClass = "open";
  if (r.status === "Waitlist") { tag = "On the waitlist"; tagClass = ""; }
  else if (r.rsvp_type === "guest") { tag = r.count === 1 ? "1 guest registered" : `${r.count} guests registered`; }
  else if (r.rsvp_type === "paid") { tag = r.count === 1 ? "1 seat held" : `${r.count} seats held`; }
  else { tag = r.count === 1 ? "You&rsquo;re going" : `You&rsquo;re going &middot; party of ${r.count}`; }
  let meta = `${MONTHS_S[d.getMonth()]} ${d.getDate()}`;
  if (r.names) meta += ` &middot; with ${esc(r.names)}`;
  if (r.brings) meta += ` &middot; bringing ${esc(r.brings)}`;
  return {
    KEY: r.event_key,
    DAY: d.getDate(),
    DOW: DOW_S[d.getDay()],
    TITLE: esc(r.event_title),
    META: meta,
    TAG: tag,
    TAGCLASS: tagClass,
  };
}

export async function onRequestGet(context) {
  const { env } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  const me = await currentResident(context);
  if (!me) return seeOther("/signin?to=/my");
  const rows = await upcomingRsvps(env, me.id);
  const tpl = await template(context, "my");
  const rowTpl = inner(tpl, "ROW");
  let body;
  if (rows.length) {
    const rendered = rows.map(r => fill(rowTpl, rowSlots(r))).join("");
    body = cut(cut(tpl, "EMPTY", null), "ROWS",
      cut(inner(tpl, "ROWS"), "ROW", rendered));
  } else {
    body = cut(cut(tpl, "ROWS", null), "EMPTY", inner(tpl, "EMPTY"));
  }
  const token = await feedTokenOf(env, me);
  // Once a calendar app has come for their feed, say when it last did: the
  // answer to "is my calendar still following this?" before it is asked.
  const st = feedState(me);
  body = cut(body, "FOLLOWING", st.last ? fill(inner(tpl, "FOLLOWING"), {
    FOLLOWLINE: st.follows
      ? `Your calendar is following this page. It last checked in ${st.when}.`
      : `Your calendar last checked in ${st.when} and has not been back since. If entries there look out of date, remove the subscription and add it again from the box above.`,
  }) : null);
  body = fill(body, {
    LABEL: esc(me.label),
    FEEDURL: `https://181residents.com/calendar/my/${token}`,
    FEEDWEBCAL: `webcal://181residents.com/calendar/my/${token}`,
  });
  const res = await page(context, "My RSVPs", body, me);
  return slideSession(res, env, me);
}
