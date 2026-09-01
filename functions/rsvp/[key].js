// GET  /rsvp/2026-09-25_a-night-in-mexico-city -> the RSVP page for that date.
// POST the same address -> confirm, change, or cancel this person's RSVP.
//
// The static calendar links here from every event that takes an RSVP. This page is
// where the live things happen: it knows who is signed in, how many seats remain,
// what this person already said, and what the rest of their unit has said, so a
// household never double-counts itself. Signed out, it offers the sign-in form
// inline and returns here afterwards. Plain forms throughout; no JavaScript needed.

import { esc, ensureResidentTables, ensureEventTables, todayPacific,
         getWindow, detailEnd } from "../_lib.js";
import {
  currentResident, liveEvent, seatsTaken, myRsvp, unitMates, othersWaiting, confirmedHeads,
  template, fill, cut, inner, page, seeOther, notReady, slideSession,
  MONTHS_S, DOW,
} from "../_resident.js";

const TYPE = { "Seat": "standard", "Paid seat": "paid", "Guest count": "guest" };

function whenOf(ev) {
  const d = new Date(ev.date + "T12:00:00");
  const day = `${DOW[d.getDay()]}, ${MONTHS_S[d.getMonth()]} ${d.getDate()}`;
  return ev.start ? `${day}<br>${esc(ev.start)}${ev.end_time ? " &ndash; " + esc(ev.end_time) : ""}` : day;
}

// "Just me · +1 · +2 · +3" for parties; plain numbers for outside guests.
// The chip markup is read from the very section being rendered, so an edit to
// one section's chips can never be silently shadowed by the other's.
function chips(section, type, current) {
  const chip = inner(section, "CHIP");
  const max = type === "guest" ? 6 : 4;
  let out = "";
  for (let n = 1; n <= max; n++) {
    const label = type === "guest" ? String(n) : (n === 1 ? "Just me" : "+" + (n - 1));
    out += fill(chip, { N: n, LABEL: label, CHECKED: n === current ? "checked" : "" });
  }
  return out;
}

function mateLine(m) {
  if (m.status === "Waitlist") return `${esc(m.name)} &middot; on the waitlist`;
  if (m.rsvp_type === "guest")
    return `${esc(m.name)} &middot; ${m.count === 1 ? "1 guest" : m.count + " guests"}`;
  return `${esc(m.name)} &middot; ${m.count === 1 ? "going" : "party of " + m.count}`;
}

async function donePage(context, me, head, sub, href, text, status = 200) {
  const tpl = await template(context, "done");
  const body = fill(cut(tpl, "LINK", inner(tpl, "LINK")), {
    HEAD: head, SUB: sub, LINKHREF: href, LINKTEXT: text,
  });
  return page(context, head.replace(/&[a-z]+;/g, "'"), body, me, status);
}

function stateLine(r) {
  if (r.status === "Waitlist") return "You&rsquo;re on the waitlist for this one.";
  if (r.rsvp_type === "guest")
    return r.count === 1 ? "You have 1 outside guest registered." : `You have ${r.count} outside guests registered.`;
  if (r.rsvp_type === "paid")
    return r.count === 1 ? "You have 1 seat held." : `You have ${r.count} seats held.`;
  return r.count === 1 ? "You&rsquo;re confirmed." : `You&rsquo;re confirmed, party of ${r.count}.`;
}

