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
  if (!/^[a-z0-9]{16,32}$/.test(String(token || ""))) return null;
  return await env.DB.prepare("SELECT * FROM bookings WHERE reg_token=?").bind(token).first();
}

async function headsOf(env, bookingId) {
  const r = await env.DB.prepare(
    `SELECT COUNT(*) AS parties,
            COALESCE(SUM(CASE WHEN plus_one IS NOT NULL AND plus_one != '' THEN 2 ELSE 1 END), 0) AS heads
     FROM guests WHERE booking_id=?`).bind(bookingId).first();
  return r || { parties: 0, heads: 0 };
}

async function regPage(context, b, state) {
  const tpl = await template(context, "register");
  let body = fill(tpl, {
    EVENT: esc(b.event_name || "A private event"),
    WHEN: whenOf(b),
    WHERE: esc(b.space || "Level 39, Residents’ Club"),
  });
  body = cut(body, "HOST", b.host
    ? fill(inner(tpl, "HOST"), { HOST: esc(b.host) }) : null);
  if (state) {
    body = cut(body, "FORM", null);
    body = cut(body, "CLOSED", fill(inner(tpl, "CLOSED"), { CLOSEDMSG: state }));
  } else {
    body = cut(body, "CLOSED", null);
    body = cut(body, "FORM", fill(inner(tpl, "FORM"), { TOKEN: esc(b.reg_token) }));
  }
  return page(context, b.event_name || "Private event", body, null);
}

function stateOf(b, heads) {
  if (!b.reg_open) return "Registration for this event is closed. If you are expected, the front desk will have you on the list; otherwise, kindly check with your host.";
  if (b.date < todayPacific()) return "This event has passed.";
  if (b.guest_cap && heads.heads >= b.guest_cap) return "The guest list is full. If you were invited, kindly check with your host; there may be room for adjustments.";
  return null;
}

export async function onRequestGet(context) {
  const { env, params } = context;
  if (!env.DB) return new Response("Not ready", { status: 503 });
  await ensureResidentTables(env);
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
  return regPage(context, b, stateOf(b, await headsOf(env, b.id)));
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
  const plus = String(form.get("plus") || "").trim().slice(0, 80);
  const state = stateOf(b, await headsOf(env, b.id));
  if (state) return seeOther(`/register/${b.reg_token}`);
  if (!name) return seeOther(`/register/${b.reg_token}`);
  if (!trap) {
    await env.DB.prepare(
      "INSERT INTO guests (booking_id, name, plus_one, created) VALUES (?, ?, ?, ?)")
      .bind(b.id, name, plus || null, new Date().toISOString()).run();
  }
  const done = await template(context, "done");
  const body = fill(cut(done, "LINK", null), {
    HEAD: "You&rsquo;re on the list",
    SUB: `${esc(name)}${plus ? " and " + esc(plus) : ""}, registered for ${esc(b.event_name || "the event")}. `
      + `On the day, come to the 181 Fremont lobby and give the event name; the front desk will be expecting you.`,
  });
  return page(context, "Registered", body, null);
}
