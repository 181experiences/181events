// POST /message -> the Contact form, landing in the admin's Messages inbox.
//
// Signed in, the note saves at once under the sender's name and unit. Signed out,
// nothing typed is lost: the same POST comes back as a "one more step" page that
// carries the note in hidden fields and asks for the resident code, then saves and
// signs them in together. GET has nothing to show, so it returns to the calendar.

import { esc, ensureResidentTables, labelOf } from "./_lib.js";
import {
  currentResident, findByCode, issueSession, sessionCookie,
  template, fill, cut, inner, page, notReady, seeOther,
  tooManyAttempts, recordAttempt, clientIp,
} from "./_resident.js";

const TOPICS = ["Share an idea", "Plan an event with us", "Something else"];

async function codeStep(context, fields, error) {
  const tpl = await template(context, "msgstep");
  let body = cut(tpl, "ERROR", error ? fill(inner(tpl, "ERROR"), { ERROR: error }) : null);
  body = fill(body, {
    TOPIC: esc(fields.topic), BODY: esc(fields.body),
    NAME: esc(fields.name), EMAIL: esc(fields.email),
  });
  return page(context, "One more step", body, null);
}

async function savedPage(context, me) {
  const tpl = await template(context, "done");
  const body = fill(cut(tpl, "LINK", inner(tpl, "LINK")), {
    HEAD: "Received",
    SUB: "Your note is with Resident Experiences, and we will get back to you within one business day.",
    LINKHREF: "/", LINKTEXT: "Back to the calendar",
  });
  return page(context, "Received", body, me);
}

async function saveMessage(env, me, fields) {
  await env.DB.prepare(
    `INSERT INTO messages (resident_id, unit, sender, topic, body, name, email, state, created)
     VALUES (?, ?, ?, ?, ?, ?, ?, 'New', ?)`)
    .bind(me.id, me.unit || "", labelOf(me), fields.topic, fields.body,
      fields.name, fields.email, new Date().toISOString()).run();
}

export async function onRequestGet() {
  return seeOther("/");
}

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  await ensureResidentTables(env);

  const form = await request.formData();
  const fields = {
    topic: TOPICS.includes(form.get("Topic")) ? form.get("Topic") : TOPICS[2],
    body: String(form.get("Message") || "").trim().slice(0, 4000),
    name: String(form.get("Name") || "").trim().slice(0, 80),
    email: String(form.get("Email") || "").trim().slice(0, 120),
  };
  if (!fields.body) return seeOther("/");

  let me = await currentResident(context);
  let cookie = null;

  if (!me) {
    const typed = form.get("code");
    if (!typed) return codeStep(context, fields, null);
    const ip = clientIp(request);
    if (await tooManyAttempts(env, ip)) {
      return codeStep(context, fields,
        "Quite a few tries in a row. Please pause a few minutes, then try again.");
    }
    me = await findByCode(env, typed);
    if (!me) {
      await recordAttempt(env, ip);
      return codeStep(context, fields,
        "That code didn&rsquo;t match. Check the card, or ask the front desk for a fresh one.");
    }
    cookie = sessionCookie(await issueSession(env, me));
  }

  await saveMessage(env, me, fields);
  const res = await savedPage(context, me);
  if (cookie) res.headers.set("set-cookie", cookie);
  return res;
}
