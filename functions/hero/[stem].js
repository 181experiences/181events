// GET /hero/{stem} -> the uploaded web hero for that event, straight from the
// kit's storage. This is the one public window into the asset shelf, and it
// serves exactly one kind: the picture the event's own public page wears.
// Everything else in the kit stays behind the staff door. No database round
// trip: the object's presence in storage is the truth, and its stored content
// type rides along. Missing means the page shows its typographic card instead,
// so a 404 here is never a resident-visible failure.
export async function onRequestGet({ params, env }) {
  if (!env.KIT) return new Response("Not here.", { status: 404 });
  const stem = String(params.stem || "");
  if (!/^[a-z0-9._-]+$/i.test(stem)) return new Response("Not here.", { status: 404 });
  const obj = await env.KIT.get(`${stem}/web-hero`);
  if (!obj) return new Response("Not here.", { status: 404 });
  return new Response(obj.body, {
    headers: {
      "content-type": (obj.httpMetadata && obj.httpMetadata.contentType) || "image/jpeg",
      "cache-control": "public, max-age=300",
    },
  });
}
