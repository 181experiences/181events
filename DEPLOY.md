# Putting 181residents.com live

Everything runs on Cloudflare, in the account where the domain is registered, and nothing costs money at this size.
The only other party is GitHub, a private repository holding code so Cloudflare can build it. No resident data ever
touches GitHub; events live in Cloudflare's own database, fonts are served from the site itself, and traffic is
measured by Cloudflare without cookies.

Do these in order. Each is a few minutes in the dashboard. Never paste a token into a file in this folder.

## 1. GitHub, once

1. Create a free account at github.com (yours only; Scott and Leigh-Ann never need it).
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

## 7. The publish hook

Pages project, **Settings**, **Builds & deployments**, **Deploy hooks**, **Add deploy hook**, name `admin-publish`,
branch `main`. Copy the URL into the `DEPLOY_HOOK` variable above, marked secret. Whenever the admin saves a Live
event, it calls this hook and Cloudflare rebuilds the calendar from the database in about two minutes.

After steps 6 and 7, trigger one deploy by hand (**Deployments**, **Retry deployment**) so the settings take effect.

## 8. Lock the admin

**Zero Trust**, **Access**, **Applications**, **Add an application**, Self-hosted.
- Application domain `181residents.com`, path `admin` (Pages serves the page at /admin); add a second path `api/*` on the same application.
- Identity providers: One-time PIN only.
- Policy: Allow, Include, Emails: your address, Scott's, Leigh-Ann's, Carley-Anne's.
- Session duration: 1 month, so nobody types a code every morning.

They enter their email, get a six-digit code, and are in. Nothing to install, nothing to remember.
Resident sign-in for the calendar itself comes later as a second Access application on the root path.

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

Each is the full calendar; only the address differs.
