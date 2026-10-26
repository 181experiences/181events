// GET /friendsgiving -> the potluck page with "On the menu so far" filled
// from the event's RSVPs: the dishes residents have signed up to bring, by
// kind, no names. The page itself is the build's template (the coded page
// module renders it); the pictures beside it stay static and pass through.
// Unpublished in the admin = no template in the build = off to the calendar.
import { esc, ensureEventTables, ensureResidentTables, todayPacific } from "../_lib.js";
import { template, fill, cut, inner } from "../_resident.js";

const SLUG = "friendsgiving-happy-hour";
const KINDS = [["main", "Main"], ["side", "Side"], ["dessert", "Dessert"], ["drink", "Drink"]];

function menuHtml(rows) {
  const by = {};
  for (const r of rows) (by[r.brings_cat] = by[r.brings_cat] || []).push(r.brings);
  return KINDS.map(([k, label]) => {
    const dishes = by[k] || [];
    const body = dishes.length ? dishes.map(esc).join(" &middot; ") : "<em>Nothing yet. Yours could be first.</em>";
    return `<div class="mkind"><b>${label}${dishes.length ? `<i>${dishes.length}</i>` : ""}</b><span>${body}</span></div>`;
  }).join("");
}

export async function onRequestGet(context) {
  const { env, request, params } = context;
  if (params.rest && params.rest.length) return env.ASSETS.fetch(request);   // /friendsgiving/img/...
  let tpl;
  try { tpl = await template(context, "friendsgiving"); }
  catch (e) { return new Response(null, { status: 302, headers: { location: "https://181residents.com/" } }); }
  let menu = null;
  try {
    if (env.DB) {
      await ensureEventTables(env); await ensureResidentTables(env);
      const ev = await env.DB.prepare(
        "SELECT date, slug, potluck FROM events WHERE slug=? AND status='Live' AND date >= ? ORDER BY date LIMIT 1")
        .bind(SLUG, todayPacific()).first();
      if (ev && ev.potluck) {
        const { results } = await env.DB.prepare(
          `SELECT brings_cat, brings FROM rsvps WHERE event_key=? AND status != 'Cancelled'
           AND brings IS NOT NULL AND brings != '' ORDER BY created`).bind(`${ev.date}_${ev.slug}`).all();
        menu = menuHtml(results);
      }
    }
  } catch (e) { menu = null; }
  const html = menu == null ? cut(tpl, "MENU", null) : fill(cut(tpl, "MENU", inner(tpl, "MENU")), { MENU: menu });
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}
