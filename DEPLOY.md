# Putting 181residents.com live

Everything runs on Cloudflare, in the account where the domain is registered, and nothing costs money at this size.
The only other party is GitHub, a private repository holding code so Cloudflare can build it. No resident data ever
touches GitHub; events live in Cloudflare's own database, fonts are served from the site itself, and traffic is
measured by Cloudflare without cookies.

Do these in order. Each is a few minutes in the dashboard. Never paste a token into a file in this folder.

## 1. GitHub, once

1. Create a free account at github.com (yours only; Scott and Leigh Anne never need it).
2. Create a new **private** repository called `181residents`. Leave it completely empty.
3. Claude pushes this folder to it from your computer. That is the only time GitHub is touched directly.

## 2. Cloudflare Pages, once

1. Cloudflare dashboard, **Workers & Pages**, **Create**, **Pages**, **Connect to Git**, choose `181residents`.
2. Build settings:
   - Framework preset: None
   - Build command: `python3 source/publish.py`
   - Build output directory: `site`
3. Deploy. The first build uses the calendar in `events_data.py`, since the database is not linked yet.
4. **Custom domains**: add `181residents.com` and `www.181residents.com`. DNS and HTTPS are automatic
   because the domain lives in the same account. The calendar is now live.

## 3. The events database, once

1. **Workers & Pages**, **D1 SQL Database**, **Create database**. Name it `residents-events`. Copy its
   **Database ID** (a long uuid shown on the database page).
2. Back in the Pages project: **Settings**, **Functions** (or **Bindings**), **D1 database bindings**,
   **Add binding**. Variable name exactly `DB`, database `residents-events`.

No tables to create and nothing to import: the first time the admin opens against an empty database it loads
the 85-event opening calendar by itself, from a seed file that ships with every build.

## 4. Web Analytics, once

Pages project, **Settings**, **Web Analytics**, **Enable**. Cloudflare adds its measurement beacon to the pages
itself; no cookies, nothing identifying. This is where the dashboard's traffic numbers come from, and they begin
collecting from this moment, so do this early.

## 5. One API token, once

**Manage Account**, **Account API Tokens**, **Create Token**, Custom token, with two permissions:
- Account, **Account Analytics**, Read
- Account, **D1**, Edit

Copy the token once; it is shown once. You will also want:
- the **Account ID**, shown on the right of the Workers & Pages overview page
- the **Site Tag** from **Analytics & Logs**, **Web Analytics**, the site, **Manage site**
- the **Database ID** from step 3

## 6. Tell Pages the settings

Pages project, **Settings**, **Environment variables**, Production. Add these, marking the token as a secret:

| Name | Value |
|---|---|
| `CF_API_TOKEN` | the token from step 5 (secret) |
| `CF_ACCOUNT_ID` | the account id |
| `CF_SITE_TAG` | the Web Analytics site tag |
| `D1_DATABASE_ID` | the database id |
| `DEPLOY_HOOK` | see step 7 |
| `SESSION_SECRET` | see step 9 (secret) |
| `OWNER_EMAILS` | see step 9 |
| `DESK_EMAILS` | see step 9 |

## 7. The publish hook

Pages project, **Settings**, **Builds & deployments**, **Deploy hooks**, **Add deploy hook**, name `admin-publish`,
branch `main`. Copy the URL into the `DEPLOY_HOOK` variable above, marked secret. Whenever the admin saves a Live
event, it calls this hook and Cloudflare rebuilds the calendar from the database in about two minutes.

After steps 6 and 7, trigger one deploy by hand (**Deployments**, **Retry deployment**) so the settings take effect.

## 8. Lock the admin

**Zero Trust**, **Access**, **Applications**, **Add an application**, Self-hosted.
- Application domain `181residents.com`, path `admin` (Pages serves the page at /admin); add a second path `api/*` on the same application.
- Identity providers: One-time PIN only.
- Policy: Allow, Include, Emails: your address, Scott's, Leigh Anne's, Carley-Ann's.
- Session duration: 1 month, so nobody types a code every morning.

They enter their email, get a six-digit code, and are in. Nothing to install, nothing to remember.
Resident sign-in is NOT Access: residents use personal codes (step 9). Never add an Access
application on the root path; it would put an email wall in front of the public calendar and the
QR standee links.

## 9. Resident sign-in, once

Residents sign in with personal codes: one code per person, grouped by unit, managed on the
admin's **Residents** screen. Three settings switch it on (add them in step 6's table):

