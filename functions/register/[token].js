// GET  /register/{token} -> the registration page for a private event, sent by
// its host to their invitees. No resident code: these are outside guests, and
// the unguessable address is the invitation.
// POST the same address -> put a name (and a plus one) on the list the front
// desk and security run from.

import { esc, ensureResidentTables, todayPacific } from "../_lib.js";
import { template, fill, cut, inner, page, seeOther, MONTHS_S, DOW } from "../_resident.js";

function whenOf(b) {
  const d = new Date(b.date + "T12:00:00");
  const day = `${DOW[d.getDay()]}, ${MONTHS_S[d.getMonth()]} ${d.getDate()}`;
  return b.start ? `${day}<br>${esc(b.start)}${b.end_time ? " &ndash; " + esc(b.end_time) : ""}` : day;
}

async function findBooking(env, token) {
  const t = String(token || "").toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]{2,63}$/.test(t)) return null;
  // Answers to the unguessable token and, when one is written, the custom
  // address; either spelling opens the same page.
  return await env.DB.prepare(
    "SELECT * FROM bookings WHERE reg_token=? OR reg_slug=?").bind(t, t).first();
}

async function headsOf(env, bookingId) {
  // Confirmed heads only: the waitlist never blocks the door count.
  const r = await env.DB.prepare(
    `SELECT COUNT(*) AS parties,
            COALESCE(SUM(CASE WHEN plus_one IS NOT NULL AND plus_one != '' THEN 2 ELSE 1 END), 0) AS heads
     FROM guests WHERE booking_id=? AND (status IS NULL OR status != 'Waitlist')`).bind(bookingId).first();
  return r || { parties: 0, heads: 0 };
}

// "7:30 PM" and its kin -> HHMM, with an hour past the start as the fallback,
// so the calendar entry always closes somewhere sensible.
function hhmm(t, fallbackStart) {
  const m = /^\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp])?/.exec(String(t || ""));
  if (m && m[1]) {
    let h = Number(m[1]);
    const mer = (m[3] || "").toLowerCase();
    if (mer === "p" && h < 12) h += 12;
    else if (mer === "a" && h === 12) h = 0;
    if (h <= 23) return String(h).padStart(2, "0") + (m[2] || "00");
  }
  const st = String(fallbackStart || "0000");
  return String((Number(st.slice(0, 2)) + 1) % 24).padStart(2, "0") + st.slice(2);
}

async function regPage(context, b, state, waitlisting) {
  const tpl = await template(context, "register");
  let body = fill(tpl, {
    EVENT: esc(b.event_name || "A private event"),
    WHEN: whenOf(b),
    WHERE: esc(b.space || "Level 39, Residents’ Club"),
  });
  body = cut(body, "HOST", b.host
    ? fill(inner(tpl, "HOST"), { HOST: esc(b.host) }) : null);
  body = cut(body, "ICS", b.date >= todayPacific()
    ? fill(inner(tpl, "ICS"), { ICSKEY: esc(b.reg_slug || b.reg_token) }) : null);
  body = cut(body, "WAITNOTE", waitlisting ? inner(tpl, "WAITNOTE") : null);
  if (state) {
    body = cut(body, "FORM", null);
    body = cut(body, "CLOSED", fill(inner(tpl, "CLOSED"), { CLOSEDMSG: state }));
  } else {
    body = cut(body, "CLOSED", null);
    body = cut(body, "FORM", fill(inner(tpl, "FORM"), { TOKEN: esc(b.reg_token) }));
  }
  return page(context, b.event_name || "Private event", body, null);
}

// A full list no longer closes the door; it starts the waitlist, the same
// promise the calendar keeps. Closed and passed still close it.
function stateOf(b) {
  if (!b.reg_open) return "Registration for this event is closed. If you are expected, the front desk will have you on the list; otherwise, kindly check with your host.";
  if (b.date < todayPacific()) return "This event has passed.";
  return null;
}

function isFull(b, heads) {
  return !!(b.guest_cap && heads.heads >= b.guest_cap);
}

