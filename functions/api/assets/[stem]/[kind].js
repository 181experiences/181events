import {
  json, noDb, adminRole, forbidden, ensureResidentTables, ASSET_KINDS,
} from "../../../_lib.js";

// One piece of one event's kit, addressed /api/assets/{stem}/{kind}:
//   PUT     the file itself (streamed to R2; replaces what was there)
//   GET     download the current file, named as it was uploaded
//   PATCH   {canva} save or clear the Canva address for this piece
//   DELETE  remove the uploaded file (the Canva link stays)
// Files live in the R2 bucket bound as KIT; rows in D1 carry the facts.

async function gate(request, env) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  return null;
}

function ids(params) {
  const stem = String(params.stem || "");
  const kind = String(params.kind || "");
  if (!/^[a-z0-9._-]+$/i.test(stem) || !ASSET_KINDS.includes(kind)) return null;
  return { stem, kind, key: `${stem}/${kind}` };
}

export async function onRequestPut({ request, params, env }) {
  const err = await gate(request, env); if (err) return err;
  if (!env.KIT) return json({ error: "File storage is not linked yet. Add the R2 bucket binding named KIT in the Pages settings." }, 503);
  const a = ids(params); if (!a) return json({ error: "Bad asset address" }, 400);
  await ensureResidentTables(env);
  const filename = decodeURIComponent(request.headers.get("x-filename") || "file").slice(0, 160);
  const type = request.headers.get("content-type") || "application/octet-stream";
  const size = Number(request.headers.get("content-length")) || 0;
  await env.KIT.put(a.key, request.body, {
    httpMetadata: { contentType: type },
    customMetadata: { filename },
  });
  const row = await env.DB.prepare(
    `INSERT INTO assets (stem, kind, filename, size, type, uploaded)
     VALUES (?, ?, ?, ?, ?, ?)
     ON CONFLICT(stem, kind) DO UPDATE SET
       filename=excluded.filename, size=excluded.size, type=excluded.type, uploaded=excluded.uploaded`)
    .bind(a.stem, a.kind, filename, size, type, new Date().toISOString()).run()
    .then(() => env.DB.prepare("SELECT * FROM assets WHERE stem=? AND kind=?").bind(a.stem, a.kind).first());
  return json({ asset: row }, 201);
}

export async function onRequestGet({ request, params, env }) {
  const err = await gate(request, env); if (err) return err;
  if (!env.KIT) return json({ error: "File storage is not linked yet." }, 503);
  const a = ids(params); if (!a) return json({ error: "Bad asset address" }, 400);
  const obj = await env.KIT.get(a.key);
  if (!obj) return json({ error: "Nothing uploaded here yet." }, 404);
  const filename = (obj.customMetadata && obj.customMetadata.filename) || `${a.stem}_${a.kind}`;
  return new Response(obj.body, {
    headers: {
      "content-type": (obj.httpMetadata && obj.httpMetadata.contentType) || "application/octet-stream",
      "content-disposition": `attachment; filename="${filename.replace(/"/g, "")}"`,
      "cache-control": "no-store",
    },
  });
}

export async function onRequestPatch({ request, params, env }) {
  const err = await gate(request, env); if (err) return err;
  const a = ids(params); if (!a) return json({ error: "Bad asset address" }, 400);
  await ensureResidentTables(env);
  const { canva } = await request.json();
  const url = String(canva || "").trim().slice(0, 400);
  if (url && !/^https:\/\//.test(url)) return json({ error: "A Canva link starts with https://" }, 400);
  await env.DB.prepare(
    `INSERT INTO assets (stem, kind, canva) VALUES (?, ?, ?)
     ON CONFLICT(stem, kind) DO UPDATE SET canva=excluded.canva`)
    .bind(a.stem, a.kind, url || null).run();
  const row = await env.DB.prepare("SELECT * FROM assets WHERE stem=? AND kind=?").bind(a.stem, a.kind).first();
  return json({ asset: row });
}

export async function onRequestDelete({ request, params, env }) {
  const err = await gate(request, env); if (err) return err;
  const a = ids(params); if (!a) return json({ error: "Bad asset address" }, 400);
  await ensureResidentTables(env);
  if (env.KIT) await env.KIT.delete(a.key);
  await env.DB.prepare(
    "UPDATE assets SET filename=NULL, size=NULL, type=NULL, uploaded=NULL WHERE stem=? AND kind=?")
    .bind(a.stem, a.kind).run();
  await env.DB.prepare(
    "DELETE FROM assets WHERE stem=? AND kind=? AND canva IS NULL AND filename IS NULL")
    .bind(a.stem, a.kind).run();
  const row = await env.DB.prepare("SELECT * FROM assets WHERE stem=? AND kind=?").bind(a.stem, a.kind).first();
  return json({ asset: row || null });
}
