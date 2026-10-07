import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail,
         RESERVED_SLUGS } from "../../_lib.js";

// Standalone pages: the occasions bigger than one event (a festival week, a
// holiday guide), written in the admin's Pages builder and published as static
// pages at the site root. Pages stay with the events tier; the desk reads.

async function noPages(request, env) {
  const role = await adminRole(request, env);
  return !role || role === "desk";
}

export function cleanSlug(v) {
  return String(v || "").toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
}

// The blocks ride as a JSON array of {kind, ...fields}; the publisher renders
// only kinds it knows, so an unknown kind can never break a build.
export function cleanBlocks(v) {
  let list = v;
  if (typeof list === "string") { try { list = JSON.parse(list); } catch (e) { list = []; } }
  if (!Array.isArray(list)) list = [];
  const out = [];
  for (const b of list.slice(0, 40)) {
    if (!b || typeof b !== "object" || typeof b.kind !== "string") continue;
    const keep = { kind: b.kind.slice(0, 20) };
    for (const k of ["heading", "when", "body", "sub", "title", "lines", "ours", "label", "url", "stem"]) {
      if (k in b) keep[k] = String(b[k] == null ? "" : b[k]).slice(0, 4000);
    }
    out.push(keep);
  }
  return JSON.stringify(out);
}

// GET /api/pages -> every page, every status. Every tier may look.
export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (!(await adminRole(request, env))) return forbidden();
  await ensureResidentTables(env);
  const { results } = await env.DB.prepare("SELECT * FROM pages ORDER BY updated DESC, id DESC").all();
  return json({ pages: results });
}

// POST /api/pages {title, slug, eyebrow, lede, blocks} -> a new Draft.
export async function onRequestPost({ request, env }) {
  const err = noDb(env); if (err) return err;
  if (await noPages(request, env)) return forbidden();
  await ensureResidentTables(env);
  const b = await request.json();
  const title = String(b.title || "").trim().slice(0, 120);
  const slug = cleanSlug(b.slug || title);
  if (!title) return json({ error: "Give the page a title." }, 400);
  if (slug.length < 3) return json({ error: "The address needs at least three characters." }, 400);
  if (RESERVED_SLUGS.has(slug)) return json({ error: `/${slug} already belongs to the site itself; pick another address.` }, 400);
  const clash = await env.DB.prepare("SELECT id FROM pages WHERE slug=?").bind(slug).first();
  if (clash) return json({ error: `The address /${slug} is already taken by another page.` }, 400);
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const now = new Date().toISOString();
  const row = await env.DB.prepare(
    `INSERT INTO pages (title, slug, eyebrow, lede, blocks, status, created, updated, updated_by)
     VALUES (?, ?, ?, ?, ?, 'Draft', ?, ?, ?) RETURNING *`)
    .bind(title, slug, String(b.eyebrow || "").trim().slice(0, 160) || null,
      String(b.lede || "").trim().slice(0, 600) || null,
      cleanBlocks(b.blocks), now, now, who).first();
  return json({ page: row }, 201);
}
