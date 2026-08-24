/* 181 Fremont admin. Talks to /api/* (Cloudflare Pages Functions, or dev_server.py locally).
   Staff only, so JavaScript is fine here. The resident site stays script-free. */
(function () {
  "use strict";
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const UNITS = 55;
  const CATS = ["Morning Offering", "Happy Hour", "Community Dinner", "Culinary Experience", "Enrichment Experience", "Signature Event"];
  const STATUSES = ["Draft", "Live", "Unpublished", "Archived"];
  const RSVPS = ["None", "Guest count", "Seat", "Paid seat"];
  const KIT = ["Web hero", "Nixplay still", "Nixplay video", "Elevator print", "Level 39 print", "Email header"];
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"];
  const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  let events = [], status = {}, analytics = null, days = 30, editing = null;

  // ---------------------------------------------------------------- helpers
  const today = () => new Date().toISOString().slice(0, 10);
  const fmt = iso => { if (!iso) return ""; const d = new Date(iso + "T12:00:00"); return `${DOW[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}`; };
  const fmtLong = iso => { if (!iso) return ""; const d = new Date(iso + "T12:00:00"); return `${["January","February","March","April","May","June","July","August","September","October","November","December"][d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`; };
  const slugify = s => s.toLowerCase().replace(/&amp;|&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const to24 = t => { const m = /(\d{1,2})(?::(\d{2}))?\s*(AM|PM)/i.exec(t || ""); if (!m) return "0000"; let h = +m[1] % 12; if (/pm/i.test(m[3])) h += 12; return String(h).padStart(2, "0") + (m[2] || "00"); };
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
  // One Airtable row per occurrence. The admin shows a series as one line.
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
    const gs = groups();
    const badge = (t, c) => ` <span class="badge2 ${c || ""}">${esc(t)}</span>`;
    $("#evlist").innerHTML = gs.map(g => {
      const h = g.head;
      const when = g.series ? `${esc(h.Series)} &middot; next ${esc(fmt(h.Date))}` : `${esc(fmt(h.Date))}, ${esc(h.Start)}`;
      const extra = (g.series ? badge("Series") : "") + (h.Price ? badge(h.Price, "pay") : "") +
        (g.rows.some(r => r.Moved) ? badge(g.rows.filter(r => r.Moved).length + " moved") : "") +
        (h.Counted === true || h.Counted === "True" ? "" : badge("Not counted", "ext"));
      const rsvp = h.RSVP === "None" || !h.RSVP ? "Drop in" : (h.Capacity ? `0 of ${h.Capacity}` : "Open");
      return `<div class="erow ${cls(g.status)}${g.mixed ? " live" : ""}" data-key="${esc(g.key)}">
        <div class="ecell etitle"><span class="et">${esc(h.Title)}${extra}</span><span class="esub">${esc(h.Category)} &middot; ${when}${g.series ? ` &middot; ${g.upcoming.length} upcoming` : ""}</span></div>
        <div class="ecell"><span class="pill ${cls(g.status)}">${esc(g.mixed ? "Mixed" : g.status)}</span></div>
        <div class="ecell"><span class="lbl">RSVPs</span>${rsvp}</div>
        <div class="ecell"><span class="lbl">Asset kit</span>0 of 6</div>
        <div class="ecell eact"><button class="mini" data-edit="${esc(g.key)}">Edit</button>${g.status !== "Archived" ? `<button class="mini ghost" data-archive="${esc(g.key)}">Archive</button>` : ""}</div>
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
    const wasLive = editing.row && editing.row.Status === "Live";
    const touchesSite = wasLive || f.Status === "Live";
    const btns = $$("#ed-actions button"); btns.forEach(b => b.disabled = true);
    try {
      if (editing.row) {
        const applyAll = editing.group && editing.group.series && $("#f-scope").checked;
        const targets = applyAll ? editing.group.upcoming : [editing.row];
        for (const r of targets) {
          const patch = r.id === editing.row.id ? f : Object.fromEntries(SERIES_FIELDS.map(k => [k, f[k]]));
          const upd = await api("/api/events/" + encodeURIComponent(r.id), { method: "PATCH", body: JSON.stringify(patch) });
          Object.assign(r, upd);
        }
      } else {
        const created = await api("/api/events", { method: "POST", body: JSON.stringify(f) });
        events.push(created); editing.row = created;
      }
      renderAll();
      if (touchesSite && status.publish) {
        toast("Saved. Publishing the calendar, live in a couple of minutes.");
        api("/api/publish", { method: "POST" }).then(r => toast(r.note || "Published.")).catch(e => toast("Saved, but publishing failed: " + e.message, "warn"));
      } else {
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
    const upcoming = live.filter(e => e.Date >= t).sort((a, b) => (a.Date + a.Start24).localeCompare(b.Date + b.Start24));
    const a = analytics || { pageviews: 0, visits: 0, byDay: [], bySource: [], byDevice: [], sample: false, configured: false };
    $("#dash-period").textContent = `Last ${days} days · ${UNITS} occupied units`;
    $("#dash-note").style.display = a.configured ? "none" : "";
    $("#dash-note").innerHTML = a.sample
      ? "<strong>Sample figures.</strong> This is what the dashboard looks like with a month of traffic. Real numbers replace them the day the site goes live."
      : "<strong>Analytics not connected yet.</strong> Traffic figures begin once Cloudflare Web Analytics is switched on for the site.";
    const perUnit = a.visits ? (a.visits / UNITS).toFixed(1) : "0";
    $("#kpis").innerHTML = [
      ["Visits", a.visits, `${a.pageviews} page views · ${perUnit} per unit`],
      ["Busiest day", a.byDay.length ? Math.max(...a.byDay.map(d => d.visits)) : 0, a.byDay.length ? "visits on " + fmt(a.byDay.reduce((m, d) => d.visits > m.visits ? d : m).date) : "no traffic yet"],
      ["Upcoming dates", upcoming.length, `${new Set(upcoming.map(e => e.Slug)).size} live listings on the calendar`],
      ["Next up", upcoming[0] ? fmt(upcoming[0].Date).replace(/^\w+, /, "") : "None", upcoming[0] ? `${upcoming[0].Title}, ${upcoming[0].Start}` : "Nothing scheduled"],
    ].map(([k, v, n]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${esc(v)}</div><div class="n">${esc(n)}</div></div>`).join("");
    $("#daychart").innerHTML = dayChart(a.byDay);
    $("#sources").innerHTML = a.bySource.length ? bars(a.bySource, "visits", a.visits) : '<div class="nodata">Sources appear once the QR standees and the weekly email are in use.</div>';
    const devs = a.byDevice.map(d => ({ label: { mobile: "Phone", tablet: "iPad or tablet", desktop: "Computer" }[d.device] || d.device, views: d.views }));
    $("#devices").innerHTML = devs.length ? bars(devs, "views", devs.reduce((s, d) => s + d.views, 0)) : '<div class="nodata">No device data yet.</div>';
    const byCat = CATS.map(c => ({ label: c, n: upcoming.filter(e => e.Category === c).length })).filter(c => c.n);
    $("#bycat").innerHTML = bars(byCat, "n");
    $("#nextlist").innerHTML = upcoming.slice(0, 6).map(e => `<div class="srow"><span class="slab">${esc(fmt(e.Date))}</span><span style="flex:1;font-size:15px;color:var(--ink)">${esc(e.Title)}</span><span class="sval" style="flex-basis:90px">${esc(e.Start)}</span></div>`).join("") || '<div class="nodata">Nothing scheduled.</div>';
    $$("#period button").forEach(b => b.classList.toggle("on", Number(b.dataset.days) === days));
  }

  // ---------------------------------------------------------------- assets, messages
  function renderAssets() {
    const gs = groups().filter(g => g.status !== "Archived");
    $("#assets").innerHTML = gs.map(g => `<div class="acard"><div class="ahead"><span class="at">${esc(g.head.Title)}</span><span class="asub">${esc(g.series ? g.head.Series : fmt(g.head.Date))} &middot; <code>${esc(stem(g.head))}</code></span></div><div class="chips">${KIT.map(k => `<span class="chip miss"><i>+</i>${k}</span>`).join("")}</div></div>`).join("");
  }

  function renderAll() { renderEvents(); renderDash(); renderAssets(); }

  // ---------------------------------------------------------------- boot
  async function loadAnalytics() {
    try { analytics = await api("/api/analytics?days=" + days); } catch (e) { analytics = null; }
    renderDash();
  }

  async function boot() {
    try { status = await api("/api/status"); } catch (e) { status = {}; }
    const bar = $("#sysbar");
    if (status.mode === "local") bar.textContent = "Local preview · saving to this computer, publishing rebuilds the local calendar";
    else if (status.airtable) bar.textContent = "Connected · " + (status.publish ? "saves publish to 181residents.com within a couple of minutes" : "publishing not yet wired, changes stay in Airtable");
    else bar.textContent = "Not connected to Airtable yet · the page is read-only until the base is linked";
    try { const d = await api("/api/events"); events = d.events; }
    catch (e) { $("#evlist").innerHTML = `<div class="erow"><div class="ecell" style="color:var(--stone)">Could not load events: ${esc(e.message)}</div></div>`; }
    renderAll();
    loadAnalytics();
  }

  document.addEventListener("click", ev => {
    const b = ev.target.closest("[data-edit],[data-archive],[data-new],[data-save],[data-period],[data-publish]");
    if (!b) return;
    if (b.dataset.edit) openEditor(b.dataset.edit);
    else if (b.dataset.archive) archiveGroup(b.dataset.archive);
    else if (b.dataset.new !== undefined) openEditor(null);
    else if (b.dataset.save) save(b.dataset.save === "keep" ? null : b.dataset.save);
    else if (b.dataset.period) { days = Number(b.dataset.period); loadAnalytics(); }
    else if (b.dataset.publish !== undefined) { b.disabled = true; api("/api/publish", { method: "POST" }).then(r => toast(r.note || "Publishing.")).catch(e => toast(e.message, "warn")).finally(() => b.disabled = false); }
  });
  document.addEventListener("change", ev => {
    if (ev.target.id === "f-occ" && editing && editing.group) openEditor(editing.group.key, ev.target.value);
    if (ev.target.id === "f-title" || ev.target.id === "f-date" || ev.target.id === "f-slug") $("#f-stem").textContent = stem({ Date: $("#f-date").value, Slug: $("#f-slug").value.trim(), Title: $("#f-title").value });
  });
  document.addEventListener("input", ev => { if (ev.target.id === "f-title" && !editing.row) $("#f-slug").placeholder = slugify(ev.target.value); });

  boot();
})();
