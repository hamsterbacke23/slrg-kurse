# SLRG Kurse

A clean, fast, searchable view of all ~1300 SLRG (Schweizerische Lebensrettungs-Gesellschaft) courses — because [the official Kurskalender](https://ausbildung.slrg.ch/Kurskalender) is painful.

Filter by category, canton, city or provider. Find the courses **closest to you** with the "in der Nähe von …" locality search and a radius slider. Open any card to jump to the official registration page.

## Stack

- **`scrape.py`** — zero-dependency Python scraper (stdlib only). Talks to the site's DWR / Java backend, paginates through every event, writes `courses.json`.
- **`geocode.py`** — enriches each course with `canton` + `lat/lng` via the official Swiss federal geo-search API ([api3.geo.admin.ch](https://api3.geo.admin.ch)). Caches per city in `geocache.json` so re-runs only fetch *new* cities.
- **`index.html`** — single-file Vue 3 + Tailwind webapp with a shadcn-inspired dark UI. No build needed (CDN ESM imports), but ships with a Vite dev server for convenience.

## Quick start

```bash
pnpm install        # only for the dev server
pnpm refresh        # scrape + geocode (smart, cached)
pnpm dev            # http://localhost:5173
```

## Commands

| Command          | What it does                                                    |
| ---------------- | --------------------------------------------------------------- |
| `pnpm scrape`    | Fetch every course from SLRG → `courses.json`                   |
| `pnpm geocode`   | Add `canton` + `lat/lng` to each course (uses `geocache.json`)  |
| `pnpm refresh`   | `scrape` + `geocode` in one go — **the one command you want**   |
| `pnpm dev`       | Start the Vite dev server with the webapp                       |
| `pnpm build`     | Build a static site to `dist/`                                  |
| `pnpm preview`   | Preview the built site                                          |

The geocoder is incremental: existing cities are read from `geocache.json` and skipped, so a refresh only hits the geo API for cities it hasn't seen before. Cities don't move much; `geocache.json` is committed to keep the cache shared.

## Python

`scrape.py` and `geocode.py` need a Python build with the `ssl` module (most do — pyenv builds without OpenSSL do not). The `scripts/run-python.mjs` shim picks the first working Python on your `PATH` (`$PYTHON` → `/opt/homebrew/bin/python3` → `/usr/local/bin/python3` → `python3` → `python`). Override with `PYTHON=/path/to/python pnpm scrape`.

## Fields per course

`key`, `category`, `city`, `canton`, `lat`, `lng`, `first_date`, `last_date`, `company`, `participation_max`, `registered`, `url`

## Deploy

This repo auto-deploys to GitHub Pages via [`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to `main`. The workflow stages `index.html` + `courses.json` and publishes them as the Pages artifact — no build step required.

To enable Pages on a fresh clone:

1. Settings → Pages → Source: **GitHub Actions**.
2. Push to `main`.

## License

MIT. Course data belongs to SLRG.
