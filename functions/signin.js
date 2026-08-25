// GET /signin  -> the sign-in page (optionally ?to=/rsvp/... to bounce back after).
// POST /signin -> checks the unit code, sets the month-long session cookie.
// Plain forms, no JavaScript needed: the resident site's doctrine holds here too.

import { ensureResidentTables } from "./_lib.js";
import {
  currentResident, findByCode, issueSession, sessionCookie, safeReturn,
  template, fill, cut, inner, page, seeOther, notReady,
  tooManyAttempts, recordAttempt, clientIp,
} from "./_resident.js";

async function signinPage(context, to, error, status = 200) {
  const tpl = await template(context, "signin");
  let body = cut(tpl, "ERROR", error ? fill(inner(tpl, "ERROR"), { ERROR: error }) : null);
  body = fill(body, { TO: safeReturn(to) });
  return page(context, "Sign in", body, null, status);
}

export async function onRequestGet(context) {
  const { env, request } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  const url = new URL(request.url);
  const me = await currentResident(context);
  if (me) return seeOther(safeReturn(url.searchParams.get("to")));
  return signinPage(context, url.searchParams.get("to"));
}

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  await ensureResidentTables(env);
  const form = await request.formData();
  const to = form.get("to");
  const ip = clientIp(request);
  if (await tooManyAttempts(env, ip)) {
    return signinPage(context, to,
      "Quite a few tries in a row. Please pause a few minutes, then try again.", 429);
  }
  const resident = await findByCode(env, form.get("code"));
  if (!resident) {
    await recordAttempt(env, ip);
    return signinPage(context, to,
      "That code didn&rsquo;t match. Check the card, or ask the front desk for a fresh one.", 200);
  }
  const token = await issueSession(env, resident);
  return seeOther(safeReturn(to), sessionCookie(token));
}
