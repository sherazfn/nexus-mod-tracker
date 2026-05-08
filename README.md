# Nexus Mod Tracker

Daily snapshots of mod updates on Nexus Mods for:

- Baldur's Gate 3 (`baldursgate3`)
- Clair Obscur: Expedition 33 (`clairobscurexpedition33`)

Live site: https://sherazfn.github.io/nexus-mod-tracker/

## How it works

A scheduled GitHub Action runs daily at 06:37 UTC. It hits the Nexus
`updated.json` endpoint for each game (1-week window), enriches changed
mods with `/mods/{id}.json` and `/files.json`, merges into
`data/{slug}.json`, regenerates `index.html`, commits, and deploys to Pages.

Bootstrap: on the first run for a game (no existing data), the scraper
uses `period=1m` to backfill a month of recent activity.

## Setup

1. Get a Personal API Key at https://www.nexusmods.com/users/myaccount?tab=api+access (bottom of the page)
2. Add it as a repo secret: `NEXUS_API_KEY`
3. Trigger the first run via Actions → "Scrape and Deploy" → "Run workflow"

## Rate limits

Personal keys: 2,500/day, 100/hour. Daily incremental runs are well under
this; the initial bootstrap with `period=1m` is the heaviest run.

## Manual run

```sh
pip install -r requirements.txt
NEXUS_API_KEY=xxxx python -m scripts.scrape
python -m scripts.generate_html
```
