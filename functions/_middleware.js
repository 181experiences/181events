// Pages serves "pretty URLs", so the admin page would also answer at /admin, /Admin,
// and friends — paths the Access application does not guard. Canonicalise every
// admin-ish path to /admin.html, the one URL Access protects (case-insensitively),
// so there is exactly one door and it is the locked one.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const p = url.pathname.toLowerCase().replace(/\/+$/, "");
  if ((p === "/admin" || p === "/admin.html") && url.pathname !== "/admin.html") {
    url.pathname = "/admin.html";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
