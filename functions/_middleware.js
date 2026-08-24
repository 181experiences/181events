// Pages redirects "pretty URLs" itself: /admin.html 308s to /admin. So /admin is the
// canonical address, the Access application guards it (case-insensitively), and this
// middleware folds every other spelling into it. One door, the locked one, and no
// redirect loop with Pages' own handling.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const p = url.pathname.toLowerCase().replace(/\/+$/, "");
  if ((p === "/admin" || p === "/admin.html") && url.pathname !== "/admin") {
    url.pathname = "/admin";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