async function rsvpPage(context, ev, key, me) {
  const { env } = context;
  const type = TYPE[ev.rsvp];   // undefined for drop-in events: facts, no forms
  const tpl = await template(context, "rsvp");

  const existing = me ? await myRsvp(env, me.id, key) : null;
  const active = existing && existing.status !== "Cancelled" ? existing : null;
  // Occupancy only matters for the fresh-RSVP form; someone already holding
  // seats gets the change screen without paying for a recount.
  const taken = ev.capacity && !active ? await seatsTaken(env, key, me ? me.id : 0) : 0;
  const full = !!(ev.capacity && taken >= ev.capacity);

  let body = fill(tpl, {
    EYEBROW: esc(ev.category || "On the calendar"),
    TITLE: esc(ev.title),
    WHEN: whenOf(ev),
    WHERE: esc(ev.location || "Level 39, Residents’ Club"),
  });
  body = cut(body, "SEATS", ev.capacity
    ? fill(inner(tpl, "SEATS"), {
        SEATS: ev.price
          ? `${ev.capacity} at the table &middot; ${esc(ev.price)} per person`
          : `${ev.capacity} places`,
      })
    : null);
  body = cut(body, "CUTOFF", ev.cutoff ? fill(inner(tpl, "CUTOFF"), { CUTOFF: esc(ev.cutoff) }) : null);

  // Drop-in events still get their shareable page: the facts, a warm word, no forms.
  if (!type) {
    body = cut(cut(cut(cut(body, "ALSO", null), "SIGNIN", null), "EXISTING", null), "FORM", null);
    body = cut(body, "DROPIN", inner(tpl, "DROPIN"));
    return page(context, ev.title, body, me);
  }
  body = cut(body, "DROPIN", null);

  // What the rest of the unit already said, so the household sees its own picture.
  const mates = me ? await unitMates(env, me, key) : [];
  body = cut(body, "ALSO", mates.length
    ? fill(inner(tpl, "ALSO"), { MATES: mates.map(mateLine).join("<br>") })
    : null);

  if (!me) {
    body = cut(cut(body, "EXISTING", null), "FORM", null);
    body = cut(body, "SIGNIN", fill(inner(tpl, "SIGNIN"), { TO: `/rsvp/${key}` }));
    return page(context, ev.title, body, null);
  }

  body = cut(body, "SIGNIN", null);

  if (active) {
    let section = inner(tpl, "EXISTING");
    section = cut(section, "CHIP", chips(section, type, active.count));
    body = cut(body, "FORM", null);
    body = cut(body, "EXISTING", fill(section, {
      KEY: key,
      STATE: stateLine(active),
      NAMES: esc(active.names || ""),
      COUNTLABEL: type === "guest" ? "Outside guests" : "Your party",
    }));
    return page(context, ev.title, body, me);
  }

  let section = inner(tpl, "FORM");
  section = cut(section, "STANDARD", type === "standard" ? inner(section, "STANDARD") : null);
  section = cut(section, "GUEST", type === "guest" ? inner(section, "GUEST") : null);
  section = cut(section, "PAID", type === "paid" ? inner(section, "PAID") : null);
  section = cut(section, "FULLNOTE", full && type !== "guest" ? inner(section, "FULLNOTE") : null);
  section = cut(section, "CHIP", chips(section, type, 1));
  const btn = full && type !== "guest" ? "Join the Waitlist"
    : type === "guest" ? "Register Guests"
    : type === "paid" ? `${esc(ev.price || "")}${ev.price ? " &middot; " : ""}Request Seats`
    : "Confirm RSVP";
  body = cut(cut(body, "EXISTING", null), "FORM", fill(section, {
    KEY: key,
    COUNTLABEL: type === "guest" ? "Outside guests" : "Your party",
    BTNTEXT: btn,
  }));
  return page(context, ev.title, body, me);
}

export async function onRequestGet(context) {
  const { env, params } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  await ensureResidentTables(env);
  const me = await currentResident(context);
  const key = String(params.key || "");
  const ev = await liveEvent(env, key);
  if (!ev) {
    return donePage(context, me, "That event isn&rsquo;t on the calendar",
      "It may have moved, or the address was mistyped. The calendar has everything that is on.",
      "/", "Back to the calendar", 404);
  }
  if (ev.date < todayPacific()) {
    return donePage(context, me, "That date has passed",
      "This event has already happened. The calendar has what&rsquo;s coming next.",
      "/", "Back to the calendar");
  }
  // The calendar window, honored here too, so a shared or guessed address can
  // never open details, RSVPs, or calendar files ahead of their time.
  await ensureEventTables(env);
  if (ev.teaser || ev.date > detailEnd(await getWindow(env))) {
    return donePage(context, me, esc(ev.title),
      `${whenOf(ev)}<br><br>This one is still coming together. The full details arrive right here, and RSVP opens with them.`,
      "/", "Back to the calendar");
  }
  const res = await rsvpPage(context, ev, key, me);
  return me ? slideSession(res, context.env, me) : res;
}

