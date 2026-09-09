// GET  /notes -> the neighbor-notes board: signed notes that fade after three
//                days, answered with raised hands rather than replies.
// POST /notes -> pin a note, raise or lower a hand, or take your own note down.
//
// The board is for the household only, so it opens with the resident code; the
// calendar stays public, but names and evening plans do not. The shape does the
// moderating: notes are signed, post-it sized, link-free, capped at two per
// person, and gone in three days. Staff can rest the whole board from the
// admin (settings key notes_open), which is the standing brake.

import { esc, ensureResidentTables, labelOf, notesOpen } from "./_lib.js";
import {
  currentResident, template, fill, cut, inner, page, seeOther, notReady, slideSession,
} from "./_resident.js";

const KEEP_DAYS = 3;

function cutoffIso() {
  return new Date(Date.now() - KEEP_DAYS * 86400000).toISOString();
}

async function sweep(env) {
  const c = cutoffIso();
  await env.DB.prepare(
    "DELETE FROM note_hands WHERE note_id IN (SELECT id FROM notes WHERE created < ?)").bind(c).run();
  await env.DB.prepare("DELETE FROM notes WHERE created < ?").bind(c).run();
}

function age(created) {
  const days = Math.floor((Date.now() - Date.parse(created)) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

async function boardPage(context, me) {
  const { env } = context;
  const tpl = await template(context, "notes");
  let body = tpl;

  if (!me) {
    body = cut(cut(cut(cut(cut(body, "CLOSED", null), "FORM", null), "NOTE", null), "EMPTY", null), "FOOT", null);
    body = cut(body, "SIGNIN", fill(inner(tpl, "SIGNIN"), { TO: "/notes" }));
    return page(context, "Neighbor Notes", body, null);
  }
  body = cut(body, "SIGNIN", null);

  if (!(await notesOpen(env))) {
    body = cut(cut(cut(cut(body, "FORM", null), "NOTE", null), "EMPTY", null), "FOOT", null);
    body = cut(body, "CLOSED", inner(tpl, "CLOSED"));
    return page(context, "Neighbor Notes", body, me);
  }
  body = cut(body, "CLOSED", null);

  await sweep(env);
  const { results: notes } = await env.DB.prepare(
    `SELECT n.*, res.name, res.unit FROM notes n JOIN residents res ON res.id = n.resident_id
     ORDER BY n.created DESC`).all();
  const { results: hands } = await env.DB.prepare(
    `SELECT h.note_id, h.resident_id, res.name, res.unit
     FROM note_hands h JOIN residents res ON res.id = h.resident_id ORDER BY h.id`).all();

  const noteTpl = inner(tpl, "NOTE");
  const rendered = notes.map((n, i) => {
    const mine = n.resident_id === me.id;
    const nh = hands.filter(h => h.note_id === n.id);
    const raised = nh.some(h => h.resident_id === me.id);
    let s = fill(noteTpl, {
      TILT: "t" + ((i % 3) + 1),
      BODY: esc(n.body),
      WHO: esc(labelOf(n)),
      AGE: age(n.created),
      ID: String(n.id),
    });
    const asking = n.asks == null || !!n.asks;
    s = cut(s, "HANDS", asking && nh.length
      ? fill(inner(noteTpl, "HANDS"), { NAMES: nh.map(h => esc(labelOf(h))).join(", "), ID: String(n.id) })
      : null);
    s = cut(s, "HAND", asking && !mine && !raised ? inner(noteTpl, "HAND") : null);
    s = cut(s, "UNHAND", asking && !mine && raised ? inner(noteTpl, "UNHAND") : null);
    s = cut(s, "REMOVE", mine ? inner(noteTpl, "REMOVE") : null);
    return fill(s, { ID: String(n.id) });
  }).join("");

  body = cut(body, "FORM", fill(inner(tpl, "FORM"), { WHO: esc(labelOf(me)) }));
  body = cut(body, "NOTE", rendered);
  body = cut(body, "EMPTY", notes.length ? null : inner(tpl, "EMPTY"));
  body = cut(body, "FOOT", inner(tpl, "FOOT"));
  return page(context, "Neighbor Notes", body, me);
}

async function donePage(context, me, head, sub) {
  const tpl = await template(context, "done");
  const body = fill(cut(tpl, "LINK", inner(tpl, "LINK")), {
    HEAD: head, SUB: sub, LINKHREF: "/notes", LINKTEXT: "Back to the board",
  });
  return page(context, head, body, me);
}

export async function onRequestGet(context) {
  const { env } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  await ensureResidentTables(env);
  const me = await currentResident(context);
  const res = await boardPage(context, me);
  return me ? slideSession(res, env, me) : res;
}

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!env.DB || !env.SESSION_SECRET) return notReady(context);
  await ensureResidentTables(env);
  const me = await currentResident(context);
  if (!me) return seeOther("/notes");
  if (!(await notesOpen(env))) return seeOther("/notes");
  await sweep(env);

  const form = await request.formData();
  const kind = String(form.get("kind") || "");

  if (kind === "post") {
    const body = String(form.get("body") || "").replace(/\s+/g, " ").trim().slice(0, 240);
    if (!body) return seeOther("/notes");
    if (/(https?:\/\/|www\.)/i.test(body)) {
      return donePage(context, me, "Plain words only",
        "Notes keep to plain words, no links, so the board stays what it is. Say it in a sentence and pin it again.");
    }
    const { c } = await env.DB.prepare(
      "SELECT COUNT(*) AS c FROM notes WHERE resident_id=?").bind(me.id).first();
    if (c >= 2) {
      return donePage(context, me, "Two notes at a time",
        "The board keeps to two notes per person, so everyone&rsquo;s fits. Take one of yours down and pin the new one.");
    }
    await env.DB.prepare("INSERT INTO notes (resident_id, body, created, asks) VALUES (?, ?, ?, ?)")
      .bind(me.id, body, new Date().toISOString(), form.get("asks") ? 1 : 0).run();
    return seeOther("/notes");
  }

  const noteId = Number(form.get("note"));
  if (!Number.isInteger(noteId)) return seeOther("/notes");
  const note = await env.DB.prepare("SELECT * FROM notes WHERE id=?").bind(noteId).first();
  if (!note) return seeOther("/notes");

  if (kind === "hand" && note.resident_id !== me.id && (note.asks == null || note.asks)) {
    await env.DB.prepare(
      "INSERT INTO note_hands (note_id, resident_id, created) VALUES (?, ?, ?) ON CONFLICT(note_id, resident_id) DO NOTHING")
      .bind(noteId, me.id, new Date().toISOString()).run();
  } else if (kind === "unhand") {
    await env.DB.prepare("DELETE FROM note_hands WHERE note_id=? AND resident_id=?").bind(noteId, me.id).run();
  } else if (kind === "remove" && note.resident_id === me.id) {
    await env.DB.prepare("DELETE FROM note_hands WHERE note_id=?").bind(noteId).run();
    await env.DB.prepare("DELETE FROM notes WHERE id=?").bind(noteId).run();
  }
  return seeOther("/notes");
}
