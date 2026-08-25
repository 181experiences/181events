// Pages redirects "pretty URLs" itself: /admin.html 308s to /admin. So /admin is the
// canonical address, the Access application guards it (case-insensitively), and this
// middleware folds every other spelling into it. One door, the locked one, and no
// redirect loop with Pages' own handling.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const p = url.pathname.toLowerCase().replace(/\/+$/, "");
  // The project also answers on its *.pages.dev address, which the Access application
  // does not cover. Anything sensitive arriving that way is sent to the real domain,
  // where the lock is. The public calendar itself may stay previewable anywhere.
  if (url.hostname.endsWith(".pages.dev") && (p === "/admin" || p === "/admin.html" || p.startsWith("/api"))) {
    return Response.redirect("https://181residents.com" + (p.startsWith("/api") ? url.pathname : "/admin"), 301);
  }
  // Resident sign-in and RSVPs live on the real domain only: the session cookie is
  // set for 181residents.com, so on any *.pages.dev address these pages would look
  // signed out forever. Send them home instead.
  if (url.hostname.endsWith(".pages.dev") &&
      (p === "/signin" || p === "/signout" || p === "/my" || p === "/message" || p.startsWith("/rsvp/"))) {
    return Response.redirect("https://181residents.com" + url.pathname + url.search, 301);
  }
  if ((p === "/admin" || p === "/admin.html") && url.pathname !== "/admin") {
    url.pathname = "/admin";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