export async function onRequestPost(context) {
  const { env, request, params } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  await ensureResidentTables(env);
  const me = await currentResident(context);
  const key = String(params.key || "");
  const ev = await liveEvent(env, key);
  if (!ev || !TYPE[ev.rsvp]) return seeOther("/");
  if (!me) return seeOther(`/rsvp/${key}`);
  if (ev.date < todayPacific()) return seeOther(`/rsvp/${key}`);
  await ensureEventTables(env);
  if (ev.teaser || ev.date > detailEnd(await getWindow(env))) return seeOther(`/rsvp/${key}`);

  const type = TYPE[ev.rsvp];
  const form = await request.formData();
  const action = String(form.get("action") || "rsvp");
  const now = new Date().toISOString();

  if (action === "cancel") {
    await env.DB.prepare(
      "UPDATE rsvps SET status='Cancelled', updated=? WHERE resident_id=? AND event_key=?")
      .bind(now, me.id, key).run();
    return donePage(context, me, "Cancelled",
      "You&rsquo;re off the list for this one, and always welcome to change your mind while there&rsquo;s room.",
      "/my", "My RSVPs");
  }

  const maxCount = type === "guest" ? 6 : 4;
  let count = Math.round(Number(form.get("count")));
  if (!Number.isFinite(count)) count = 1;
  count = Math.max(1, Math.min(maxCount, count));
  const names = String(form.get("names") || "").trim().slice(0, 120);

  // Who holds what decides who gets what. A confirmed party never forfeits its
  // seats by editing; growing must fit or nothing changes; and while anyone is
  // waitlisted, a freed seat goes to the queue, never to whoever taps next.
  const mine = await myRsvp(env, me.id, key);
  const held = mine && mine.status === "Confirmed" ? mine : null;
  let status = "Confirmed";
  if (ev.capacity && type !== "guest") {
    if (held && count <= held.count) {
      status = "Confirmed";
    } else if (held) {
      const taken = await seatsTaken(env, key, me.id);
      if (taken + count > ev.capacity) {
        return donePage(context, me, "Not enough room to grow",
          `There isn&rsquo;t space for the larger party at the moment, so nothing has changed: you still hold ${held.count === 1 ? "your seat" : "your " + held.count + " seats"}. Ask Resident Experiences about the difference; sometimes room opens up.`,
          "/my", "My RSVPs");
      }
    } else {
      const taken = await seatsTaken(env, key, me.id);
      const waiting = await othersWaiting(env, key, me.id);
      if (taken + count > ev.capacity || waiting > 0) status = "Waitlist";
    }
  }

  // A revived RSVP queues from now, not from its first life.
  await env.DB.prepare(
    `INSERT INTO rsvps (resident_id, event_key, event_date, event_title, rsvp_type, count, names, status, created, updated)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(resident_id, event_key) DO UPDATE SET
       rsvp_type=excluded.rsvp_type, count=excluded.count, names=excluded.names,
       status=excluded.status, updated=excluded.updated,
       created=CASE WHEN rsvps.status='Cancelled' THEN excluded.created ELSE rsvps.created END`)
    .bind(me.id, key, ev.date, ev.title, type, count, names, status, now, now).run();

  // Two parties can race past the capacity check; recount after writing and step
  // back onto the waitlist if the room oversold. Better a courteous wait than
  // fourteen places at a twelve-seat table.
  if (status === "Confirmed" && ev.capacity && type !== "guest") {
    if (await confirmedHeads(env, key) > ev.capacity) {
      await env.DB.prepare(
        "UPDATE rsvps SET status='Waitlist', updated=? WHERE resident_id=? AND event_key=?")
        .bind(now, me.id, key).run();
      status = "Waitlist";
    }
  }

  if (status === "Waitlist") {
    return donePage(context, me, "You&rsquo;re on the waitlist",
      "Every seat is spoken for at the moment. You hold a place in the order requests arrived, and Resident Experiences will reach out if one opens.",
      "/my", "My RSVPs");
  }
  const sub = type === "guest"
    ? (count === 1 ? "Your guest is registered. We&rsquo;ll pour and plate for one more." : `Your ${count} guests are registered. We&rsquo;ll pour and plate for them.`)
    : type === "paid"
      ? "Your seats are requested. Resident Experiences confirms them in the order requests arrive, and payment is arranged with your confirmation."
      : "You&rsquo;re on the list, and it now appears under My RSVPs, where you can change or cancel anytime.";
  return donePage(context, me,
    type === "paid" ? "Request received" : "You&rsquo;re in", sub, "/my", "My RSVPs");
}
