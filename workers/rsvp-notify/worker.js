// rsvp-notify: the one place the site sends email from, and only to staff.
//
// The Pages Functions call this Worker through a service binding (NOTIFY)
// whenever an RSVP is made, changed, or cancelled, or an outside guest
// registers. It sends one plain-text email to Leo through Cloudflare Email
// Routing, which delivers only to destination addresses verified in the
// dashboard, so this can never be aimed at an arbitrary inbox.
//
// Setup lives in DEPLOY.md, step "RSVP notifications".

import { EmailMessage } from "cloudflare:email";

const FROM = "rsvps@181residents.com";
const TO = "leonardo@181sf.com";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("rsvp-notify", { status: 200 });
    let subject = "RSVP update", body = "";
    try {
      const d = await request.json();
      subject = String(d.subject || subject).replace(/[\r\n]+/g, " ").slice(0, 180);
      body = String(d.body || "");
    } catch (e) { return new Response("bad request", { status: 400 }); }
    const mime = [
      `From: 181 Fremont RSVPs <${FROM}>`,
      `To: <${TO}>`,
      `Subject: ${subject}`,
      `Date: ${new Date().toUTCString()}`,
      `Message-ID: <${crypto.randomUUID()}@181residents.com>`,
      "MIME-Version: 1.0",
      "Content-Type: text/plain; charset=utf-8",
      "",
      body,
      "",
      "-- ",
      "181residents.com admin: https://181residents.com/admin",
    ].join("\r\n");
    try {
      await env.SEND.send(new EmailMessage(FROM, TO, mime));
      return new Response("sent");
    } catch (e) {
      return new Response("send failed: " + (e && e.message), { status: 500 });
    }
  },
};
