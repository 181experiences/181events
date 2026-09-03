/* 181 Fremont admin. Talks to /api/* (Cloudflare Pages Functions, or dev_server.py locally).
   Staff only, so JavaScript is fine here. The resident site stays script-free. */
(function () {
  "use strict";
  // The Cloudflare Access team domain, used only by Sign out to end the SSO
  // session. If the team domain is ever renamed in Zero Trust -> Settings,
  // this is the one line to update.
  const ACCESS_TEAM = "181sf-events.cloudflareaccess.com";

  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const UNITS = 55;
  const CATS = ["Morning Offering", "Happy Hour", "Community Dinner", "Culinary Experience", "Enrichment Experience", "Signature Event", "Board Meeting"];
  const STATUSES = ["Draft", "Live", "Unpublished", "Archived"];
  const RSVPS = ["None", "Guest count", "Seat", "Paid seat"];
  // The six pieces of every event's kit: what each is, and where it actually goes.
  const KITINFO = [
    { slug: "web-hero", name: "Web hero", spec: "1600 × 900 JPG, under 500 KB",
      where: "The picture atop this event's page on the site. Without one, the page shows the typographic card, which is fine." },
    { slug: "nixplay-still", name: "Nixplay still", spec: "1080 × 1920 PNG or JPG, portrait",
      where: "The bar, lobby, and Level 7 screens, sent to the frames at their email address." },
    { slug: "nixplay-video", name: "Nixplay video", spec: "1080 × 1920 MP4, 10 to 20 seconds",
      where: "The same three screens. Uploads by hand in the Nixplay dashboard; email cannot carry video." },
    { slug: "elevator-print", name: "Elevator print", spec: "8.5 × 11 portrait PDF, 300 DPI",
      where: "The printed sign in the elevator frames, posted one week out, removed the morning after." },
    { slug: "level39-print", name: "Level 39 print", spec: "8.5 × 11 portrait PDF, 300 DPI",
      where: "The sign on the Level 39 landing, worth printing whenever the event is up here. Its QR differs from the elevator's so scans are told apart." },
    { slug: "email-header", name: "Email header", spec: "1200 × 600 JPG, under 200 KB",
      where: "Tops the Mailchimp campaign for this event, and the weekly email when featured." },
  ];
  let assets = [], assetStorage = false;
  const assetOf = (st, slug) => assets.find(a => a.stem === st && a.kind === slug);
  // The MASTER kit lives on the event family itself (its slug): one upload,
  // every date of a series inherits it. A single date may carry its own
  // override, keyed by that date's full stem, which wins for that day alone.
  const masterKey = e => e.Slug || slugify(e.Title || "");
  const resolvedAsset = (e, kindSlug) => assetOf(stem(e), kindSlug) || assetOf(masterKey(e), kindSlug);
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"];
  const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  let events = [], status = {}, analytics = null, days = 30, editing = null;
  let role = "staff", residents = [], msgs = [], rsvps = [];
  let evError = null;   // a failed events load must say so, never render as a quiet zero
  let rp = { mode: "none", days: new Set(), ord: "Last", wd: 0, end: "cal", times: 6, until: "" };
  const DOWFULL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  function calendarEnd() {
    const m = events.reduce((a, e) => e.Date > a ? e.Date : a, "");
    return m || today();
  }

  function addDays(iso, n) { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); }

  function ruleDates(anchor) {
    // Every date the current rule generates, starting at the anchor date.
    const out = [];
    const capIso = rp.end === "date" && rp.until ? rp.until : calendarEnd();
    const capN = rp.end === "count" ? Math.max(2, Math.min(60, rp.times || 6)) : 366;
    if (rp.mode === "daily") {
      for (let d = anchor; d <= capIso && out.length < capN; d = addDays(d, 1)) out.push(d);
    } else if (rp.mode === "weekly") {
      const want = rp.days.size ? rp.days : new Set([new Date(anchor + "T12:00:00").getDay()]);
      for (let d = anchor; d <= capIso && out.length < capN; d = addDays(d, 1)) {
        if (want.has(new Date(d + "T12:00:00").getDay())) out.push(d);
      }
    } else if (rp.mode === "monthly") {
      const a = new Date(anchor + "T12:00:00");
      for (let y = a.getFullYear(), m = a.getMonth(), guard = 0; guard < 14 && out.length < capN; guard++) {
        const hits = [];
        for (let dd = 1; dd <= 31; dd++) {
          const d = new Date(y, m, dd, 12);
          if (d.getMonth() !== m) break;
          if (d.getDay() === Number(rp.wd)) hits.push(d);
        }
        const ordIdx = { First: 0, Second: 1, Third: 2, Fourth: 3, Last: hits.length - 1 }[rp.ord];
        const pick = hits[ordIdx];
        if (pick) {
          const iso = pick.toISOString().slice(0, 10);
          if (iso >= anchor && iso <= capIso) out.push(iso);
        }
        m++; if (m > 11) { m = 0; y++; }
      }
    }
    return out;
  }

  function ruleLabel() {
    if (rp.mode === "daily") return "Every day";
    if (rp.mode === "weekly") {
      const names = [...rp.days].sort().map(i => DOWFULL[i]);
      if (!names.length) return "Every week";
      if (names.length === 1) return "Every " + names[0];
      return "Every " + names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
    }
    if (rp.mode === "monthly") return `${rp.ord} ${DOWFULL[rp.wd]} of the month`;
    return "";
  }

  function rpRefresh() {
    $$("#rp-picks .pick").forEach(b => b.classList.toggle("on", b.dataset.rp === rp.mode));
    $$("#rp-days .pick").forEach(b => b.classList.toggle("on", rp.days.has(Number(b.dataset.wd))));
    $$("#rp-endpicks .pick").forEach(b => b.classList.toggle("on", b.dataset.en === rp.end));
    $("#rp-weekly").style.display = rp.mode === "weekly" ? "" : "none";
    $("#rp-monthly").style.display = rp.mode === "monthly" ? "" : "none";
    $("#rp-ends").style.display = rp.mode === "none" ? "none" : "";
    $("#rp-times").style.display = rp.end === "count" ? "" : "none";
    $("#rp-until").style.display = rp.end === "date" ? "" : "none";
    if (rp.mode !== "none") $("#f-series").value = ruleLabel();
    else if (!editing || !editing.row) $("#f-series").value = "";
    const anchor = $("#f-date").value;
    const n = rp.mode === "none" || !anchor ? 0 : ruleDates(anchor).length;
    $("#rp-preview").textContent = rp.mode === "none" ? "" :
      (n ? `${n} dates, ${fmt(ruleDates(anchor)[0])} through ${fmt(ruleDates(anchor)[n - 1])}. Each becomes its own entry.` :
           "Pick a start date above and the dates will preview here.");
  }

  // ---------------------------------------------------------------- helpers
  // The building's day, not UTC's: after 5 PM Pacific those differ, and tonight's
  // dinner must not fall out of the counts while residents are still arriving.
  const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
  const fmt = iso => { if (!iso) return ""; const d = new Date(iso + "T12:00:00"); return `${DOW[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}`; };
  const fmtLong = iso => { if (!iso) return ""; const d = new Date(iso + "T12:00:00"); return `${["January","February","March","April","May","June","July","August","September","October","November","December"][d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`; };
  const slugify = s => s.toLowerCase().replace(/&amp;|&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const to24 = t => { const m = /(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?/i.exec(String(t || "").trim()); if (!m || !m[1]) return "0000"; let h = +m[1]; if (m[3]) { h = h % 12; if (/pm/i.test(m[3])) h += 12; } if (h > 23) return "0000"; return String(h).padStart(2, "0") + (m[2] || "00"); };
  const stem = e => `${e.Date}_${e.Slug || slugify(e.Title || "")}`;
  const cls = s => (s || "Draft").toLowerCase();

  async function api(path, opts) {
    const r = await fetch(path, Object.assign({ headers: { "content-type": "application/json" } }, opts || {}));
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || data.detail || ("Request failed: " + r.status));
    return data;
  }

  let toastTimer;
  function toast(msg, kind) {
    const t = $("#toast"); t.textContent = msg; t.className = "toast show " + (kind || "");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.className = "toast", 4200);
  }

  function go(screen) { const r = $("#s-" + screen); if (r) { r.checked = true; window.scrollTo(0, 0); } }

  // ---------------------------------------------------------------- grouping
  // One database row per occurrence. The admin shows a series as one line.
  function groups() {
    const by = new Map();
    for (const e of events) {
      const key = e.Series ? "s:" + (e.Slug || slugify(e.Title)) : "e:" + e.id;
      if (!by.has(key)) by.set(key, { key, series: !!e.Series, rows: [] });
      by.get(key).rows.push(e);
    }
    const t = today();
    const out = [];
    for (const g of by.values()) {
      g.rows.sort((a, b) => (a.Date + a.Start24).localeCompare(b.Date + b.Start24));
      g.series = g.rows.length > 1;
      g.head = g.rows.find(r => r.Date >= t) || g.rows[g.rows.length - 1];
      g.upcoming = g.rows.filter(r => r.Date >= t);
      const st = new Set(g.rows.map(r => r.Status || "Draft"));
      g.status = st.size === 1 ? [...st][0] : (st.has("Live") ? "Live" : [...st][0]);
      g.mixed = st.size > 1;
      out.push(g);
    }
    out.sort((a, b) => (a.head.Date + a.head.Start24).localeCompare(b.head.Date + b.head.Start24));
    return out;
  }

  // ---------------------------------------------------------------- events list
  function renderEvents() {
    if (evError) {
      $("#evlist").innerHTML = `<div class="erow"><div class="ecell" style="color:var(--stone)">Could not load events: ${esc(evError)}</div></div>`;
      $("#evcount").textContent = "The events could not be loaded, so nothing below is current.";
      return;
    }
    const gs = groups().filter(g => !inArchive(g));
    const badge = (t, c) => ` <span class="badge2 ${c || ""}">${esc(t)}</span>`;
    $("#evlist").innerHTML = gs.map(g => {
      const h = g.head;
      const when = g.series ? `${esc(h.Series)} &middot; next ${esc(fmt(h.Date))}` : `${esc(fmt(h.Date))}, ${esc(h.Start)}`;
      const extra = (g.series ? badge("Series") : "") + (h.Price ? badge(h.Price, "pay") : "") +
        (g.rows.some(r => r.Moved) ? badge(g.rows.filter(r => r.Moved).length + " moved") : "") +
        (h.Counted === true || h.Counted === "True" ? "" : badge("Not counted", "ext"));
      const counts = rsvpForGroup(g);
      const rsvp = h.RSVP === "None" || !h.RSVP ? "Drop in"
        : `${counts.heads}${h.Capacity && !g.series ? ` of ${h.Capacity}` : ""}${counts.wait ? ` · ${counts.wait} waiting` : ""}`;
      const kits = kitCount(masterKey(h));
      return `<div class="erow ${cls(g.status)}${g.mixed ? " live" : ""}" data-key="${esc(g.key)}">
        <div class="ecell etitle"><span class="et">${esc(h.Title)}${extra}</span><span class="esub">${esc(h.Category)} &middot; ${when}${g.series ? ` &middot; ${g.upcoming.length} upcoming` : ""}</span></div>
        <div class="ecell"><span class="pill ${cls(g.status)}">${esc(g.mixed ? "Mixed" : g.status)}</span></div>
        <div class="ecell"><span class="lbl">RSVPs</span>${rsvp}</div>
        <div class="ecell"><span class="lbl">Asset kit</span>${kits} of 6</div>
        <div class="ecell eact">${g.series ? `<button class="mini ghost" data-dates="${esc(g.key)}">${(g.upcoming.length || g.rows.length)} dates</button>` : ""}<button class="mini ghost" data-copylink="${esc(stem(h))}" title="Copies this date's page address, for emails and reminders">Link</button><button class="mini" data-edit="${esc(g.key)}">Edit</button>${g.status === "Unpublished" ? `<button class="mini ghost" data-archive="${esc(g.key)}" title="Filed away, kept for reporting">Archive</button>` : ""}</div>
      </div>
      <div class="edates" data-dates-for="${esc(g.key)}" style="display:none">${(g.upcoming.length ? g.upcoming : g.rows).map(r => `
        <div class="edrow"><span class="edwhen">${esc(fmt(r.Date))} &middot; ${esc(r.Start)}</span>
          <span class="pill ${cls(r.Status)}">${esc(r.Status || "Draft")}</span>
          ${r.Moved ? '<span class="badge2">moved</span>' : ""}
          <button class="mini ghost" data-copylink="${esc(stem(r))}" title="Copies this date's page address">Link</button>
          <button class="mini" data-editrow="${esc(g.key)}|${esc(r.id)}">Edit this date</button></div>`).join("")}${g.upcoming.length && g.rows.length > g.upcoming.length ? `
        <div class="edrow" style="color:var(--stone)">${g.rows.length - g.upcoming.length} passed date${g.rows.length - g.upcoming.length === 1 ? "" : "s"} ride with the listing, in reporting and later in the Archive.</div>` : ""}
      </div>`;
    }).join("");
    $("#evcount").textContent = `${gs.length} current listings, ${events.filter(e => e.Status === "Live" && e.Date >= today()).length} live upcoming dates. Passed and cancelled listings rest in the Archive. Nothing appears on the resident site until its status is Live.`;
  }

  // ---------------------------------------------------------------- editor
  // "RSVP closes" is a date input now; rows from before carry text like
  // "Monday, Aug 31", which converts on open so nothing is lost or retyped.
  const CUT_MON = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, june: 6,
                    jul: 7, july: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12 };
  function cutoffIso(cutoff, eventDate) {
    const c = String(cutoff || "").trim();
    if (!c) return "";
    if (/^\d{4}-\d{2}-\d{2}$/.test(c)) return c;
    const m = /([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?$/.exec(c);
    if (!m) return "";
    const mon = CUT_MON[m[1].toLowerCase().slice(0, 4)] || CUT_MON[m[1].toLowerCase().slice(0, 3)];
    if (!mon || !eventDate) return "";
    const mk = y => `${y}-${String(mon).padStart(2, "0")}-${String(m[2]).padStart(2, "0")}`;
    const y = Number(String(eventDate).slice(0, 4));
    return mk(y) > eventDate ? mk(y - 1) : mk(y);
  }

  // The form's field inputs, set from one place so the editor and the change
  // history's "Load this version" fill them identically.
  function applyFields(e) {
    const set = (id, v) => { $(id).value = v == null ? "" : v; };
    set("#f-title", e.Title); set("#f-date", e.Date); set("#f-start", e.Start); set("#f-end", e.End);
    set("#f-loc", e.Location); set("#f-host", e.Host); set("#f-series", e.Series); set("#f-cap", e.Capacity);
    set("#f-price", e.Price); set("#f-cutoff", cutoffIso(e.Cutoff, e.Date)); set("#f-desc", e.Description); set("#f-slug", e.Slug || "");
    $("#f-marquee").checked = e.Marquee === true || e.Marquee === "True";
    $("#f-teaser").checked = e.Teaser === true || e.Teaser === "True";
    $("#f-closed").checked = e.Closed === true || e.Closed === "True";
    $$("input[name=cat]").forEach((r, i) => r.checked = CATS[i] === e.Category);
    $$("input[name=rt]").forEach((r, i) => r.checked = RSVPS[i] === (e.RSVP || "None"));
    const counted = e.Counted === true || e.Counted === "True";
    $("#co-0").checked = counted; $("#co-1").checked = !counted;
    $("#f-stem").textContent = stem({ Date: e.Date, Slug: e.Slug, Title: e.Title });
  }

  // Buttons follow the row: Publish turns to Unpublish once an event is out,
  // and to Publish changes when a working copy waits; Archive only wakes from
  // Unpublished; Cancel & notify stands ready on any published event that
  // takes RSVPs, sign-ups or not.
  function refreshEdActions() {
    const row = editing && editing.row;
    const live = !!(row && row.Status === "Live");
    const draft = !!(row && row.Draft);
    $("#ed-pill").className = "pill " + cls(row ? row.Status : "Draft");
    $("#ed-pill").textContent = (row ? row.Status || "Draft" : "Draft") + (draft ? " · draft pending" : "");
    $("#ed-publish").textContent = live ? (draft ? "Publish changes" : "Unpublish") : "Publish";
    $("#ed-discard").style.display = draft ? "" : "none";
    $("#ed-archivebtn").disabled = !(row && row.Status === "Unpublished");
    $("#ed-draftnote").style.display = draft ? "" : "none";
    if (draft) $("#ed-draftnote").innerHTML =
      "<strong>A saved draft is loaded below, and it is not on the resident site.</strong> " +
      "Residents still see the published version. <strong>Publish changes</strong> applies what you see; " +
      "<strong>Discard draft</strong> lets it go.";
    $("#ed-actions-note").textContent = !row
      ? "Publish puts it on the calendar; Save draft keeps it here, unpublished, until it is ready."
      : live
        ? (draft ? "" : "Edits to a published event save as a draft first, then go out with Publish changes.")
        : row.Status === "Unpublished"
          ? "Off the calendar with its RSVPs held. Publish puts it back; Archive files it away."
          : "";
    const rsvpOn = !!(row && row.RSVP && row.RSVP !== "None");
    const edStemNow = row ? stem(row) : null;
    const hasRsvpers = !!edStemNow && rsvps.some(x => x.event_key === edStemNow);
    $("#ed-cancel").disabled = !(live && rsvpOn);
    $("#ed-cancel-note").textContent = live && rsvpOn
      ? (hasRsvpers
          ? "Cancelling pulls this date from the calendar, holds its RSVPs, and opens a note to everyone signed up."
          : "Cancelling pulls this date from the calendar. Nobody has signed up yet, so there is nobody to notify.")
      : "";
  }

  function openEditor(key, rowId) {
    const g = key ? groups().find(x => x.key === key) : null;
    const row = g ? (rowId ? g.rows.find(r => r.id === rowId) : g.head) : null;
    editing = { group: g, row };
    // A Live row with a working copy opens showing the working copy; the row
    // itself, what residents see, stays untouched underneath.
    const e = row ? (row.Draft ? { ...row, ...row.Draft } : row)
      : { Status: "Draft", Category: "Enrichment Experience", Location: "Level 39, Residents’ Club", Host: "Resident Experiences", RSVP: "Seat", Counted: true, Date: today() };
    $("#ed-title").textContent = row ? "Edit event" : "New event";
    $("#ed-sub").textContent = row ? `${e.Title} · ${fmtLong(e.Date)}` : "Fill in the essentials, save a draft, and come back to it.";
    // occurrence picker for a series
    const occ = $("#ed-occ");
    if (g && g.series) {
      occ.style.display = "";
      // Passed dates leave the picker: time already filed them. If a passed
      // date was opened anyway (an old link, the archive), it stays listed so
      // the form matches what is on screen.
      const occRows = g.upcoming.length ? [...g.upcoming] : [...g.rows];
      if (row && !occRows.includes(row)) occRows.unshift(row);
      $("#f-occ").innerHTML = occRows.map(r => `<option value="${esc(r.id)}"${r.id === e.id ? " selected" : ""}>${esc(fmt(r.Date))} · ${esc(r.Status || "Draft")}${r.Moved ? " · moved" : ""}${r.Date < today() ? " · passed" : ""}</option>`).join("");
      $("#ed-scope").style.display = "";
      $("#f-scope").checked = true;
      $("#f-scope-n").textContent = String(g.upcoming.length);
    } else { occ.style.display = "none"; $("#ed-scope").style.display = "none"; $("#f-scope").checked = false; }
    // The repeat builder creates rows, so it only shows for a brand-new event.
    // An existing series is edited through the occurrence picker above.
    $("#rp-builder").style.display = row ? "none" : "";
    if (!row) { rp = { mode: "none", days: new Set(), ord: "Last", wd: 0, end: "cal", times: 6, until: "" }; rpRefresh(); }
    applyFields(e);
    refreshEdActions();
    loadHistory(row);
    renderEditorKit();
    go("editor");
  }

  // ------------------------------------------------------------ change history
  let edHistory = [];
  async function loadHistory(row) {
    const sec = $("#ed-history-sec");
    edHistory = [];
    if (!row) { sec.style.display = "none"; return; }
    try { edHistory = (await api("/api/history?event=" + encodeURIComponent(row.id))).history || []; }
    catch (e) { edHistory = []; }
    if (editing.row !== row) return;   // the editor moved on while we fetched
    sec.style.display = edHistory.length ? "" : "none";
    $("#ed-history").innerHTML = edHistory.map((h, i) => {
      const when = new Date(h.at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
      const fields = h.changes ? Object.keys(h.changes).filter(k => k !== "Status") : [];
      const what = esc(h.action) + (fields.length && h.action !== "Created" ? " · " + fields.join(", ") : "");
      return `<div class="edrow" style="display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;padding:9px 0">`
        + `<span style="white-space:nowrap;color:var(--ink)">${esc(when)}</span>`
        + `<span style="color:var(--ink-soft)">${esc(h.who || "")}</span>`
        + `<span class="sgrow" style="color:var(--ink-soft)">${what}</span>`
        + (h.snapshot ? `<button class="mini ghost" data-histload="${i}">Load this version</button>` : "")
        + `</div>`;
    }).join("");
  }

  function loadVersion(i) {
    const h = edHistory[Number(i)];
    if (!h || !h.snapshot || !editing.row) return;
    applyFields(h.snapshot);
    const when = new Date(h.at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    toast(`Loaded the version from ${when}. Nothing changes until you publish it or save it as a draft.`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function readForm() {
    const pick = (name, list) => { const i = $$(`input[name=${name}]`).findIndex(r => r.checked); return i < 0 ? list[0] : list[i]; };
    const title = $("#f-title").value.trim();
    const f = {
      Title: title, Date: $("#f-date").value, Start: $("#f-start").value.trim(), End: $("#f-end").value.trim(),
      Start24: to24($("#f-start").value), Location: $("#f-loc").value.trim(), Host: $("#f-host").value.trim() || "Resident Experiences",
      Category: pick("cat", CATS), RSVP: pick("rt", RSVPS),
      Capacity: $("#f-cap").value ? Number($("#f-cap").value) : null, Price: $("#f-price").value.trim(),
      Series: $("#f-series").value.trim(), Cutoff: $("#f-cutoff").value.trim(), Description: $("#f-desc").value.trim(),
      Marquee: $("#f-marquee").checked, Teaser: $("#f-teaser").checked, Closed: $("#f-closed").checked,
      Counted: $("#co-0").checked, Moved: editing.row ? !!editing.row.Moved : false,
      Slug: $("#f-slug").value.trim() || slugify(title),
    };
    return f;
  }

  function validate(f) {
    if (!f.Title) return "Give the event a title.";
    if (!f.Date) return "Pick a date.";
    if (!f.Start) return "Add a start time, like 5:30 PM.";
    if (f.Status === "Live" && !f.Description && !f.Teaser)
      return "A published event needs a description, since residents will read it. Tick Coming soon to publish it without one.";
    return null;
  }

  // Which field changes ripple across a series when "apply to every upcoming occurrence" is ticked.
  const SERIES_FIELDS = ["Title", "Start", "End", "Start24", "Location", "Host", "Category", "RSVP", "Capacity", "Price", "Series", "Cutoff", "Description", "Counted", "Image", "Status", "Teaser", "Closed"];

  async function save(status) {
    const f = readForm();
    f.Status = status;
    const err = validate(f); if (err) { toast(err, "warn"); return; }
    let told = false;
    const wasLive = editing.row && editing.row.Status === "Live";
    const touchesSite = wasLive || f.Status === "Live";
    const btns = $$("#ed-actions button"); btns.forEach(b => b.disabled = true);
    try {
      if (editing.row) {
        const applyAll = editing.group && editing.group.series && $("#f-scope").checked;
        const targets = applyAll ? editing.group.upcoming : [editing.row];
        const priors = targets.map(r => ({ Date: r.Date, Start: r.Start, End: r.End, Location: r.Location, Title: r.Title, Slug: r.Slug, Status: r.Status }));
        let done = 0, failed = 0, firstErr = "";
        for (const r of targets) {
          const patch = r.id === editing.row.id ? f : Object.fromEntries(SERIES_FIELDS.map(k => [k, f[k]]));
          try {
            const upd = await api("/api/events/" + encodeURIComponent(r.id), { method: "PATCH", body: JSON.stringify(patch) });
            Object.assign(r, upd); done++;
          } catch (ex) { failed++; if (!firstErr) firstErr = ex.message; }
        }
        if (failed) { toast(`Saved ${done} of ${targets.length} dates. ${failed} failed: ${firstErr}`, "warn"); told = true; }
        else if (targets.length > 1) { toast(`Saved all ${done} upcoming dates.`); told = true; }
        const changed = [];
        targets.forEach((r, i) => {
          const o = priors[i];
          if (o.Status === "Live" && (o.Date !== r.Date || o.Start !== r.Start || o.End !== r.End || o.Location !== r.Location))
            changed.push({ o, n: r });
        });
        if (changed.length) { notifyEventChange(changed); told = true; }
      } else if (rp.mode !== "none") {
        const dates = ruleDates(f.Date);
        if (!dates.length) { toast("The repeat rule produces no dates. Check the start date.", "warn"); return; }
        let made = 0;
        for (const d of dates) {
          const created = await api("/api/events", { method: "POST", body: JSON.stringify({ ...f, Date: d }) });
          events.push(created); made++;
        }
        editing.row = events[events.length - 1];
        toast(`Created ${made} dates of ${f.Title}.`); told = true;
      } else {
        const created = await api("/api/events", { method: "POST", body: JSON.stringify(f) });
        events.push(created); editing.row = created;
      }
      renderAll();
      if (touchesSite && status.publish) {
        if (!told) toast("Saved. Publishing the calendar, live in a couple of minutes.");
        api("/api/publish", { method: "POST" }).then(r => toast(r.note || "Published.")).catch(e => toast("Saved, but publishing failed: " + e.message, "warn"));
      } else if (!told) {
        toast(f.Status === "Draft" ? "Saved as a draft. Nothing changes on the resident site." : "Saved.");
      }
      go("events");
    } catch (e) { toast(e.message, "warn"); }
    finally { btns.forEach(b => b.disabled = false); refreshEdActions(); }
  }

  // A published event's edits live in a working copy: residents keep seeing
  // the published version until Publish changes applies it. With apply-to-all
  // ticked, the copy rides to every upcoming Live date of the series.
  async function saveWorkingCopy() {
    const f = readForm();
    if (!f.Title) { toast("Give the event a title.", "warn"); return; }
    const applyAll = editing.group && editing.group.series && $("#f-scope").checked;
    const targets = applyAll ? editing.group.upcoming.filter(r => r.Status === "Live") : [editing.row];
    const btns = $$("#ed-actions button"); btns.forEach(b => b.disabled = true);
    try {
      for (const r of targets) {
        const copy = r.id === editing.row.id ? f
          : Object.fromEntries(SERIES_FIELDS.filter(k => k !== "Status").map(k => [k, f[k]]));
        const upd = await api("/api/events/" + encodeURIComponent(r.id),
          { method: "PATCH", body: JSON.stringify({ __draft: copy }) });
        Object.assign(r, upd);
      }
      toast(targets.length > 1
        ? `Draft saved on ${targets.length} dates. Residents still see the published version.`
        : "Draft saved. Residents see the published version until you publish the changes.");
    } catch (e) { toast(e.message, "warn"); }
    finally { btns.forEach(b => b.disabled = false); refreshEdActions(); }
  }

  async function discardWorkingCopy() {
    const row = editing && editing.row; if (!row || !row.Draft) return;
    if (!confirm("Let the saved draft go? The editor returns to what residents see.")) return;
    const applyAll = editing.group && editing.group.series && $("#f-scope").checked;
    const targets = applyAll ? editing.group.upcoming.filter(r => r.Draft) : [row];
    try {
      for (const r of targets) {
        const upd = await api("/api/events/" + encodeURIComponent(r.id),
          { method: "PATCH", body: JSON.stringify({ __draft: null }) });
        Object.assign(r, upd);
      }
      openEditor(editing.group ? editing.group.key : null, row.id);
      toast("Draft discarded. This is what residents see.");
    } catch (e) { toast(e.message, "warn"); }
  }

  // The three verb buttons. Publish is the only road onto the calendar,
  // Unpublish the only quiet road off it, and Archive waits behind Unpublish
  // on purpose, so nothing leaves the calendar and the records in one motion.
  function edPublishClick() {
    const row = editing && editing.row;
    if (row && row.Status === "Live" && !row.Draft) { save("Unpublished"); return; }
    save("Live");
  }
  function edSaveDraftClick() {
    const row = editing && editing.row;
    if (row && row.Status === "Live") { saveWorkingCopy(); return; }
    save(row ? row.Status || "Draft" : "Draft");
  }
  function edArchiveClick() {
    const row = editing && editing.row; if (!row || row.Status !== "Unpublished") return;
    if (!confirm(`Archive "${row.Title}"? It is filed away and stays in reporting; publishing it again walks it back out.`)) return;
    save("Archived");
  }

  // ---------------------------------------------------- settings: window + lists
  // Locations and hosts are named once on the Settings screen and offered in
  // the event editor's dropdowns; the calendar window dials live on Events.
  const DEFAULT_LOCATIONS = ["Level 39, Residents’ Club", "Level 7 Terrace", "Lobby", "Fitness Center"];
  const DEFAULT_HOSTS = ["Resident Experiences", "181 Fremont Residences Association", "The Board",
                         "Leo Ramirez", "Leigh Anne", "Carley-Ann", "Scott"];
  let listSettings = { locations: DEFAULT_LOCATIONS.slice(), hosts: DEFAULT_HOSTS.slice() };

  function renderListSettings() {
    const chip = (v, attr, i) => `<span class="setchip">${esc(v)}<button class="x" ${attr}="${i}" title="Remove from the list">&times;</button></span>`;
    const l = $("#set-locs"), h = $("#set-hosts");
    if (l) l.innerHTML = listSettings.locations.map((v, i) => chip(v, "data-delloc", i)).join("")
      || '<span class="hint">Nothing listed yet.</span>';
    if (h) h.innerHTML = listSettings.hosts.map((v, i) => chip(v, "data-delhost", i)).join("")
      || '<span class="hint">Nothing listed yet.</span>';
    const dl = document.getElementById("locs"), dh = document.getElementById("hosts");
    if (dl) dl.innerHTML = listSettings.locations.map(v => `<option value="${esc(v)}">`).join("");
    if (dh) dh.innerHTML = listSettings.hosts.map(v => `<option value="${esc(v)}">`).join("");
  }

  async function saveLists() {
    renderListSettings();
    try {
      await api("/api/settings", { method: "PUT", body: JSON.stringify(
        { locations: listSettings.locations, hosts: listSettings.hosts }) });
    } catch (e) { toast(e.message, "warn"); }
  }

  async function loadWindow() {
    try {
      const w = await api("/api/settings");
      $("#w-weeks").value = String(w.detail_weeks);
      $("#w-months").value = String(w.horizon_months);
      if (Array.isArray(w.locations) && w.locations.length) listSettings.locations = w.locations;
      if (Array.isArray(w.hosts) && w.hosts.length) listSettings.hosts = w.hosts;
    } catch (e) {}   // the desk tier has no events screen, and no business here
    renderListSettings();
  }
  async function saveWindow(btn) {
    btn.disabled = true;
    try {
      await api("/api/settings", { method: "PUT", body: JSON.stringify({
        detail_weeks: Number($("#w-weeks").value), horizon_months: Number($("#w-months").value) }) });
      if (status.publish) {
        toast("Window saved. The calendar is rebuilding with it, live in a couple of minutes.");
        api("/api/publish", { method: "POST" }).catch(() => {});
      } else toast("Window saved. It takes effect at the next publish.");
    } catch (e) { toast(e.message, "warn"); }
    finally { btn.disabled = false; }
  }

  async function archiveGroup(key) {
    const g = groups().find(x => x.key === key); if (!g) return;
    const n = g.upcoming.length;
    if (!confirm(n > 1 ? `Archive all ${n} upcoming dates of "${g.head.Title}"? They leave the calendar and stay in reporting.` : `Archive "${g.head.Title}"? It leaves the calendar and stays in reporting.`)) return;
    try {
      let touched = false;
      for (const r of (n ? g.upcoming : [g.head])) { if (r.Status === "Live") touched = true; Object.assign(r, await api("/api/events/" + encodeURIComponent(r.id), { method: "PATCH", body: JSON.stringify({ Status: "Archived" }) })); }
      renderAll();
      if (touched && status.publish) { api("/api/publish", { method: "POST" }).catch(() => {}); toast("Archived. The calendar updates in a couple of minutes."); }
      else toast("Archived.");
    } catch (e) { toast(e.message, "warn"); }
  }

  // ---------------------------------------------------------------- dashboard
  function bars(rows, key, total) {
    const top = Math.max(1, ...rows.map(r => r[key]));
    return rows.map(r => `<div class="srow"><span class="slab">${esc(r.label)}</span><span class="strack"><span class="sfill" style="width:${Math.round(r[key] / top * 100)}%"></span></span><span class="sval">${r[key]}${total ? `<small> · ${Math.round(r[key] / total * 100)}%</small>` : ""}</span></div>`).join("");
  }

  function dayChart(byDay) {
    if (!byDay.length) return '<div class="nodata">Nothing yet. Figures begin the day the site goes live.</div>';
    const W = 720, H = 150, pad = 4, n = byDay.length, bw = Math.max(2, (W - pad * 2) / n - 2);
    const top = Math.max(1, ...byDay.map(d => d.visits));
    let s = `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="Visits per day">`;
    byDay.forEach((d, i) => {
      const h = Math.round((d.visits / top) * (H - 30)); const x = pad + i * ((W - pad * 2) / n); const y = H - 22 - h;
      const dt = new Date(d.date + "T12:00:00");
      s += `<rect x="${x.toFixed(1)}" y="${y}" width="${bw.toFixed(1)}" height="${h}" rx="1" class="${dt.getDay() === 2 || dt.getDay() === 4 ? "bar hot" : "bar"}"><title>${esc(fmt(d.date))}: ${d.visits} visits, ${d.views} views</title></rect>`;
      if (n <= 31 ? (i % 5 === 0) : (i % 15 === 0)) s += `<text x="${(x + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle" class="tick">${MONTHS[dt.getMonth()]} ${dt.getDate()}</text>`;
    });
    return s + "</svg>";
  }

  function renderDash() {
    const t = today();
    // Time-aware like the resident site's Next Event tile: once an event has
    // started, the dashboard's Next up and Coming up move on to what is ahead.
    const nowHM = new Date().toTimeString().slice(0, 5).replace(":", "");
    const live = events.filter(e => e.Status === "Live");
    const upcoming = live.filter(e => (e.Date > t || (e.Date === t && (e.Start24 || "2359") > nowHM))
        && e.Category !== "Board Meeting")
      .sort((a, b) => (a.Date + a.Start24).localeCompare(b.Date + b.Start24));
    const a = analytics || { pageviews: 0, visits: 0, byDay: [], bySource: [], byDevice: [], sample: false, configured: false };
    $("#dash-period").textContent = `Last ${days} days · ${UNITS} occupied units`;
    $("#dash-note").style.display = a.configured ? "none" : "";
    $("#dash-note").innerHTML = a.sample
      ? "<strong>Sample figures.</strong> This is what the dashboard looks like with a month of traffic. Real numbers replace them the day the site goes live."
      : "<strong>Analytics not connected yet.</strong> Traffic figures begin once Cloudflare Web Analytics is switched on for the site.";
    const perUnit = a.visits ? (a.visits / UNITS).toFixed(1) : "0";
    const sums = rsvpSummary();
    const heads = sums.reduce((s, x) => s + x.heads, 0), waiting = sums.reduce((s, x) => s + x.waitHeads, 0);
    $("#kpis").innerHTML = [
      ["Visits", a.visits, `${a.pageviews} page views · ${perUnit} per unit`],
      ["Busiest day", a.byDay.length ? Math.max(...a.byDay.map(d => d.visits)) : 0, a.byDay.length ? "visits on " + fmt(a.byDay.reduce((m, d) => d.visits > m.visits ? d : m).date) : "no traffic yet"],
      ["RSVPs ahead", heads, waiting ? `${waiting} on waitlists` : "confirmed heads for upcoming dates"],
      ["Upcoming dates", upcoming.length, `${new Set(upcoming.map(e => e.Slug)).size} live listings on the calendar`],
      ["Next up", upcoming[0] ? fmt(upcoming[0].Date).replace(/^\w+, /, "") : "None", upcoming[0] ? `${upcoming[0].Title}, ${upcoming[0].Start}` : "Nothing scheduled"],
    ].map(([k, v, n]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${esc(v)}</div><div class="n">${esc(n)}</div></div>`).join("");
    $("#daychart").innerHTML = dayChart(a.byDay);
    $("#sources").innerHTML = a.bySource.length ? bars(a.bySource, "visits", a.visits) : '<div class="nodata">Sources appear once the QR standees and the weekly email are in use.</div>';
    const devs = a.byDevice.map(d => ({ label: { mobile: "Phone", tablet: "iPad or tablet", desktop: "Computer" }[d.device] || d.device, views: d.views }));
    $("#devices").innerHTML = devs.length ? bars(devs, "views", devs.reduce((s, d) => s + d.views, 0)) : '<div class="nodata">No device data yet.</div>';
    // Board meetings live on their own page, not the resident calendar, so the
    // category chart keeps to what residents actually see.
    const byCat = CATS.filter(c => c !== "Board Meeting").map(c => ({ label: c, n: upcoming.filter(e => e.Category === c).length })).filter(c => c.n);
    $("#bycat").innerHTML = bars(byCat, "n");
    renderRsvps();
    $("#nextlist").innerHTML = upcoming.slice(0, 6).map(e => `<div class="srow"><span class="slab">${esc(fmt(e.Date))}</span><span class="sgrow" style="font-size:15px;color:var(--ink)">${esc(e.Title)}</span><span class="sval" style="white-space:nowrap">${esc(e.Start)}</span></div>`).join("") || '<div class="nodata">Nothing scheduled.</div>';
    $$("#period button").forEach(b => b.classList.toggle("on", Number(b.dataset.days) === days));
  }

  // ---------------------------------------------------------------- rsvps
  // One RSVP row per person per event; heads = the count each row carries.
  // The summary is derived state, computed once and cached until rsvps change,
  // since the events list asks for it per row.
  let rsvpCache = null;
  function rsvpSummaries() {
    if (rsvpCache) return rsvpCache;
    const t = today();
    const by = new Map();
    for (const r of rsvps) {
      if (r.status === "Cancelled") continue;
      if (!by.has(r.event_key)) by.set(r.event_key, {
        key: r.event_key, date: r.event_date, title: r.event_title, type: r.rsvp_type,
        parties: 0, heads: 0, waitParties: 0, waitHeads: 0, rows: [],
      });
      const s = by.get(r.event_key);
      s.rows.push(r);
      if (r.status === "Waitlist") { s.waitParties++; s.waitHeads += r.count; }
      else { s.parties++; s.heads += r.count; }
    }
    const all = [...by.values()];
    rsvpCache = {
      upcoming: all.filter(s => s.date >= t).sort((a, b) => a.date.localeCompare(b.date)),
      past: all.filter(s => s.date < t).sort((a, b) => b.date.localeCompare(a.date)),
    };
    return rsvpCache;
  }
  function rsvpSummary() { return rsvpSummaries().upcoming; }

  // When a Live event with sign-ups moves or is cancelled, everyone affected
  // deserves one email naming the change. The addresses come from the RSVPs;
  // the draft opens BCC'd in the operator's own mail program, one click to send.
  function rsvperEmails(stems) {
    const set = new Set();
    for (const r of rsvps) if (stems.has(r.event_key) && r.email) set.add(r.email.toLowerCase());
    return [...set];
  }

  function openBccDraft(subject, body, emails) {
    window.location.href = "mailto:?bcc=" + encodeURIComponent(emails.join(","))
      + "&subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
  }

  function notifyEventChange(changed) {
    const oldStems = new Set(changed.map(c => stem(c.o)));
    const affected = rsvps.filter(r => oldStems.has(r.event_key));
    if (!affected.length) return;
    const emails = rsvperEmails(oldStems);
    // the local rsvp rows follow the server's re-addressing, so counts stay true
    for (const rv of rsvps) {
      const c = changed.find(x => stem(x.o) === rv.event_key);
      if (c) { rv.event_key = stem(c.n); rv.event_date = c.n.Date; rv.event_title = c.n.Title; }
    }
    rsvpCache = null;
    if (!emails.length) {
      toast("Saved. Those signed up have no email on file, so a call or a word at the desk carries the change.");
      return;
    }
    const lines = changed.map(c => {
      const bits = [];
      if (c.o.Date !== c.n.Date || c.o.Start !== c.n.Start || c.o.End !== c.n.End)
        bits.push(`now ${fmt(c.n.Date)}, ${c.n.Start}${c.n.End ? " to " + c.n.End : ""} (was ${fmt(c.o.Date)}, ${c.o.Start})`);
      if (c.o.Location !== c.n.Location) bits.push(`now in ${c.n.Location}`);
      return `${c.n.Title}: ${bits.join("; ")}`;
    });
    const first = changed[0].n;
    const body = `Hello,\n\nA change to an event you RSVP'd for:\n\n${lines.join("\n")}\n\n`
      + `If you added it to your calendar, open the event and tap Add to My Calendar again; the entry updates itself in place. `
      + `If you subscribe to the calendar, it updates on its own.\n\n`
      + `https://181residents.com/rsvp/${stem(first)}\n\nWarmly,\nResident Experiences\n181 Fremont`;
    toast("Saved. A note to everyone signed up is opening; send it so nobody arrives at the wrong hour.");
    openBccDraft(`Update: ${first.Title}`, body, emails);
  }

  function cancelEvent() {
    const row = editing && editing.row; if (!row) return;
    const st = stem(row);
    if (!confirm(`Cancel "${row.Title}" on ${fmt(row.Date)}? It leaves the calendar, its RSVPs stay held, and a note opens to everyone signed up.`)) return;
    api("/api/events/" + encodeURIComponent(row.id), { method: "PATCH", body: JSON.stringify({ Status: "Unpublished" }) })
      .then(upd => {
        Object.assign(row, upd);
        renderAll();
        if (status.publish) api("/api/publish", { method: "POST" }).catch(() => {});
        const emails = rsvperEmails(new Set([st]));
        if (emails.length) {
          const body = `Hello,\n\nWith our apologies, ${row.Title} on ${fmt(row.Date)} is cancelled.\n\n`
            + `If you added it to your calendar, kindly remove that entry. If you subscribe to the calendar, it disappears on its own.\n\n`
            + `Warmly,\nResident Experiences\n181 Fremont`;
          openBccDraft(`Cancelled: ${row.Title}, ${fmt(row.Date)}`, body, emails);
          toast("Cancelled. The note to everyone signed up is opening; send it and nobody shows up to an empty room.");
        } else {
          toast("Cancelled and pulled from the calendar. Those signed up have no email on file; a call closes the loop.");
        }
        go("events");
      })
      .catch(e => toast(e.message, "warn"));
  }

  // A change made on someone's behalf deserves a word to them. No mail service
  // exists in this stack by design, so the word travels the same way the code
  // cards do: a pre-written email opens from the operator's own mailbox.
  function notifyRsvp(r, kind, extra) {
    if (!r.email) {
      toast(`No email on file for ${r.name}${r.unit ? " · " + r.unit : ""}. A call or a word at the desk closes the loop.`);
      return;
    }
    const when = fmt(r.event_date);
    const what = r.rsvp_type === "guest"
      ? (r.count === 1 ? "1 outside guest" : `${r.count} outside guests`)
      : (r.count === 1 ? "a party of 1" : `a party of ${r.count}`);
    let line;
    if (kind === "cancel") line = `As requested, we have taken you off the list for ${r.event_title} on ${when}. If plans change again, you are always welcome back while there is room.`;
    else if (kind === "confirm") line = `Good news: room opened up for ${r.event_title} on ${when}, and your spot is confirmed, ${what}.`;
    else if (kind === "moved") line = `As requested, your RSVP has moved: it now stands for ${r.event_title} on ${when}, ${what}${r.status === "Waitlist" ? ", currently on the waitlist" : ""}. It was for ${extra}.`;
    else line = `As requested, your RSVP for ${r.event_title} on ${when} is updated: ${what}${r.status === "Waitlist" ? ", currently on the waitlist" : ""}.`;
    const href = "mailto:" + encodeURIComponent(r.email)
      + "?subject=" + encodeURIComponent(`Your RSVP for ${r.event_title}, ${when}`)
      + "&body=" + encodeURIComponent(`Hello ${r.name},\n\n${line}\n\nWarmly,\nResident Experiences\n181 Fremont`);
    window.location.href = href;
  }

  function patchRsvp(id, body, after) {
    api("/api/rsvps/" + id, { method: "PATCH", body: JSON.stringify(body) })
      .then(u => {
        const row = rsvps.find(x => String(x.id) === String(u.id));
        if (row) Object.assign(row, { status: u.status, count: u.count, names: u.names });
        rsvpCache = null;
        renderDash(); renderEvents();
        if (after) after(row);
      })
      .catch(e => toast(e.message, "warn"));
  }

  // The add card doubles as the RSVP editor, the same pattern as residents and
  // reservations: Edit on a row fills it with the person held fixed, and the
  // event select means a slip of the hand at booking time is two clicks to fix.
  let editingRsvp = null;
  function exitRsvpEdit() {
    editingRsvp = null;
    $("#ar-person").disabled = false;
    $("#ar-head").style.display = "none";
    const sb = document.querySelector("[data-savearsvp]");
    if (sb) sb.textContent = "Save RSVP";
    $("#ar-names").value = "";
    $("#ar-card").style.display = "none";
  }

  function openAddRsvp() {
    const card = $("#ar-card");
    if (editingRsvp) exitRsvpEdit();
    else if (card.style.display !== "none") { card.style.display = "none"; return; }
    const people = residents.filter(p => p.status === "Active")
      .sort((a, b) => (a.unit + a.name).localeCompare(b.unit + b.name, undefined, { numeric: true }));
    $("#ar-person").innerHTML = people.map(p => `<option value="${p.id}">${esc(p.label)}</option>`).join("");
    const t = today();
    const evs = events.filter(e => e.Status === "Live" && e.Date >= t && e.RSVP && e.RSVP !== "None")
      .sort((a, b) => (a.Date + a.Start24).localeCompare(b.Date + b.Start24));
    $("#ar-event").innerHTML = evs.map(e => `<option value="${esc(stem(e))}">${esc(fmt(e.Date))} · ${esc(e.Title)}${e.RSVP === "Guest count" ? " (outside guests)" : ""}</option>`).join("");
    if (!people.length || !evs.length) { toast("Needs at least one active person and one live upcoming event.", "warn"); return; }
    card.style.display = "";
  }

  function openRsvpEdit(row) {
    exitRsvpEdit();
    openAddRsvp();
    if ($("#ar-card").style.display === "none") return;
    editingRsvp = row;
    $("#ar-person").value = String(row.resident_id);
    $("#ar-person").disabled = true;
    if (![...$("#ar-event").options].some(o => o.value === row.event_key)) {
      $("#ar-event").insertAdjacentHTML("afterbegin",
        `<option value="${esc(row.event_key)}">${esc(fmt(row.event_date))} · ${esc(row.event_title)} (current)</option>`);
    }
    $("#ar-event").value = row.event_key;
    $("#ar-count").value = String(Math.min(6, Math.max(1, row.count)));
    $("#ar-names").value = row.names || "";
    $("#ar-head").style.display = "";
    $("#ar-head").textContent = `Editing ${row.name}'s RSVP · now ${row.event_title}, ${fmt(row.event_date)}`;
    const sb = document.querySelector("[data-savearsvp]");
    if (sb) sb.textContent = "Save Changes";
    $("#ar-card").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveRsvpEdit() {
    const row = editingRsvp; if (!row) return;
    const newKey = $("#ar-event").value;
    const count = Number($("#ar-count").value);
    const names = $("#ar-names").value.trim();
    if (newKey === row.event_key) {
      patchRsvp(row.id, { count, names }, updated => {
        exitRsvpEdit();
        toast("Updated. A note to the resident is opening; send it so the change is in writing.");
        if (updated) notifyRsvp(updated, "update");
      });
      return;
    }
    // A move books the new event first, so its own capacity and waitlist rules
    // give the honest answer; only then is the old seat released.
    try {
      const d = await api("/api/rsvps", { method: "POST",
        body: JSON.stringify({ resident_id: row.resident_id, event_key: newKey, count, names }) });
      await api("/api/rsvps/" + row.id, { method: "PATCH", body: JSON.stringify({ status: "Cancelled" }) });
      rsvps = rsvps.filter(x => String(x.id) !== String(row.id) && String(x.id) !== String(d.rsvp.id));
      rsvps.push(d.rsvp);
      rsvpCache = null; renderDash(); renderEvents();
      const oldWhat = `${row.event_title} on ${fmt(row.event_date)}`;
      exitRsvpEdit();
      toast(d.rsvp.status === "Waitlist"
        ? `Moved. ${d.rsvp.name} is on the new event's waitlist: it is full or others are ahead in line.`
        : `Moved. ${d.rsvp.name} is confirmed on the new event.`);
      if (d.rsvp.email && confirm(`Open a note to ${d.rsvp.name} about the move? It sends from your own mailbox.`))
        notifyRsvp(d.rsvp, "moved", oldWhat);
    } catch (e) { toast(e.message, "warn"); }
  }

  function saveAddRsvp() {
    const body = {
      resident_id: Number($("#ar-person").value),
      event_key: $("#ar-event").value,
      count: Number($("#ar-count").value),
      names: $("#ar-names").value.trim(),
    };
    api("/api/rsvps", { method: "POST", body: JSON.stringify(body) })
      .then(d => {
        const i = rsvps.findIndex(x => String(x.id) === String(d.rsvp.id));
        if (i >= 0) rsvps[i] = d.rsvp; else rsvps.push(d.rsvp);
        rsvpCache = null;
        renderDash(); renderEvents();
        $("#ar-names").value = "";
        $("#ar-card").style.display = "none";
        toast(d.rsvp.status === "Waitlist"
          ? `Saved. ${d.rsvp.name} is on the waitlist: the event is full or others are ahead in line.`
          : `Saved. ${d.rsvp.name} is confirmed.`);
      })
      .catch(e => toast(e.message, "warn"));
  }

  function rsvpForGroup(g) {
    const keys = new Set(g.upcoming.map(stem));
    let heads = 0, wait = 0;
    for (const s of rsvpSummary()) if (keys.has(s.key)) { heads += s.heads; wait += s.waitHeads; }
    return { heads, wait };
  }

  let pastRsvpsOpen = false;
  function renderRsvps() {
    const box = $("#rsvplist"); if (!box) return;
    const { upcoming: sums, past } = rsvpSummaries();
    if (!sums.length && !past.length) {
      box.innerHTML = '<div class="nodata">Nothing yet. Figures begin with the first RSVP made on the site.</div>';
      return;
    }
    const ev = key => events.find(e => stem(e) === key);
    let html = sums.length ? "" : '<div class="nodata">Nothing ahead. Figures begin with the next RSVP made on the site.</div>';
    html += sums.map(s => {
      const e = ev(s.key);
      const cap = e && e.Capacity ? ` of ${e.Capacity}` : "";
      const what = s.type === "guest" ? `${s.heads} outside guests` : `${s.heads}${cap} ${s.type === "paid" ? "seats" : "going"}`;
      const wait = s.waitHeads ? ` &middot; ${s.waitHeads} waitlisted` : "";
      const units = new Set(s.rows.map(r => r.unit).filter(Boolean));
      const dupUnit = units.size < s.rows.filter(r => r.unit).length;
      return `<div class="srow" style="cursor:pointer" data-rsvpkey="${esc(s.key)}"><span class="slab">${esc(fmt(s.date))}</span>
        <span class="sgrow" style="font-size:15px;color:var(--ink)">${esc(s.title)}${dupUnit ? ' <span class="flagmany" title="One unit holds more than one RSVP for this event">unit twice</span>' : ""}</span>
        <span class="sval">${what}${wait}</span></div>
        <div class="card" data-rsvpdetail="${esc(s.key)}" style="display:none;margin:4px 0 10px">
        ${s.rows.map(r => `<div class="srow"><span class="slab">${esc(r.unit || "Role")} &middot; ${esc(r.name)}</span>
          <span class="sgrow" style="font-size:14px;color:var(--ink-soft)">${r.status === "Waitlist" ? "Waitlist" : (s.type === "guest" ? `${r.count} guest${r.count === 1 ? "" : "s"}` : `party of ${r.count}`)}${r.names ? ` &middot; ${esc(r.names)}` : ""}</span>
          <span class="sval" style="font-size:12px;color:var(--stone)">${esc((r.created || "").slice(0, 10))}</span>
          <span class="eact">
          ${r.status === "Waitlist" ? `<button class="mini" data-wconfirm="${r.id}" title="Give this party the freed seats, then let them know">Confirm seats</button>` : ""}
          <button class="mini ghost" data-redit="${r.id}" title="Change the party, the names, or move it to another event">Edit</button>
          <button class="mini ghost" data-rcancel="${r.id}" title="Take them off the list; you choose whether a note goes">Cancel</button>
          </span></div>`).join("")}
        </div>`;
    }).join("");
    // Passed events keep their lists, folded at the foot: who held seats is the
    // survey and thank-you audience, and Email guests opens the BCC draft.
    if (past.length) {
      html += `<div class="srow" style="cursor:pointer" data-pastchev>
        <span class="sgrow" style="color:var(--stone)">Past events &middot; ${past.length}</span>
        <span class="sval" style="color:var(--stone)">${pastRsvpsOpen ? "Hide" : "Show"}</span></div>
      <div id="pastrsvps" style="${pastRsvpsOpen ? "" : "display:none"}">
        ${past.map(s => {
          const went = s.type === "guest" ? `${s.heads} outside guests` : `${s.heads} confirmed`;
          const wait = s.waitParties ? ` &middot; ${s.waitParties} stayed waitlisted` : "";
          const mails = new Set(s.rows.filter(r => r.status !== "Waitlist" && r.email).map(r => r.email.toLowerCase()));
          const dark = s.rows.filter(r => r.status !== "Waitlist" && !r.email).length;
          return `<div class="srow" style="cursor:pointer" data-rsvpkey="${esc(s.key)}"><span class="slab">${esc(fmt(s.date))}</span>
            <span class="sgrow" style="font-size:15px;color:var(--ink)">${esc(s.title)}</span>
            <span class="sval">${went}${wait}</span></div>
            <div class="card" data-rsvpdetail="${esc(s.key)}" style="display:none;margin:4px 0 10px">
            <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px">
              ${mails.size ? `<button class="mini" data-pastmail="${esc(s.key)}" title="A BCC draft to everyone who held seats, for the thank-you or the survey">Email guests &middot; ${mails.size}</button>` : ""}
              ${dark ? `<span class="hint" style="margin:0">${dark} ${dark === 1 ? "party has" : "parties have"} no email on file.</span>` : ""}
            </div>
            ${s.rows.map(r => `<div class="srow"><span class="slab">${esc(r.unit || "Role")} &middot; ${esc(r.name)}</span>
              <span class="sgrow" style="font-size:14px;color:var(--ink-soft)">${r.status === "Waitlist" ? "Waitlisted" : (s.type === "guest" ? `${r.count} guest${r.count === 1 ? "" : "s"}` : `party of ${r.count}`)}${r.names ? ` &middot; ${esc(r.names)}` : ""}</span>
              <span class="sval" style="font-size:12px;color:var(--stone)">${esc(r.email || "no email")}</span></div>`).join("")}
            </div>`;
        }).join("")}
      </div>`;
    }
    box.innerHTML = html;
  }
  function emailPastGuests(key) {
    const s = rsvpSummaries().past.find(x => x.key === key);
    if (!s) return;
    const emails = [...new Set(s.rows.filter(r => r.status !== "Waitlist" && r.email).map(r => r.email.toLowerCase()))];
    if (!emails.length) { toast("Nobody who held seats has an email on file.", "warn"); return; }
    openBccDraft(`${s.title} at 181 Fremont`,
      `Hello,\n\nThank you for joining us for ${s.title}. We would love to hear how it was for you.\n\n\nWarmly,\nResident Experiences\n181 Fremont`,
      emails);
  }

  // ---------------------------------------------------------------- residents
  function renderResidents() {
    const box = $("#reslist"); if (!box) return;
    const roles = residents.filter(r => r.kind === "role");
    const people = residents.filter(r => r.kind !== "role");
    const byUnit = new Map();
    for (const p of people) {
      if (!byUnit.has(p.unit)) byUnit.set(p.unit, []);
      byUnit.get(p.unit).push(p);
    }
    const units = [...byUnit.keys()].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    const active = people.filter(p => p.status === "Active" && !p.expired);
    $("#rescount").textContent = `${people.length} people across ${units.length} units, ${active.length} with working codes, plus ${roles.length} role account${roles.length === 1 ? "" : "s"}.`;

    const pill = p => p.status !== "Active" ? '<span class="pill archived">Disabled</span>'
      : p.expired ? '<span class="pill unpublished">Ended</span>'
      : p.ends ? `<span class="pill draft">Ends ${esc(p.ends)}</span>`
      : '<span class="pill live">Active</span>';
    const mailHref = p => "mailto:" + encodeURIComponent(p.email)
      + "?subject=" + encodeURIComponent("Your 181 Fremont resident code")
      + "&body=" + encodeURIComponent(`Hello ${p.name},\n\nYour personal code for 181residents.com is:\n\n    ${p.code}\n\nTap RSVP on any event, enter the code once, and you stay signed in for a month on that device. Your RSVPs and notes to us save under your name.\n\nWarmly,\nResident Experiences\n181 Fremont`);
    // Three buttons, no more: the two the desk reaches for at 10 pm, and Edit,
    // which opens everything else (end dates, standing, disable, delete) in the
    // card above, one deliberate step away from the row.
    // Every row carries the same three controls, so the columns line up whether
    // or not an email is on file: an empty mailbox just shades its button.
    const mailBtn = p => p.email && p.status === "Active"
      ? `<a class="mini" href="${mailHref(p)}" title="Opens your own mail app with the code written out">Email code</a>`
      : `<span class="mini off" title="${p.status !== "Active" || p.expired ? "Available once the code is active again" : "No email on file. Edit adds one."}">Email code</span>`;
    const row = p => `<div class="rrow${p.status !== "Active" || p.expired ? " off" : ""}">
      <span class="rname">${esc(p.name)}${p.email ? `<em>${esc(p.email)}</em>` : ""}</span>
      <span><span class="rcode">${esc(p.code)}</span></span>
      <span class="rpills">${pill(p)}${p.tenure === "tenant" ? '<span class="pill tenant">Tenant</span>' : ""}</span>
      <span class="eact">
        ${mailBtn(p)}
        <button class="mini" data-rotate="${p.id}" title="A fresh code; the old one stops working everywhere">Rotate</button>
        <button class="mini ghost" data-resedit="${p.id}" title="Name, email, unit, tenant, end date, disable, delete">Edit</button>
      </span></div>`;
    // Unit cards fold. A search narrows to the households that match and opens
    // them; with nothing typed, cards keep whatever open state they were left
    // in, role accounts leading and open by default.
    const q = resFilter.trim().toLowerCase();
    const matches = p => !q || `${p.name} ${p.email} ${p.unit} ${p.label}`.toLowerCase().includes(q);
    const card = (head, rows, cls, key) => {
      if (q && !rows.some(matches)) return "";
      const open = q || openUnits.has(key);
      return `<div class="ucard${open ? " open" : ""}">
        <div class="uhead${cls ? " " + cls : ""}" data-uchev="${esc(key)}"><span class="chev">&#8250;</span>${head}<span class="ucount">${rows.length}</span></div>
        <div class="ubody">${rows.map(row).join("")}</div></div>`;
    };

    // Role accounts always lead, in their own dress, so staff never reads as a unit.
    let html = "";
    if (roles.length) html += card("Role accounts", roles, "role", "__roles");
    html += units.map(u => {
      const rows = byUnit.get(u);
      const activeCodes = rows.filter(p => p.status === "Active" && !p.expired).length;
      const flag = activeCodes > 4 ? ` <span class="flagmany" title="More than four working codes on one unit is worth a look">${activeCodes} codes</span>` : "";
      return card(`Unit ${esc(u)}${flag}`, rows, "", u);
    }).join("");
    if (!people.length && !roles.length) html = '<div class="nodata" style="padding:20px">Nobody yet. Add people above, or paste the whole building at once.</div>';
    else if (q && !html) html = `<div class="nodata" style="padding:20px">Nobody matches &ldquo;${esc(resFilter.trim())}&rdquo;.</div>`;
    box.innerHTML = html;
  }

  async function loadResidents() {
    try { const d = await api("/api/residents"); residents = d.residents; } catch (e) {
      residents = [];
      renderResidents();
      $("#rescount").textContent = "Could not load residents: " + e.message;
      return;
    }
    renderResidents();
  }

  async function addResident() {
    const isRole = $("#r-role").checked;
    const body = {
      kind: isRole ? "role" : "resident",
      unit: $("#r-unit").value.trim(), name: $("#r-name").value.trim(),
      email: $("#r-email").value.trim(), ends: $("#r-ends").value,
      tenure: $("#r-tenure").value,
    };
    try {
      const d = await api("/api/residents", { method: "POST", body: JSON.stringify(body) });
      residents.push(...d.residents); renderResidents();
      ["#r-unit", "#r-name", "#r-email", "#r-ends", "#r-tenure"].forEach(s => $(s).value = "");
      $("#r-role").checked = false;
      toast(`Added ${d.residents[0].label}. Their code: ${d.residents[0].code}`);
    } catch (e) { toast(e.message, "warn"); }
  }

  async function addBulk() {
    const bulk = $("#r-bulk").value;
    if (!bulk.trim()) { toast("Paste at least one line first: unit, name, email.", "warn"); return; }
    try {
      const d = await api("/api/residents", { method: "POST", body: JSON.stringify({ bulk }) });
      residents.push(...d.residents); renderResidents();
      $("#r-bulk").value = "";
      toast(`Added ${d.residents.length} ${d.residents.length === 1 ? "person" : "people"}. Codes are in the list.`);
    } catch (e) { toast(e.message, "warn"); }
  }

  // Folding and finding. openUnits remembers which cards are open across
  // re-renders; the find box overrides it while a search is typed.
  let openUnits = new Set(["__roles"]);
  let resFilter = "";
  document.addEventListener("click", ev => {
    const h = ev.target.closest("[data-uchev]");
    if (!h || ev.target.closest("button,a,.mini")) return;
    const cardEl = h.closest(".ucard");
    cardEl.classList.toggle("open");
    if (cardEl.classList.contains("open")) openUnits.add(h.dataset.uchev);
    else openUnits.delete(h.dataset.uchev);
  });
  document.addEventListener("input", ev => {
    if (ev.target.id === "r-find") { resFilter = ev.target.value; renderResidents(); }
  });

  // ------------------------------------------------------- resident edit mode
  // The add-person card doubles as the editor: Edit on a row fills it, the
  // buttons swap, and the rarely-used levers (disable, delete) live here,
  // one deliberate step off the row.
  let editingResId = null;
  function enterResEdit(p) {
    editingResId = p.id;
    $("#r-unit").value = p.unit || ""; $("#r-name").value = p.name || "";
    $("#r-email").value = p.email || ""; $("#r-ends").value = p.ends || "";
    $("#r-tenure").value = p.tenure || "";
    $("#res-formhead").style.display = "";
    $("#res-formhead").textContent = `Editing ${p.label} · added ${(p.created || "").slice(0, 10)}`;
    document.querySelector("[data-addres]").style.display = "none";
    $("#res-rolecheck").style.display = "none";
    $("#res-bulk").style.display = "none";
    document.querySelector("[data-saveres]").style.display = "";
    document.querySelector("[data-cancelres]").style.display = "";
    const t = document.querySelector("[data-edittoggle]");
    t.style.display = ""; t.textContent = p.status === "Active" ? "Disable" : "Restore";
    document.querySelector("[data-editdelete]").style.display = "";
    $("#res-formhead").closest(".card").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function exitResEdit() {
    editingResId = null;
    ["r-unit", "r-name", "r-email", "r-ends", "r-tenure"].forEach(id => { $("#" + id).value = ""; });
    $("#res-formhead").style.display = "none";
    document.querySelector("[data-addres]").style.display = "";
    $("#res-rolecheck").style.display = "";
    $("#res-bulk").style.display = "";
    ["[data-saveres]", "[data-cancelres]", "[data-edittoggle]", "[data-editdelete]"]
      .forEach(s => { document.querySelector(s).style.display = "none"; });
  }
  async function saveResEdit() {
    if (!editingResId) return;
    const name = $("#r-name").value.trim();
    if (!name) { toast("A name is needed.", "warn"); return; }
    await patchResident(editingResId, {
      name, unit: $("#r-unit").value.trim(), email: $("#r-email").value.trim(),
      ends: $("#r-ends").value, tenure: $("#r-tenure").value,
    }, u => `Saved ${u.label}.`);
    exitResEdit();
  }

  async function patchResident(id, body, note) {
    try {
      const upd = await api("/api/residents/" + id, { method: "PATCH", body: JSON.stringify(body) });
      const i = residents.findIndex(r => String(r.id) === String(id));
      if (i >= 0) residents[i] = upd;
      renderResidents();
      if (note) toast(note(upd));
    } catch (e) { toast(e.message, "warn"); }
  }

  function printCards() {
    const list = residents.filter(p => p.status === "Active" && !p.expired);
    if (!list.length) { toast("Nobody to print for yet.", "warn"); return; }
    const card = p => `<div class="pc"><div class="pc-h">181 Fremont<span>Resident Events</span></div>
      <div class="pc-n">${esc(p.name)}${p.unit ? ` &middot; Unit ${esc(p.unit)}` : ""}</div>
      <div class="pc-c">${esc(p.code)}</div>
      <div class="pc-s">181residents.com &middot; tap RSVP on any event and enter this code once.<br>
      It stays signed in for a month on your device. Lost it? The front desk has a fresh one.</div></div>`;
    const w = window.open("", "_blank");
    w.document.write(`<!DOCTYPE html><html><head><title>181 Fremont resident code cards</title><style>
      body{font-family:'Hanken Grotesk',-apple-system,sans-serif;margin:24px;color:#16161a}
      .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
      .pc{border:1px solid #b9afa1;border-radius:6px;padding:20px 22px;page-break-inside:avoid}
      .pc-h{font-size:15px;letter-spacing:.18em;text-transform:uppercase}
      .pc-h span{display:block;font-size:9px;letter-spacing:.24em;color:#7a7266;margin-top:3px}
      .pc-n{font-size:16px;font-weight:600;margin-top:14px}
      .pc-c{font-family:ui-monospace,Menlo,monospace;font-size:26px;letter-spacing:.08em;margin:10px 0;color:#c41f26}
      .pc-s{font-size:11px;color:#55555f;line-height:1.5}
      @media print{body{margin:8mm}}
    </style></head><body><div class="grid">${list.map(card).join("")}</div>
    <script>window.print()<\/script></body></html>`);
    w.document.close();
  }

  // ---------------------------------------------------------------- messages
  function renderMsgs() {
    const box = $("#msglist"); if (!box) return;
    const visible = msgs.filter(m => m.state !== "Archived");
    const fresh = visible.filter(m => m.state === "New").length;
    $("#msgcount").textContent = visible.length
      ? `${visible.length} message${visible.length === 1 ? "" : "s"}, ${fresh} awaiting a reply. Residents are promised an answer within one business day.`
      : "Nothing yet. Notes from the Message tile land here the moment they are sent.";
    $("#msg-redacted").style.display = role === "owner" || !visible.length ? "none" : "";
    const msgsLabel = document.querySelector('.navbar label[for="s-msgs"]');
    if (msgsLabel) msgsLabel.textContent = fresh ? `Messages · ${fresh}` : "Messages";
    box.innerHTML = visible.map(m => {
      const when = (m.created || "").slice(0, 10);
      const state = m.state === "New" ? '<span class="mstate new">New</span>'
        : `<span class="mstate replied">Replied${m.replied ? " " + esc(m.replied.slice(0, 10)) : ""}</span>`;
      const text = m.body != null
        ? `<div class="mtext">${esc(m.body).replace(/\n/g, "<br>")}</div>`
          + (m.name || m.email ? `<div style="font-size:13px;color:var(--stone);margin-top:8px">${esc([m.name, m.email].filter(Boolean).join(" · "))}</div>` : "")
        : '<div class="mshade" title="Message text is private to Leo"></div>';
      const acts = role === "owner" ? `<span class="eact" style="margin-left:auto">
          ${m.state === "New" ? `<button class="mini" data-mreplied="${m.id}">Mark replied</button>` : ""}
          <button class="mini ghost" data-marchive="${m.id}">Archive</button></span>` : "";
      return `<div class="mrow"><div class="mtop">
        <span class="munit">${esc(m.sender || "Resident")}</span>
        <span class="mkind">${esc(m.topic || "Note")}</span>${state}
        <span class="mwhen">${esc(when)}</span>${acts}</div>${text}</div>`;
    }).join("");
  }

  async function loadMsgs() {
    try { const d = await api("/api/messages"); msgs = d.messages; } catch (e) {
      msgs = [];
      renderMsgs();
      $("#msgcount").textContent = "Could not load messages: " + e.message;
      return;
    }
    renderMsgs();
  }

  // ---------------------------------------------------------------- assets
  function kitCount(st) {
    return KITINFO.filter(k => { const a = assetOf(st, k.slug); return a && a.uploaded; }).length;
  }

  // A group belongs in the archive when nothing about it is still to come:
  // its last date passed, it was cancelled (Unpublished), or it was archived.
  // Time does the filing; restoring an event walks it back out.
  function inArchive(g) {
    const t = today();
    return !g.rows.some(r => r.Date >= t && r.Status !== "Archived" && r.Status !== "Unpublished");
  }

  function kitRowsHtml(st) {
    return KITINFO.map(k => {
      const a = assetOf(st, k.slug);
      const up = a && a.uploaded;
      const state = up
        ? `<span class="akstate done">${esc(a.filename)} &middot; ${a.size ? Math.max(1, Math.round(a.size / 1024)) + " KB &middot; " : ""}${esc((a.uploaded || "").slice(0, 10))}</span>`
        : `<span class="akstate miss">Not uploaded</span>`;
      return `<div class="akrow">
        <span class="akname">${k.name}<em>${k.spec}</em></span>
        <span>${state}<span class="akwhere">${k.where}</span></span>
        <span class="akact">
          ${up ? `<a class="mini" href="/api/assets/${esc(st)}/${k.slug}" title="The final version, for any admin on any device">Download</a>` : ""}
          <button class="mini${up ? " ghost" : ""}" data-aupload="${esc(st)}|${k.slug}" ${assetStorage ? "" : 'disabled title="Link the R2 bucket first; see the note above"'}>${up ? "Replace" : "Upload"}</button>
          ${a && a.canva ? `<a class="mini ghost" href="${esc(a.canva)}" target="_blank" rel="noopener" title="Opens the design in Canva for editing">Canva</a>` : ""}
          <button class="mini ghost" data-acanva="${esc(st)}|${k.slug}" title="Save the Canva address where this piece is edited">${a && a.canva ? "Edit link" : "Canva link"}</button>
          ${up ? `<button class="mini ghost" data-adelete="${esc(st)}|${k.slug}">Remove file</button>` : ""}
        </span></div>`;
    }).join("");
  }

  // The editor shows a date's EFFECTIVE kit: its own override when one exists,
  // else what it inherits from the series master. Overriding touches this date
  // alone; "Back to series kit" hands the date back to the master.
  function renderEditorKit() {
    const box = $("#ak"); if (!box || !editing) return;
    const row = editing.row;
    if (!row) {
      box.innerHTML = '<div class="akrow"><span class="akstate miss">Save the event first; its kit then lives under Assets, and each date can override it here.</span></div>';
      return;
    }
    const mk = masterKey(row), dk = stem(row);
    const isSeries = !!(editing.group && editing.group.series);
    box.innerHTML = KITINFO.map(k => {
      const own = isSeries ? assetOf(dk, k.slug) : null;
      const mast = assetOf(mk, k.slug);
      const ownUp = own && own.uploaded, mastUp = mast && mast.uploaded;
      const eff = ownUp ? own : (mastUp ? mast : null);
      const effKey = ownUp ? dk : mk;
      let state;
      if (ownUp) state = `<span class="akstate done">This date&rsquo;s own &middot; ${esc(own.filename)} &middot; ${esc((own.uploaded || "").slice(0, 10))}</span>`;
      else if (mastUp) state = `<span class="akstate done">${isSeries ? "From the series kit" : "Uploaded"} &middot; ${esc(mast.filename)} &middot; ${esc((mast.uploaded || "").slice(0, 10))}</span>`;
      else state = `<span class="akstate miss">Not uploaded${isSeries ? " &middot; the series kit lives under Assets" : ""}</span>`;
      const canva = (own && own.canva) || (mast && mast.canva);
      const acts = [
        eff ? `<a class="mini" href="/api/assets/${esc(effKey)}/${k.slug}">Download</a>` : "",
        isSeries
          ? `<button class="mini ghost" data-aupload="${esc(dk)}|${k.slug}" ${assetStorage ? "" : 'disabled title="Link the R2 bucket first"'}>${ownUp ? "Replace override" : "Override this date"}</button>`
          : `<button class="mini${eff ? " ghost" : ""}" data-aupload="${esc(mk)}|${k.slug}" ${assetStorage ? "" : 'disabled title="Link the R2 bucket first"'}>${eff ? "Replace" : "Upload"}</button>`,
        ownUp ? `<button class="mini ghost" data-adelete="${esc(dk)}|${k.slug}" title="This date returns to the series kit">Back to series kit</button>` : "",
        canva ? `<a class="mini ghost" href="${esc(canva)}" target="_blank" rel="noopener">Canva</a>` : "",
      ].join("");
      return `<div class="akrow"><span class="akname">${k.name}<em>${k.spec}</em></span><span>${state}</span><span class="akact">${acts}</span></div>`;
    }).join("");
  }

  function assetCard(g, sub) {
    const st = masterKey(g.head);
    const overrides = g.series ? assets.filter(a => a.stem !== st && a.stem.endsWith("_" + st)).length : 0;
    const inherit = g.series ? ` &middot; every date inherits this kit${overrides ? `, ${overrides} date override${overrides === 1 ? "" : "s"} (see the date in the editor)` : ""}` : "";
    return `<div class="acard"><div class="ahead" data-chev>
      <span><span class="at">${esc(g.head.Title)}</span><span class="asub">${sub} &middot; <code>${esc(st)}</code> &middot; ${kitCount(st)} of 6 uploaded${inherit}</span></span>
      <span class="chev">&rsaquo;</span></div>
      <div class="aklist">${kitRowsHtml(st)}</div></div>`;
  }

  function renderAssets() {
    const box = $("#assets"); if (!box) return;
    const note = $("#assets-storage");
    if (note) note.style.display = assetStorage ? "none" : "";
    const all = groups();
    const gs = all.filter(g => !inArchive(g));
    const archived = all.length - gs.length;
    const ce = $("#arch-count-e"), ca = $("#arch-count-a");
    if (ce) ce.textContent = archived;
    if (ca) ca.textContent = archived;
    box.innerHTML = gs.map(g => assetCard(g, esc(g.series ? g.head.Series : fmt(g.head.Date)))).join("")
      || '<div class="nodata">Nothing current. New events bring their kits with them.</div>';
    renderArchive(all.filter(inArchive));
  }

  function renderArchive(gs) {
    const box = $("#archlist"); if (!box) return;
    gs.sort((a, b) => b.rows[b.rows.length - 1].Date.localeCompare(a.rows[a.rows.length - 1].Date));
    $("#archcount").textContent = gs.length
      ? `${gs.length} listing${gs.length === 1 ? "" : "s"}, newest first. Files and Canva links stay live for reference.`
      : "Empty so far. Events arrive here on their own once their last date passes.";
    box.innerHTML = gs.map(g => {
      const first = g.rows[0].Date, last = g.rows[g.rows.length - 1].Date;
      const span = g.series ? `${fmt(first)} to ${fmt(last)}` : fmt(g.head.Date);
      const why = g.status === "Archived" ? "Archived" : g.status === "Unpublished" ? "Cancelled" : "Passed";
      const sub = `${esc(span)} &middot; <span class="pill ${cls(g.status === "Live" ? "archived" : g.status)}">${why}</span> <button class="mini ghost" data-edit="${esc(g.key)}" style="margin-left:8px">Open</button>`;
      return assetCard(g, sub);
    }).join("");
  }

  async function loadAssets() {
    try { const d = await api("/api/assets"); assets = d.assets; assetStorage = d.storage; }
    catch (e) { assets = []; assetStorage = false; }
    renderAssets();
  }

  let pendingAsset = null;
  function uploadAsset(st, slug) {
    pendingAsset = { st, slug };
    const inp = $("#afile"); inp.value = ""; inp.click();
  }

  async function sendAssetFile(file) {
    const { st, slug } = pendingAsset; pendingAsset = null;
    if (file.size > 95 * 1024 * 1024) { toast("That file is over the 95 MB upload ceiling. Compress it, or keep the master in Canva.", "warn"); return; }
    toast(`Uploading ${file.name}…`);
    try {
      const r = await fetch(`/api/assets/${encodeURIComponent(st)}/${slug}`, {
        method: "PUT",
        headers: { "x-filename": encodeURIComponent(file.name), "content-type": file.type || "application/octet-stream" },
        body: file,
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Upload failed: " + r.status);
      assets = assets.filter(a => !(a.stem === st && a.kind === slug)).concat([d.asset]);
      renderAssets(); renderEvents(); renderEditorKit();
      toast(`${file.name} is up. Any admin can download it from here now.`);
    } catch (e) { toast(e.message, "warn"); }
  }

  function editCanva(st, slug) {
    const a = assetOf(st, slug);
    const v = prompt("The Canva address for this piece (blank removes the link):", (a && a.canva) || "https://www.canva.com/design/");
    if (v === null) return;
    api(`/api/assets/${encodeURIComponent(st)}/${slug}`, { method: "PATCH", body: JSON.stringify({ canva: v.trim() }) })
      .then(d => {
        assets = assets.filter(x => !(x.stem === st && x.kind === slug));
        if (d.asset) assets.push(d.asset);
        renderAssets(); renderEditorKit();
        toast(v.trim() ? "Canva link saved." : "Canva link removed.");
      })
      .catch(e => toast(e.message, "warn"));
  }

  // ---------------------------------------------------------------- spaces
  // Reservations for the Level 39 rooms. Residents see only "Reserved" with the
  // space and hours on /spaces; the note stays in this admin.
  let bookings = [];

  // The guest lists behind private events, fetched per reservation when its
  // panel opens and kept for the session.
  let guestsByBooking = {};
  const openGuestPanels = new Set();

  // The registration page's address: the written one when set, else the token.
  const regPath = b => `/register/${b.reg_slug || b.reg_token}`;

  function guestSection(b) {
    const g = guestsByBooking[b.id];
    const heads = r => r.plus_one ? 2 : 1;
    const rows = !g ? '<div class="nodata" style="padding:12px">Loading&hellip;</div>'
      : !g.length ? '<div class="nodata" style="padding:12px">Nobody registered yet. Copy the link and the host sends it to the invitees.</div>'
      : g.map(r => `<div class="srow">
          <span class="slab">${esc(r.name)}${r.plus_one ? ` <span style="color:var(--stone)">+ ${esc(r.plus_one)}</span>` : ""}</span>
          <span class="sgrow" style="font-size:12px;color:var(--stone)">${esc((r.created || "").slice(0, 10))}${r.arrived ? ` · in at ${new Date(r.arrived).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` : ""}</span>
          <span class="eact">
            <button class="mini${r.arrived ? "" : " ghost"}" data-garrive="${r.id}|${b.id}">${r.arrived ? "Arrived ✓" : "Arrived"}</button>
            <button class="mini ghost" data-gdel="${r.id}|${b.id}" title="Remove this registration">Remove</button>
          </span></div>`).join("");
    const total = (g || []).reduce((a, r) => a + heads(r), 0);
    const inCount = (g || []).filter(r => r.arrived).length;
    return `
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0 12px">
        <button class="mini" data-bkreg="${b.id}">${b.reg_open ? "Close registration" : "Open registration"}</button>
        <button class="mini ghost" data-bkcopy="${b.id}" title="The unguessable page the host sends to invitees">Copy registration link</button>
        <a class="mini ghost" href="${esc(regPath(b))}" target="_blank" rel="noopener" title="The page invitees see, exactly as it stands">View page</a>
        <button class="mini ghost" data-bkprint="${b.id}" title="The list the desk and security run from">Print guest list</button>
        <span class="hint" style="margin:0">${b.reg_open ? "Registration is open" : "Registration is closed"}${b.guest_cap ? ` · cap ${b.guest_cap}` : ""}${g ? ` · ${g.length} ${g.length === 1 ? "party" : "parties"}, ${total} guests, ${inCount} arrived` : ""}</span>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:6px">
        <div class="field" style="margin:0"><label class="fl" for="g-name-${b.id}">Add at the desk</label><input class="inp" id="g-name-${b.id}" autocapitalize="words" placeholder="Guest name"></div>
        <div class="field" style="margin:0"><label class="fl" for="g-plus-${b.id}">Plus one</label><input class="inp" id="g-plus-${b.id}" autocapitalize="words" placeholder="Optional"></div>
        <button class="mini" data-gadd="${b.id}" style="margin-bottom:2px">Add</button>
      </div>
      ${rows}`;
  }

  function renderBookings() {
    const box = $("#bklist"); if (!box) return;
    const t = today();
    const ahead = bookings.filter(b => b.date >= t).sort((a, b2) => (a.date + (a.start24 || "")).localeCompare(b2.date + (b2.start24 || "")));
    $("#bkcount").textContent = ahead.length
      ? `${ahead.length} reservation${ahead.length === 1 ? "" : "s"} ahead. Residents see the space and hours only, marked Reserved, never who or why.`
      : "Nothing reserved ahead. Residents see open rooms and can walk in anytime.";
    // Every reservation folds like a unit card: the header carries what the eye
    // scans for, the body holds the working parts, and a private event's guest
    // machinery lives inside its own card.
    box.innerHTML = ahead.map(b => {
      const open = openGuestPanels.has(b.id);
      const isEvent = !!b.event_name;
      const hours = b.start ? `${esc(b.start)}${b.end_time ? " – " + esc(b.end_time) : ""}` : "";
      return `<div class="ucard${open ? " open" : ""}">
        <div class="uhead" data-bkchev="${b.id}"><span class="chev">&#8250;</span>
          <span>${esc(b.event_name || b.space)}</span>
          <span style="font-weight:400;color:var(--stone)">${esc(fmt(b.date))}${hours ? " · " + hours : ""}</span>
          <span class="ucount">${isEvent ? `${b.guest_parties || 0} ${(b.guest_parties || 0) === 1 ? "party" : "parties"} · ${b.guest_arrived || 0} in` : "reservation"}</span>
        </div>
        <div class="ubody"><div style="padding:12px 16px 16px">
          <div style="font-size:13px;color:var(--ink-soft)">${isEvent ? `${esc(b.space)}${b.host ? " · hosted by " + esc(b.host) : ""}` : esc(b.space)}${b.note ? ` · ${esc(b.note)} <span style="color:var(--stone)">(staff only)</span>` : ""}</div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">
            <button class="mini ghost" data-bkedit="${b.id}" title="Space, date, hours, note, event name, host, cap. The page invitees see is drawn from these.">Edit</button>
            <button class="mini ghost" data-unbook="${b.id}">Remove</button>
          </div>
          ${isEvent ? guestSection(b) : ""}
        </div></div>
      </div>`;
    }).join("");
  }

  async function loadGuests(bookingId) {
    try {
      const d = await api("/api/guests?booking=" + bookingId);
      guestsByBooking[bookingId] = d.guests;
    } catch (e) { toast(e.message, "warn"); guestsByBooking[bookingId] = []; }
    renderBookings();
  }

  function printGuestList(b) {
    const g = guestsByBooking[b.id] || [];
    const lines = [];
    let n = 0;
    for (const r of g) {
      n++; lines.push({ n, name: r.name, note: "" });
      if (r.plus_one) { n++; lines.push({ n, name: r.plus_one, note: `guest of ${r.name}` }); }
    }
    const w = window.open("", "_blank");
    w.document.write(`<!DOCTYPE html><html><head><title>${esc(b.event_name || "Guest list")}</title><style>
      body{font-family:Georgia,serif;color:#16161a;margin:40px;font-size:14px}
      h1{font-size:22px;margin:0 0 2px} .sub{color:#55555f;margin:0 0 6px}
      .meta{font-size:12px;color:#7a7266;margin-bottom:20px}
      table{width:100%;border-collapse:collapse}
      th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#7a7266;padding:6px 8px;border-bottom:2px solid #16161a}
      td{padding:8px;border-bottom:1px solid #ddd6cb}
      .box{display:inline-block;width:14px;height:14px;border:1.5px solid #16161a}
      .n{color:#7a7266;width:30px} .note{color:#7a7266;font-style:italic}
      @media print{ body{margin:16px} }
    </style></head><body>
    <h1>${esc(b.event_name || "Private event")} &middot; Guest List</h1>
    <p class="sub">${esc(b.space)}, 181 Fremont &middot; ${esc(fmt(b.date))}${b.start ? ` &middot; ${esc(b.start)}${b.end_time ? " – " + esc(b.end_time) : ""}` : ""}${b.host ? ` &middot; hosted by ${esc(b.host)}` : ""}</p>
    <p class="meta">${g.length} ${g.length === 1 ? "party" : "parties"}, ${lines.length} expected guests &middot; guests give the event name at the door &middot; printed ${new Date().toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</p>
    <table><tr><th></th><th>#</th><th>Guest</th><th></th></tr>
    ${lines.map(l => `<tr><td><span class="box"></span></td><td class="n">${l.n}</td><td>${esc(l.name)}</td><td class="note">${esc(l.note)}</td></tr>`).join("")}
    </table></body></html>`);
    w.document.close();
    w.focus();
    w.print();
  }

  async function loadBookings() {
    try { const d = await api("/api/bookings"); bookings = d.bookings; } catch (e) {
      bookings = [];
      renderBookings();
      $("#bkcount").textContent = "Could not load reservations: " + e.message;
      return;
    }
    renderBookings();
  }

  // The reservation card doubles as the editor, same as the residents card:
  // Edit fills it, the buttons swap, and the registration link never changes.
  let editingBkId = null;
  function enterBkEdit(b) {
    editingBkId = b.id;
    $("#bk-space").value = b.space || ""; $("#bk-date").value = b.date || "";
    $("#bk-start").value = b.start || ""; $("#bk-end").value = b.end_time || "";
    $("#bk-note").value = b.note || ""; $("#bk-event").value = b.event_name || "";
    $("#bk-host").value = b.host || ""; $("#bk-cap").value = b.guest_cap || "";
    $("#bk-slug").value = b.reg_slug || "";
    $("#bk-formhead").style.display = "";
    $("#bk-formhead").textContent = `Editing ${b.event_name || b.space} · ${fmt(b.date)}`;
    document.querySelector("[data-addbooking]").style.display = "none";
    $("#bk-addhint").style.display = "none";
    document.querySelector("[data-savebk]").style.display = "";
    document.querySelector("[data-cancelbk]").style.display = "";
    $("#bk-formhead").closest(".card").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function exitBkEdit() {
    editingBkId = null;
    ["#bk-space", "#bk-date", "#bk-start", "#bk-end", "#bk-note", "#bk-event", "#bk-host", "#bk-cap", "#bk-slug"]
      .forEach(s => { $(s).value = ""; });
    $("#bk-formhead").style.display = "none";
    document.querySelector("[data-addbooking]").style.display = "";
    $("#bk-addhint").style.display = "";
    document.querySelector("[data-savebk]").style.display = "none";
    document.querySelector("[data-cancelbk]").style.display = "none";
  }
  async function saveBkEdit() {
    const b = bookings.find(x => x.id === editingBkId); if (!b) { exitBkEdit(); return; }
    const space = $("#bk-space").value.trim(), date = $("#bk-date").value;
    if (!space || !date) { toast("A space and a date are needed.", "warn"); return; }
    try {
      const d = await api("/api/bookings/" + b.id, { method: "PATCH", body: JSON.stringify({
        space, date, start: $("#bk-start").value.trim(), end: $("#bk-end").value.trim(),
        note: $("#bk-note").value.trim(), event_name: $("#bk-event").value.trim(),
        host: $("#bk-host").value.trim(), guest_cap: $("#bk-cap").value ? Number($("#bk-cap").value) : null,
        reg_slug: $("#bk-slug").value.trim(),
      }) });
      Object.assign(b, d.booking);
      renderBookings();
      exitBkEdit();
      toast("Saved. The Spaces page and the registration page both show it now.");
    } catch (e) { toast(e.message, "warn"); }
  }

  async function addBooking() {
    const body = {
      space: $("#bk-space").value.trim(), date: $("#bk-date").value,
      start: $("#bk-start").value.trim(), end: $("#bk-end").value.trim(),
      note: $("#bk-note").value.trim(),
      event_name: $("#bk-event").value.trim(), host: $("#bk-host").value.trim(),
      guest_cap: $("#bk-cap").value ? Number($("#bk-cap").value) : null,
      reg_slug: $("#bk-slug").value.trim(),
    };
    if (!body.space || !body.date) { toast("A space and a date are needed.", "warn"); return; }
    try {
      const d = await api("/api/bookings", { method: "POST", body: JSON.stringify(body) });
      bookings.push(d.booking); renderBookings();
      ["#bk-space", "#bk-date", "#bk-start", "#bk-end", "#bk-note", "#bk-event", "#bk-host", "#bk-cap", "#bk-slug"].forEach(s => $(s).value = "");
      toast(body.event_name
        ? "Reserved. Open its Guests panel to switch on registration and copy the link for the host."
        : "Reserved. It shows on the Spaces page immediately.");
    } catch (e) { toast(e.message, "warn"); }
  }

  function renderAll() { renderEvents(); renderDash(); renderAssets(); }

  // ---------------------------------------------------------------- csv export
  function csvCell(v) { v = String(v == null ? "" : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
  function exportCsv() {
    const a = analytics || { byDay: [], bySource: [], byDevice: [], visits: 0, pageviews: 0, sample: false };
    const t = today();
    const upcoming = events.filter(e => e.Status === "Live" && e.Date >= t);
    const rows = [];
    rows.push(["181 Fremont Resident Experiences, analytics export"]);
    rows.push(["Exported", t, a.sample ? "SAMPLE FIGURES, site not yet collecting" : `last ${days} days`]);
    rows.push([]);
    rows.push(["Totals"]); rows.push(["Visits", a.visits]); rows.push(["Page views", a.pageviews]);
    rows.push(["Live upcoming dates", upcoming.length]);
    rows.push([]);
    rows.push(["Visits by day"]); rows.push(["Date", "Visits", "Page views"]);
    for (const d of a.byDay) rows.push([d.date, d.visits, d.views]);
    rows.push([]);
    rows.push(["Traffic by source"]); rows.push(["Source", "Visits"]);
    for (const s2 of a.bySource) rows.push([s2.label, s2.visits]);
    rows.push([]);
    rows.push(["Devices"]); rows.push(["Device", "Page views"]);
    for (const d of a.byDevice) rows.push([d.device, d.views]);
    rows.push([]);
    rows.push(["Live calendar by category"]); rows.push(["Category", "Upcoming dates"]);
    for (const c of CATS) { const n = upcoming.filter(e => e.Category === c).length; if (n) rows.push([c, n]); }
    const sums = rsvpSummary();
    rows.push([]);
    rows.push(["RSVPs by event, upcoming"]);
    rows.push(["Date", "Event", "Type", "Parties", "Heads", "Capacity", "Waitlisted heads"]);
    for (const s2 of sums) {
      const e = events.find(x => stem(x) === s2.key);
      rows.push([s2.date, s2.title, s2.type, s2.parties, s2.heads, e && e.Capacity ? e.Capacity : "", s2.waitHeads]);
    }
    if (!sums.length) rows.push(["No RSVPs yet"]);
    rows.push([]);
    rows.push(["Messages"]);
    rows.push(["Awaiting reply", msgs.filter(m => m.state === "New").length]);
    rows.push(["Replied", msgs.filter(m => m.state === "Replied").length]);
    const csv = rows.map(r => r.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `181fremont-analytics-${t}-${days}d.csv`;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 5000);
    toast("Downloaded. The file opens straight into Excel.");
  }

  // ---------------------------------------------------------------- boot
  async function loadAnalytics() {
    try { analytics = await api("/api/analytics?days=" + days); } catch (e) { analytics = null; }
    renderDash();
  }

  async function boot() {
    try { status = await api("/api/status"); } catch (e) { status = {}; }
    let whoEmail = "";
    // Fail closed: if the identity check cannot answer, nobody is staff. The
    // shell shows nothing but a sign-in card until a real tier comes back.
    try { const w = await api("/api/whoami"); role = w.role || "none"; whoEmail = w.email || ""; }
    catch (e) { role = "none"; }
    if (role === "none") {
      const nav = document.querySelector(".navbar"); if (nav) nav.style.display = "none";
      document.querySelector(".body").innerHTML = `<div class="wrap" style="max-width:520px;padding:70px 20px;text-align:center">
        <h1 style="font-size:21px">Sign in to continue</h1>
        <p style="color:var(--ink-soft);margin:12px 0 22px">This is the staff side of 181residents.com. Your sign-in
        did not carry through, so nothing is shown. Reload to try again, or sign out above and sign back in.</p>
        <button class="btn" onclick="location.reload()">Reload</button></div>`;
      $("#who").innerHTML = "Not signed in";
      const gbar = $("#sysbar"); if (gbar) gbar.textContent = "Sign-in required · nothing loads without it";
      return;
    }
    document.body.classList.add("role-" + role);
    const roleName = { owner: "owner", staff: "staff", desk: "front desk" }[role] || role;
    $("#who").innerHTML = `Signed in as ${esc(roleName)}<strong>${esc(whoEmail || "181 Fremont · Level 39")}</strong>`;
    const bar = $("#sysbar");
    if (status.mode === "local") bar.textContent = `Local preview · saving to this computer, publishing rebuilds the local calendar · signed in as ${role}`;
    else if (status.db) bar.textContent = "Connected · " + (status.publish ? "saves publish to 181residents.com within a couple of minutes" : "publishing not yet wired, changes stay in the database")
      + (status.signin ? "" : " · resident sign-in not switched on yet: set SESSION_SECRET in the Pages settings")
      + (role === "none" ? " · Access did not pass your email through, so nothing will load: reload the page, or use Sign out above and sign back in" : "");
    else bar.textContent = "Events database not linked yet · add the D1 binding named DB in the Pages settings";
    // Installed as an app, a healthy plumbing report is noise; hide it there.
    if (status.db && (status.signin || status.mode === "local") && role !== "none") bar.classList.add("quiet");

    // Every tier, the desk included, gets the dashboard and the RSVP work; the
    // server refuses event writes for the desk, and its tabs are hidden by CSS.
    try {
      let d = await api("/api/events"); events = d.events;
      if (!events.length && status.db && status.mode === "cloudflare") {
        const s = await api("/api/seed", { method: "POST" });
        if (s.seeded) { toast(`Loaded the opening calendar: ${s.count} events.`); d = await api("/api/events"); events = d.events; }
      }
    }
    catch (e) { evError = e.message; }
    try { rsvps = (await api("/api/rsvps")).rsvps; } catch (e) { rsvps = []; }
    rsvpCache = null;
    await loadAssets();
    renderAll();
    loadAnalytics();
    loadResidents();
    loadMsgs();
    loadBookings();
    loadWindow();
  }

  document.addEventListener("click", ev => {
    const r = ev.target.closest("[data-rotate],[data-ends],[data-toggle],[data-rdelete],[data-resedit],[data-saveres],[data-cancelres],[data-edittoggle],[data-editdelete],[data-addres],[data-addbulk],[data-printcards],[data-mreplied],[data-marchive],[data-wconfirm],[data-redit],[data-rcancel],[data-pastchev],[data-pastmail],[data-addrsvp],[data-savearsvp],[data-closearsvp],[data-copylink],[data-aupload],[data-acanva],[data-adelete],[data-rsvpkey],[data-addbooking],[data-unbook],[data-bkchev],[data-bkreg],[data-bkcopy],[data-bkprint],[data-gadd],[data-garrive],[data-gdel],[data-bkedit],[data-savebk],[data-cancelbk]");
    if (r) {
      if (r.dataset.bkedit) {
        const b = bookings.find(x => String(x.id) === r.dataset.bkedit);
        if (b) enterBkEdit(b);
        return;
      }
      if (r.dataset.savebk !== undefined) { saveBkEdit(); return; }
      if (r.dataset.cancelbk !== undefined) { exitBkEdit(); return; }
      if (r.dataset.bkchev) {
        const id = Number(r.dataset.bkchev);
        if (openGuestPanels.has(id)) openGuestPanels.delete(id);
        else {
          openGuestPanels.add(id);
          const b = bookings.find(x => x.id === id);
          if (b && b.event_name && !guestsByBooking[id]) loadGuests(id);
        }
        renderBookings();
        return;
      }
      if (r.dataset.bkreg) {
        const b = bookings.find(x => String(x.id) === r.dataset.bkreg); if (!b) return;
        api("/api/bookings/" + b.id, { method: "PATCH", body: JSON.stringify({ reg_open: !b.reg_open }) })
          .then(d => {
            Object.assign(b, d.booking); renderBookings();
            toast(b.reg_open
              ? "Registration is open. Copy the link and hand it to the host."
              : "Registration is closed. The list stands; the page politely turns latecomers to their host.");
          }).catch(e => toast(e.message, "warn"));
        return;
      }
      if (r.dataset.bkcopy) {
        const b = bookings.find(x => String(x.id) === r.dataset.bkcopy); if (!b) return;
        const link = "https://181residents.com" + regPath(b);
        (navigator.clipboard ? navigator.clipboard.writeText(link) : Promise.reject())
          .then(() => toast("Registration link copied. The host sends it to the invitees."))
          .catch(() => prompt("Copy the registration link:", link));
        return;
      }
      if (r.dataset.bkprint) {
        const b = bookings.find(x => String(x.id) === r.dataset.bkprint); if (!b) return;
        if (!guestsByBooking[b.id]) { toast("Open the Guests panel first, so the list is loaded."); return; }
        printGuestList(b);
        return;
      }
      if (r.dataset.gadd) {
        const id = Number(r.dataset.gadd);
        const name = $(`#g-name-${id}`).value.trim();
        if (!name) { toast("A guest name is needed.", "warn"); return; }
        api("/api/guests", { method: "POST", body: JSON.stringify({ booking_id: id, name, plus_one: $(`#g-plus-${id}`).value.trim() }) })
          .then(d => {
            (guestsByBooking[id] = guestsByBooking[id] || []).push(d.guest);
            const b = bookings.find(x => x.id === id);
            if (b) { b.guest_parties = (b.guest_parties || 0) + 1; b.guest_heads = (b.guest_heads || 0) + (d.guest.plus_one ? 2 : 1); }
            renderBookings();
            toast(`${d.guest.name} is on the list.`);
          }).catch(e => toast(e.message, "warn"));
        return;
      }
      if (r.dataset.garrive) {
        const [gid, bid] = r.dataset.garrive.split("|").map(Number);
        const row = (guestsByBooking[bid] || []).find(x => x.id === gid); if (!row) return;
        api("/api/guests/" + gid, { method: "PATCH", body: JSON.stringify({ arrived: !row.arrived }) })
          .then(d => {
            Object.assign(row, d.guest);
            const b = bookings.find(x => x.id === bid);
            if (b) b.guest_arrived = (guestsByBooking[bid] || []).filter(x => x.arrived).length;
            renderBookings();
          }).catch(e => toast(e.message, "warn"));
        return;
      }
      if (r.dataset.gdel) {
        const [gid, bid] = r.dataset.gdel.split("|").map(Number);
        const row = (guestsByBooking[bid] || []).find(x => x.id === gid);
        if (!row || !confirm(`Remove ${row.name}${row.plus_one ? " and " + row.plus_one : ""} from the list?`)) return;
        api("/api/guests/" + gid, { method: "DELETE" })
          .then(() => {
            guestsByBooking[bid] = (guestsByBooking[bid] || []).filter(x => x.id !== gid);
            const b = bookings.find(x => x.id === bid);
            if (b) { b.guest_parties = Math.max(0, (b.guest_parties || 0) - 1); b.guest_heads = Math.max(0, (b.guest_heads || 0) - (row.plus_one ? 2 : 1)); }
            renderBookings();
          }).catch(e => toast(e.message, "warn"));
        return;
      }
      if (r.dataset.rotate) {
        const p = residents.find(x => String(x.id) === r.dataset.rotate);
        if (p && confirm(`Rotate ${p.label}'s code? The old one stops working everywhere, on every device, right away.`))
          patchResident(r.dataset.rotate, { rotate: true }, u => `New code for ${u.label}: ${u.code}`);
      } else if (r.dataset.ends) {
        const p = residents.find(x => String(x.id) === r.dataset.ends);
        const v = prompt("Access ends on (YYYY-MM-DD), or blank for no end date:", p && p.ends || "");
        if (v !== null) {
          if (v && !/^\d{4}-\d{2}-\d{2}$/.test(v.trim())) { toast("Dates read as YYYY-MM-DD, like 2026-09-30.", "warn"); return; }
          patchResident(r.dataset.ends, { ends: v.trim() }, u => u.ends ? `${u.label}'s code works through ${u.ends}.` : `${u.label}'s code no longer has an end date.`);
        }
      } else if (r.dataset.toggle) {
        const p = residents.find(x => String(x.id) === r.dataset.toggle);
        if (p) patchResident(r.dataset.toggle, { status: p.status === "Active" ? "Disabled" : "Active" },
          u => u.status === "Active" ? `${u.label} is restored.` : `${u.label} is disabled and signed out everywhere.`);
      } else if (r.dataset.rdelete) {
        const p = residents.find(x => String(x.id) === r.dataset.rdelete);
        if (p && confirm(`Delete ${p.label} entirely? Their code and any RSVPs they made are removed for good. For someone who moved out, Disable is the better choice; it keeps their history.`)) {
          api("/api/residents/" + r.dataset.rdelete, { method: "DELETE" })
            .then(() => {
              residents = residents.filter(x => String(x.id) !== r.dataset.rdelete);
              renderResidents();
              toast(`${p.label} is deleted.`);
            })
            .catch(e => toast(e.message, "warn"));
        }
      } else if (r.dataset.resedit) {
        const p = residents.find(x => String(x.id) === r.dataset.resedit);
        if (p) enterResEdit(p);
      } else if (r.dataset.saveres !== undefined) saveResEdit();
      else if (r.dataset.cancelres !== undefined) exitResEdit();
      else if (r.dataset.edittoggle !== undefined) {
        const p = residents.find(x => String(x.id) === String(editingResId));
        if (p) patchResident(p.id, { status: p.status === "Active" ? "Disabled" : "Active" },
          u => u.status === "Active" ? `${u.label} is restored.` : `${u.label} is disabled and signed out everywhere.`)
          .then(() => {
            const t = document.querySelector("[data-edittoggle]");
            const q = residents.find(x => String(x.id) === String(editingResId));
            if (t && q) t.textContent = q.status === "Active" ? "Disable" : "Restore";
          });
      } else if (r.dataset.editdelete !== undefined) {
        const p = residents.find(x => String(x.id) === String(editingResId));
        if (p && confirm(`Delete ${p.label} entirely? Their code and any RSVPs they made are removed for good. For someone who moved out, Disable is the better choice; it keeps their history.`)) {
          api("/api/residents/" + p.id, { method: "DELETE" })
            .then(() => {
              residents = residents.filter(x => String(x.id) !== String(p.id));
              exitResEdit();
              renderResidents();
              toast(`${p.label} is deleted.`);
            })
            .catch(e => toast(e.message, "warn"));
        }
      } else if (r.dataset.addres !== undefined) addResident();
      else if (r.dataset.addbulk !== undefined) addBulk();
      else if (r.dataset.printcards !== undefined) printCards();
      else if (r.dataset.mreplied) {
        api("/api/messages/" + r.dataset.mreplied, { method: "PATCH", body: JSON.stringify({ state: "Replied" }) })
          .then(u => { const m = msgs.find(x => String(x.id) === String(u.id)); if (m) { m.state = u.state; m.replied = u.replied; } renderMsgs(); })
          .catch(e => toast(e.message, "warn"));
      } else if (r.dataset.marchive) {
        api("/api/messages/" + r.dataset.marchive, { method: "PATCH", body: JSON.stringify({ state: "Archived" }) })
          .then(u => { const m = msgs.find(x => String(x.id) === String(u.id)); if (m) m.state = u.state; renderMsgs(); })
          .catch(e => toast(e.message, "warn"));
      } else if (r.dataset.wconfirm) {
        patchRsvp(r.dataset.wconfirm, { status: "Confirmed" }, row => {
          toast("Confirmed. A note to the resident is opening; send it so they know their seats came through.");
          if (row) notifyRsvp(row, "confirm");
        });
      } else if (r.dataset.redit) {
        const row = rsvps.find(x => String(x.id) === r.dataset.redit);
        if (row) openRsvpEdit(row);
      } else if (r.dataset.rcancel) {
        const row = rsvps.find(x => String(x.id) === r.dataset.rcancel);
        if (!row) return;
        if (!confirm(`Cancel ${row.name}'s RSVP for ${row.event_title}?`)) return;
        patchRsvp(r.dataset.rcancel, { status: "Cancelled" }, () => {
          rsvps = rsvps.filter(x => String(x.id) !== r.dataset.rcancel);
          rsvpCache = null;
          renderDash(); renderEvents();
          toast("Cancelled. Their seats are free for the waitlist; use Confirm seats to hand them on.");
          // The note is offered, never assumed: sometimes the resident is
          // standing right there, and sometimes they asked for no fuss.
          if (row.email) {
            if (confirm(`Open a note to ${row.name} about the cancellation? It sends from your own mailbox.`))
              notifyRsvp(row, "cancel");
          } else {
            toast(`No email on file for ${row.name}; a call or a word at the desk closes the loop.`);
          }
        });
      } else if (r.dataset.aupload) {
        const [st, slug] = r.dataset.aupload.split("|");
        uploadAsset(st, slug);
      } else if (r.dataset.acanva) {
        const [st, slug] = r.dataset.acanva.split("|");
        editCanva(st, slug);
      } else if (r.dataset.adelete) {
        const [st, slug] = r.dataset.adelete.split("|");
        const k = KITINFO.find(x => x.slug === slug);
        if (confirm(`Remove the uploaded ${k ? k.name : "file"} for ${st}? The Canva link, if any, stays.`)) {
          api(`/api/assets/${encodeURIComponent(st)}/${slug}`, { method: "DELETE" })
            .then(d => {
              assets = assets.filter(x => !(x.stem === st && x.kind === slug));
              if (d.asset) assets.push(d.asset);
              renderAssets(); renderEvents(); renderEditorKit();
              toast("File removed.");
            })
            .catch(e => toast(e.message, "warn"));
        }
      } else if (r.dataset.copylink) {
        const url = "https://181residents.com/rsvp/" + r.dataset.copylink;
        navigator.clipboard.writeText(url)
          .then(() => toast("Copied: " + url))
          .catch(() => prompt("Copy the event link:", url));
      } else if (r.dataset.addrsvp !== undefined) openAddRsvp();
      else if (r.dataset.savearsvp !== undefined) { if (editingRsvp) saveRsvpEdit(); else saveAddRsvp(); }
      else if (r.dataset.closearsvp !== undefined) exitRsvpEdit();
      else if (r.dataset.pastchev !== undefined) { pastRsvpsOpen = !pastRsvpsOpen; renderRsvps(); }
      else if (r.dataset.pastmail) emailPastGuests(r.dataset.pastmail);
      else if (r.dataset.rsvpkey) {
        const d = document.querySelector(`[data-rsvpdetail="${CSS.escape(r.dataset.rsvpkey)}"]`);
        if (d) d.style.display = d.style.display === "none" ? "" : "none";
      } else if (r.dataset.addbooking !== undefined) addBooking();
      else if (r.dataset.unbook) {
        const b2 = bookings.find(x => String(x.id) === r.dataset.unbook);
        if (b2 && confirm(`Remove the ${b2.space} reservation on ${fmt(b2.date)}? The room shows as open again.`))
          api("/api/bookings/" + r.dataset.unbook, { method: "DELETE" })
            .then(() => { bookings = bookings.filter(x => String(x.id) !== r.dataset.unbook); renderBookings(); })
            .catch(e => toast(e.message, "warn"));
      }
      return;
    }
    const b = ev.target.closest("[data-edit],[data-archive],[data-new],[data-edpublish],[data-edsavedraft],[data-eddiscard],[data-edarchive],[data-histload],[data-savewindow],[data-addloc],[data-addhost],[data-delloc],[data-delhost],[data-period],[data-publish],[data-fmt],[data-dates],[data-editrow],[data-export]");
    if (!b) return;
    if (b.dataset.export !== undefined) { exportCsv(); return; }
    if (b.dataset.dates) {
      const d = document.querySelector(`[data-dates-for="${CSS.escape(b.dataset.dates)}"]`);
      if (d) d.style.display = d.style.display === "none" ? "" : "none";
      return;
    }
    if (b.dataset.editrow) {
      const [k, id] = b.dataset.editrow.split("|");
      openEditor(k, id);
      $("#f-scope").checked = false;   // editing one chosen date: default to just that date
      return;
    }
    if (b.dataset.fmt) {
      const ta = $("#f-desc"), t = b.dataset.fmt, a = ta.selectionStart, z = ta.selectionEnd;
      ta.value = ta.value.slice(0, a) + `<${t}>` + ta.value.slice(a, z) + `</${t}>` + ta.value.slice(z);
      ta.focus(); ta.setSelectionRange(a + t.length + 2, z + t.length + 2);
      return;
    }
    if (b.dataset.edit) openEditor(b.dataset.edit);
    else if (b.dataset.archive) archiveGroup(b.dataset.archive);
    else if (b.dataset.new !== undefined) openEditor(null);
    else if (b.dataset.edpublish !== undefined) edPublishClick();
    else if (b.dataset.edsavedraft !== undefined) edSaveDraftClick();
    else if (b.dataset.eddiscard !== undefined) discardWorkingCopy();
    else if (b.dataset.edarchive !== undefined) edArchiveClick();
    else if (b.dataset.histload !== undefined) loadVersion(b.dataset.histload);
    else if (b.dataset.savewindow !== undefined) saveWindow(b);
    else if (b.dataset.addloc !== undefined) {
      const v = $("#loc-new").value.trim();
      if (!v) return;
      if (!listSettings.locations.includes(v)) { listSettings.locations.push(v); saveLists(); }
      $("#loc-new").value = "";
      toast("Location saved. The event editor offers it now.");
    } else if (b.dataset.addhost !== undefined) {
      const v = $("#host-new").value.trim();
      if (!v) return;
      if (!listSettings.hosts.includes(v)) { listSettings.hosts.push(v); saveLists(); }
      $("#host-new").value = "";
      toast("Host saved. The event editor offers them now.");
    } else if (b.dataset.delloc !== undefined) {
      listSettings.locations.splice(Number(b.dataset.delloc), 1); saveLists();
    } else if (b.dataset.delhost !== undefined) {
      listSettings.hosts.splice(Number(b.dataset.delhost), 1); saveLists();
    }
    else if (b.dataset.period) { days = Number(b.dataset.period); loadAnalytics(); }
    else if (b.dataset.publish !== undefined) { b.disabled = true; api("/api/publish", { method: "POST" }).then(r => toast(r.note || "Publishing.")).catch(e => toast(e.message, "warn")).finally(() => b.disabled = false); }
  });
  document.addEventListener("click", ev => {
    const b = ev.target.closest("#rp-picks .pick, #rp-days .pick, #rp-endpicks .pick");
    if (!b) return;
    if (b.dataset.rp) rp.mode = b.dataset.rp;
    else if (b.dataset.wd !== undefined) { const n = Number(b.dataset.wd); rp.days.has(n) ? rp.days.delete(n) : rp.days.add(n); }
    else if (b.dataset.en) rp.end = b.dataset.en;
    rpRefresh();
  });
  document.addEventListener("change", ev => {
    if (["rp-ord", "rp-wd", "rp-times", "rp-until", "f-date"].includes(ev.target.id)) {
      if (ev.target.id === "rp-ord") rp.ord = ev.target.value;
      if (ev.target.id === "rp-wd") rp.wd = Number(ev.target.value);
      if (ev.target.id === "rp-times") rp.times = Number(ev.target.value);
      if (ev.target.id === "rp-until") rp.until = ev.target.value;
      if ($("#rp-builder").style.display !== "none") rpRefresh();
    }
  });
  document.addEventListener("change", ev => {
    if (ev.target.id === "f-occ" && editing && editing.group) openEditor(editing.group.key, ev.target.value);
    if (ev.target.id === "f-title" || ev.target.id === "f-date" || ev.target.id === "f-slug") $("#f-stem").textContent = stem({ Date: $("#f-date").value, Slug: $("#f-slug").value.trim(), Title: $("#f-title").value });
  });
  document.addEventListener("input", ev => { if (ev.target.id === "f-title" && !editing.row) $("#f-slug").placeholder = slugify(ev.target.value); });
  document.addEventListener("change", ev => {
    if (ev.target.id === "afile" && pendingAsset && ev.target.files && ev.target.files[0]) {
      sendAssetFile(ev.target.files[0]);
    }
  });
  document.addEventListener("click", ev => {
    const b = ev.target.closest("#ed-cancel");
    if (b && !b.disabled) cancelEvent();
  });
  document.addEventListener("click", ev => {
    const head = ev.target.closest("[data-chev]");
    if (!head || ev.target.closest("button,a,.mini")) return;
    head.closest(".acard").classList.toggle("open");
  });

  // Sign out must clear BOTH Access sessions: this site's cookie, and the one
  // on the Access team domain, or Access quietly signs the same person back in.
  // The site cookie goes first in the background; then a real visit to the team
  // domain's logout ends the other and returns straight to the login screen.
  const so = document.querySelector(".signout");
  if (so) so.addEventListener("click", ev => {
    ev.preventDefault();
    const done = () => {
      if (window.location.hostname === "localhost") { window.location.href = "/admin.html"; return; }
      window.location.href = `https://${ACCESS_TEAM}/cdn-cgi/access/logout?returnTo=`
        + encodeURIComponent("https://181residents.com/admin");
    };
    fetch("/cdn-cgi/access/logout", { credentials: "same-origin" }).catch(() => {}).finally(done);
  });

  boot();
})();
