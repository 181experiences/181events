# Putting 181residents.com live

Everything runs on Cloudflare, in the account where the domain is registered. Nothing costs money at this size.
Do these in order. Each step is a few minutes in the dashboard. Never paste a token or key into a file in this folder.

## 1. GitHub, once

1. Create a free account at github.com (yours only; Scott and Leigh-Ann never need it).
2. Create a new **private** repository called `181residents`. Leave it empty.
3. Back on this computer, Claude pushes this folder to it. That is the only time GitHub is touched directly.

## 2. Cloudflare Pages, once

1. Cloudflare dashboard, **Workers & Pages**, **Create**, **Pages**, **Connect to Git**. Choose the `181residents` repository.
2. Build settings:
   - Framework preset: None
   - Build command: `python source/publish.py`
   - Build output directory: `site`
3. Deploy. The first build takes about a minute and uses the events in `events_data.py`, since Airtable is not linked yet.
4. **Custom domains**: add `181residents.com` and `www.181residents.com`. DNS and HTTPS are automatic because the domain lives in the same account.

## 3. Web Analytics, once

Pages project, **Settings**, **Web Analytics**, **Enable**. Cloudflare adds the measurement beacon to every page itself; no cookies, nothing identifying. This is where Scott's traffic numbers come from.

Then, so the admin can read them: **Manage Account**, **Account API Tokens**, **Create Token**, template "Read analytics and logs" (Account Analytics: Read). Copy the token once. The account id is on the right of the Workers & Pages overview page. The site tag is under **Analytics & Logs**, **Web Analytics**, the site, **Manage site**.

## 4. Airtable, once

Follow `airtable/SETUP.md`. You end up with a base id (`app...`) and a personal access token (`pat...`) with read and write on the Events table.
Give the token `data.records:read` and `data.records:write`, since the admin page writes through it.

## 5. Tell Pages the secrets

Pages project, **Settings**, **Environment variables**, Production. Add these, and mark each as a secret:

| Name | Value |
|---|---|
| `AIRTABLE_TOKEN` | the `pat...` token |
| `AIRTABLE_BASE` | the `app...` id |
| `CF_API_TOKEN` | the analytics token from step 3 |
| `CF_ACCOUNT_ID` | the account id |
| `CF_SITE_TAG` | the Web Analytics site tag |
| `DEPLOY_HOOK` | see step 6 |

## 6. The publish button

Pages project, **Settings**, **Builds & deployments**, **Deploy hooks**, **Add deploy hook**, name it `admin-publish`, branch `main`. Copy the URL into the `DEPLOY_HOOK` variable above. Whenever the admin saves a Live event, it calls this URL and Cloudflare rebuilds the calendar from Airtable in about two minutes.

After adding or changing variables, trigger one deploy by hand (**Deployments**, **Retry deployment**) so the Functions pick them up.

## 7. Lock the admin

**Zero Trust**, **Access**, **Applications**, **Add an application**, Self-hosted.
- Application domain: `181residents.com`, path `admin.html`. Add a second path `api/*` on the same application.
- Identity providers: One-time PIN only.
- Policy: Allow, Include, Emails: your address, Scott's, Leigh-Ann's.
- Session duration: 1 month, so the three of you are not asked for a code every morning.

That is the whole login. They type their email, get a six-digit code, and are in. Nothing to remember.

Resident sign-in for the calendar itself comes later, as a second Access application on the root path with the resident email list.

## Day to day

- Edit events in the admin at 181residents.com/admin.html. Saving a Live event publishes by itself.
- Nothing else to run. The build happens on Cloudflare.
- To roll back a bad deploy: Pages project, **Deployments**, pick the previous one, **Rollback**.

## QR standee links

Print these, one per standee, so each scan is counted separately on the dashboard:

| Standee | Link |
|---|---|
| Lobby | `https://181residents.com/q/lobby/` |
| Coffee bar | `https://181residents.com/q/coffee/` |
| Fitness center | `https://181residents.com/q/fitness/` |
| Leo's office | `https://181residents.com/q/office/` |
| Weekly email | `https://181residents.com/q/email/` |

Each one is the full calendar; only the address differs.
