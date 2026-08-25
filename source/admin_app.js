/* 181 Fremont admin. Talks to /api/* (Cloudflare Pages Functions, or dev_server.py locally).
   Staff only, so JavaScript is fine here. The resident site stays script-free. */
(function () {
  "use strict";
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const UNITS = 55;
  const CATS = ["Morning Offering", "Happy Hour", "Community Dinner", "Culinary Experience", "Enrichment Experience", "Signature Event", "Board Meeting"];
  const STATUSES = ["Draft", "Live", "Unpublished", "Archived"];
  const RSVPS = ["None", "Guest count", "Seat", "Paid seat"];
  const KIT = ["Web hero", "Nixplay still", "Nixplay video", "Elevator print", "Level 39 print", "Email header"];
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
    const gs = groups();
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
      return `<div class="erow ${cls(g.status)}${g.mixed ? " live" : ""}" data-key="${esc(g.key)}">
        <div class="ecell etitle"><span class="et">${esc(h.Title)}${extra}</span><span class="esub">${esc(h.Category)} &middot; ${when}${g.series ? ` &middot; ${g.upcoming.length} upcoming` : ""}</span></div>
        <div class="ecell"><span class="pill ${cls(g.status)}">${esc(g.mixed ? "Mixed" : g.status)}</span></div>
        <div class="ecell"><span class="lbl">RSVPs</span>${rsvp}</div>
        <div class="ecell"><span class="lbl">Asset kit</span>0 of 6</div>
        <div class="ecell eact">${g.series ? `<button class="mini ghost" data-dates="${esc(g.key)}">${g.rows.length} dates</button>` : ""}<button class="mini" data-edit="${esc(g.key)}">Edit</button>${g.status !== "Archived" ? `<button class="mini ghost" data-archive="${esc(g.key)}">Archive</button>` : ""}</div>
      </div>
      <div class="edates" data-dates-for="${esc(g.key)}" style="display:none">${g.rows.map(r => `
        <div class="edrow"><span class="edwhen">${esc(fmt(r.Date))} &middot; ${esc(r.Start)}</span>
          <span class="pill ${cls(r.Status)}">${esc(r.Status || "Draft")}</span>
          ${r.Moved ? '<span class="badge2">moved</span>' : ""}
          <button class="mini" data-editrow="${esc(g.key)}|${esc(r.id)}">Edit this date</button></div>`).join("")}
      </div>`;
    }).join("");
    $("#evcount").textContent = `${gs.length} listings, ${events.filter(e => e.Status === "Live" && e.Date >= today()).length} live upcoming dates. Nothing appears on the resident site until its status is Live.`;
  }

  // ---------------------------------------------------------------- editor
  function openEditor(key, rowId) {
    const g = key ? groups().find(x => x.key === key) : null;
    const row = g ? (rowId ? g.rows.find(r => r.id === rowId) : g.head) : null;
    editing = { group: g, row };
    const e = row || { Status: "Draft", Category: "Enrichment Experience", Location: "Level 39, Residents’ Club", Host: "Resident Experiences", RSVP: "Seat", Counted: true, Date: today() };
    $("#ed-title").textContent = row ? "Edit event" : "New event";
    $("#ed-pill").className = "pill " + cls(e.Status); $("#ed-pill").textContent = e.Status || "Draft";
    $("#ed-sub").textContent = row ? `${e.Title} · ${fmtLong(e.Date)}` : "Fill in the essentials, save as a draft, and come back to it.";
    // occurrence picker for a series
    const occ = $("#ed-occ");
    if (g && g.series) {
      occ.style.display = "";
      $("#f-occ").innerHTML = g.rows.map(r => `<option value="${esc(r.id)}"${r.id === e.id ? " selected" : ""}>${esc(fmt(r.Date))} · ${esc(r.Status || "Draft")}${r.Moved ? " · moved" : ""}</option>`).join("");
      $("#ed-scope").style.display = "";
      $("#f-scope").checked = true;
      $("#f-scope-n").textContent = String(g.upcoming.length);
    } else { occ.style.display = "none"; $("#ed-scope").style.display = "none"; $("#f-scope").checked = false; }
    // The repeat builder creates rows, so it only shows for a brand-new event.
    // An existing series is edited through the occurrence picker above.
    $("#rp-builder").style.display = row ? "none" : "";
    if (!row) { rp = { mode: "none", days: new Set(), ord: "Last", wd: 0, end: "cal", times: 6, until: "" }; rpRefresh(); }
    const set = (id, v) => { $(id).value = v == null ? "" : v; };
    set("#f-title", e.Title); set("#f-date", e.Date); set("#f-start", e.Start); set("#f-end", e.End);
    set("#f-loc", e.Location); set("#f-host", e.Host); set("#f-series", e.Series); set("#f-cap", e.Capacity);
    set("#f-price", e.Price); set("#f-cutoff", e.Cutoff); set("#f-desc", e.Description); set("#f-slug", e.Slug || "");
    $("#f-marquee").checked = e.Marquee === true || e.Marquee === "True";
    $$("input[name=cat]").forEach((r, i) => r.checked = CATS[i] === e.Category);
    $$("input[name=st]").forEach((r, i) => r.checked = STATUSES[i] === (e.Status || "Draft"));
    $$("input[name=rt]").forEach((r, i) => r.checked = RSVPS[i] === (e.RSVP || "None"));
    const counted = e.Counted === true || e.Counted === "True";
    $("#co-0").checked = counted; $("#co-1").checked = !counted;
    $("#f-stem").textContent = stem({ Date: e.Date, Slug: e.Slug, Title: e.Title });
    $("#ed-cancel").disabled = true;
    $("#ed-cancel-note").textContent = status.email ? "" : "Guest notifications switch on once RSVPs are collected on the site.";
    $("#ak").innerHTML = KIT.map(k => `<div class="akrow"><span class="akname">${k}<em>${k.startsWith("Nixplay") ? "1080 × 1920, portrait" : k.includes("print") ? "8.5 × 11, PDF 300 DPI" : k === "Web hero" ? "1600 × 900, JPG" : "1200 × 600, JPG"}</em></span><span class="akstate miss">Not uploaded</span><span class="akact"><span class="mini ghost" title="Uploads arrive with the next build">Upload</span></span></div>`).join("");
    go("editor");
  }

  function readForm() {
    const pick = (name, list) => { const i = $$(`input[name=${name}]`).findIndex(r => r.checked); return i < 0 ? list[0] : list[i]; };
    const title = $("#f-title").value.trim();
    const f = {
      Title: title, Date: $("#f-date").value, Start: $("#f-start").value.trim(), End: $("#f-end").value.trim(),
      Start24: to24($("#f-start").value), Location: $("#f-loc").value.trim(), Host: $("#f-host").value.trim() || "Resident Experiences",
      Category: pick("cat", CATS), Status: pick("st", STATUSES), RSVP: pick("rt", RSVPS),
      Capacity: $("#f-cap").value ? Number($("#f-cap").value) : null, Price: $("#f-price").value.trim(),
      Series: $("#f-series").value.trim(), Cutoff: $("#f-cutoff").value.trim(), Description: $("#f-desc").value.trim(),
      Marquee: $("#f-marquee").checked, Counted: $("#co-0").checked, Moved: editing.row ? !!editing.row.Moved : false,
      Slug: $("#f-slug").value.trim() || slugify(title),
    };
    return f;
  }

  function validate(f) {
    if (!f.Title) return "Give the event a title.";
    if (!f.Date) return "Pick a date.";
    if (!f.Start) return "Add a start time, like 5:30 PM.";
    if (f.Status === "Live" && !f.Description) return "A Live event needs a description, since residents will read it.";
    return null;
  }

  // Which field changes ripple across a series when "apply to every upcoming occurrence" is ticked.
  const SERIES_FIELDS = ["Title", "Start", "End", "Start24", "Location", "Host", "Category", "RSVP", "Capacity", "Price", "Series", "Cutoff", "Description", "Counted", "Image", "Status"];

  async function save(overrideStatus) {
    const f = readForm();
    if (overrideStatus) f.Status = overrideStatus;
    const err = validate(f); if (err) { toast(err, "warn"); return; }
    let told = false;
    const wasLive = editing.row && editing.row.Status === "Live";
    const touchesSite = wasLive || f.Status === "Live";
    const btns = $$("#ed-actions button"); btns.forEach(b => b.disabled = true);
    try {
      if (editing.row) {
        const applyAll = editing.group && editing.group.series && $("#f-scope").checked;
        const targets = applyAll ? editing.group.upcoming : [editing.row];
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
    finally { btns.forEach(b => b.disabled = false); $("#ed-cancel").disabled = true; }
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
    const live = events.filter(e => e.Status === "Live");
    const upcoming = live.filter(e => e.Date >= t && e.Category !== "Board Meeting")
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
    $("#nextlist").innerHTML = upcoming.slice(0, 6).map(e => `<div class="srow"><span class="slab">${esc(fmt(e.Date))}</span><span style="flex:1;font-size:15px;color:var(--ink)">${esc(e.Title)}</span><span class="sval" style="flex-basis:90px">${esc(e.Start)}</span></div>`).join("") || '<div class="nodata">Nothing scheduled.</div>';
    $$("#period button").forEach(b => b.classList.toggle("on", Number(b.dataset.days) === days));
  }

  // ---------------------------------------------------------------- rsvps
  // One RSVP row per person per event; heads = the count each row carries.
  // The summary is derived state, computed once and cached until rsvps change,
  // since the events list asks for it per row.
  let rsvpCache = null;
  function rsvpSummary() {
    if (rsvpCache) return rsvpCache;
    const t = today();
    const by = new Map();
    for (const r of rsvps) {
      if (r.event_date < t || r.status === "Cancelled") continue;
      if (!by.has(r.event_key)) by.set(r.event_key, {
        key: r.event_key, date: r.event_date, title: r.event_title, type: r.rsvp_type,
        parties: 0, heads: 0, waitParties: 0, waitHeads: 0, rows: [],
      });
      const s = by.get(r.event_key);
      s.rows.push(r);
      if (r.status === "Waitlist") { s.waitParties++; s.waitHeads += r.count; }
      else { s.parties++; s.heads += r.count; }
    }
    rsvpCache = [...by.values()].sort((a, b) => a.date.localeCompare(b.date));
    return rsvpCache;
  }

  function rsvpForGroup(g) {
    const keys = new Set(g.upcoming.map(stem));
    let heads = 0, wait = 0;
    for (const s of rsvpSummary()) if (keys.has(s.key)) { heads += s.heads; wait += s.waitHeads; }
    return { heads, wait };
  }

  function renderRsvps() {
    const box = $("#rsvplist"); if (!box) return;
    const sums = rsvpSummary();
    if (!sums.length) {
      box.innerHTML = '<div class="nodata">Nothing yet. Figures begin with the first RSVP made on the site.</div>';
      return;
    }
    const ev = key => events.find(e => stem(e) === key);
    box.innerHTML = sums.map(s => {
      const e = ev(s.key);
      const cap = e && e.Capacity ? ` of ${e.Capacity}` : "";
      const what = s.type === "guest" ? `${s.heads} outside guests` : `${s.heads}${cap} ${s.type === "paid" ? "seats" : "going"}`;
      const wait = s.waitHeads ? ` &middot; ${s.waitHeads} waitlisted` : "";
      const units = new Set(s.rows.map(r => r.unit).filter(Boolean));
      const dupUnit = units.size < s.rows.filter(r => r.unit).length;
      return `<div class="srow" style="cursor:pointer" data-rsvpkey="${esc(s.key)}"><span class="slab">${esc(fmt(s.date))}</span>
        <span style="flex:1;font-size:15px;color:var(--ink)">${esc(s.title)}${dupUnit ? ' <span class="flagmany" title="One unit holds more than one RSVP for this event">unit twice</span>' : ""}</span>
        <span class="sval" style="flex-basis:190px;white-space:nowrap">${what}${wait}</span></div>
        <div class="card" data-rsvpdetail="${esc(s.key)}" style="display:none;margin:4px 0 10px">
        ${s.rows.map(r => `<div class="srow"><span class="slab">${esc(r.unit || "Role")} &middot; ${esc(r.name)}</span>
          <span style="flex:1;font-size:14px;color:var(--ink-soft)">${r.status === "Waitlist" ? "Waitlist" : (s.type === "guest" ? `${r.count} guest${r.count === 1 ? "" : "s"}` : `party of ${r.count}`)}${r.names ? ` &middot; ${esc(r.names)}` : ""}</span>
          <span class="sval" style="flex-basis:90px;font-size:12px;color:var(--stone)">${esc((r.created || "").slice(0, 10))}</span>
          ${r.status === "Waitlist" ? `<button class="mini" data-wconfirm="${r.id}" title="Give this party the freed seats, then let them know">Confirm seats</button>` : ""}</div>`).join("")}
        </div>`;
    }).join("");
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
    const row = p => `<div class="rrow${p.status !== "Active" || p.expired ? " off" : ""}">
      <span class="rname">${esc(p.name)}${p.email ? `<em>${esc(p.email)}</em>` : ""}</span>
      <span><span class="rcode">${esc(p.code)}</span></span>
      <span>${pill(p)}</span>
      <span class="ecell" style="font-size:12px;color:var(--stone)">${esc((p.created || "").slice(0, 10))}</span>
      <span class="eact">
        ${p.email && p.status === "Active" ? `<a class="mini" href="${mailHref(p)}" title="Opens your own mail app with the code written out">Email code</a>` : ""}
        <button class="mini" data-rotate="${p.id}" title="A fresh code; the old one stops working everywhere">Rotate</button>
        <button class="mini ghost" data-ends="${p.id}" title="Set or clear the date this code stops working">Ends</button>
        <button class="mini ghost" data-toggle="${p.id}">${p.status === "Active" ? "Disable" : "Restore"}</button>
      </span></div>`;

    let html = "";
    if (roles.length) {
      html += `<div class="evlist" style="margin-bottom:14px"><div class="unithead">Role accounts</div>${roles.map(row).join("")}</div>`;
    }
    html += `<div class="evlist">` + units.map(u => {
      const rows = byUnit.get(u);
      const activeCodes = rows.filter(p => p.status === "Active" && !p.expired).length;
      const flag = activeCodes > 4 ? ` <span class="flagmany" title="More than four working codes on one unit is worth a look">${activeCodes} codes</span>` : "";
      return `<div class="unithead">Unit ${esc(u)}${flag}</div>` + rows.map(row).join("");
    }).join("") + `</div>`;
    if (!people.length && !roles.length) html = '<div class="nodata" style="padding:20px">Nobody yet. Add people above, or paste the whole building at once.</div>';
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
    };
    try {
      const d = await api("/api/residents", { method: "POST", body: JSON.stringify(body) });
      residents.push(...d.residents); renderResidents();
      ["#r-unit", "#r-name", "#r-email", "#r-ends"].forEach(s => $(s).value = "");
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

  // ---------------------------------------------------------------- assets, messages
  function renderAssets() {
    const gs = groups().filter(g => g.status !== "Archived");
    $("#assets").innerHTML = gs.map(g => `<div class="acard"><div class="ahead"><span class="at">${esc(g.head.Title)}</span><span class="asub">${esc(g.series ? g.head.Series : fmt(g.head.Date))} &middot; <code>${esc(stem(g.head))}</code></span></div><div class="chips">${KIT.map(k => `<span class="chip miss"><i>+</i>${k}</span>`).join("")}</div></div>`).join("");
  }

  // ---------------------------------------------------------------- spaces
  // Reservations for the Level 39 rooms. Residents see only "Reserved" with the
  // space and hours on /spaces; the note stays in this admin.
  let bookings = [];

  function renderBookings() {
    const box = $("#bklist"); if (!box) return;
    const t = today();
    const ahead = bookings.filter(b => b.date >= t).sort((a, b2) => (a.date + (a.start24 || "")).localeCompare(b2.date + (b2.start24 || "")));
    $("#bkcount").textContent = ahead.length
      ? `${ahead.length} reservation${ahead.length === 1 ? "" : "s"} ahead. Residents see the space and hours only, marked Reserved, never who or why.`
      : "Nothing reserved ahead. Residents see open rooms and can walk in anytime.";
    box.innerHTML = ahead.map(b => `<div class="rrow">
      <span class="rname">${esc(b.space)}${b.note ? `<em>${esc(b.note)} · staff only</em>` : ""}</span>
      <span class="ecell">${esc(fmt(b.date))}</span>
      <span class="ecell">${esc(b.start || "")}${b.end_time ? " – " + esc(b.end_time) : ""}</span>
      <span></span>
      <span class="eact"><button class="mini ghost" data-unbook="${b.id}">Remove</button></span>
    </div>`).join("");
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

  async function addBooking() {
    const body = {
      space: $("#bk-space").value.trim(), date: $("#bk-date").value,
      start: $("#bk-start").value.trim(), end: $("#bk-end").value.trim(),
      note: $("#bk-note").value.trim(),
    };
    if (!body.space || !body.date) { toast("A space and a date are needed.", "warn"); return; }
    try {
      const d = await api("/api/bookings", { method: "POST", body: JSON.stringify(body) });
      bookings.push(d.booking); renderBookings();
      ["#bk-space", "#bk-date", "#bk-start", "#bk-end", "#bk-note"].forEach(s => $(s).value = "");
      toast("Reserved. It shows on the Spaces page immediately.");
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
    try { role = (await api("/api/whoami")).role || "staff"; } catch (e) { role = "staff"; }
    document.body.classList.add("role-" + role);
    const bar = $("#sysbar");
    if (status.mode === "local") bar.textContent = `Local preview · saving to this computer, publishing rebuilds the local calendar · signed in as ${role}`;
    else if (status.db) bar.textContent = "Connected · " + (status.publish ? "saves publish to 181residents.com within a couple of minutes" : "publishing not yet wired, changes stay in the database")
      + (status.signin ? "" : " · resident sign-in not switched on yet: set SESSION_SECRET in the Pages settings")
      + (role === "none" ? " · Access did not pass your email through, so nothing will load: reload the page, or sign out of Access and back in" : "");
    else bar.textContent = "Events database not linked yet · add the D1 binding named DB in the Pages settings";

    // The desk tier works with people and codes; the calendar is not its business,
    // so it lands on Residents and never asks for what the server would refuse.
    if (role === "desk") {
      go("res");
      loadResidents();
      loadMsgs();
      loadBookings();
      return;
    }
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
    renderAll();
    loadAnalytics();
    loadResidents();
    loadMsgs();
    loadBookings();
  }

  document.addEventListener("click", ev => {
    const r = ev.target.closest("[data-rotate],[data-ends],[data-toggle],[data-addres],[data-addbulk],[data-printcards],[data-mreplied],[data-marchive],[data-wconfirm],[data-rsvpkey],[data-addbooking],[data-unbook]");
    if (r) {
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
        api("/api/rsvps/" + r.dataset.wconfirm, { method: "PATCH", body: JSON.stringify({ status: "Confirmed" }) })
          .then(u => {
            const row = rsvps.find(x => String(x.id) === String(u.id));
            if (row) row.status = u.status;
            rsvpCache = null;
            renderDash(); renderEvents();
            toast("Confirmed. Kindly let the resident know their seats came through.");
          })
          .catch(e => toast(e.message, "warn"));
      } else if (r.dataset.rsvpkey) {
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
    const b = ev.target.closest("[data-edit],[data-archive],[data-new],[data-save],[data-period],[data-publish],[data-fmt],[data-dates],[data-editrow],[data-export]");
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
    else if (b.dataset.save) save(b.dataset.save === "keep" ? null : b.dataset.save);
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

  boot();
})();
