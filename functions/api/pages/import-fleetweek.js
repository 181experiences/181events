import { json, noDb, adminRole, forbidden, ensureResidentTables, accessEmail } from "../../_lib.js";

// One-time migration: the hardcoded Fleet Week page, reborn as a builder page.
// Visiting /api/pages/import-fleetweek in the signed-in admin creates it as a
// DRAFT with the full block content for review; publishing it hands /fleetweek
// over to the builder (build_site renders the hardcoded module only while no
// published builder page claims the slug). Idempotent: if a fleetweek page
// already exists, nothing is made twice. Delete this file, fleetweek_page.py,
// and the build fallback once the handover has happened.

const BLOCKS = [
  { kind: "feature",
    heading: "Watch the air show from the Terrace",
    when: "Friday, October 9 to Sunday, October 11 · Noon to 4:00 PM",
    body: "The air show flies over the Bay from noon to 4:00 each day, and the Terrace looks right at it. The Residents’ Club will be pouring lemonade and ice water through the show, with popcorn, chips, and snacks set out alongside.\n\nThe Blue Angels close the show each afternoon, flying roughly 3:00 to 4:00; if you only come up for one hour, that is the hour. No sign-up needed; just come up." },
  { kind: "heading", heading: "Your Fleet Week cheat sheet",
    sub: "The week at a glance, from the city’s official program. Tap a day to open it." },
  { kind: "fold", title: "Wednesday, October 7",
    lines: "10:00 AM : Ship tours begin: Pier 27 until 1:00, Pier 35 until 4:00. Free walk-aboard visits with the sailors and crews.\n2:00 PM : USAF Band of the Golden West at Ghirardelli Square\n3:00 PM : Navy Band Southwest woodwinds at Grace Cathedral\n5:00 PM : Military bands at Huntington Park, Japantown, and Pier 39" },
  { kind: "fold", title: "Thursday, October 8",
    lines: "10:00 AM : Ship tours at Piers 27 and 35, until 4:00\n12:00 PM : Navy Band Southwest at the Ferry Building back plaza\n6:00 PM : Honor Our Fallen ceremony at the Marines’ Memorial\n7:00 PM : Heroes Block Party with the Navy Band Destroyers" },
  { kind: "fold", title: "Friday, October 9",
    ours: "The Residents’ Club · lemonade, water, and snacks for the air show · noon to 4:00",
    lines: "11:00 AM : Parade of Ships along the waterfront, the fleet arriving under the Golden Gate\n12:00 PM : Air show over the Bay until 4:00, flown between the Golden Gate Bridge and Alcatraz; the Blue Angels close the show\nAll day : Neighborhood concerts across the city" },
  { kind: "fold", title: "Saturday, October 10",
    ours: "The Residents’ Club · lemonade, water, and snacks for the air show · noon to 4:00",
    lines: "10:00 AM : K9 Heroes at Duboce Park, until 11:00\n10:00 AM : Fleet Fest at Fisherman’s Wharf until 7:00: live music, food, and a beer garden at the SkyStar Wheel, and the Service & Safety Expo at Pier 27\n10:00 AM : Ship tours at Piers 27 and 35, until 4:00\n12:00 PM : Air show over the Bay until 4:00; the Blue Angels close the show" },
  { kind: "fold", title: "Sunday, October 11",
    ours: "The Residents’ Club · lemonade, water, and snacks for the air show · noon to 4:00",
    lines: "10:00 AM : Fleet Fest at the SkyStar Wheel, until 5:00\n10:00 AM : Ship tours at Piers 27 and 35, until 4:00\n12:00 PM : Air show over the Bay until 4:00; the Blue Angels close the final show of the year\n12:30 PM : Fleet Week bands march in the Italian Heritage Parade, North Beach" },
  { kind: "fold", title: "Monday, October 12",
    lines: "9:00 AM : Last ship tours: Pier 35 until noon\n9:00 AM : High School Band Challenge at the Golden Gate Park Bandshell, until noon" },
  { kind: "heading", heading: "Worth knowing" },
  { kind: "bullets",
    lines: "San Francisco has hosted Fleet Week since 1981, and today it is one of the largest in the country.\nThe air show is flown over the water between the Golden Gate Bridge and Alcatraz, which is exactly the stretch the Terrace faces.\nThis year’s lineup includes the U.S. Navy Blue Angels, the Air Force F-22 Raptor, the Marine Corps F-35B, the Patriots Jet Team, and a United Airlines 777 flying a fully choreographed demonstration.\nWatching from Marina Green is free; so are the ship tours and nearly every event of the week.\nNavy ships open their decks at Piers 27 and 35 every day from Wednesday through Monday; you can walk aboard and meet the crews." },
  { kind: "heading", heading: "Where to go in the city" },
  { kind: "links",
    lines: "Marina Green : The air show’s festival center, Friday through Sunday. Free general admission, food, and the loudest seat in the house.\nFisherman’s Wharf and the SkyStar Wheel : Fleet Fest on Saturday (10 to 7) and Sunday (10 to 5): live music, food, a beer garden, classic and military vehicles, and family activities.\nPier 27 : The Service & Safety Expo, Saturday and Sunday: first responders, live demonstrations, and equipment up close.\nPiers 27 and 35 : Ship tours, Wednesday through Monday. Lines move best in the morning.\nA resident’s tip : The waterfront is one long walk from the Ferry Building to the Wharf; skip the parking and take Muni or your feet. Afternoons turn cool when the fog comes to watch too, so bring a layer." },
  { kind: "links",
    lines: "Maps, the full program, and air show tickets : https://fleetweeksf.org : fleetweeksf.org" },
];

export async function onRequestGet({ request, env }) {
  const err = noDb(env); if (err) return err;
  const role = await adminRole(request, env);
  if (!role || role === "desk") return forbidden();
  await ensureResidentTables(env);
  const existing = await env.DB.prepare("SELECT id, status FROM pages WHERE slug='fleetweek'").first();
  if (existing) return json({ note: `Fleet Week is already in Pages (${existing.status}). Nothing was made twice.` });
  const who = (await accessEmail(request)) || env.DEV_ROLE || "staff";
  const now = new Date().toISOString();
  await env.DB.prepare(
    `INSERT INTO pages (title, slug, eyebrow, lede, blocks, status, created, updated, updated_by)
     VALUES (?, 'fleetweek', ?, ?, ?, 'Draft', ?, ?, ?)`)
    .bind("Fleet Week 2026",
      "The Residents’ Club · October 4 to 12",
      "The fleet is in, the bands are out, and the Blue Angels are back over the Bay. Here is our plan for the show, and a resident’s cheat sheet to the whole week.",
      JSON.stringify(BLOCKS), now, now, who).run();
  return json({ note: "Fleet Week imported as a Draft in Pages. Open it there, read it over, and Publish; the address hands over seamlessly." });
}
