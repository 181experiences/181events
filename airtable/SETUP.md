# Airtable as the calendar admin

Airtable holds the events. The site is rebuilt from whatever is marked Published.
Editing a row changes the event; any status other than Live removes it from the calendar. Day to day you will do this from the admin page rather than in Airtable itself.

## One-time setup, about fifteen minutes

1. Create a free account at airtable.com with leonardo@181sf.com.
2. Create a base from scratch. Name it `181 Fremont Resident Experiences`.
3. Rename the first table to `Events`, then use **Import data → CSV file** and choose `events_import.csv` from this folder. Tick "first row is the header". All 85 events land as rows.
4. Set these field types, which the CSV import cannot guess:
   - `Status`: Single select with Draft, Live, Unpublished, Archived
   - `Marquee`, `Counted`, `Moved`: Checkbox
   - `Date`: Date (no time)
   - `Category`: Single select. The six values are Morning Offering, Happy Hour, Community Dinner, Culinary Experience, Enrichment Experience, Signature Event.
   - `RSVP`: Single select with None, Guest count, Seat, Paid seat
   - `Capacity`: Number
   - `Description`: Long text. Paragraphs are separated by a blank line.
   - Everything else stays Single line text.
5. Make a personal access token: account icon → Developer hub → Personal access tokens → Create. Scope `data.records:read`, access limited to this base. Copy it once; it is shown once.
6. The base id is the part of the URL that starts with `app`, for example `appXXXXXXXXXXXXXX`.

## Publishing a change

In PowerShell, in this folder:

    $env:AIRTABLE_TOKEN = "pat..."
    $env:AIRTABLE_BASE  = "app..."
    python source\publish.py

Then drag the `site` folder into Cloudflare Pages as usual. The token lives only in that terminal window; do not paste it into any file here.

## What each column means

| Column | What it does on the site |
|---|---|
| Status | Only Live rows reach the calendar. Draft is never shown, Unpublished is pulled but keeps its RSVPs, Archived is over and kept for reporting |
| Date, Start, End, Start24 | Start24 is the sort key, four digits, 24-hour, e.g. 1730 |
| RSVP | None: no button. Guest count: the "how many of you" picker. Seat: one seat. Paid seat: shows the Price |
| Capacity | Shows "RSVP · 12 places" on the card |
| Series | The "Repeats" line on the event, e.g. Every Tuesday |
| Cutoff | The RSVP-by date shown for workshops |
| Marquee | Featured treatment on the home screen |
| Counted | Whether it counts in the monthly attendance report (Leigh-Ann's café does not) |
| Moved | Shows the "moved this month" note styling |
| Image | A CSS gradient for the card header. Leave blank for the default |
| Slug | Stable id for links and calendar files. Lower case, hyphens, no spaces. Keep it the same across a series |

## Adding a new event

Add a row, fill Date, Title, Category, Start, End, Start24, Slug, set Status to Live, then publish. For a recurring event, duplicate the row and change the date.