1. `SESSION_SECRET`, marked secret: a long random string that signs the month-long session
   cookies. Generate one anywhere (40+ random characters); never reuse another password. Until it
   is set, RSVP buttons, My RSVPs, and the Contact form show a quiet "nearly ready" page.
2. `OWNER_EMAILS`: your addresses, comma separated (leonardo@181sf.com plus your two personal).
   Owners see everything, including the text of resident messages. If this is unset, nobody can
   read message bodies, by design.
3. `DESK_EMAILS`: `concierge@181sf.com`. The desk tier gets the Dashboard, Residents, Spaces,
   Messages (redacted), and full RSVP handling: adding one for a resident who phones or asks in
   passing, editing, cancelling, and promoting from the waitlist. It cannot touch the calendar
   itself. Anyone else the Access lock admits (Scott, Leigh Anne, Carley-Ann) gets full events
   and residents powers, with message bodies redacted.

Then add `concierge@181sf.com` to the "181 admin" Access policy (same application, one more
email), so the front desk can sign in for late-night code rescues: look the person up, Rotate,
read the fresh code over the phone or email it from the desk mailbox.

First population: open Residents, paste the building in bulk (one line per person:
`unit, name, email`), and print the code cards. The Front Desk role account seeds itself with
its own code on first load.

## 10. Asset storage, once

The Assets screen stores each event's final artwork (PDF, PNG, JPG, MP4) so any admin on any
device can download it; a Canva link sits beside each file for edits. Canva links work
immediately; uploads need one binding:

1. Cloudflare dashboard, **R2 Object Storage**, **Create bucket**, name it `residents-assets`.
   Free tier (10 GB) is far more than a season of artwork.
2. Pages project, **Settings**, **Bindings**, add an **R2 bucket** binding named exactly `KIT`,
   pointing at `residents-assets`. Retry the latest deployment so it takes effect.

Uploads cap at about 95 MB per file; keep video masters in Canva and upload the export.

## Calendar feeds, for calendars and machines

- `https://181residents.com/calendar/feed` is the whole resident calendar as a live iCal feed:
  subscribe once in Apple, Google, or Outlook and it maintains itself, cancellations included.
  A "keep the calendar in your pocket" box at the foot of the calendar screen offers it.
- Every resident's My RSVPs page offers a **private feed of just their events** at an
  unguessable address: subscribe once and their calendar carries what they said yes to,
  follows dates when staff move them, and lets go of cancellations. Disabling the person
  quiets their feed.
- Calendar files carry version stamps, so adding a one-time copy again after a change
  updates the entry in place instead of duplicating it.
- **Add to My Calendar leads with the subscription.** On an event page the button opens
  a small panel instead of handing over a file. For an event that takes an RSVP it says
  the RSVP will arrive on its own and that the confirmation shows how; for everything
  else it offers the whole-calendar subscription. The one-time copy (`/ics/...`) stays
  beneath, small, and says it will not update. Outside-guest pages, the Board page and
  the coded pages (/gala, /friendsgiving) keep their one-time links as they were.
