# 181 Fremont Resident Events

The resident calendar for 181residents.com. Static site, no build step, no dependencies.

---

## Deploying to Cloudflare Pages

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Upload assets**
2. Name the project `181residents`
3. Drag this whole folder in
4. **Deploy**
5. Custom domains → **Set up a custom domain** → `181residents.com` (and `www`)

DNS is automatic when the domain is registered in the same Cloudflare account. HTTPS is issued within a few minutes.

To update later, drag the folder in again. Every deploy keeps the previous one, so a rollback is one click.

---

## What is in here

| File | What it is |
|---|---|
| `index.html` | The whole resident site. Every screen, every event, self-contained. |
| `admin.html` | The admin prototype. Not linked from the resident site. |
| `manifest.webmanifest` | Name, colours, and icons for the home-screen install. |
| `icon.svg`, `icon-512.png`, `icon-192.png` | App icons, the bay mark. |
| `icon-maskable-512.png` | Android variant, inset for circular cropping. |
| `apple-touch-icon.png` | 180 × 180 for iPhone. |
| `favicon-32.png` | Browser tab. |
| `robots.txt` | Keeps the site out of search results while it is resident-only. |
| `_headers` | Basic security headers, read by Cloudflare Pages. |

---

## How it is built

Everything is generated from three Python files, which are not deployed:

- `events_data.py`: the calendar. Recurring series generate their own occurrences across a date range; one-offs are listed individually; `SERIES_OVERRIDES` moves or skips a single occurrence without disturbing the pattern.
- `build_proto.py`: renders the resident site.
- `build_admin.py`: renders the admin.
- `build_site.py`: runs both, adds the manifest, icons, and install prompt, and writes this folder.

To add an event, add a row in Airtable and run `python source/publish.py` (see `airtable/SETUP.md`). Until Airtable is set up, edit `events_data.py` and run `python source/build_site.py`. To extend the calendar into another month, move `RANGE_END`.

- `airtable_fields.py`: the column contract between Airtable and the generator.
- `airtable_export.py`: writes `airtable/events_import.csv` for the one-time import.
- `publish.py`: pulls Published rows from Airtable into `events_live.json` and rebuilds. When that file exists it replaces the series and one-offs in `events_data.py`; delete it to fall back.

### Why there is no framework

The site has to work on a 78-year-old's iPad and in whatever sandboxed preview someone forwards it into. Navigation, month switching, view toggles, day panels and RSVP states all run on CSS `:checked` selectors, so the calendar works with JavaScript entirely disabled. The only script on the page is the save-to-home-screen prompt, which is progressive enhancement and degrades to nothing.

---

## What is not built yet

The site is complete as a calendar. These need accounts and a backend:

| Piece | Needs |
|---|---|
| Event editing | Airtable base, see `airtable/SETUP.md`. Publishing is a manual script run until the GitHub Action exists. |
| RSVP submission | Airtable, same base as the events. |
| Message form | Done for now: posts to `mailto:leonardo@181sf.com` with topic, message, optional name, unit, and email. Replace with an Airtable form once login exists. |
| Resident login | Cloudflare Access, one-time email PIN. Free to 50 users. |
| Payment ($75 dinner) | Stripe, in the building's name rather than a personal account. |
| Analytics | Cloudflare Web Analytics (free, no cookies) or Plausible. Either is a script beacon, so it only counts residents with JavaScript on, which is the honest trade for a no-JS site. Each QR standee links with its own tag, e.g. `181residents.com/?from=lobby`, so scans are attributable. Views, RSVPs, and scans by source feed the monthly report and the admin dashboard. |

RSVP buttons currently show their confirmation state without sending anything. The message button works.

### Nixplay frames

Bar, lobby, and Level 7 are all portrait. Event stills for the frames are 1080 × 1920. The frames accept email at the building's Nixplay address, which is a credential and lives outside this repo.
