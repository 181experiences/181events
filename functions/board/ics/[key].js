// GET /board/ics/2026-09-10_board-meeting -> one meeting as a calendar file.
import { ensureResidentTables } from "../../_lib.js";
import { parseEventKey } from "../../_resident.js";
import { plainIcs, icsEvent } from "../_ics.js";

export async function onRequestGet({ env, params }) {
  const k = parseEventKey(params.key);
  if (!k || !env.DB) return new Response("Not found", { status: 404 });
  await ensureResidentTables(env);
  const ev = await env.DB.prepare(
    "SELECT * FROM events WHERE category='Board Meeting' AND status='Live' AND date=? AND slug=?")
    .bind(k.date, k.slug).first();
  if (!ev) return new Response("Not found", { status: 404 });
  return new Response(plainIcs(icsEvent(ev), "181 Fremont Board Meeting"), {
    headers: {
      "content-type": "text/calendar; charset=utf-8",
      "content-disposition": `attachment; filename="${k.date}_${k.slug}.ics"`,
      "cache-control": "no-store",
    },
  });
}
