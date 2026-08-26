// Pages redirects "pretty URLs" itself: /admin.html 308s to /admin. So /admin is the
// canonical address, the Access application guards it (case-insensitively), and this
// middleware folds every other spelling into it. One door, the locked one, and no
// redirect loop with Pages' own handling.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const p = url.pathname.toLowerCase().replace(/\/+$/, "");
  // The project also answers on *.pages.dev addresses, which the "181 admin"
  // Access application does not cover. When the project's own preview Access
  // policy is switched on, gated requests arrive carrying the Access login
  // token, and previews may exercise the locked areas in place: the API guards
  // verify that token's signature before trusting it, so a forged header gets
  // refused rather than admitted. Ungated pages.dev traffic is sent to the real
  // domain, where the lock is. The public calendar stays previewable anywhere.
  const gated = !!context.request.headers.get("cf-access-jwt-assertion");
  if (url.hostname.endsWith(".pages.dev") && !gated && (p === "/admin" || p === "/admin.html" || p.startsWith("/api"))) {
    return Response.redirect("https://181residents.com" + (p.startsWith("/api") ? url.pathname : "/admin"), 301);
  }
  // Resident sign-in and RSVPs likewise stay on the real domain for ungated
  // traffic (their cookie belongs to 181residents.com); on a gated preview they
  // run in place, with their own cookie on the preview host, for staff testing.
  if (url.hostname.endsWith(".pages.dev") && !gated &&
      (p === "/signin" || p === "/signout" || p === "/my" || p === "/message" || p.startsWith("/rsvp/"))) {
    return Response.redirect("https://181residents.com" + url.pathname + url.search, 301);
  }
  if ((p === "/admin" || p === "/admin.html") && url.pathname !== "/admin") {
    url.pathname = "/admin";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
