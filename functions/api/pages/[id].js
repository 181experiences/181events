import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail,
         RESERVED_SLUGS } from "../../_lib.js";
import { cleanSlug, cleanBlocks } from "./index.js";

async function noPages(request, env) {
  const role = await adminRole(request, env);
  return !role || role === "desk";
}

// PATCH /api/pages/:id -> edits, the working copy ({__draft}), and the
// lifecycle: Publish is the only road onto the site, Unpublish holds the
// content with the link falling back to the calendar, Archive files an
// unpublished page away. A field PATCH clears the working copy: applying
// the fields IS the apply, exactly as events behave.
export async function onRequestPatch(context) {
  const { request, params, env } = context;
  const err = noDb(env); if (err) return err;
  if (await noPages(request, env)) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const b = await request.json();
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const now = new Date().toISOString();

  if ("__draft" in b) {
    const row = await env.DB.prepare(
      "UPDATE pages SET draft_json=?, updated=?, updated_by=? WHERE id=? RETURNING *")
      .bind(b.__draft ? JSON.stringify(b.__draft).slice(0, 60000) : null, now, who, id).first();
    if (!row) return json({ error: "No such page" }, 404);
    return json({ page: row });
  }

  const sets = [], vals = [];
  if ("title" in b) {
    const title = String(b.title || "").trim().slice(0, 120);
    if (!title) return json({ error: "Give the page a title." }, 400);
    sets.push("title=?"); vals.push(title);
  }
  if ("slug" in b) {
    const slug = cleanSlug(b.slug);
    if (slug.length < 3) return json({ error: "The address needs at least three characters." }, 400);
    if (RESERVED_SLUGS.has(slug)) return json({ error: `/${slug} already belongs to the site itself; pick another address.` }, 400);
    const clash = await env.DB.prepare("SELECT id FROM pages WHERE slug=? AND id!=?").bind(slug, id).first();
    if (clash) return json({ error: `The address /${slug} is already taken by another page.` }, 400);
    sets.push("slug=?"); vals.push(slug);
  }
  if ("eyebrow" in b) { sets.push("eyebrow=?"); vals.push(String(b.eyebrow || "").trim().slice(0, 160) || null); }
  if ("lede" in b) { sets.push("lede=?"); vals.push(String(b.lede || "").trim().slice(0, 600) || null); }
  if ("blocks" in b) { sets.push("blocks=?"); vals.push(cleanBlocks(b.blocks)); }
  if ("status" in b) {
    if (!["Draft", "Published", "Unpublished", "Archived"].includes(b.status)) return json({ error: "Bad status" }, 400);
    sets.push("status=?"); vals.push(b.status);
  }
  if (!sets.length) return json({ error: "Nothing to change" }, 400);
  // Applying fields is the apply: the working copy clears with every real save.
  sets.push("draft_json=NULL", "updated=?", "updated_by=?"); vals.push(now, who);
  const row = await env.DB.prepare(
    `UPDATE pages SET ${sets.join(",")} WHERE id=? RETURNING *`).bind(...vals, id).first();
  if (!row) return json({ error: "No such page" }, 404);
  return json({ page: row });
}

// DELETE /api/pages/:id -> drafts only; residents never saw one, nothing is lost.
export async function onRequestDelete(context) {
  const { request, params, env } = context;
  const err = noDb(env); if (err) return err;
  if (await noPages(request, env)) return forbidden();
  await ensureResidentTables(env);
  const id = Number(params.id);
  if (!Number.isInteger(id)) return json({ error: "Bad id" }, 400);
  const row = await env.DB.prepare("SELECT * FROM pages WHERE id=?").bind(id).first();
  if (!row) return json({ error: "No such page" }, 404);
  if ((row.status || "Draft") !== "Draft")
    return json({ error: "Only drafts delete. A published page is unpublished first, then archived, so its record stays." }, 400);
  await env.DB.prepare("DELETE FROM pages WHERE id=?").bind(id).run();
  return json({ ok: true });
}