- **The confirmation is where a resident subscribes.** After a confirmed RSVP, and on the
  page of any RSVP they hold, a block offers their private RSVP feed once ("Put your RSVPs
  on your calendar"). Template `cal`, rendered by `calBox` in `functions/_resident.js`.
- **Knowing who already follows.** When a calendar app (Google, Outlook, Apple; never a
  browser) fetches a resident's private feed, the feed route stamps `residents.feed_last`
  and `feed_agent`. A stamp inside four days means their calendar is following: the block
  then says "On its way to your calendar" and offers nothing, and My RSVPs says when the
  calendar last checked in (or that it has gone quiet, with what to do). This is the one
  per-resident record about feeds; it is shown only to that resident, never in the admin,
  whose Calendar subscriptions counter stays counts only.
- When a Live event with sign-ups changes date, time, or place, or is cancelled with the
  editor's Cancel button, the admin opens one email BCC'd to everyone signed up, pre-written.
- `https://181residents.com/board/feed` is the same for Board meetings.
- Each event page (`/rsvp/{date}_{slug}`) is the shareable address for one event; the admin's
  **Link** buttons copy it, ready for emails.

## Previewing changes before they go live

Code changes land on the `preview` branch first. Cloudflare Pages builds every push to it
automatically at `https://preview.181events.pages.dev`: same build, not the live domain. When
it looks right, the branch merges to `main` and the same build goes live. Every past
deployment in the Deployments list keeps a permanent address of its own: the build history.

**Previewing the admin** needs the project's preview lock switched on, once: Pages project,
**Settings**, find **Access policy** (sometimes under General), and **Enable** it. That puts
the same one-time-PIN wall in front of every preview address. Cloudflare creates a new
application for it in Zero Trust; open **Zero Trust, Access, Applications**, find the one
named for the Pages project, and set its policy to the same staff emails as "181 admin"
(One-time PIN, one-month session). From then on `https://preview.181events.pages.dev/admin`
works behind that wall. Two cautions: the preview admin reads and writes the SAME database as
the live site (there is only one), so treat it as a place to look, not to save; and without
the preview lock enabled, all locked areas on pages.dev addresses bounce to the live domain,
which is the safe default. The server verifies the Access login token's signature on preview
hosts, so the wall cannot be talked around with forged headers.

## Board meetings and spaces

- **Board meetings** are entered like any event under the category **Board Meeting**. They never
  appear on the resident calendar; they live at `/board`, with per-meeting calendar files and a
  subscription feed at `/board/feed` that carries cancellations to subscribers automatically.
- **Space reservations** are entered on the admin's **Spaces** screen. Residents see only the
  room, date, and hours, marked Reserved, at `/spaces`; the note field stays in the admin.

One data note from the launch database: rows seeded before Aug 24 spell Leigh Anne's name with a
hyphen. Open the Café 181 series in the editor, correct the host and description once with "apply
to every upcoming date" ticked, and the whole series updates.

## Day to day

- Edit events at 181residents.com/admin. Saving a Live event publishes by itself; "Publish calendar" forces it.
- Nothing runs on any office computer. Builds happen on Cloudflare.
- Rollback: Pages project, **Deployments**, pick the previous one, **Rollback**.
- The "Next Event" tile on the resident home page is baked in at build time. A quiet week with no edits can
  leave it stale, so give the deploy hook a nightly nudge: in Cloudflare, **Workers & Pages**, create a Worker
  with a Cron Trigger at `0 10 * * *` (3 AM Pacific) whose only job is `fetch(DEPLOY_HOOK, {method: "POST"})`.
  Claude has the worker script when you get there; skipping this is fine for launch week.

## QR standee links

Print these, one per standee, so each scan is counted separately on the dashboard:

| Standee | Link |
|---|---|
| Lobby | `https://181residents.com/q/lobby/` |
| Coffee bar | `https://181residents.com/q/coffee/` |
| Fitness center | `https://181residents.com/q/fitness/` |
| Leo's office | `https://181residents.com/q/office/` |
| Weekly email | `https://181residents.com/q/email/` |
| Level 39 bar sign | `https://181residents.com/q/bar/` |
| Nixplay screens | `https://181residents.com/q/screens/` |

The bar sign and the Nixplay still are generated by `source/make_qr_signs.py` into `print/`:
a print-ready 8.5 x 11 PDF for the bar, and a 1080 x 1920 portrait still for the frames.

Each is the full calendar; only the address differs.

## RSVP notifications (email to Leo on every RSVP change)

The site itself still sends no resident-facing email; this is one plain-text
note to staff, through Cloudflare's own Email Routing, whenever an RSVP is
made, changed, or cancelled, or an outside guest registers. Five dashboard
steps, all on the 181residents.com account:

1. **181residents.com zone -> Email -> Email Routing -> Get started / Enable.**
   Accept the DNS records it adds (MX and SPF on 181residents.com).
2. **Destination addresses -> Add:** `leonardo@181sf.com`, then click the link
   in the verification email that arrives there. Email Routing will only ever
   deliver to verified destinations, which is the safety of this design.
3. **Workers & Pages -> Create -> Worker**, name it `rsvp-notify`, and paste in
   `workers/rsvp-notify/worker.js` from this repository. Deploy it.
4. On the worker: **Settings -> Bindings -> Add -> Send email**, variable name
   `SEND`, destination address `leonardo@181sf.com`.
5. On the Pages project **181events**: **Settings -> Bindings** (Functions) ->
   **Add -> Service binding**, variable name `NOTIFY`, service `rsvp-notify`,
   then **Retry deployment** so the binding takes.

Test: change any RSVP from the admin; the note should be in Leo's inbox within
a minute. Without the binding the site behaves exactly as before, quietly.
Check-ins and door notes are deliberately quiet; only real changes to a
booking (standing, party size, names) send mail.

## Inventory (Operations tab): the report email and the starting list

The Operations tab's Inventory door emails every submitted count to the
department heads. It rides the same `rsvp-notify` Worker, with two additions
in `workers/rsvp-notify/worker.js`: a `to` list of its own and an HTML body.

1. **Re-paste the Worker.** Workers & Pages -> rsvp-notify -> Edit code, replace
   the whole file with `workers/rsvp-notify/worker.js` from this repository,
   Deploy. Until this is done the old Worker ignores the `to` list and sends
   the report as plain text to the RSVP addresses instead; nothing breaks.
2. **Verify each department head's address** under 181residents.com zone ->
   Email -> Email Routing -> Destination addresses -> Add. Each person clicks
   the link in the verification email once. Email Routing delivers only to
   verified destinations; an unverified address simply never receives the
   report, with no error anywhere.
3. **Add the addresses in the admin**: Operations -> Inventory -> The item
   list -> "Inventory reports go to". Staff and owner tiers only.
4. **Load the starting list** once: Operations -> Inventory -> The item list ->
   "Load the starting list" (shown only while the list is empty). It inserts
   `source/inventory_catalog.json`, after which the list lives in D1 and is
   edited on the site.

The report's From is `reports@181residents.com`; like `rsvps@`, it needs no
mailbox. Test: start a count, type a few numbers, press Submit; the report
should reach every verified recipient within a minute, and the count's card
shows when and to whom it went.

## The Black Book (Services > Black Book)

The front desk's city guide. Three sources, kept apart on purpose so each
can say when it last spoke:

- **The file**: `source/guide_places.json` rides the admin page as inline
  JSON. It is what the weekly check found on each place's own website. Each
  listing carries `auto_updated` (shown as "Information automatically updated
  on"), its `sources`, and `history`, the list of what the system changed and
  when. A change here is a change to the file, a rebuild, and a push.
  `desk_note` is the line the desk reads before quoting a listing; it is never
  emailed or printed.
- **The team**: anyone signed in, the desk included, can Edit a listing. An
  edit is stored in the database table `guide_notes` as `edits`, laid over the
  file field by field (`{ field: { v, base } }`, where `base` is what the file
  said at the time). The team's entry wins. If the weekly check later changes
  that same field in the file, the card shows both readings with Keep ours and
  Take the new one. Mark verified by phone stamps `verified_at` and
  `verified_by` (shown as "Location information last verified on, by").
- **The house**: our connection there (a name, a number, a note), same table.

Every write goes through `PUT /api/guide/<place id>` (actions `edit`,
`verify`, `resolve`, `connection`), `POST /api/guide` (a place added) or
`DELETE /api/guide/<place id>` (a team place removed), and lands in `change_log` with kind
`guide`. A listing's History merges those rows with the file's own `history`,
so it reads as one record: who or System, the date and time, and what changed.

**Places the team adds.** Add a place (beside the count, and offered when a
search finds nothing) opens the same form as Edit, empty. A place needs a name,
an address, and a dot on the map: choose Set on the map and click where it
stands. `POST /api/guide` stores the whole record in the table `guide_added`,
shaped like an entry of the file, with an id that starts `t-`. From then on it
is corrected, verified and connected like any other place; its card reads
"Added by the team on, by" where a file place reads "Information automatically
updated on". The weekly check does not cover it: the team keeps it current
until it is folded into the file. Remove from the book (inside Edit, team
places only) is `DELETE /api/guide/<id>`: the row is stamped, not deleted.

**The dot.** Every place's position is the field `latlon` ("lat,lon"). Move
the dot in Edit is an edit like any other, logged as "the dot was moved". No
address is ever sent to a geocoder; the click on our own drawing is the
position.

**Crowd ratings.** Each file place carries `ratings`: Google's and Yelp's
score and review count, and the date read. They show as one small grey line
on the card and one line in the email and the printout. Only the two sites'
own pages count as a source (Google's results panel or Maps page, Yelp's own
listing); a number from an aggregator is never entered. The team cannot edit
them; the weekly check refreshes them.

Applying a weekly check: copy its `guide_places.proposed.json` over
`source/guide_places.json`, rebuild, commit, and push on the owner's word.

The map is our own drawing, not a map service. `source/guide_map.json` holds
two line drawings (about 1.3 miles around the tower, and the whole city) made
once by `source/make_guide_map.py` from OpenStreetMap street data (credit:
OpenStreetMap contributors, shown under the map). To redraw: fetch the three
Overpass extracts the script's header names, then run it on that folder.
Places are positioned from the `lat` and `lon` in the facts file; distance is
straight-line miles from the tower, and the minutes are labelled estimates.