export async function onRequestGet(context) {
  const { env, params } = context;
  if (!env.DB) return new Response("Not ready", { status: 503 });
  await ensureResidentTables(env);
  // {token}.ics hands the same event to a calendar app, real file semantics,
  // matching the Add to My Calendar residents already know.
  if (String(params.token || "").endsWith(".ics")) {
    const b2 = await findBooking(env, String(params.token).slice(0, -4));
    if (!b2) return new Response("Not here.", { status: 404 });
    const d = b2.date.replace(/-/g, "");
    const start = b2.start24 || "1800";
    const clean = v => String(v || "").replace(/[\r\n,;]/g, " ");
    const CRLF = "\r\n";
    const body = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//181 Fremont//Private Events//EN",
      "BEGIN:VEVENT", `UID:181fremont-reg-${b2.id}@181residents.com`,
      `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`,
      `DTSTART:${d}T${start}00`, `DTEND:${d}T${hhmm(b2.end_time, start)}00`,
      `SUMMARY:${clean(b2.event_name || "Private event")}`,
      `LOCATION:181 Fremont - ${clean(b2.space || "Level 39")}`,
      "END:VEVENT", "END:VCALENDAR"].join(CRLF) + CRLF;
    return new Response(body, { headers: { "content-type": "text/calendar; charset=utf-8" } });
  }
  const b = await findBooking(env, params.token);
  if (!b) {
    const done = await template(context, "done");
    const body = fill(cut(cut(done, "LINK", inner(done, "LINK")), "ICON", null), {
      HEAD: "That page isn&rsquo;t here",
      SUB: "The address may have been mistyped, or the invitation withdrawn. Kindly check with whoever sent it.",
      LINKHREF: "https://181residents.com", LINKTEXT: "181 Fremont",
    });
    return page(context, "Not found", body, null, 404);
  }
  return regPage(context, b, stateOf(b), isFull(b, await headsOf(env, b.id)));
}

export async function onRequestPost(context) {
  const { env, request, params } = context;
  if (!env.DB) return new Response("Not ready", { status: 503 });
  await ensureResidentTables(env);
  const b = await findBooking(env, params.token);
  if (!b) return seeOther("/");
  const form = await request.formData();
  // The honeypot: a field people never see. Anything in it is a bot, which
  // gets a polite success and writes nothing.
  const trap = String(form.get("website") || "");
  const name = String(form.get("name") || "").trim().slice(0, 80);
  const email = String(form.get("email") || "").trim().slice(0, 120);
  const plus = String(form.get("plus") || "").trim().slice(0, 80);
  if (stateOf(b)) return seeOther(`/register/${b.reg_token}`);
  if (!name || !email || !/.+@.+\..+/.test(email)) return seeOther(`/register/${b.reg_token}`);
  // A full list waitlists the whole party rather than turning it away; a
  // party of two never splits across the line.
  const heads = await headsOf(env, b.id);
  const wanting = plus ? 2 : 1;
  const waitlisted = !!(b.guest_cap && heads.heads + wanting > b.guest_cap);
  if (!trap) {
    await env.DB.prepare(
      "INSERT INTO guests (booking_id, name, plus_one, created, email, status) VALUES (?, ?, ?, ?, ?, ?)")
      .bind(b.id, name, plus || null, new Date().toISOString(), email, waitlisted ? "Waitlist" : null).run();
  }
  const done = await template(context, "done");
  const body = fill(cut(done, "LINK", null), waitlisted
    ? {
        HEAD: "You&rsquo;re on the waitlist",
        SUB: `${esc(name)}${plus ? " and " + esc(plus) : ""}, on the waitlist for ${esc(b.event_name || "the event")}. `
          + `The list is full at the moment; if seats open, you&rsquo;ll hear at ${esc(email)}.`,
      }
    : {
        HEAD: "You&rsquo;re on the list",
        SUB: `${esc(name)}${plus ? " and " + esc(plus) : ""}, registered for ${esc(b.event_name || "the event")}. `
          + `On the day, come to the 181 Fremont lobby and give the event name; the front desk will be expecting you.`,
      });
  return page(context, waitlisted ? "On the waitlist" : "Registered", body, null);
}
