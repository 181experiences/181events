# 181 Fremont Resident Events

The resident calendar for 181residents.com. Static site, no build step, no dependencies.

---

## Deploying

See `DEPLOY.md` at the root of the repository. The short version: the site is built by Cloudflare Pages from the GitHub repository, the admin at `/admin.html` edits events in Cloudflare D1, and saving a Live event rebuilds the calendar by itself.

## Deploying by hand, the fallback

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
| `admin.html` | The staff admin: dashboard, events, assets, messages, instructions. Reads and writes through `/api/*`. Not linked from the resident site; protected by Cloudflare Access. |
| `q/` | One copy of the calendar per QR standee, so scans are counted by source. |
| `manifest.webmanifest` | Name, colours, and icons for the home-screen install. |
| `icon.svg`, `icon-512.png`, `icon-192.png` | App icons, the bay mark. |
| `icon-maskable-512.png` | Android variant, inset for circular cropping. |
| `apple-touch-icon.png` | 180 × 180 for iPhone. |
| `favicon-32.png` | Browser tab. |
| `robots.txt` | Keeps the site out of search results while it is resident-only. |
| `events_seed.json` | The opening calendar, used once to fill an empty events database. |
| `fonts/` | Marcellus and Hanken Grotesk, served from here. No outside font servers. |
| `_headers` | Basic security headers, read by Cloudflare Pages. |

---

## How it is built

Everything is generated from three Python files, which are not deployed:

- `events_data.py`: the calendar. Recurring series generate their own occurrences across a date range; one-offs are listed individually; `SERIES_OVERRIDES` moves or skips a single occurrence without disturbing the pattern.
- `build_proto.py`: renders the resident site.
- `build_admin.py`: renders the admin.
- `build_site.py`: runs both, adds the manifest, icons, and install prompt, and writes this folder.

To add an event, use the admin page, or before launch run `python source/publish.py` (see `DEPLOY.md`). Until the database is linked, edit `events_data.py` and run `python source/build_site.py`. To extend the calendar into another month, move `RANGE_END`.

- `fields.py`: the field contract shared by the builders, the API, and the database.
- `make_seed.py`: writes `events_seed.json`, the opening calendar that seeds an empty database.
- `publish.py`: pulls Live rows from the D1 events database into `events_live.json` and rebuilds. When that file exists it replaces the series and one-offs in `events_data.py`; delete it to fall back.

### Why there is no framework

The site has to work on a 78-year-old's iPad and in whatever sandboxed preview someone forwards it into. Navigation, month switching, view toggles, day panels and RSVP states all run on CSS `:checked` selectors, so the calendar works with JavaScript entirely disabled. The only script on the page is the save-to-home-screen prompt, which is progressive enhancement and degrades to nothing.

---

## What is not built yet

The site is complete as a calendar. These need accounts and a backend:

| Piece | Needs |
|---|---|
| Event editing | Built. The admin page writes to Cloudflare D1 through Pages Functions in `functions/`, and a deploy hook rebuilds the calendar. Steps in `DEPLOY.md`. |
| Admin dashboard | Built. Reads Cloudflare Web Analytics through `functions/api/analytics.js`: visits by day, by source, by device. RSVP and attendance figures join once sign-ups exist. |
| RSVP submission | Same D1 database, an rsvps table, once resident sign-in exists. |
| Message form | Done for now: posts to `mailto:leonardo@181sf.com` with topic, message, optional name, unit, and email. Becomes a logged inbox once resident sign-in exists. |
| Staff login | Cloudflare Access in front of `admin.html` and `api/*`, one-time email PIN, three addresses. Steps in `DEPLOY.md`. |
| Resident login | Cloudflare Access on the calendar itself, one-time email PIN. Free to 50 users. |
| Payment ($75 dinner) | Stripe, in the building's name rather than a personal account. |
| Analytics | Cloudflare Web Analytics (free, no cookies) or Plausible. Either is a script beacon, so it only counts residents with JavaScript on, which is the honest trade for a no-JS site. Each QR standee links with its own tag, e.g. `181residents.com/?from=lobby`, so scans are attributable. Views, RSVPs, and scans by source feed the monthly report and the admin dashboard. |

RSVP buttons currently show their confirmation state without sending anything. The message button works.

### Nixplay frames

Bar, lobby, and Level 7 are all portrait. Event stills for the frames are 1080 × 1920. The frames accept email at the building's Nixplay address, which is a credential and lives outside this repo.
