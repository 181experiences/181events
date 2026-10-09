// rsvp-notify: the one place the site sends email from, and only to staff.
//
// The Pages Functions call this Worker through a service binding (NOTIFY)
// whenever an RSVP is made, changed, or cancelled, an outside guest
// registers, or an inventory count is submitted. It sends plain-text (or
// text + HTML) email through Cloudflare Email Routing, which delivers only
// to destination addresses verified in the dashboard, so this can never be
// aimed at an arbitrary inbox.
//
// Payload: { subject, body, html?, to?: [addresses], from? }. Without `to`
// the note goes to TO_LIST (the RSVP record). With `to` (the inventory
// report's department heads, kept under Settings) it goes there instead;
// an unverified address simply fails to send and is counted as such.
//
// Setup lives in DEPLOY.md, step "RSVP notifications". Keep this file and
// the dashboard paste in lockstep: the Worker runs from the paste.

import { EmailMessage } from "cloudflare:email";

const DEFAULT_FROM = "rsvps@181residents.com";
// Only addresses on the site's own domain may appear as the sender.
const FROM_OK = new Set(["rsvps@181residents.com", "reports@181residents.com"]);
const FROM_NAME = { "rsvps@181residents.com": "181 Fremont RSVPs", "reports@181residents.com": "181 Fremont Reports" };
// Every verified destination listed here gets its own copy of every RSVP note.
// leonardo@ is the work record; the gmail copy is the backstop that caught
// the mail-filtering gap once already.
const TO_LIST = ["leonardo@181sf.com", "181sf.leo@gmail.com"];

function cleanAddr(v) {
  const s = String(v || "").trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) ? s : "";
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("rsvp-notify", { status: 200 });
    let subject = "RSVP update", body = "", html = "", to = [], from = DEFAULT_FROM;
    try {
      const d = await request.json();
      subject = String(d.subject || subject).replace(/[\r\n]+/g, " ").slice(0, 180);
      body = String(d.body || "");
      html = String(d.html || "");
      if (Array.isArray(d.to)) to = [...new Set(d.to.map(cleanAddr).filter(Boolean))].slice(0, 25);
      if (d.from && FROM_OK.has(String(d.from).toLowerCase())) from = String(d.from).toLowerCase();
    } catch (e) { return new Response("bad request", { status: 400 }); }
    if (!to.length) to = TO_LIST;
    let sent = 0, lastErr = null;
    for (const addr of to) {
      const head = [
        `From: ${FROM_NAME[from] || "181 Fremont"} <${from}>`,
        `To: <${addr}>`,
        `Subject: ${subject}`,
        `Date: ${new Date().toUTCString()}`,
        `Message-ID: <${crypto.randomUUID()}@181residents.com>`,
        "MIME-Version: 1.0",
      ];
      const foot = "\r\n-- \r\n181residents.com admin: https://181residents.com/admin";
      let mime;
      if (html) {
        const b = "=_181_" + crypto.randomUUID().replace(/-/g, "");
        mime = [...head,
          `Content-Type: multipart/alternative; boundary="${b}"`, "",
          `--${b}`, "Content-Type: text/plain; charset=utf-8", "", body + foot, "",
          `--${b}`, "Content-Type: text/html; charset=utf-8", "", html, "",
          `--${b}--`, ""].join("\r\n");
      } else {
        mime = [...head, "Content-Type: text/plain; charset=utf-8", "", body + foot, ""].join("\r\n");
      }
      try {
        await env.SEND.send(new EmailMessage(from, addr, mime));
        sent++;
      } catch (e) { lastErr = e; }
    }
    if (sent) return new Response(`sent to ${sent} of ${to.length}`);
    return new Response("send failed: " + (lastErr && lastErr.message), { status: 500 });
  },
};
