import { json } from "../_lib.js";

// GET /api/analytics?days=30
// Reads Cloudflare Web Analytics (free, privacy-first, no cookies) through the GraphQL API.
// Needs CF_API_TOKEN (permission: Account Analytics Read), CF_ACCOUNT_ID, and CF_SITE_TAG
// (the Web Analytics site tag shown in the dashboard). Returns zeros when not configured.
const QUERY = `
query ($accountTag: String!, $siteTag: String!, $since: Date!, $until: Date!) {
  viewer { accounts(filter: { accountTag: $accountTag }) {
    byDay: rumPageloadEventsAdaptiveGroups(limit: 100, orderBy: [date_ASC],
      filter: { siteTag: $siteTag, date_geq: $since, date_leq: $until }) {
      count sum { visits } dimensions { date } }
    byPath: rumPageloadEventsAdaptiveGroups(limit: 50, orderBy: [count_DESC],
      filter: { siteTag: $siteTag, date_geq: $since, date_leq: $until }) {
      count sum { visits } dimensions { requestPath } }
    byDevice: rumPageloadEventsAdaptiveGroups(limit: 10, orderBy: [count_DESC],
      filter: { siteTag: $siteTag, date_geq: $since, date_leq: $until }) {
      count dimensions { deviceType } }
    byReferer: rumPageloadEventsAdaptiveGroups(limit: 20, orderBy: [count_DESC],
      filter: { siteTag: $siteTag, date_geq: $since, date_leq: $until }) {
      count dimensions { refererHost } }
  } }
}`;

// QR standees land on their own paths so scans are attributable. Keep in step with build_site.py.
export const SOURCES = { "/q/lobby/": "QR, Lobby", "/q/coffee/": "QR, Coffee Bar",
  "/q/fitness/": "QR, Fitness Center", "/q/office/": "QR, Leo's Office", "/q/email/": "Weekly email" };

export async function onRequestGet({ request, env }) {
  const days = Math.min(90, Math.max(1, Number(new URL(request.url).searchParams.get("days") || 30)));
  const until = new Date(), since = new Date(until.getTime() - (days - 1) * 86400000);
  const iso = d => d.toISOString().slice(0, 10);
  const empty = { configured: false, days, since: iso(since), until: iso(until),
    pageviews: 0, visits: 0, byDay: [], byPath: [], bySource: [], byDevice: [], byReferer: [] };
  if (!(env.CF_API_TOKEN && env.CF_ACCOUNT_ID && env.CF_SITE_TAG)) return json(empty);

  const r = await fetch("https://api.cloudflare.com/client/v4/graphql", {
    method: "POST",
    headers: { "Authorization": `Bearer ${env.CF_API_TOKEN}`, "content-type": "application/json" },
    body: JSON.stringify({ query: QUERY, variables: {
      accountTag: env.CF_ACCOUNT_ID, siteTag: env.CF_SITE_TAG, since: iso(since), until: iso(until) } }),
  });
  if (!r.ok) return json({ ...empty, error: "Cloudflare " + r.status }, 502);
  const data = await r.json();
  const acc = data?.data?.viewer?.accounts?.[0];
  if (!acc) return json({ ...empty, error: "No analytics account data", detail: data.errors }, 502);

  const byDay = acc.byDay.map(g => ({ date: g.dimensions.date, views: g.count, visits: g.sum.visits }));
  const byPath = acc.byPath.map(g => ({ path: g.dimensions.requestPath, views: g.count, visits: g.sum.visits }));
  const bySource = Object.entries(SOURCES).map(([path, label]) => {
    const hit = byPath.find(p => p.path === path);
    return { label, path, visits: hit ? hit.visits : 0 };
  });
  const direct = byPath.filter(p => !(p.path in SOURCES)).reduce((a, p) => a + p.visits, 0);
  bySource.push({ label: "Direct or saved to home screen", path: "/", visits: direct });
  return json({ ...empty, configured: true,
    pageviews: byDay.reduce((a, d) => a + d.views, 0), visits: byDay.reduce((a, d) => a + d.visits, 0),
    byDay, byPath, bySource,
    byDevice: acc.byDevice.map(g => ({ device: g.dimensions.deviceType, views: g.count })),
    byReferer: acc.byReferer.map(g => ({ host: g.dimensions.refererHost || "direct", views: g.count })) });
}
